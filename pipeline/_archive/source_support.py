# -*- coding: utf-8 -*-
"""Classify three drawn electrical cases from contact with existing model bodies.

Call apply(M, els) after architecture/extras and the ordinary support pass.
The ordinary pass must count a.sys 'lower' cases as unsupported ('float').
No geometry is changed, no host is created, and no distance allowance is added.
This proves geometric contact, not fixing strength, penetrations, or site work.
"""
import collections
import copy
import hashlib
import json
import math

from shapely.geometry import Point, Polygon, box
from shapely.strtree import STRtree

import support

EPS = 1e-9  # Floating point equality only; there is no support tolerance.
SYSTEMS = {"ltg", "earth", "telephone", "tel"}
VERTICAL_HOSTS = {"A.wall", "S.wall", "S.col"}
BASE_HOSTS = {"A.clad", "A.rail"}
FLOOR_HOSTS = {"A.floor"}


def geometry_hash(g):
    return hashlib.sha256(json.dumps(g, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def footprint(g):
    """True plan footprint, including rotated boxes and polygon holes."""
    k = g[0]
    if k == "b":
        x, y, w, d, angle = g[1:6]
        theta = math.radians(angle)
        c, s = math.cos(theta), math.sin(theta)
        return Polygon([(x + u*c - v*s, y + u*s + v*c)
                        for u, v in [(-w/2, -d/2), (w/2, -d/2),
                                     (w/2, d/2), (-w/2, d/2)]])
    if k == "r":
        return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    if k == "p":
        return Polygon(g[1], g[4] if len(g) > 4 and g[4] else None)
    if k == "cyl":
        # An inscribed circle approximation cannot manufacture an external contact.
        return Point(g[1], g[2]).buffer(g[3], quad_segs=64)
    return None


class Bodies:
    def __init__(self, els, categories):
        self.rows = []
        self.polys = []
        for e in els:
            if e["c"] not in categories:
                continue
            p = footprint(e["g"])
            z0, z1 = support.zr(e["g"])
            if p is None or p.is_empty or not p.is_valid or z0 is None or z1 <= z0:
                continue
            self.rows.append((e, z0, z1))
            self.polys.append(p)
        self.tree = STRtree(self.polys) if self.polys else None

    def contacts(self, p):
        if self.tree is None:
            return
        for index in self.tree.query(p, predicate="intersects"):
            yield self.rows[index], self.polys[index]


def proof(e, p, z0, z1, host, hp, hz0, hz1, method):
    intersection = p.intersection(hp)
    return {
        "method": method,
        "host_id": host["id"], "host_category": host["c"],
        "host_type": host.get("t"), "host_level": host["l"],
        "host_geometry_sha256": geometry_hash(host["g"]),
        "element_geometry_sha256": geometry_hash(e["g"]),
        "element_z_m": [z0, z1], "host_z_m": [hz0, hz1],
        "host_bounds_cm": list(hp.bounds),
        "xy_gap_cm": p.distance(hp),
        "xy_intersection_area_cm2": intersection.area,
        "xy_intersection_length_cm": intersection.length,
        "overlap_z_m": [max(z0, hz0), min(z1, hz1)],
    }


def apply(M, els=None):
    """Clear only proven false unsupported flags, record hosts, and return the changes.

    A floor box must fit completely in an actual floor volume. A vertical tape
    must contact a wall/column through a positive height interval. An air rod's
    actual bottom must equal a cladding/rail top at an overlapping plan position.
    Earth rods and pits are excluded: a concrete penetration is not a soil host.
    """
    els = M["els"] if els is None else els
    ordinary = support.Support(els, M["levels"])
    walls = Bodies(els, VERTICAL_HOSTS)
    bases = Bodies(els, BASE_HOSTS)
    floors = Bodies(els, FLOOR_HOSTS)
    meta = M.setdefault("meta", {})
    saved = {q["id"]: q for q in meta.get("source_support", {}).get("changes", [])}
    changes = []
    delta = collections.Counter()

    for i, e in enumerate(els):
        a = e.get("a") or {}
        if a.get("sys") not in SYSTEMS:
            continue
        t = e.get("t")
        if t not in ("elr_down", "elr_air_terminal", "elr_floorbox"):
            continue
        p = footprint(e["g"])
        z0, z1 = support.zr(e["g"])
        if p is None or not p.is_valid or z0 is None or z1 <= z0:
            continue
        proofs = []
        if t == "elr_down" and a["sys"] == "ltg":
            new_kind, method = "ok", "vertical_tape_wall_column_contact"
            for (h, hz0, hz1), hp in walls.contacts(p):
                overlap = min(z1, hz1) - max(z0, hz0)
                section = p.intersection(hp)
                if overlap > EPS and (section.area > EPS or section.length > EPS):
                    proofs.append(proof(e, p, z0, z1, h, hp, hz0, hz1, method))
        elif t == "elr_air_terminal" and a["sys"] == "ltg":
            new_kind, method = "ok", "air_terminal_base_on_existing_parapet_top"
            for (h, hz0, hz1), hp in bases.contacts(p):
                if abs(z0 - hz1) <= EPS and p.intersection(hp).area > EPS:
                    proofs.append(proof(e, p, z0, z1, h, hp, hz0, hz1, method))
        elif t == "elr_floorbox" and a["sys"] in ("telephone", "tel"):
            new_kind, method = "buried", "floorbox_contained_in_existing_floor_volume"
            for (h, hz0, hz1), hp in floors.contacts(p):
                if hz0 <= z0 + EPS and z1 <= hz1 + EPS and hp.covers(p):
                    proofs.append(proof(e, p, z0, z1, h, hp, hz0, hz1, method))
        if not proofs:
            previous = a.get("source_support")
            if previous and previous.get("status") == "existing_body_contact":
                # A changed/removed host invalidates the earlier proof; never retain a stale override.
                ordinary_kind = ordinary.analyse(i)
                new = {"kind": ordinary_kind["kind"], "proofs": [],
                       "status": "proof_invalidated_missing_current_contact"}
                record = {"id": e["id"], "type": t, "system": a["sys"], "level": e["l"],
                          "source_page": a.get("source_page"), "source_xy": copy.deepcopy(a.get("source_xy")),
                          "old": copy.deepcopy(previous), "new": new,
                          "geometry_preserved": True, "geometry_sha256": geometry_hash(e["g"]),
                          "old_counter_kind": previous["kind"],
                          "new_counter_kind": "float" if ordinary_kind["kind"] == "lower" else ordinary_kind["kind"]}
                a.pop("source_support", None)
                if previous["kind"] == "buried":
                    a.pop("buried", None)
                if ordinary_kind["kind"] in ("float", "lower"):
                    a["unsupported"] = 1
                else:
                    a.pop("unsupported", None)
                a["mount_note"] = "دليل التلامس السابق لم يعد قائمًا مع جسم موجود؛ يلزم مراجعة السند مع حفظ الموضع"
                e["a"] = a
                changes.append(record)
                saved[e["id"]] = record
                delta[previous["kind"]] -= 1
                delta[record["new_counter_kind"]] += 1
            continue
        proofs.sort(key=lambda q: q["host_id"])
        new = {"kind": new_kind, "proofs": proofs, "status": "existing_body_contact"}
        # A second invocation is inert; a rebuilt element loses this marker and is rechecked.
        if not a.get("unsupported") and a.get("source_support") == new:
            continue
        old = ordinary.analyse(i)
        if old["kind"] not in ("float", "lower") and not a.get("unsupported"):
            continue
        geometry_before = geometry_hash(e["g"])
        record = {"id": e["id"], "type": t, "system": a["sys"], "level": e["l"],
                  "source_page": a.get("source_page"), "source_xy": copy.deepcopy(a.get("source_xy")),
                  "old": copy.deepcopy(old), "new": copy.deepcopy(new),
                  "geometry_preserved": True, "geometry_sha256": geometry_before,
                  "old_counter_kind": "float" if old["kind"] == "lower" else old["kind"],
                  "new_counter_kind": new_kind}
        a.pop("unsupported", None)
        a["source_support"] = new
        if new_kind == "buried":
            a["buried"] = 1
            a["mount_note"] = "الصندوق الأرضي بكامل حجمه داخل طبقة أرضية موجودة في المجسم؛ الموضع محفوظ، وأبعاد الصندوق افتراض معلن"
        elif t == "elr_air_terminal":
            a["mount_note"] = "قاعدة قضيب الالتقاط تلامس قمة دروة موجودة عند المنسوب نفسه؛ الموضع محفوظ، وتفصيل تثبيت القاعدة بانتظار التأكيد"
        else:
            a["mount_note"] = "شريط النحاس النازل يلامس جسم جدار أو عمود موجود خلال ارتفاع موجب؛ الموضع محفوظ، وتفصيل مشابك التثبيت بانتظار التأكيد"
        e["a"] = a
        assert geometry_hash(e["g"]) == geometry_before
        changes.append(record)
        saved[e["id"]] = record
        delta[record["old_counter_kind"]] -= 1
        delta[new_kind] += 1

    # These are the ordinary pass's recorded buckets, before this narrow correction.
    counters = meta.get("support")
    counters_updated = bool(changes and isinstance(counters, dict) and
                            all(isinstance(counters.get(k, 0), (int, float)) and
                                counters.get(k, 0) + n >= 0 for k, n in delta.items()))
    if counters_updated:
        for k, n in delta.items():
            counters[k] = counters.get(k, 0) + n
    if changes:
        meta["source_support"] = {
            "changes": [saved[k] for k in sorted(saved)],
            "count": len(saved),
            "active_count": sum(q["new"].get("status") == "existing_body_contact" for q in saved.values()),
            "last_counter_delta": dict(delta),
            "support_counters_updated": counters_updated,
            "counter_method": "network lower counted as float; raw diagnosis retained in old.kind",
            "scope": "contact classification only; geometry and tolerances unchanged",
        }
    return changes
