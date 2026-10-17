"""Regression cases: real hole, boundary contact, positive intersection, open mesh."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
from completion_coordination import audit


def element(eid, g):
    return {'id': eid, 'c': 'A.door', 'l': 'G', 'g': g}


def run():
    wall = element('wall', ['p', [[0, 0], [100, 0], [100, 100], [0, 100]], 0, 3,
                            [[[25, 25], [75, 25], [75, 75], [25, 75]]]])
    opening = element('opening', ['r', 30, 30, 70, 70, 0, 2])
    contact = element('contact', ['r', 100, 0, 120, 20, 0, 2])
    crossing = element('crossing', ['b', 0, 50, 30, 30, 45, 0, 2])
    surface = element('surface', ['mesh', [[10, 10, 0], [20, 10, 1], [10, 20, 0]], [[0, 1, 2]]])
    M = {'els': [wall, opening, contact, crossing, surface], 'clashes': []}
    r = audit(M, ['wall'])
    assert len(r['rows']) == 1 and {r['rows'][0]['ea'], r['rows'][0]['eb']} == {'wall', 'crossing'}
    assert r['unsupported_geometry_counts'] == {'mesh': 1}
    assert r['target_count'] == r['supported_targets'] == 1
    assert r['negative_result_is_complete_clearance'] is False
    print(json.dumps({'pass': True, 'cases': ['polygon_hole', 'zero_volume_contact', 'rotated_solid_crossing', 'open_mesh_excluded']}, ensure_ascii=False))


if __name__ == '__main__':
    run()
