"""Normalize six touching-hole slab encodings without changing their domain.

This is a bounded representation repair, not original-PDF source acceptance.
No hole, height, point position, material, type or structural design is added.
The raft has a different invalidity and is deliberately outside this repair.
"""
import copy
import hashlib
import json
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union

DATA_PATH = Path(__file__).with_name('data') / 'structural_topology_repairs.json'


def apply(M, els=None):
    els = M['els'] if els is None else els
    data = json.loads(DATA_PATH.read_text())
    index = {e['id']: e for e in els}
    changed = []
    for eid, row in data['records'].items():
        e = index[eid]
        assert (e['c'], e['t'], e['l']) == (row['category'], row['type'], row['level']), eid
        assert e['g'] in (row['before_g'], row['after_g']), ('Topology identity changed', eid)
        old, new = row['before_g'], row['after_g']
        outer = Polygon(old[1])
        holes = [Polygon(h) for h in old[4]]
        assert outer.is_valid and all(p.is_valid for p in holes), eid
        domain = outer.difference(unary_union(holes))
        result = Polygon(new[1], new[4])
        assert result.is_valid and result.equals(domain), eid
        assert result.area == Polygon(old[1], old[4]).area, eid
        assert old[2:4] == new[2:4], eid
        if e['g'] != new:
            changed.append(eid)
            e['g'] = copy.deepcopy(new)
        e.setdefault('a', {}).update(
            topology_repair='touching_hole_to_exterior_notch',
            topology_repair_record=eid,
            topology_domain_preserved=True,
            topology_source_placement_verified=False,
            topology_repair_note='فتحة الدرج التي تلامس الحد الخارجي أصبحت تجويفًا في المحيط بدل حلقة ثقب غير صالحة. المساحة والمجال البولياني والمناسيب والحدود محفوظة؛ لا فتحة جديدة أو اعتماد للمصدر القديم.')
    summary = {'records': list(data['records']), 'count': data['count'],
               'changed_this_run': changed, 'all_defined_domains_preserved': True,
               'holes_added': 0, 'coordinates_moved': 0, 'Z_unchanged': True,
               'source_authority_limit_ar': data['source_authority_limit_ar'],
               'data_sha256': hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()}
    M.setdefault('meta', {})['structural_topology_repairs'] = summary
    return summary
