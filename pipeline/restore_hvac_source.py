"""Restore HVAC graphic anchors from the supplied PDF, without choosing a host.

The thermostat circle locates the plan glyph. It does not dimension the physical
device or its mounting face. FCU-R-LR supplies a quad anchor and plan angle; the
model body dimensions and elevations remain explicit display assumptions.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

DATA_PATH = Path(__file__).with_name("data") / "restore_hvac_source.json"
TYPES = {}


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def apply(M, els=None):
    """Change only the 107 named anchors (and the one drawn FCU angle)."""
    els = M["els"] if els is None else els
    D = json.loads(DATA_PATH.read_text())
    changes, missing, mismatched = [], [], []
    by_id = {e["id"]: e for e in els}
    legacy_keys = ("snap_cm", "snap_note", "guess_from", "guess_host", "guess_kind",
                   "guess_cm", "guess_dz_cm", "guess_conf", "guess_intent", "guess_conv")
    for eid, row in D["records"].items():
        e = by_id.get(eid)
        if e is None:
            missing.append(eid)
            continue
        if (e.get("t"), e.get("c"), e.get("l"), e["g"][0]) != (
                row["type"], row["category"], row["level"], "b"):
            mismatched.append(eid)
            continue
        source = row["source"]
        before = copy.deepcopy(e["g"])
        g = e["g"]
        g[1], g[2] = [round(v, 4) for v in source["source_xy"]]
        is_fcu = row["type"] == "fcu"
        if is_fcu:
            g[5] = round(source["source_angle"], 4)
        a = e.setdefault("a", {})
        for key in legacy_keys:
            a.pop(key, None)
        a.update({
            "sys": row["system"], "source_locked_xy": True,
            "source_page": source["source_page"],
            "source_sheet": source["source_sheet"],
            "source_kind": source["source_kind"],
            "source_pdf_sha256": source["source_pdf_sha256"],
            "source_layer": source["source_layer"],
            "source_drawing_indices": source["source_drawing_indices"],
            "source_poly_index": source["source_poly_index"],
            "source_pdf_points": copy.deepcopy(source["source_pdf_points"]),
            "source_transform": copy.deepcopy(source["source_transform"]),
            "source_xy": copy.deepcopy(source["source_xy"]),
            "source_semantic_text": copy.deepcopy(source["source_text"]),
            "source_semantics_checked": True, "source_class_semantics_checked": True,
            "source_rotation_verified": is_fcu,
            "source_rotation_deg": source["source_angle"],
            "source_dimensions_verified": False, "source_Z_verified": False,
            "source_material_verified": False, "source_mount_face_verified": False,
            "source_height_assumed": True, "source_body_dimensions_assumed": True,
            "source_geometry_role": "proxy_body_at_source_graphic_anchor",
            "source_mount_pending": True,
            "hvac_source_record": eid, "hvac_source_record_sha256": _sha(row),
            "hvac_previous_placement": {
                "audit_before_g": copy.deepcopy(row["before_g"]),
                "legacy_snap_cm": row.get("legacy_snap_cm"),
                "legacy_guess_from": copy.deepcopy(row.get("legacy_guess_from")),
                "legacy_guess_host": row.get("legacy_guess_host"),
                "audit_delta_cm": copy.deepcopy(row["source_xy_delta_from_audited_model_cm"]),
            },
            "mount_note": "موضع جسم العرض عند رمز المسقط الأصلي؛ وجه التثبيت والارتفاع والمقاس التنفيذي غير مثبتة. لا نقل إلى أقرب مضيف.",
            "assumed": ("جسم عرض مؤقت عند مركز رمز " + ("FCU-R-LR" if is_fcu else "T") +
                        "؛ دائرة T لا تعطي اتجاهًا أو مقاس جهاز، ومستطيل FCU يثبت زاوية رمز المسقط فقط. "
                        "أبعاد الجسم الحالية ومنسوباه والمادة واللون الحقيقي وتفصيل التثبيت تبقى افتراضات معلنة؛ لم تتغير Z أو الأبعاد أو المادة."),
        })
        if is_fcu:
            a["source_registration_limit"] = source["source_registration_proof"]["limit"]
        elif source["source_page"] == "MECH1:6":
            a["source_registration_limit"] = source["source_registration_proof"]["limit"]
        if before != g:
            changes.append({"id": eid, "before_g": before, "after_g": copy.deepcopy(g),
                            "delta_xy_cm": [round(g[i+1]-before[i+1], 4) for i in (0, 1)],
                            "distance_cm": round(math.hypot(g[1]-before[1], g[2]-before[2]), 4)})
    stats = {**D["summary"], "active_count": len(D["records"])-len(missing)-len(mismatched),
             "last_geometry_changed": len(changes), "missing": missing,
             "identity_mismatches": mismatched,
             "data_sha256": hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
             "source_limit_ar": D["source_limit_ar"],
             "external_report": "pipeline/data/restore_hvac_source.json"}
    M.setdefault("meta", {})["hvac_source_restore"] = stats
    return {**stats, "changes": changes}
