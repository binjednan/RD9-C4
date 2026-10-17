# -*- coding: utf-8 -*-
"""Saved geometry encoding/validity gate. This is not a drawing approval."""
import json
import math
from pathlib import Path
from shapely.geometry import Polygon
from shapely.validation import explain_validity


def audit(M):
    findings = []
    polygon_count = 0
    mesh_count = 0
    ids = set()
    for e in M['els']:
        eid = e['id']
        if eid in ids:
            findings.append({'id': eid, 'kind': 'duplicate_id'})
        ids.add(eid)
        g = e.get('g')
        def finite(v):
            if isinstance(v, (int, float)):
                return math.isfinite(v)
            if isinstance(v, list):
                return all(finite(x) for x in v)
            return v is None or isinstance(v, str)
        if not isinstance(g, list) or not g or not finite(g):
            findings.append({'id': eid, 'kind': 'malformed_or_nonfinite_geometry'})
            continue
        if g[0] == 'mesh':
            mesh_count += 1
            try:
                vertices, faces = g[1:3]
                assert vertices and faces
                assert all(isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v) for v in vertices)
                for face in faces:
                    assert len(face) == 3 and len(set(face)) == 3
                    assert all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(vertices) for i in face)
                    # Use one unit system for the area test: XY cm, Z m.
                    a, b, c = ([vertices[i][0], vertices[i][1], vertices[i][2] * 100] for i in face)
                    u, v = ([b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)])
                    cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
                    assert sum(x*x for x in cross) > 0
            except (AssertionError, TypeError, ValueError, IndexError) as er:
                findings.append({'id': eid, 'kind': 'malformed_or_degenerate_triangle_mesh', 'reason': str(er)})
            continue
        if g[0] != 'p':
            continue
        polygon_count += 1
        try:
            p = Polygon(g[1], g[4] if len(g) > 4 and g[4] else [])
            if not p.is_valid:
                findings.append({'id': eid, 'kind': 'invalid_polygon', 'reason': explain_validity(p)})
            if p.is_empty or p.area <= 0:
                findings.append({'id': eid, 'kind': 'nonpositive_polygon_area'})
            if g[3] < g[2]:
                findings.append({'id': eid, 'kind': 'inverted_polygon_z'})
        except (TypeError, ValueError, IndexError) as er:
            findings.append({'id': eid, 'kind': 'malformed_polygon_encoding', 'reason': str(er)})
    return {'schema': 'saved-geometry-integrity-v1', 'elements_checked': len(M['els']),
            'polygon_prisms_checked': polygon_count, 'findings': findings,
            'triangle_meshes_checked': mesh_count,
            'pass': not findings, 'source_geometry_acceptance': False,
            'limit_ar': 'صلاحية الترميز والمضلعات والأرقام والمعرفات فقط؛ لا تثبت مطابقة المخطط أو المنسوب أو التنفيذ.'}


if __name__ == '__main__':
    model = Path(__file__).resolve().parents[1] / 'src' / 'model.json'
    result = audit(json.loads(model.read_text(encoding='utf-8')))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['pass'] else 1)
