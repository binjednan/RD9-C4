# -*- coding: utf-8 -*-
"""Post-process src/model.json (no PDFs needed): adds data that is derivable from what is already in the model
and from the pure-data knowledge-base modules.

  python3 pipeline/post_model.py            # reads the frozen pipeline/data/baseline/model.base.json, writes src/model.json (pure output)

Adds / replaces these keys:
  types      asset-type cards: doors/windows (kb.py) and electrical device classes (kb_elec.py); every field is
             taken from those modules, assumptions are kept apart in 'asm' and the card is marked 'derived'.
  fin, finq  finish schedule A500 (finishes.py) + model-derived areas for floor/ceiling codes (BOQ reconciliation)
  ral        paint-system table supplied by the client (RAL.xlsx) — RAL values are NOT defined there ("RAL xxxx"),
             conflicts with the A500 extraction are flagged, never resolved.
  clashes    geometric clash candidates (MEP vs structure, duct vs pipe) computed from element geometry.
             MEP elevations above the ceiling are assumptions (see element cards), so these are candidates only.
Nothing here is invented: whatever is not in the documents stays out or is explicitly flagged.
"""
import json, os, sys, collections, math, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kb, kb_elec, finishes
from shapely.geometry import Polygon, LineString, Point, box
from shapely.affinity import rotate as shp_rotate
from shapely.strtree import STRtree

SRC = os.path.join(os.path.dirname(HERE), "src", "model.json")
# The X sequence uses a minimum of four digits; it may grow beyond 9999.
# Parse the full sequence so later rebuilds retire/reuse every accessory once.
X_SUFFIX = re.compile(r"-X(\d{4,})$")
import freeze_baseline as _FB
_FB.verify()  # fail-closed: input is the frozen, hash-verified baseline; src/model.json is output only
M = json.load(open(_FB.BASE, encoding="utf-8"))
# Owner drawing-only mode keeps the current base shapes and all legacy analyses.
# Regenerate only literal source alternatives; none enter correction engines.
if M.get('meta',{}).get('owner_render_only'):
    import source_drawings_delivery as _DRAW
    from source_batch import remap_index_refs as _remap_source_indices
    _before_ids=[e['id'] for e in M['els']]
    M['els'][:]=[e for e in M['els'] if not e.get('a',{}).get('alt') and not e['id'].endswith('-ALT')]
    M['_source_index_remap_pending']=True
    try:
        summary=_DRAW.apply(M)
    finally:
        M.pop('_source_index_remap_pending',None)
    _DRAW.display_only(M)
    _after_index={e['id']: i for i,e in enumerate(M['els'])}
    _remap_source_indices(M,{i:_after_index[eid] for i,eid in enumerate(_before_ids) if eid in _after_index},
                          [i for i,eid in enumerate(_before_ids) if eid not in _after_index])
    import generated_layer as _GEN
    _GEN.apply(M)   # assemblies generated from drawing samples (pipeline/data/generated); never part of the frozen baseline
    import pipe_dimensions as _PD
    _PDR=_PD.apply(M)   # standards-based pipe diameters (axes untouched)
    import window_sections as _WS
    _WS.apply(M)   # frame sections from A803 / A1502 (centre planes unchanged)
    import decisions as _DEC
    _DEC.apply(M, force_lifecycle=bool(_PDR['diameter_changed']))   # owner decisions (pipeline/data/decisions): applied after all layers, rollback = delete the file
    import progress as _PROG
    _PROG.apply(M)   # progress log shown in the viewer (docs/RESUME_STATE.md)
    # Recompute opt-in route results after loading proposal data. The original
    # drawing-only results and their populations remain separate and unchanged.
    if any(e.get('a', {}).get('network_proposal') for e in M['els']):
        import lifecycle as _PROPOSED_LIFECYCLE
        _PROPOSED_LIFECYCLE.add_proposals(M)
    with open(SRC+'.tmp','w',encoding='utf-8') as _output:
        json.dump(M,_output,ensure_ascii=False,separators=(',',':'))
    os.replace(SRC+'.tmp',SRC)
    print('Source drawings written')
    sys.exit(0)
raise SystemExit("post_model: legacy chain archived in _archive/post_model_legacy.py; only owner_render_only is supported")
