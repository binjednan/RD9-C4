# -*- coding: utf-8 -*-
"""Independent XY gate for drawn networks (Z assumptions are reported separately).

Run: python3 tools/check_drawn_positions.py [--model PATH] [--output PATH]
Exit 1: source/geometry deviation exceeds 0.2 cm, or a network has guess_from.
The JSON report includes every checked, derived, and uncovered element. Coverage
is never promoted to a pass for elements lacking an identifiable drawing anchor.
This reads extraction JSON and PDF-coordinate metadata; it does not rebuild the
model or call its generators. Legacy derived connectors and explicitly recorded
ventilation break bridges are reported as derived, outside exact-position claims.
ARF finishes derived from existing model footprints are listed separately as
explicit scope exclusions; their plan geometry has no independent piece anchor.
Position proof measures X/Y. Pile length and diameter are separately checked
against explicit source literals; their top elevation remains unverified.
Assumed heights and dimensions do not become exact proof.
"""
import argparse, collections, functools, hashlib, json, math, os, re, sys
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA=os.path.join(ROOT,'pipeline','data')
SUFFIX=re.compile(r'-(VT|SM|ST|FP|WS|ELR|SG|AD|PG|DTR|DRG|DSM|DCO|ES|ETR|GC|SRF|LHS|WSC|WST|WMT|VSC|D16|BND)\d{4}$|-((?:ALT))$')
TOL=.2
LEGACY_REVIEW={'M.pipe-R-S0029','M.pipe-R-S0135','P.ff-B-M0138','P.ff-B-M0148','P.ff-R-M0007'}

def read(name):
    p=os.path.join(DATA,name+'.json')
    if not os.path.exists(p):return {}
    stat=os.stat(p)
    return _read_revision(p,stat.st_mtime_ns,stat.st_size)

@functools.lru_cache(maxsize=48)
def _read_revision(path,mtime_ns,size):
    # Versioned reads keep a source fresh if another builder updates its data.
    # The returned dictionaries are audit inputs only and are never mutated.
    with open(path,encoding='utf-8')as f:return json.load(f)

def centre(g):
    if g[0] in ('b','cyl','sph'):return [g[1],g[2]]
    if g[0]=='r':return [(g[1]+g[3])/2,(g[2]+g[4])/2]
    if g[0] in ('t','d','rs','tri'):return boxcentre([p[:2] for p in g[1]])
    if g[0]=='p':return boxcentre(g[1])
    return None

def boxcentre(points):
    return [(min(p[k] for p in points)+max(p[k] for p in points))/2 for k in (0,1)]

def flat(p):return isinstance(p,(list,tuple)) and len(p)>=2 and isinstance(p[0],(int,float))
def points(p):return [p[:2]] if flat(p) else [q[:2] for q in p]
def line(p):
    p=points(p)
    # Raw CAD chains may repeat the join vertex between independent line
    # items. Remove exact adjacent duplicates only in this temporary distance
    # geometry; preserve every original PDF/metadata point for source checks.
    p=[q for i,q in enumerate(p) if not i or q!=p[i-1]]
    return Point(p[0]) if all(math.dist(p[0],q)<1e-8 for q in p) else LineString(p)
def deviation(e,p,mode='point'):
    if mode=='point':return math.dist(centre(e['g']),points(p)[0])
    if mode=='path':return line([q[:2] for q in e['g'][1]]).hausdorff_distance(line(p))
    if mode=='linework':return max(Point(q[:2]).distance(p) for q in e['g'][1])
    if mode=='face':
        g=e['g'];return math.dist([g[1]+g[3]/2,g[2]],p)
    if mode=='beam_path':
        g=e['g'];angle=math.radians(g[5]);dx=g[3]/2*math.cos(angle);dy=g[3]/2*math.sin(angle)
        return line([[g[1]-dx,g[2]-dy],[g[1]+dx,g[2]+dy]]).hausdorff_distance(line(p))
    raise ValueError(mode)

def source_transform(p,tr):return [[q[0]*tr['s']+tr['ox'],-q[1]*tr['s']+tr['oy']] for q in points(p)]

def pdf_sheet(book,page):
    registry=os.path.join(DATA,'reg_verified.json')
    stat=os.stat(registry) if os.path.exists(registry) else None
    return _pdf_sheet_revision(book,page,stat.st_mtime_ns if stat else None,stat.st_size if stat else None)

@functools.lru_cache(maxsize=48)
def _pdf_sheet_revision(book,page,registry_mtime_ns,registry_size):
    sys.path.insert(0,os.path.join(ROOT,'pipeline'))
    import lib
    return lib.Sheet(book,page)

def pdf_drawing_points(book,page,indices):
    sh=pdf_sheet(book,page)
    return [[x,y] for i in indices for p in sh.D[i]['polys'] for x,y in p]

def fire_centreline_check(e):
    """Compare a single FFC axis with the midpoint of two actual PDF faces.

    Face metadata is a pair of paths, so it must not be read as a single route.
    The independent PDF paths prove each face before deriving their midpoint.
    """
    a=e.get('a') or {};D=read('fire_source_corrections').get('ffc_ground',{})
    if e['id']!=D.get('keep_id') or a.get('source_kind')!='centreline_from_two_pipe_faces':return None
    sh=pdf_sheet('MECH2',11);indices=D.get('source_drawing_indices',[])
    if len(indices)!=2 or a.get('source_drawing_indices')!=indices:return None
    raw=[]
    for di in indices:
        d=sh.D[di]
        if d['layer']!='M_FF_FFC' or d.get('fill') or len(d['polys'])!=1 or len(d['polys'][0])!=3:return None
        raw.append(d['polys'][0])
    saved=a.get('source_pdf_points');xy=a.get('source_xy');tr=a.get('source_transform')
    if not saved or not xy or not tr or len(saved)!=2 or len(xy)!=2:return None
    world=[source_transform(p,sh.reg) for p in raw]
    midpoint=[[sum(q[k] for q in pair)/2 for k in (0,1)] for pair in zip(*world)]
    anchor=max(line(saved[i]).hausdorff_distance(line(raw[i]))*sh.reg['s'] for i in range(2))
    anchor=max(anchor,max(line(D['source_pdf_points'][i]).hausdorff_distance(line(raw[i]))*sh.reg['s'] for i in range(2)))
    metadata=max(line(xy[i]).hausdorff_distance(line(world[i])) for i in range(2))
    metadata=max(metadata,line(D['centreline_xy_cm']).hausdorff_distance(line(midpoint)))
    transform=max(math.dist(p,q) for i in range(2) for p,q in zip(source_transform(raw[i],tr),world[i]))
    return {'method':'Original MECH2:11 two 6-inch FFC pipe faces; complete route midpoint',
            'deviation_cm':deviation(e,midpoint,'path'),'metadata_deviation_cm':metadata,
            'source_anchor_deviation_cm':anchor,'source_transform_deviation_cm':transform,
            'reference':'MECH2:11 / FF-101','source_xy':midpoint,
            'spatial_basis':'Centreline derived independently from two drawn pipe faces; Z remains assumed'}

def electrical_legacy_anchors():return read('electrical_source_restore').get('source_anchors',{})

@functools.lru_cache(maxsize=3)
def lift_original_page(book,page):
    import lib
    return lib.doc(book)[page-1].get_drawings()

def lift_head_wall_check(e):
    """Two complete closed structural plan profiles; Z remains datum derived."""
    q=read('lift_head_supports').get('records',{}).get(e['id']);a=e.get('a')or{}
    if not q or a.get('source_kind')!='closed_structural_wall_outline' or e['g'][0]!='p':return None
    source=q['source'];book,page=source['source_page'].split(':');page=int(page)
    if book!='STR' or page!=23 or a.get('source_page')!=source['source_page']or a.get('source_drawing_indices')!=source['source_drawing_indices']:return None
    sh=pdf_sheet(book,page);drawing=lift_original_page(book,page)[source['source_drawing_indices'][0]]
    import lib
    paths=lib.flat_path(drawing)
    if len(paths)!=1 or drawing.get('layer')!='S-COL-HATCH' or a.get('source_layer')!='S-COL-HATCH':return None
    raw=paths[0]
    if math.dist(raw[0],raw[-1])>.001:return None
    polygon=Polygon(raw)
    if not polygon.is_valid or polygon.area<=0:return None
    world=source_transform(raw,sh.reg);saved=a.get('source_pdf_points');tr=a.get('source_transform');meta=a.get('source_xy')
    if not saved or not meta or not tr:return None
    return {'method':'Original STR:23 complete closed S-COL-HATCH wall profile',
            'deviation_cm':Polygon(e['g'][1],e['g'][4]).hausdorff_distance(Polygon(world)),
            'metadata_deviation_cm':max(Polygon(meta).hausdorff_distance(Polygon(world)),Polygon(source['source_xy']).hausdorff_distance(Polygon(world))),
            'source_anchor_deviation_cm':max(Polygon(saved).hausdorff_distance(polygon),Polygon(source['source_pdf_points']).hausdorff_distance(polygon))*sh.reg['s'],
            'source_transform_deviation_cm':max(math.dist(p,v)for p,v in zip(source_transform(raw,tr),world)),
            'reference':source['source_page'],'source_xy':world,
            'spatial_basis':'Exact closed plan profile only; top/bottom are derived from concrete datums, bearing/rebar are unverified'}

def lift_architectural_boundary_checks(M,tolerance):
    """Check five derived SRF pieces against raw A105 outer/inner edges.

    They remain derived architectural footprints. The enclosing architectural
    rectangle is not promoted to an independently closed structural slab.
    """
    elements=[e for e in M['els']if re.search(r'-SRF\d{4}$',e['id'])]
    if not elements:return []
    P=read('roof_lift_source').get('sources',{}).get('architectural_plan',{})
    checks=[];sh=pdf_sheet('ARCH1',8);drawings=lift_original_page('ARCH1',8)
    import lib
    indices=P.get('source_drawing_indices',[])
    if indices!=[4459,4461,4460,4462,4463]:return [{'id':'SRF-source','pass':False,'reason':'Missing or changed source boundary primitives'}]
    paths={di:[p for poly in lib.flat_path(drawings[di])for p in poly]for di in indices}
    expected_layers={4459:'ELE 4',4461:'A-WALL',4460:'ELE 4',4462:'ELE 4',4463:'ELE 4'}
    if any(drawings[di].get('layer')!=expected_layers[di]or drawings[di].get('layer')not in P['source_layer']for di in indices):return [{'id':'SRF-source','pass':False,'reason':'Original architectural boundary layer mismatch'}]
    raw_source_error=max(line(saved).hausdorff_distance(line(paths[di]))for di,saved in zip(indices,P['source_pdf_points']))*sh.reg['s']
    x0=min(p[0]for p in paths[4459]);x1=max(p[0]for p in paths[4459]);y0=min(p[1]for p in paths[4459]);y1=max(p[1]for p in paths[4459])
    ix0=paths[4463][0][0];iy0=paths[4460][0][1];iy1=paths[4462][0][1]
    outer_pdf=[[x0,y1],[x1,y1],[x1,y0],[x0,y0]];inner_pdf=[[ix0,iy1],[x1,iy1],[x1,iy0],[ix0,iy0]]
    raw_edges=unary_union([line(lib.flat_path(drawings[di])[pi])for di in indices for pi in range(len(lib.flat_path(drawings[di])))])
    # Boundary lines have full source support, including the actual east line.
    # Intersections can retain empty geometry members, whose Hausdorff
    # distance is NaN. Measure complete unbacked boundary length directly;
    # a missing closure cannot pass through max(..., NaN) arithmetic.
    boundary_error=max(Polygon(p).exterior.difference(raw_edges).length for p in(outer_pdf,inner_pdf))*sh.reg['s']
    outer=source_transform(outer_pdf,sh.reg);inner=source_transform(inner_pdf,sh.reg)
    bx0,by0,bx1,by1=Polygon(outer).bounds;bix0,biy0,bix1,biy1=Polygon(inner).bounds
    expected={'architectural_outer_boundary':Polygon(outer),'architectural_inner_boundary':Polygon(inner),
              'left_outer_minus_inner':box(bx0,by0,bix0,by1),
              'south_outer_minus_inner':box(bix0,by0,bx1,biy0),
              'north_outer_minus_inner':box(bix0,biy1,bx1,by1)}
    data_error=max(Polygon(P['outer_boundary_pdf']).hausdorff_distance(Polygon(outer_pdf))*sh.reg['s'],Polygon(P['inner_boundary_pdf']).hausdorff_distance(Polygon(inner_pdf))*sh.reg['s'])
    for e in elements:
        a=e.get('a')or{};part=a.get('source_boundary_part');target=expected.get(part)
        if target is None or e['g'][0]!='p' or a.get('source_kind')!='derived_from_architectural_boundary':checks.append({'id':e['id'],'pass':False,'reason':'Missing source architectural boundary classification'});continue
        anchor=max(line(saved).hausdorff_distance(line(paths[di]))for di,saved in zip(indices,a.get('source_pdf_points',[])))*sh.reg['s'] if len(a.get('source_pdf_points',[]))==len(indices) else float('inf')
        transform=max(math.dist(p,v)for path in paths.values()for p,v in zip(source_transform(path,a['source_transform']),source_transform(path,sh.reg)))
        err=Polygon(e['g'][1],e['g'][4]).hausdorff_distance(target)
        meta_error=Polygon(a['source_xy']).hausdorff_distance(target)
        checks.append({'id':e['id'],'reference':'ARCH1:8','source_boundary_part':part,
                       'method':'Derived architectural outer/inner boundary piece from original A105 line primitives',
                       'deviation_cm':err,'metadata_deviation_cm':meta_error,
                       'raw_source_deviation_cm':max(raw_source_error,anchor,data_error,boundary_error),
                       'source_transform_deviation_cm':transform,
                       'classification':'derived_architectural_not_structural_extent',
                       'pass':max(err,meta_error,raw_source_error,anchor,data_error,boundary_error,transform)<=tolerance})
    return checks

@functools.lru_cache(maxsize=6)
def garbage_original_page(page):
    import lib
    return lib.doc('ARCH1')[page-1].get_drawings()

@functools.lru_cache(maxsize=1)
def garbage_original_literals():
    import lib
    return lib.doc('ARCH2')[17].get_texttrace()

def garbage_source_check(e):
    """Full-plan glyph centres and separate A1100 literal dimensions.

    The 43.6 cm graphic circle is never promoted to a device diameter. Source
    text proves 600/300 mm and 1.5 mm SS304 separately. A hopper's source plate
    proves XY; the literal 59x75 frame sizes do not prove its mounting Z/depth.
    The repeated roof symbol is one fan marker, with no body-size claim.
    """
    D=read('garbage_chute_remaining');q=next((q for q in D.get('records',[])if q['id']==e['id']),None)
    a=e.get('a')or{}
    if not q or a.get('source_kind')!='garbage_plan_graphic_anchor' or a.get('source_plan_role')!=q['role'] or e['l']!=q['level']:return None
    source=q['source'];ref=source['source_page'];book,page=ref.split(':');page=int(page)
    if book!='ARCH1' or a.get('source_page')!=ref or a.get('source_drawing_indices')!=source['source_drawing_indices'] or a.get('source_poly_index')!=source['source_poly_index']:return None
    sh=pdf_sheet(book,page);drawing=garbage_original_page(page)[source['source_drawing_indices'][0]]
    import lib
    raw=lib.flat_path(drawing)[source['source_poly_index']]
    if drawing.get('layer')!=source['source_layer']or a.get('source_layer')!=source['source_layer']:return None
    role=q['role'];expected_n={'chute':34,'hopper':5,'vent':41,'fan_marker':41}[role]
    if len(raw)!=expected_n or math.dist(raw[0],raw[-1])>.001:return None
    if role in('chute','vent','fan_marker'):
        bbox=[min(p[k]for p in raw)for k in(0,1)]+[max(p[k]for p in raw)for k in(0,1)]
        if abs((bbox[2]-bbox[0])/(bbox[3]-bbox[1])-1)>.02:return None
    literal_data=[D['literals'][i]for i in q['literal_refs']]
    if a.get('source_dimension_literals')!=literal_data:return None
    literal_verified=True
    for literal in literal_data:
        span=garbage_original_literals()[literal['texttrace_index']]
        if ''.join(chr(c[0])for c in span['chars'])!=literal['text'] or list(span['bbox'])!=literal['bbox'] or span.get('layer')!=literal['layer']:literal_verified=False
    if not literal_verified:return None
    saved=a.get('source_pdf_points');meta=a.get('source_xy');tr=a.get('source_transform')
    if not saved or not meta or not tr or len(saved)!=len(raw)or len(source['source_pdf_points'])!=len(raw):return None
    xy=source_transform([boxcentre(raw)],sh.reg)[0]
    result={'method':'Original ARCH1 plan glyph/plate centre; separate original A1100 text dimensions',
            'deviation_cm':math.dist(centre(e['g']),xy),
            'metadata_deviation_cm':max(math.dist(meta,xy),math.dist(source['source_xy'],xy)),
            'source_anchor_deviation_cm':max(math.dist(p,v)for savedpoints in(saved,source['source_pdf_points'])for p,v in zip(savedpoints,raw))*sh.reg['s'],
            'source_transform_deviation_cm':max(math.dist(p,v)for p,v in zip(source_transform(raw,tr),source_transform(raw,sh.reg))),
            'reference':ref,'source_xy':xy,'source_literal_dimensions_verified':True,
            'spatial_basis':'Plan graphic anchor only; literal diameter/frame size is separate. Z/support/openings and remaining detail remain unverified'}
    if role in('chute','vent'):
        if e['g'][0]!='p'or not e['g'][4]or len(e['g'][4])!=1:return None
        diameter=q['diameter_cm'];outer=e['g'][1];inner=e['g'][4][0]
        bounds=Polygon(outer).bounds;ibounds=Polygon(inner).bounds
        result['source_diameter_deviation_cm']=max(abs(bounds[2]-bounds[0]-diameter),abs(bounds[3]-bounds[1]-diameter))
        result['literal_wall_thickness_max_error_cm']=max(abs(abs(bounds[k]-ibounds[k])-q['sheet_thickness_cm'])for k in range(4))
    elif role=='hopper':
        if e['g'][0]!='b':return None
        result['literal_frame_width_error_cm']=abs(e['g'][3]-59)
        result['literal_frame_height_error_cm']=abs((e['g'][7]-e['g'][6])*100-75)
    else:
        if not a.get('source_is_annotation'):return None
    return result

@functools.lru_cache(maxsize=4)
def electrical_tail_original_page(page):
    import lib
    return lib.doc('ELEC1')[page-1].get_drawings()

def electrical_tail_check(e):
    """Read the two original POWER-CONN. curves/lines and arrow vertices.

    Plan paths and the V arrow's middle vertex are source bound. The small
    connector inside the device glyph is reported separately as derived.
    No circuit-to-board route, Z, physical diameter or device body is proved.
    """
    a=e.get('a')or{};D=read('electrical_trace_restore')
    q=next((q for q in D.get('records',[])if q['id']==a.get('source_trace_record')),None)
    if not q or e['l']!=q['level'] or e['c']!='E.tray':return None
    kind=a.get('source_kind');ref=q['source'];book,page=ref.split(':');page=int(page)
    if book!='ELEC1' or a.get('source_page')!=ref:return None
    primitive=a.get('source_primitives')
    key=next((k for k in ('curve','straight','arrow')if primitive==[[q[k]['drawing'],q[k]['poly']]]),None)
    if not key:return None
    source=q[key];sh=pdf_sheet(book,page);drawing=electrical_tail_original_page(page)[source['drawing']]
    import lib
    raw=lib.flat_path(drawing,100)[source['poly']]
    raw_items=[[item[0]]+[[p.x,p.y]for p in item[1:]]for item in drawing['items']if item[0]in('l','c')]
    if len(raw_items)!=len(drawing['items'])or raw_items!=source['raw_items']or raw_items!=a.get('source_raw_items'):return None
    if drawing.get('layer')!='POWER-CONN.'or source['layer']!=drawing.get('layer')or a.get('source_layer')!=drawing.get('layer'):return None
    saved=a.get('source_pdf_points');meta=a.get('source_xy');tr=a.get('source_transform')
    if not saved or not meta or not tr:return None
    world=source_transform(raw,sh.reg)
    anchor=line(source['pdf_points']).hausdorff_distance(line(raw))*sh.reg['s']
    transform=max(math.dist(p,v)for p,v in zip(source_transform(raw,tr),world))
    if kind=='raw_electrical_connection_polyline':
        if key not in('curve','straight')or e.get('t')!='wire_power'or e['g'][0]!='t':return None
        anchor=max(anchor,line(saved).hausdorff_distance(line(raw))*sh.reg['s'])
        metadata=max(line(meta).hausdorff_distance(line(world)),line(source['xy_cm']).hausdorff_distance(line(world)))
        error=deviation(e,world,'path');source_xy=world
    elif kind=='raw_electrical_arrow_tip':
        if key!='arrow'or e.get('t')!='wire_circuit_end'or len(raw)!=3 or e['g'][0]!='cyl':return None
        # Both arms meet at the middle vertex; do not choose a label or the
        # closest endpoint of a different route as the circuit boundary.
        if math.dist(raw[0],raw[1])<.1 or abs(math.dist(raw[0],raw[1])-math.dist(raw[1],raw[2]))>.02:return None
        tip=raw[1];tip_xy=world[1]
        anchor=max(anchor,math.dist(saved[0],tip)*sh.reg['s'],math.dist(q['arrow_tip_pdf'],tip)*sh.reg['s'])
        metadata=max(math.dist(meta,tip_xy),math.dist(q['arrow_tip_xy'],tip_xy))
        error=math.dist(centre(e['g']),tip_xy);source_xy=tip_xy
    else:return None
    return {'method':'Original ELEC1 POWER-CONN. raw Bezier/line path or V-arrow middle vertex',
            'deviation_cm':error,'metadata_deviation_cm':metadata,
            'source_anchor_deviation_cm':anchor,'source_transform_deviation_cm':transform,
            'reference':ref,'source_xy':source_xy,
            'spatial_basis':'Literal plan trace or arrow boundary only; Z, diameter, device body and board feeder remain unverified'}

@functools.lru_cache(maxsize=6)
def water_original_page(page):
    import lib
    p=lib.doc('MECH2')[page-1]
    return p.get_drawings(),p.get_texttrace()

def _water_primitive_check(p,page):
    """Preserve primitive ordering, not just a nearest-line distance."""
    import lib
    drawings,_=water_original_page(page);d=drawings[p['drawing']]
    if d.get('layer')!=p['layer'] or p['layer']not in('M_WS_CW','M_WS_HW','M_FF_PIPE'):return None
    raw=lib.flat_path(d,10)[p['poly']]
    if len(raw)!=len(p['raw_pdf_points']):return None
    error=max(math.dist(u,v)for u,v in zip(raw,p['raw_pdf_points']))
    return raw,error

def _source_type(e, old):
    # Explicit owner rename of already volumetric bodies; all source geometry checks remain unchanged.
    renamed={'valve_source_graphic','ws_lifting_graphic','ws_filtration_pump_graphic','ws_booster_graphic','ws_media_filter_graphic','ws_pv_graphic','ws_break_tank_graphic','ws_uv_graphic','ws_water_meter_graphic'}
    return old[:-8] if old in renamed and e.get('t')==old[:-8] else old

def water_source_check(e):
    """Read original CW paths or the union bbox of a whole device glyph.

    Break curves and set frames are not promoted to water pipes. Device
    markers prove only a source anchor/semantic label, never body dimensions,
    Z, colour, hydraulics, physical ports or duty/standby assignment.
    """
    a=e.get('a')or{};D=read('water_supply_mixed_corrections'if a.get('source_correction_wave')=='mixed560'else'water_supply_source_corrections');kind=a.get('source_kind')
    if kind=='raw_water_pipe_without_break_glyph':
        q=next((q for q in D.get('restore_records',[])if q['id']==a.get('source_record')),None)
        if not q or e['c']!=q['category']or e.get('t')!=_source_type(e,q['type'])or e['l']!=q['level']or e['g'][0]!='t':return None
        k=a.get('source_part_index');parts=q['parts']
        if not isinstance(k,int)or not 0<=k<len(parts):return None
        p=parts[k];page=int(q['source'].split(':')[1]);sh=pdf_sheet('MECH2',page)
        if a.get('source_page')!=q['source']or a.get('source_primitives')!=[[p['drawing'],p['poly']]]or a.get('source_vertex_indices')!=p['vertex_indices']:return None
        proof=_water_primitive_check(p,page)
        if proof is None:return None
        raw,anchor=proof
        # These selected primitives are actual continuous straight CW routes.
        # A Bezier arc/glyph cannot enter this path class.
        drawing=water_original_page(page)[0][p['drawing']]
        if any(item[0]!='l'for item in drawing['items']):return None
        selected=[raw[i]for i in p['vertex_indices']];world=source_transform(selected,sh.reg)
        saved=a.get('source_pdf_points');meta=a.get('source_xy');tr=a.get('source_transform')
        if not saved or not meta or not tr or len(saved)!=len(selected)or len(meta)!=len(world):return None
        anchor=max(anchor,max(math.dist(u,v)for u,v in zip(saved,selected)),max(math.dist(u,v)for u,v in zip(p['pdf_points'],selected)))*sh.reg['s']
        metadata=max(max(math.dist(u,v)for u,v in zip(meta,world)),max(math.dist(u,v)for u,v in zip(p['xy_cm'],world)))
        transform=max(math.dist(u,v)for u,v in zip(source_transform(selected,tr),world))
        error=deviation(e,world,'path');xy=world;method='Original MECH2 CW straight primitives with exact selected vertices; break glyphs excluded'
    elif kind=='water_device_whole_glyph_bbox_anchor':
        q=next((q for q in D.get('device_markers',[])if q['id']==e['id']),None)
        if not q or(e['c'],e.get('t'),e['l'])!=(q['category'],_source_type(e,q['type']),q['level']):return None
        page=int(q['source'].split(':')[1]);sh=pdf_sheet('MECH2',page)
        if a.get('source_page')!=q['source']or a.get('source_primitives')!=[[p['drawing'],p['poly']]for p in q['glyph_primitives']]:return None
        raw=[];anchor=0
        for p in q['glyph_primitives']:
            proof=_water_primitive_check(p,page)
            if proof is None:return None
            pp,er=proof;raw.extend(pp);anchor=max(anchor,er)
        for p in q['source_leaders']:
            proof=_water_primitive_check(p,page)
            if proof is None:return None
            anchor=max(anchor,proof[1])
        ctr=boxcentre(raw);xy=source_transform([ctr],sh.reg)[0]
        tx=q['source_texttrace'];tt=water_original_page(page)[1][tx['index']]
        literal=''.join(chr(c[0])for c in tt['chars'])
        if literal!=tx['s']or a.get('source_texttrace',{}).get('s')!=literal:return None
        if a.get('source_spec_texttraces')!=q.get('source_spec_texttraces'):return None
        for spec in q.get('source_spec_texttraces',[]):
            actual=water_original_page(page)[1][spec['index']]
            if ''.join(chr(c[0])for c in actual['chars'])!=spec['s']:return None
        saved=a.get('source_pdf_points');meta=a.get('source_xy');tr=a.get('source_transform')
        if not saved or len(saved)!=1 or not meta or not tr:return None
        anchor=max(anchor,math.dist(saved[0],ctr),math.dist(q['source_pdf_centre'],ctr))*sh.reg['s']
        metadata=max(math.dist(meta,xy),math.dist(q['source_xy_cm'],xy))
        transform=math.dist(source_transform([ctr],tr)[0],xy)
        error=math.dist(centre(e['g']),xy);method='Original MECH2 complete water-device glyph union bbox and independently read literal callout'
    else:return None
    return {'method':method,'deviation_cm':error,'metadata_deviation_cm':metadata,
        'source_anchor_deviation_cm':anchor,'source_transform_deviation_cm':transform,
        'reference':q['source'],'source_xy':xy,
        'spatial_basis':'Source XY only; physical device body / pipe diameter / Z / material / mounting / connection remain unverified'}

def water_retirement_checks(M,tolerance):
    D=read('water_supply_source_corrections')
    if not M.get('meta',{}).get('water_supply_source_corrections'):return []
    present={e['id']for e in M['els']};out=[]
    for p in D.get('nonpipe_set_frames',[]):
        page=19 if p['drawing']==5793 else 22;proof=_water_primitive_check(p,page)
        out.append({'id':'WSC-frame-'+str(p['drawing']),'method':'Original source equipment frame retained as semantic evidence, not a hydraulic conductor',
            'pass':proof is not None and proof[1]*pdf_sheet('MECH2',page).reg['s']<=tolerance})
    for r in D.get('retire_records',[]):
        out.append({'id':r['id'],'method':'Confirmed equipment-body/frame stroke is absent from the hydraulic pipe inventory',
                    'source':r['source'],'pass':r['id']not in present})
    return out

def water_mixed_review_check(e,tolerance=TOL):
    """Independent open-line support, with no pipe role inferred from proximity.

    Closed symbols and curves are excluded from the XY envelope. Dash gaps are
    retained as derived spans; a successful raw-data check does not turn them
    into a complete literal pipe route or a verified hydraulic connection.
    """
    import lib
    a=e.get('a')or{};D=read('water_supply_mixed_corrections')
    q=next((q for q in D.get('review_records',[])if q['id']==e['id']),None)
    if not q or (e['c'],e.get('t'),e['l'],e['g'][0])!=(q['category'],_source_type(e,q['type']),q['level'],'t'):return None
    if a.get('source_page')!=q['source']or a.get('source_primitives')!=[[p['drawing'],p['poly']]for p in q['source_primitives']]:return None
    page=int(q['source'].split(':')[1]);sh=pdf_sheet('MECH2',page);raw_lines=[];anchor=0;transform=0
    for p in q['source_primitives']:
        proof=_water_primitive_check(p,page)
        if proof is None:return None
        raw,err=proof;anchor=max(anchor,err*sh.reg['s'])
        world=source_transform(raw,sh.reg)
        transform=max(transform,max(math.dist(u,v)for u,v in zip(source_transform(raw,a['source_transform']),world)))
        actual=water_original_page(page)[0][p['drawing']]
        if all(item[0]=='l'for item in actual['items'])and math.dist(raw[0],raw[-1])>.001:raw_lines.append(line(world))
    if not raw_lines:return None
    union=unary_union(raw_lines);model=line([p[:2]for p in e['g'][1]])
    unchanged=hashlib.sha256(json.dumps(e['g'],separators=(',',':')).encode()).hexdigest()==q['whole_trace_geometry_sha256']
    error=max(Point(p[:2]).distance(union)for p in e['g'][1])
    return {'method':'Original MECH2 open linear water strokes only; closed device glyphs and S curves excluded',
        'deviation_cm':error,'source_anchor_deviation_cm':anchor,'source_transform_deviation_cm':transform,
        'whole_trace_source_covered':model.difference(union.buffer(tolerance)).length<=1e-6,
        'review_geometry_unchanged':unchanged,'reference':q['source'],
        'spatial_basis':'Conditional source XY trace only; semantic device/body, Z, diameter, material and hydraulic contact are unverified'}

def _water_dash_rule_check(q,page):
    """Check exceptional dash continuation witnesses in fresh HW linework.

    This proves a drawn line-type interpretation at a turn or crossing. It
    does not establish a hydraulic junction, physical port or elevation.
    """
    import lib
    rule=q.get('linetype_rule')
    if not rule:return None
    drawings,_=water_original_page(page);sh=pdf_sheet('MECH2',page);polys={}
    for di in rule['drawings']:
        d=drawings[di]
        if d.get('layer')!='M_WS_HW' or any(i[0]!='l'for i in d['items']):return None
        paths=lib.flat_path(d,10)
        if len(paths)!=1:return None
        polys[di]=source_transform(paths[0],sh.reg)
    def vertex(binding):return polys[binding[0]][binding[1]]
    kind=rule['kind'];axis=0 if rule.get('collinear_axis')=='X'else 1
    tolerance=.001;details={'kind':kind,'source_drawings':rule['drawings']}
    if kind=='aligned_bathtub_hot_stem_dash':
        u,v=map(vertex,rule['end_vertices']);error=abs(u[axis]-v[axis])
        ok=error<=tolerance and math.dist(u,v)>tolerance
        details.update(axis_deviation_cm=error,endpoints_xy=[u,v])
    elif kind=='overlapping_dash_phases_at_same_turn':
        u,v=map(vertex,rule['turn_vertices']);error=math.dist(u,v)
        # Multiple phase offsets are source strokes, not missing components.
        baseline=u[axis];errs=[abs(p[axis]-baseline)for di in rule['drawings'][2:]for p in polys[di]]
        ok=error<=tolerance and max(errs,default=0)<=tolerance
        details.update(turn_deviation_cm=error,phase_axis_deviation_cm=max(errs,default=0),turn_xy=[u,v])
    elif kind in('dash_interval_crossed_by_actual_T_branch','dash_tail_by_fixture_branch_crossing'):
        u,v=map(vertex,rule['dash_end_vertices']);axis_error=abs(u[axis]-v[axis]);along=1-axis
        lo,hi=sorted((u[along],v[along]));witness=rule.get('crossing_vertex')or rule['crossing_segment']
        pts=polys[witness[0]]
        if kind=='dash_interval_crossed_by_actual_T_branch':
            w=vertex(witness);other=pts[1 if witness[1]==0 else 0]
            crossing=abs(w[axis]-u[axis])<=tolerance and lo<=w[along]<=hi and abs(other[along]-w[along])<=tolerance
        else:
            w,z=pts[witness[1]],pts[witness[2]]
            crossing=abs(w[along]-z[along])<=tolerance and lo<=w[along]<=hi and min(w[axis],z[axis])<=u[axis]<=max(w[axis],z[axis])
        ok=axis_error<=tolerance and crossing
        details.update(axis_deviation_cm=axis_error,dash_endpoints_xy=[u,v],crossing_source_xy=pts)
    else:return None
    details['pass']=ok;details['hydraulic_contact_verified']=False
    return details

def water_mixed_source_checks(M,tolerance):
    """Raw retirement evidence and derived dash evidence stay separate."""
    if not M.get('meta',{}).get('water_supply_mixed_corrections'):return [],[]
    D=read('water_supply_mixed_corrections');E={e['id']:e for e in M['els']};out=[];derived=[]
    for r in D.get('retire_records',[]):
        page=int(r['source'].split(':')[1]);proofs=[_water_primitive_check(p,page)for p in r['source_primitives']]
        valid=all(p is not None and p[1]*pdf_sheet('MECH2',page).reg['s']<=tolerance for p in proofs)
        out.append({'id':r['id'],'method':'Original water S-break graphic or equipment frame is absent from pipe inventory',
            'source':r['source'],'source_role':r['role'],'pass':r['id']not in E and valid and all(i in E for i in r.get('preserved_device_ids',[]))})
    for r in D.get('review_records',[]):
        if r['status']=='whole_open_linear_trace_within_0.2cm':continue
        e=E.get(r['id']);proof=water_mixed_review_check(e,tolerance)if e else None
        ref=r.get('legend_reference')or{};page=ref.get('page');ti=ref.get('texttrace_index');literal=None
        if page and isinstance(ti,int):literal=''.join(chr(c[0])for c in water_original_page(page)[1][ti]['chars'])
        witness=_water_dash_rule_check(r,int(r['source'].split(':')[1]))if r.get('linetype_rule')else None
        ok=proof is not None and literal==ref.get('literal')and proof['review_geometry_unchanged'] and max(proof['deviation_cm'],proof['source_anchor_deviation_cm'],proof['source_transform_deviation_cm'])<=tolerance and(not r.get('linetype_rule')or witness is not None and witness['pass'])
        derived.append({'id':r['id'],'method':'Independently read HW dash strokes, legend and turn/crossing witnesses; dash continuation remains derived',
            'proof_scope':'derived_dash_route_raw_bindings_only','reference':r['source'],'source_review_status':r['status'],
            'nonperiodic_pending_spans_cm':r['pending_spans_cm'],'raw_bindings':proof,'turn_or_crossing_rule':witness,
            'whole_literal_route_verified':False,'pass':ok})
    return out,derived

def _water_meter_graphic_proof(q,page):
    """Read the circle and the actual M character from original PDF vectors."""
    import lib
    drawings,text=water_original_page(page);d=drawings[q['drawing']]
    if d.get('layer')!=q['layer']or len(d['items'])!=4 or any(i[0]!='c'for i in d['items']):return None
    raw_items=[[it[0]]+[[p.x,p.y]for p in it[1:]]for it in d['items']]
    if raw_items!=q['raw_items']:return None
    paths=lib.flat_path(d,10)
    if len(paths)!=1 or len(paths[0])!=41:return None
    raw=paths[0];ctr=boxcentre(raw);glyph=q['text_M'];ch=text[glyph['trace_index']]['chars'][glyph['char_index']]
    if chr(ch[0])!='M'or ch[1]!=glyph['glyph']or list(ch[2])!=glyph['origin_pdf']or list(ch[3])!=glyph['bbox_pdf']:return None
    box_=[min(p[0]for p in raw),min(p[1]for p in raw),max(p[0]for p in raw),max(p[1]for p in raw)]
    cb=ch[3]
    if not(box_[0]<=cb[0]<=cb[2]<=box_[2] and box_[1]<=cb[1]<=cb[3]<=box_[3]):return None
    sh=pdf_sheet('MECH2',page);xy=source_transform([ctr],sh.reg)[0]
    return {'raw':raw,'centre':ctr,'xy':xy,'anchor_deviation_cm':math.dist(ctr,q['source_pdf_centre'])*sh.reg['s'],'metadata_deviation_cm':math.dist(xy,q['source_xy_cm'])}

def water_meter_source_check(e):
    """Circle-M anchor only: graphic size is not a physical meter dimension."""
    D=read('water_meter_source_remaining');a=e.get('a')or{};q=next((q for q in D.get('meter_markers',[])if q['id']==e['id']),None)
    if not q or(e['c'],e.get('t'),e['l'],e['g'][0])!=(q['category'],_source_type(e,q['type']),q['level'],'cyl'):return None
    page=int(q['source_page'].split(':')[1]);proof=_water_meter_graphic_proof(q,page);legend=D['pages'][str(page)]['legend'];text=water_original_page(page)[1]
    if proof is None or _water_meter_graphic_proof(legend['meter_circle'],page)is None:return None
    if ''.join(chr(c[0])for c in text[legend['WATER_METER_trace']]['chars'])!=legend['label']:return None
    if a.get('source_page')!=q['source_page']or a.get('source_primitives')!=[[q['drawing'],q['poly']]]or a.get('source_M_character')!=q['text_M']or a.get('source_raw_items')!=q['raw_items']:return None
    saved=a.get('source_pdf_points');meta=a.get('source_xy');tr=a.get('source_transform')
    if not saved or len(saved)!=len(proof['raw'])or not meta or not tr:return None
    flags=('source_dimensions_verified','source_Z_verified','source_material_verified','source_finish_verified','source_mount_verified','source_contact_verified','source_ports_verified')
    if any(a.get(k)is not False for k in flags)or not a.get('no_connectors')or not a.get('source_graphic_radius_not_body_dimension'):return None
    sh=pdf_sheet('MECH2',page)
    return {'method':'Original MECH2 circle-M curves, contained M glyph and WATER METER legend; XY presence only',
        'deviation_cm':math.dist(centre(e['g']),proof['xy']),
        'metadata_deviation_cm':max(proof['metadata_deviation_cm'],math.dist(meta,proof['xy'])),
        'source_anchor_deviation_cm':max(proof['anchor_deviation_cm'],max(math.dist(u,v)for u,v in zip(saved,proof['raw']))*sh.reg['s']),
        'source_transform_deviation_cm':math.dist(source_transform([proof['centre']],tr)[0],proof['xy']),
        'reference':q['source_page'],'source_xy':proof['xy'],'spatial_basis':'Circle-M graphic anchor only; body dimensions/Z/material/ports/contact remain unverified'}

def water_meter_source_checks(M,tolerance):
    """Retire W/M text proxies; independently retain existing washer presence."""
    if not M.get('meta',{}).get('water_meter_source_remaining'):return []
    import lib
    D=read('water_meter_source_remaining');E={e['id']:e for e in M['els']};checks=[]
    for q in D['retire_false_WM']:
        page=int(q['source_page'].split(':')[1]);t=water_original_page(page)[1][q['source_texttrace_index']]
        valid=''.join(chr(c[0])for c in t['chars'])==q['raw_text']=='W/M'
        for saved in q['source_chars']:
            ch=t['chars'][saved['char_index']]
            valid=valid and chr(ch[0])==saved['char'] and ch[1]==saved['glyph']and list(ch[2])==saved['origin_pdf']and list(ch[3])==saved['bbox_pdf']
        checks.append({'id':q['id'],'method':'Original W/M washing-area text proxy is absent from water-meter/device inventory','reference':q['source_page'],'pass':valid and q['id']not in E})
    for q in D['existing_washer_presence']:
        book,page=q['source_page'].split(':');page=int(page);p=lib.doc(book)[page-1];drawings=p.get_drawings();text=p.get_texttrace();valid=q['existing_id']in E
        context=q['source_context_word'];valid=valid and ''.join(chr(c[0])for c in text[context['texttrace_index']]['chars'])==context['literal']=='WASH'
        for saved in q['source_primitives']:
            d=drawings[saved['drawing']];raw=lib.flat_path(d,10)[0]
            valid=valid and d.get('layer')==saved['layer']and len(raw)==len(saved['pdf_points'])and max(math.dist(u,v)for u,v in zip(raw,saved['pdf_points']))<=1e-6
        checks.append({'id':q['existing_id'],'method':'Existing washer display body retained once; original architectural square/circle/WASH glyph proves presence only','reference':q['source_page'],'whole_body_geometry_verified':False,'pass':valid})
    return checks

@functools.lru_cache(maxsize=2)
def hvac_original_page(page):
    """Original PDF paths/text, including quadrilateral vector control data."""
    import lib
    p=lib.doc('MECH1')[page-1]
    return p.get_drawings(),p.get_texttrace()

def hvac_source_check(e):
    """T-circle anchor or explicitly labelled FCU quad, independently from PDF.

    A thermostat circle proves its graphic centre and the T glyph. The FCU quad
    additionally proves its plan-symbol angle. Device dimensions, Z, material
    and mounting face remain unverified, including when the old body is kept.
    """
    a=e.get('a')or{};q=read('restore_hvac_source').get('records',{}).get(e['id'])
    if not q or (e['c'],e.get('t'),e['l'],e['g'][0])!=(q['category'],_source_type(e,q['type']),q['level'],'b'):return None
    source=q['source'];ref=source['source_page'];book,page=ref.split(':');page=int(page)
    kind=source['source_kind']
    if book!='MECH1' or a.get('source_kind')!=kind or a.get('source_page')!=ref:return None
    if a.get('source_drawing_indices')!=source['source_drawing_indices'] or a.get('source_poly_index')!=source['source_poly_index']:return None
    sh=pdf_sheet(book,page);drawings,text=hvac_original_page(page)
    di=source['source_drawing_indices'][0];pi=source['source_poly_index'];drawing=drawings[di]
    import lib
    raw=lib.flat_path(drawing)[pi]
    if drawing.get('layer')!=source['source_layer'] or drawing.get('layer')!=a.get('source_layer'):return None
    pdf_centre=boxcentre(raw);xy=source_transform([pdf_centre],sh.reg)[0]
    raw_items=[]
    for item in drawing['items']:
        if item[0]in('l','c'):raw_items.append([item[0]]+[[p.x,p.y]for p in item[1:]])
        elif item[0]=='qu':
            quad=item[1];raw_items.append(['qu',[[p.x,p.y]for p in(quad.ul,quad.ur,quad.lr,quad.ll)]])
        else:return None
    if raw_items!=source['source_raw_items']:return None
    angle=None;rotation_ok=True;text_ok=False
    if kind=='thermostat_circle_graphic_anchor':
        if len(raw)!=41 or math.dist(raw[0],raw[-1])>.001 or len(raw_items)!=4 or any(i[0]!='c'for i in raw_items):return None
        radii=[math.dist(pdf_centre,p)for p in raw]
        if max(radii)-min(radii)>.04:return None
        radius=(max(p[0]for p in raw)-min(p[0]for p in raw))/2
        for literal in source['source_text']:
            ti,ci=literal['texttrace_index'],literal['char_index'];span=text[ti];char=span['chars'][ci]
            actual=chr(char[0]);bbox=list(char[3]);charcentre=[(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2]
            off=[charcentre[k]-pdf_centre[k]for k in(0,1)]
            if actual!='T' or len(span['chars'])!=1 or span.get('layer')!=literal['layer'] or bbox!=literal['char_bbox']:return None
            if max(abs(off[k]-literal['circle_T_offset_pdf_points'][k])for k in(0,1))>1e-8:return None
            if abs(off[0])>.2*radius or not 1.05*radius<off[1]<1.35*radius:return None
            text_ok=True
    elif kind=='fcu_plan_quad_anchor_angle':
        if len(raw_items)!=1 or raw_items[0][0]!='qu' or len(raw)!=5:return None
        world=source_transform(raw,sh.reg)
        p,qedge=max(zip(world,world[1:]),key=lambda pair:math.dist(*pair))
        angle=math.degrees(math.atan2(qedge[1]-p[1],qedge[0]-p[0]))%180
        def angle_gap(a,b):return abs((a-b+90)%180-90)
        rotation_ok=angle_gap(e['g'][5],angle)<.01 and angle_gap(source['source_angle'],angle)<.01 and angle_gap(a.get('source_rotation_deg',1e9),angle)<.01
        polygon=Polygon(raw)
        for literal in source['source_text']:
            span=text[literal['index']];actual=''.join(chr(c[0])for c in span['chars']);bbox=list(span['bbox'])
            if actual!='FCU-R-LR' or actual!=literal['literal'] or bbox!=literal['bbox'] or span.get('layer')!=literal['layer']:return None
            if not polygon.covers(Point((bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2)):return None
            text_ok=True
    else:return None
    saved=a.get('source_pdf_points');tr=a.get('source_transform');meta=a.get('source_xy')
    if not saved or not tr or not meta or not text_ok or a.get('source_semantic_text')!=source['source_text']:return None
    if len(saved)!=len(raw) or len(source['source_pdf_points'])!=len(raw):return None
    return {'method':'Original MECH1 vector glyph with original T/FCU-R-LR text identity; graphic anchor only',
            'deviation_cm':math.dist(centre(e['g']),xy),
            'metadata_deviation_cm':max(math.dist(meta,xy),math.dist(source['source_xy'],xy)),
            'source_anchor_deviation_cm':max(math.dist(p,q)for savedpoints in(saved,source['source_pdf_points'])for p,q in zip(savedpoints,raw))*sh.reg['s'],
            'source_transform_deviation_cm':max(math.dist(p,q)for p,q in zip(source_transform(raw,tr),source_transform(raw,sh.reg))),
            'reference':ref,'source_xy':xy,'source_semantic_text_verified':text_ok,
            'source_symbol_angle_deg':angle,'source_rotation_matches_symbol':rotation_ok,
            'spatial_basis':'Graphic centre and labelled FCU plan-symbol angle only; body dimensions, Z, material and mount remain unverified'}

def electrical_legacy_check(e):
    """Recompute the drawn cluster centre from each original PDF primitive."""
    a=e.get('a') or {};q=electrical_legacy_anchors().get(e['id'])
    if not q or a.get('source_kind')!='drawn_symbol_cluster_bbox_centre':return None
    if (e['c'],e.get('t'),e['l'])!=(q['expected_category'],q['expected_type'],q['expected_level']):return None
    ref=q['source'];book,page=ref.split(':');sh=pdf_sheet(book,int(page))
    indices=q['raw_drawing_primitives']
    if a.get('source_primitives')!=indices or a.get('source_page')!=ref:return None
    raw=[p for di,pi in indices for p in sh.D[di]['polys'][pi]]
    if not raw:return None
    pdf_centre=boxcentre(raw);xy=source_transform([pdf_centre],sh.reg)[0]
    saved=a.get('source_pdf_points');tr=a.get('source_transform');meta=a.get('source_xy')
    if not saved or not tr or not meta:return None
    return {'method':'Original PDF vector-cluster bbox centre; actual drawing/poly indices',
        'deviation_cm':math.dist(centre(e['g']),xy),
        'metadata_deviation_cm':max(math.dist(meta,xy),math.dist(q['source_xy_cm'],xy)),
        'source_anchor_deviation_cm':max(math.dist(saved[0],pdf_centre),math.dist(q['source_pdf_centre_pt'],pdf_centre))*sh.reg['s'],
        'source_transform_deviation_cm':math.dist(source_transform([pdf_centre],tr)[0],xy),
        'reference':ref,'source_xy':xy,'spatial_basis':'Drawn electrical symbol centre only; physical size, mounting direction and Z are separate'}

def electrical_semantic_check(e):
    """Recompute each selected glyph from original PDF paths, excluding leaders.

    This establishes symbol X/Y. It does not use the old model's size, material,
    colour or mounting height as evidence for the physical device.
    """
    a=e.get('a') or {};D=read('electrical_symbol_semantics')
    q=D.get('records',{}).get(e['id']) or next((q for q in D.get('create_sensors',[]) if q['id']==e['id']),None)
    if not q or not q.get('class_verified') or q['action']=='remove_nondevice_fragment':return None
    ref=q['source'];book,page=ref.split(':');sh=pdf_sheet(book,int(page))
    indices=q['selected_glyph_primitives'];raw=[sh.D[di]['polys'][pi] for di,pi in indices]
    if not raw or a.get('source_primitives')!=indices or a.get('source_page')!=ref:return None
    if any(i not in q['raw_drawing_primitives'] for i in indices):return None
    kind=q['source_kind']
    if a.get('source_kind')!=kind:return None
    if kind=='circle_bounds_centre':
        if len(raw)!=1 or len(raw[0])!=41 or math.dist(raw[0][0],raw[0][-1])>.001:return None
        b=boxcentre(raw[0]);rad=[math.dist(b,p) for p in raw[0]]
        if max(rad)-min(rad)>.03:return None
    elif kind!='drawn_symbol_glyph_bbox_centre':return None
    if q.get('expected_category'):
        identity=(q.get('target_category',q['expected_category']),q.get('target_type',q['expected_type']),q['expected_level'])
    else:identity=('E.socket','e_S11','1')
    if (e['c'],e.get('t'),e['l'])!=identity:return None
    saved=a.get('source_pdf_points');tr=a.get('source_transform');meta=a.get('source_xy')
    if not saved or not tr or not meta or len(saved)!=len(raw) or len(q['glyph_pdf_points'])!=len(raw):return None
    pdf_centre=boxcentre([p for path in raw for p in path]);xy=source_transform([pdf_centre],sh.reg)[0]
    anchor=max(line(saved[i]).hausdorff_distance(line(raw[i])) for i in range(len(raw)))*sh.reg['s']
    anchor=max(anchor,max(line(q['glyph_pdf_points'][i]).hausdorff_distance(line(raw[i])) for i in range(len(raw)))*sh.reg['s'],
               math.dist(q['glyph_pdf_centre_pt'],pdf_centre)*sh.reg['s'])
    transform=max(math.dist(p,v) for path in raw for p,v in zip(source_transform(path,tr),source_transform(path,sh.reg)))
    return {'method':'Original PDF selected complete glyph paths; feed lines, text and leaders excluded',
            'deviation_cm':math.dist(centre(e['g']),xy),
            'metadata_deviation_cm':max(math.dist(meta,xy),math.dist(q['source_xy_cm'],xy)),
            'source_anchor_deviation_cm':anchor,'source_transform_deviation_cm':transform,
            'reference':ref,'source_xy':xy,
            'spatial_basis':'Electrical glyph centre only; physical dimensions, Z, material and finish remain unverified'}

def electrical_semantic_reviews(M,tolerance):
    """Verify removed annotation identities and named DB reuse from original PDF."""
    D=read('electrical_symbol_semantics');byid={e['id']:e for e in M['els']};reviews=[]
    active=any((e.get('a') or {}).get('source_semantics_checked') for e in M['els'])
    if not active:return reviews
    for eid,q in D.get('records',{}).items():
        if q['action']!='remove_nondevice_fragment':continue
        book,page=q['source'].split(':');sh=pdf_sheet(book,int(page))
        raw=[sh.D[di]['polys'][pi] for di,pi in q['raw_drawing_primitives']]
        err=max((line(p).hausdorff_distance(line(v)) for p,v in zip(raw,q['raw_pdf_points'])),default=float('inf'))*sh.reg['s']
        reviews.append({'id':eid,'reference':q['source'],'method':'Original PDF annotation primitive identity; absent nondevice body',
                        'raw_deviation_cm':err,'present':eid in byid,'parser':q['parser'],
                        'pass':err<=tolerance and len(raw)==len(q['raw_pdf_points']) and eid not in byid})
    for q in D.get('board_reuse',[]):
        eid=q['symbol_id'];book,page=q['source'].split(':');sh=pdf_sheet(book,int(page))
        word=sh.WD[q['source_word_index']];bbox=list(word['bbox'])
        raw=[sh.D[di]['polys'][pi] for di,pi in q['source_leader_primitives']]
        err=max((line(p).hausdorff_distance(line(v)) for p,v in zip(raw,q['source_leader_pdf_points'])),default=float('inf'))*sh.reg['s']
        err=max(err,max(abs(v-w) for v,w in zip(bbox,q['source_word_bbox_pdf_pt']))*sh.reg['s'])
        e=byid.get(eid);word_ok=word['s']==q['source_word_text'] and word['layer']==q['source_word_layer']
        old_present=[i for i in q['former_derived_board_ids'] if i in byid]
        a=(e or {}).get('a') or {}
        metadata_ok=e is not None and e.get('t')=='e_P17' and e.get('mark')==word['s'] and a.get('source_board_identity')==q
        reviews.append({'id':eid,'reference':q['source'],'method':'Actual DB label word and attached raw leader; existing complete glyph reused',
                        'raw_deviation_cm':err,'word_verified':word_ok,'former_bodies_present':old_present,
                        'pass':err<=tolerance and word_ok and metadata_ok and not old_present})
    return reviews

@functools.lru_cache(maxsize=8)
def cleanout_raw_bindings(sh):
    """Recompute unique CO word-to-cap bindings from raw paths, once per sheet."""
    caps=[]
    for di,d in enumerate(sh.D):
        if d['layer'] not in ('M_DR_WP','M_DR_SP','M_DR_VP') or d.get('fill'):continue
        for pi,p in enumerate(d['polys']):
            if len(p) not in (4,5) or p[1]!=p[3]:continue
            stem=[p[0][k]-p[1][k] for k in (0,1)];arm=[p[2][k]-p[1][k] for k in (0,1)]
            sl,al=math.hypot(*stem),math.hypot(*arm)
            if not sl or not al or abs(sum(v*w for v,w in zip(stem,arm)))/(sl*al)>.1:continue
            if not 2<al*sh.reg['s']<25 or not 2<sl*sh.reg['s']<70:continue
            if len(p)==5:
                other=[p[4][k]-p[1][k] for k in (0,1)];ol=math.hypot(*other)
                if not ol or not 2<ol*sh.reg['s']<25 or abs(sum(v*w for v,w in zip(arm,other))/(al*ol)+1)>.05:continue
            caps.append(((di,pi),sh.T(*p[1])))
    chosen={};used=collections.Counter();xmax,ymax=(4440,4440) if sh.pageno==2 else (3230,1900)
    for wi,w in enumerate(sh.WD):
        xy=sh.T(w['x'],w['y'])
        if w['s'] not in ('CO','FCO') or w['layer'] not in ('M_DR_TEXT',None,''):continue
        if not -30<xy[0]<xmax or not -100<xy[1]<ymax:continue
        if sh.pageno in (5,6,7) and w['x']>1800:continue
        nearest=min(caps,key=lambda q:math.dist(xy,q[1]),default=None)
        if nearest and math.dist(xy,nearest[1])<60:chosen[wi]=nearest[0];used[nearest[0]]+=1
    return {wi:key for wi,key in chosen.items() if used[key]==1}

@functools.lru_cache(maxsize=8)
def floortrap_raw_bindings(sh):
    """Recompute the one-candidate FT bindings from the original double circles."""
    circles=[]
    for di,d in enumerate(sh.D):
        if d['layer']!='M_DR_WP' or d.get('fill') or len(d['polys'])!=1 or len(d['polys'][0])!=41:continue
        r=d['rect'];w=(r[2]-r[0])*sh.reg['s'];h=(r[3]-r[1])*sh.reg['s']
        if 11<w<15.4 and abs(w-h)<.1:circles.append((di,w,sh.T((r[0]+r[2])/2,(r[1]+r[3])/2)))
    candidates=[]
    for di,w,xy in circles:
        inner=[i for i,v,p in circles if .5<w-v<1.6 and math.dist(xy,p)<.35]
        if len(inner)==1:candidates.append((di,inner[0],xy))
    bindings={};used=collections.Counter()
    for ti,t in enumerate(sh.TX):
        if t['layer']!='M_DR_TEXT' or t['s'].strip() not in ('FT','FW'):continue
        b=t['bbox'];xy=sh.T((b[0]+b[2])/2,(b[1]+b[3])/2)
        hits=[(di,ii) for di,ii,p in candidates if math.dist(xy,p)<60]
        if len(hits)==1:bindings[ti]=hits[0];used[hits[0]]+=1
    return {ti:key for ti,key in bindings.items() if used[key]==1}

def drain_trace_check(e,tolerance):
    """Verify an entire reviewed drain trace against actual named PDF vectors."""
    a=e.get('a') or {};q=read('drain_trace_review').get('records',{}).get(e['id'])
    if not q or q['status']!='raw_drawn_linework' or not q['whole_trace_xy_verified']:return None
    if a.get('source_page')!=q['source'] or a.get('source_primitives')!=q['source_primitives']:return None
    book,page=q['source'].split(':');sh=pdf_sheet(book,int(page));raw=[];saved=[];world=[]
    for r in q['raw_primitives']:
        d=sh.D[r['drawing']]
        if d['layer']!=q['layer'] or d.get('fill'):return None
        p=d['polys'][r['poly']];raw.append(p);saved.append(r['pdf_points']);world.append(source_transform(p,sh.reg))
    if not raw or e['g'][0]!='t':return None
    drawing=unary_union([line(p)for p in world]);path=line([p[:2]for p in e['g'][1]])
    probes=[Point(p[:2])for p in e['g'][1]]+[path.interpolate(i*.5)for i in range(1,int(path.length/.5))]
    maximum=max(p.distance(drawing)for p in probes)
    outside=path.difference(drawing.buffer(tolerance,cap_style=1,join_style=1))
    tr=a.get('source_transform')
    if not tr:return None
    raw_error=max(line(p).hausdorff_distance(line(v))for p,v in zip(raw,saved))*sh.reg['s']
    transform=max(math.dist(v,w)for p in raw for v,w in zip(source_transform(p,tr),source_transform(p,sh.reg)))
    guard=hashlib.sha256(json.dumps(e['g'],separators=(',',':')).encode()).hexdigest()
    return {'method':'Complete reviewed drain XY trace inside actual PDF layer vectors; no old model as position source',
            'deviation_cm':maximum,'source_anchor_deviation_cm':raw_error,'source_transform_deviation_cm':transform,
            'reference':q['source'],'whole_trace_source_covered':outside.is_empty,
            'review_geometry_unchanged':guard==q['geometry_guard_sha256'],
            'outside_source_trace_cm':outside.length,
            'spatial_basis':'Drawn linework XY only; nominal size, material, Z and physical symbol parts unverified'}

def _current_drain_riser(e):
    """Scope current generated drain V segments independently of old ordinals."""
    a=e.get('a')or{}
    return ((e.get('c')=='P.drain' and e.get('t')in('pipe_soil','pipe_waste')
        and bool(a.get('riser')) and bool(re.search(r'-V\d{4}$',e.get('id',''))))
        or(a.get('source_generation_module')=='pipeline/risers.py'
           and a.get('source_trace_status')=='derived_vertical_riser'))

def drain_riser_generation_checks(M):
    """Independent classification/identity guards, never a raw XY source test.

    Recompute exact unique c/t/l/g mapping from current geometry and the frozen
    historical review. Historical nearby plan lines remain candidate references;
    they cannot verify a vertical segment or a hydraulic connection.
    """
    old={eid:q for eid,q in read('drain_trace_review').get('records',{}).items()
         if q.get('status')=='derived_vertical_riser'}
    def canonical(e):return json.dumps([e['c'],e.get('t'),e['l'],e['g']],separators=(',',':'))
    current=[e for e in M['els']if _current_drain_riser(e)]
    historical_keys=collections.defaultdict(list);current_keys=collections.Counter(canonical(e)for e in current)
    for eid,q in old.items():
        historical_keys[canonical({'c':q['category'],'t':q['type'],'l':q['level'],'g':q['reviewed_g']})].append(eid)
    checks=[];bindings={}
    for e in current:
        a=e.get('a')or{};key=canonical(e);hits=historical_keys.get(key,[])
        unique=len(hits)==1 and current_keys[key]==1
        expected=hits[0]if unique else None
        status='exact_unique'if unique else'ambiguous'if hits else'unmatched'
        signature=hashlib.sha256(key.encode()).hexdigest();errors=[]
        if e.get('c')!='P.drain' or e.get('t')not in('pipe_soil','pipe_waste')or a.get('riser')is not True or not re.search(r'-V\d{4}$',e.get('id','')):
            errors.append('Generated drain riser category/type/ID/provenance flag changed')
        g=e.get('g')or[]
        if not(len(g)==3 and g[0]=='t' and len(g[1])==2
            and all(len(p)==3 and all(math.isfinite(v)for v in p)for p in g[1])
            and g[1][0][:2]==g[1][1][:2] and g[1][0][2]!=g[1][1][2]):
            errors.append('Current generated riser is no longer a finite vertical two-point segment')
        if a.get('source_generation_module')!='pipeline/risers.py':errors.append('Actual generator provenance missing')
        if a.get('source_generation_identity_sha256')!=signature:errors.append('Generated c/t/l/g identity guard changed')
        if a.get('source_trace_status')!='derived_vertical_riser' or a.get('source_kind')!='derived_vertical_riser' or a.get('derived')is not True:
            errors.append('Current generated riser must remain derived')
        if a.get('source_derived_historical_record')!=expected or a.get('source_derived_binding_status')!=status:
            errors.append('Historical binding is not a unique exact c/t/l/g match')
        if any(a.get(k)is True for k in('source_locked_xy','source_XY_verified','source_Z_verified',
                'source_dimensions_verified','source_material_verified','source_mount_verified',
                'source_ports_verified','source_contact_verified','whole_trace_xy_verified','physical_geometry_verified')):
            errors.append('Generated riser improperly promotes source position/body/contact proof')
        if any(a.get(k)is not None for k in('source_page','source_transform','source_primitives','source_trace_record')):
            errors.append('Historical candidate primitives are mislabeled as a current source anchor')
        candidate=a.get('source_derived_historical_candidate')
        if expected:
            q=old[expected]
            if not candidate or candidate.get('historical_id')!=expected or candidate.get('reference')!=q['source'] or candidate.get('source_primitives')!=q['source_primitives'] or candidate.get('proof_scope')!='nearby_plan_candidates_only_not_a_riser_position_or_Z_source':
                errors.append('Historical plan candidate reference guard changed')
        elif candidate is not None:errors.append('Ambiguous/unmatched riser has a claimed historical candidate binding')
        bindings[e['id']]={'current_id':e['id'],'historical_id':expected,'binding_status':status,
                            'canonical_identity_sha256':signature}
        checks.append({'id':e['id'],'method':'Current risers.py output classification and unique exact historical c/t/l/g identity',
            'proof_scope':'derived_generation_identity_only_not_drawn_XY_Z_or_contact',
            'historical_id':expected,'binding_status':status,'reference':'pipeline/risers.py',
            'errors':errors,'pass':not errors})
    counts=collections.Counter(q['binding_status']for q in bindings.values())
    return {'schema':'c4.derived-drain-riser-generation-audit.v1','current_count':len(current),
        'historical_count':len(old),'exact_unique_count':counts['exact_unique'],
        'unmatched_count':counts['unmatched'],'ambiguous_count':counts['ambiguous'],
        'checks':checks,'bindings':bindings,'findings':sum(not q['pass']for q in checks),
        'scope':'Classification/unchanged identity only; every current riser excluded from raw drawn-position count'}

@functools.lru_cache(maxsize=4)
def pile_raw_texttrace(sh):
    import lib
    return lib.doc('STR')[sh.pageno-1].get_texttrace()

def pile_source_check(e):
    """Check raw pile circles and stated diameter/length; never promote top Z."""
    import numpy as np
    a=e.get('a') or {};D=read('structural_source_restore')
    q=next((q for q in D.get('piles',[])if q['id']==e['id']),None)
    if not q or e['c']!='S.pile' or e['l']!='B' or e['g'][0]!='cyl':return None
    sh=pdf_sheet('STR',11);source=q['source'];indices=source['drawing_indices']
    if a.get('source_drawing_indices')!=indices or a.get('source_page') not in ('STR:11',11):return None
    if len(indices)not in (1,5) or any(sh.D[i]['layer']!='PILES$0$ST-PILE'for i in indices):return None
    raw=[sh.D[i]['polys']for i in indices];saved=a.get('source_pdf_points')
    if not saved or len(saved)!=len(raw)or len(source['source_pdf_points'])!=len(raw):return None
    pts=[p for paths in raw for path in paths for p in path]
    if len(indices)==1:
        drawing=sh.D[indices[0]]
        if len(drawing['items'])!=4 or any(it[0]!='c'for it in drawing['items']):return None
        r=drawing['rect'];pdf_center=[(r[0]+r[2])/2,(r[1]+r[3])/2];radius=(r[2]-r[0]+r[3]-r[1])/4
    else:
        if any(len(paths)!=1 for paths in raw):return None
        # Centre the calculation before fitting; the result is derived from the
        # five actual dashed arcs and not their incomplete bounding rectangle.
        p=np.asarray(pts);mu=p.mean(axis=0);u=p-mu
        fit=np.linalg.lstsq(np.column_stack((2*u[:,0],2*u[:,1],np.ones(len(u)))),(u*u).sum(axis=1),rcond=None)[0]
        pdf_center=list(mu+fit[:2]);radius=math.sqrt(fit[2]+fit[0]**2+fit[1]**2)
    raw_error=0
    for i,paths in enumerate(raw):
        if len(saved[i])!=len(paths)or len(source['source_pdf_points'][i])!=len(paths):return None
        for j,path in enumerate(paths):
            raw_error=max(raw_error,line(saved[i][j]).hausdorff_distance(line(path)),
                          line(source['source_pdf_points'][i][j]).hausdorff_distance(line(path)))
    raw_error=max(raw_error,math.dist(source['pdf_center'],pdf_center))*sh.reg['s']
    traces=pile_raw_texttrace(sh)
    for field,expected in (('length_literal','Pile length = 13m'),('diameter_literal','Pile diameter (P1) = 0.6m')):
        literal=D.get(field,{})
        if not isinstance(literal,dict) or a.get('source_'+field)!=literal:return None
        tt=traces[literal['texttrace_index']];lo,hi=literal['char_range'];chars=tt['chars'][lo:hi]
        text=''.join(chr(c[0])for c in chars)
        if text!=expected or tt.get('layer')!=literal.get('source_layer',literal.get('layer')):return None
        bbox=[min(c[3][0]for c in chars),min(c[3][1]for c in chars),max(c[3][2]for c in chars),max(c[3][3]for c in chars)]
        raw_error=max(raw_error,max(abs(v-w)for v,w in zip(bbox,literal['pdf_bbox']))*sh.reg['s'])
        raw_chars=[[c[0],list(c[2]),list(c[3])]for c in chars]
        if raw_chars!=literal['text_chars']:return None
    tr=a.get('source_transform');xy=a.get('source_xy')
    if not tr or not xy:return None
    world=source_transform([pdf_center],sh.reg)[0]
    return {'method':'Original STR:11 P1 circle arcs plus literal pile diameter0.6m and length13m',
        'deviation_cm':math.dist(e['g'][1:3],world),
        'metadata_deviation_cm':max(math.dist(xy,world),math.dist(source['source_xy'],world)),
        'source_anchor_deviation_cm':raw_error,
        'source_transform_deviation_cm':math.dist(source_transform([pdf_center],tr)[0],world),
        'source_length_deviation_cm':abs(e['g'][5]-e['g'][4]-13)*100,
        'source_diameter_deviation_cm':abs(e['g'][3]*2-60),
        'drawn_circle_radius_cm':radius*sh.reg['s'],'reference':'STR:11 / S-7 P1',
        'z_top_unverified':e['g'][5],
        'spatial_basis':'Derived circle-fit XY in recorded STR registration; source13m length and60cm diameter; top-Z/embedment unverified'}

def source_metadata(e,proof):
    a=e.get('a') or {};xy=a.get('source_xy');pdf=a.get('source_pdf_points');tr=a.get('source_transform')
    if xy is None or not tr or not pdf or not proof:return None
    world=source_transform(pdf,tr);mode='point' if flat(xy) or e['g'][0] not in ('t','d') else 'path'
    # A symbol's source polygon maps its centre; a route maps all its vertices.
    expected=boxcentre(world) if mode=='point' else world
    meta=math.dist(boxcentre(points(xy)),expected) if mode=='point' else line(xy).hausdorff_distance(line(world))
    if e['g'][0]=='b' and proof.get('source_is_route'):
        mode='beam_path';expected=world
    measured=deviation(e,expected,mode)
    if proof.get('source_is_strip'):
        # The strip axis is drawn. Its 1 cm depth is an explicitly stated display
        # assumption, so compare the same buffered source axis, including bends.
        expected_strip=LineString(world).buffer(.5,cap_style=2,join_style=2)
        measured=Polygon(e['g'][1],e['g'][4] or None).hausdorff_distance(expected_strip)
    if proof.get('source_is_polygon'):
        holes=proof.get('source_holes_world') or None
        expected_polygon=Polygon(world,holes)
        g=e['g']
        actual_polygon=Polygon(g[1],g[4] or None) if g[0]=='p' else Polygon([[g[1],g[2]],[g[3],g[2]],[g[3],g[4]],[g[1],g[4]]])
        measured=actual_polygon.boundary.hausdorff_distance(expected_polygon.boundary)
        if not flat(xy):meta=Polygon(points(xy)).boundary.hausdorff_distance(Polygon(world).boundary)
        if holes:
            inner_xy=a.get('source_inner_xy')
            meta=max(meta,Polygon(inner_xy).boundary.hausdorff_distance(Polygon(holes[0]).boundary)) if inner_xy else float('inf')
        expected=world
    return {'method':'PDF coordinate transform, checked against '+proof['method'],'deviation_cm':measured,
            'metadata_deviation_cm':meta,'source_anchor_deviation_cm':proof['anchor_deviation_cm'],
            'source_transform_deviation_cm':proof['transform_deviation_cm'],
            'reference':proof.get('reference') or a.get('source_page'),'source_xy':expected,
            'spatial_basis':'upper-floor drawn symbol; vertical trace is derived' if a.get('source_other_page') else 'drawn source anchor'}

def source_proof(e,WS,SG,ELR,ST,AD,PG):
    """Bind metadata to independently saved extraction points, never to itself."""
    a=e.get('a') or {};pdf=a.get('source_pdf_points');tr=a.get('source_transform')
    if not pdf or not tr:return None
    suffix=SUFFIX.search(e['id']);suffix=suffix.group(1) if suffix else None
    reference=a.get('source_page');anchors=[];partial=False;route=False;raw_error=0;strip=False;polygon=False;holes=[]
    if suffix=='WS':
        S=WS.get('site',{});I=WS.get('irrigation',{});t=e.get('t');bindings={};n=0
        def bind(c,level,typ,records):
            nonlocal n
            for q in records:
                n+=1;bindings[f'{c}-{level}-WS{n:04d}']=(typ,q)
        bind('P.cold','G','ws_site_pipe',S.get('pipes',[]));bind('P.cold','G','ws_fill_drop',S.get('fill_drops',[]))
        bind('P.cold','G','ws_site_meter',S.get('meters',[]));bind('P.cold','G','ws_meter_box',[S.get('cabinet',{})])
        bind('P.cold','G','ws_site_chamber',S.get('chambers',[]));bind('P.tank','R','ws_tank_raw',S.get('tanks',[])[:1])
        bind('P.tank','R','ws_tank_filtered',S.get('tanks',[])[1:]);bind('P.pump','B','irr_pump',I.get('pumps',[]))
        bind('P.irr','B','irr_pipe',I.get('pipes',[]));bind('P.irr','G','irr_pipe',I.get('ground_pipes',[]))
        bind('P.irr','G','irr_chamber',I.get('chambers',[]))
        if e['id'] not in bindings or bindings[e['id']][0]!=t:return None
        q=bindings[e['id']][1];sh=pdf_sheet('MECH2',q['page'])
        if reference!=f'MECH2:{q["page"]}':return None
        if q.get('primitive'):
            di,pi=q['primitive'];d=sh.D[di]
            if d['layer']!='M_WS_CW':return None
            raw=d['polys'][pi]
            method='Original MECH2 water/irrigation drawing primitive; fixed extraction identity'
        else:
            # These two symbols are assemblies. Recompute their bbox from actual
            # PDF strokes; the saved diagonal alone does not establish its source.
            selected=[]
            for d in sh.D:
                if d['layer']!='M_WS_CW':continue
                for path in d['polys']:
                    world=source_transform(path,sh.reg);b=[min(p[0]for p in world),min(p[1]for p in world),max(p[0]for p in world),max(p[1]for p in world)]
                    if t=='ws_meter_box':
                        include=len(path)==4 and 325<b[0]<400 and 1560<b[1]<1610 and 'f' in d['type']
                    else:
                        cy=q['centre'][1];include=580<b[0]<655 and b[2]<655 and cy-18<b[1] and b[3]<cy+18
                    if include:selected.extend(path)
            if not selected:return None
            xs=[p[0]for p in selected];ys=[p[1]for p in selected]
            raw=[[min(xs),max(ys)],[max(xs),min(ys)]]
            method='Original MECH2 multi-stroke assembly bbox; display dimensions remain separate'
        raw_error=line(q['pdf_points']).hausdorff_distance(line(raw))*sh.reg['s']
        anchors=[(raw,sh.reg)];route=t in ('ws_site_pipe','irr_pipe')
        if t in ('ws_tank_raw','ws_tank_filtered','ws_site_chamber','irr_chamber'):polygon=True
        if t in ('ws_tank_raw','ws_tank_filtered'):
            method='MECH2:17 actual GRP body outline (not surrounding frame), fixed identity and original PDF primitive'
    elif suffix=='SG':
        for pg in SG.get('pages',[]):
            if reference!=f'ARCH2:{pg["page"]}':continue
            anchors.extend(([q['source_pdf_point']],pg['reg']) for q in pg['markers'] if q['code']==e.get('mark'))
        method='signage_remaining.json original text positions'
    elif (suffix=='ELR' or a.get('source_drawing') is not None) and reference in ELR.get('sheets',{}):
        sh=ELR.get('sheets',{}).get(reference,{})
        rr=[q for q in sh.get('items',[]) if q.get('drawing')==a.get('source_drawing') and q.get('kind')==a.get('kind')]
        for q in rr:
            raw=q.get('path_pdf',[q['pdf']]);anchors.append((raw,sh['registration']))
            route=bool(q.get('path_pdf'))
            if len(points(pdf))==2 and len(points(raw))>2:
                anchors.extend(([p,r],sh['registration']) for p,r in zip(raw,raw[1:]));partial=True
        method='electrical_remaining.json drawing index and original PDF points'
    elif suffix=='ST' and e.get('t')=='storm_co':
        sheet=ST.get('sheets',{}).get(levelkey(e['l']),{});rr=sheet.get('cleanouts',[])
        matches=[q for q in rr if q.get('source_primitive')==a.get('source_primitive')]
        if len(matches)!=1:return None
        q=matches[0];sh=pdf_sheet('MECH2',sheet['page']);di,pi=q['source_primitive'];d=sh.D[di]
        if d['layer']!='M_DR_RAIN':return None
        raw=d['polys'][pi];world=source_transform(raw,sh.reg)
        if len(raw)==4 and math.dist(world[1],world[3])<.1:
            stem=[world[1][k]-world[0][k]for k in(0,1)];arm=[world[2][k]-world[1][k]for k in(0,1)]
            sl,al=math.hypot(*stem),math.hypot(*arm)
            if not 18<sl<22 or not 6<al<9 or abs(sum(v*w for v,w in zip(stem,arm)))/(sl*al)>.06:return None
            point=raw[1]
        elif len(raw)==5:
            stem=[world[2][k]-world[1][k]for k in(0,1)];arm=[world[4][k]-world[3][k]for k in(0,1)]
            sl,al=math.hypot(*stem),math.hypot(*arm)
            if not sl>200 or not 14<al<17 or abs(sum(v*w for v,w in zip(stem,arm)))/(sl*al)>.02:return None
            if math.dist(world[2],[(world[3][k]+world[4][k])/2 for k in(0,1)])>.4:return None
            point=raw[2]
        else:return None
        raw_error=math.dist(point,q['source_pdf_point'])*sh.reg['s']
        anchors=[([point],sh.reg)];reference=f'MECH2:{sheet["page"]}'
        method='Original storm CO cap junction; perpendicular bar checked independently from actual PDF primitive'
    elif suffix=='AD' and a.get('source_kind')=='derived_from_plan_strip':
        source=AD.get('desk',{});indices=a.get('source_drawing_indices',[])
        if len(indices)!=1:return None
        rr=[q for q in source.get('slats',[]) if q['drawing_index']==indices[0]]
        if not rr:return None
        raw=pdf_drawing_points(source['set'],source['page'],indices)
        raw_error=line(pdf).hausdorff_distance(line(raw))*source['source_transform']['s']
        anchors=[(q['pdf_points'],source['source_transform']) for q in rr]
        method='ARCH1:5 independent A02_FURNITURE_FIXED PDF strip'
        reference=f'{source["set"]}:{source["page"]}';strip=True
    elif suffix=='PG' and a.get('source_kind')=='drawn_polygon':
        if a.get('source_set')!=PG.get('source_set') or a.get('source_page')!=PG.get('source_page'):return None
        indices=a.get('source_drawing_indices',[])
        rr=[p for unit in PG.get('units',[]) if unit['id']==a.get('unit') for p in unit['parts']
            if p['drawing_indices']==indices and e.get('t')=='roof_pergola_'+p['kind']]
        if len(rr)!=1:return None
        q=rr[0];book=PG['source_set'];page=PG['source_page'];sh=pdf_sheet(book,page)
        if not indices or a.get('source_layer')!=q['layer'] or any(sh.D[i]['layer']!=q['layer'] for i in indices):return None
        raw=sh.D[indices[0]]['polys'][0]
        raw_error=Polygon(pdf).boundary.hausdorff_distance(Polygon(raw).boundary)*sh.reg['s']
        raw_error=max(raw_error,Polygon(q['pdf_points']).boundary.hausdorff_distance(Polygon(raw).boundary)*sh.reg['s'])
        if q.get('inner_pdf_points'):
            inner=a.get('source_inner_pdf_points')
            if not inner or len(indices)!=2:return None
            raw_inner=sh.D[indices[1]]['polys'][0]
            raw_error=max(raw_error,Polygon(inner).boundary.hausdorff_distance(Polygon(raw_inner).boundary)*sh.reg['s'],
                          Polygon(q['inner_pdf_points']).boundary.hausdorff_distance(Polygon(raw_inner).boundary)*sh.reg['s'])
            holes=[source_transform(inner,tr)]
        elif a.get('source_inner_pdf_points'):return None
        anchors=[(q['pdf_points'],sh.reg)]
        method='ARCH1:9 actual outer/inner pergola polygons and drawing indices in original PDF'
        reference=f'{book}:{page}';polygon=True
    elif suffix=='DRG' and reference=='MECH2:4':
        sh=pdf_sheet('MECH2',4);D=read('drain_site_remaining');di=a.get('source_drawing');pi=a.get('source_poly_index',0)
        rr=[q for q in D.get('routes',[])+D.get('chambers',[])+D.get('gratings',[]) if q['drawing_index']==di and q['poly_index']==pi]
        if len(rr)!=1 or sh.D[di]['layer']!=rr[0]['layer'] or a.get('source_layer')!=rr[0]['layer']:return None
        q=rr[0];raw=sh.D[di]['polys'][pi]
        raw_error=line(q['pdf_points']).hausdorff_distance(line(raw))*sh.reg['s']
        if q['kind']=='chamber':
            ii=q['inner_drawing'];inner=a.get('source_inner_pdf_points')
            if not inner or a.get('source_inner_drawing')!=ii:return None
            inner_raw=sh.D[ii]['polys'][0]
            raw_error=max(raw_error,line(inner).hausdorff_distance(line(inner_raw))*sh.reg['s'],line(q['inner_pdf_points']).hausdorff_distance(line(inner_raw))*sh.reg['s'])
            holes=[source_transform(inner,sh.reg)]
        polygon=q['kind']!='pipe';route=q['kind']=='pipe'
        anchors=[(raw,sh.reg)];method='MECH2:4 original uncropped DR-102 pipe / GT / PR / channel primitive'
    elif suffix=='DTR' and reference=='MECH2:8':
        sh=pdf_sheet('MECH2',8);D=read('drain_top_remaining');di=a.get('source_drawing')
        rr=[q for q in D.get('symbols',[]) if q['drawing_index']==di and _source_type(e,q['type'])==e.get('t')]
        if len(rr)!=1 or sh.D[di]['layer']!=rr[0]['layer'] or a.get('source_layer')!=rr[0]['layer']:return None
        d=sh.D[di]
        if len(d['polys'])!=1 or len(d['polys'][0])!=41:return None
        r=d['rect'];raw=[[(r[0]+r[2])/2,(r[1]+r[3])/2]]
        raw_error=line(rr[0]['pdf_points']).hausdorff_distance(line(raw))*sh.reg['s']
        anchors=[(raw,sh.reg)];method='MECH2:8 actual 4-inch top-roof termination circle, original PDF drawing index'
    elif suffix=='DSM' and reference=='MECH2:2':
        sh=pdf_sheet('MECH2',2);D=read('drain_semantic_review');di=a.get('source_drawing');pi=a.get('source_poly_index',0)
        rr=[q for q in D.get('bodies',[]) if q['drawing_index']==di and q['poly_index']==pi and q['kind']==e.get('t')]
        if len(rr)!=1 or sh.D[di]['layer']!=rr[0]['layer'] or a.get('source_layer')!=rr[0]['layer']:return None
        q=rr[0];raw=sh.D[di]['polys'][pi]
        raw_error=line(q['pdf_points']).hausdorff_distance(line(raw))*sh.reg['s']
        if q.get('inner_drawing'):
            ii=q['inner_drawing'];inner=a.get('source_inner_pdf_points')
            if not inner or a.get('source_inner_drawing')!=ii:return None
            actual=sh.D[ii]['polys'][0]
            raw_error=max(raw_error,line(inner).hausdorff_distance(line(actual))*sh.reg['s'])
            holes=[source_transform(inner,sh.reg)]
        anchors=[(raw,sh.reg)];polygon=e['g'][0] in ('r','p')
        method='MECH2:2 original sump / pump / SDT / oil separator / grating glyph; source-plan extent only'
    elif a.get('sys')=='drain_pressure_legacy' and reference in ('MECH2:2','MECH2:4'):
        sh=pdf_sheet('MECH2',int(reference.split(':')[1]));D=read('drain_semantic_review')
        rr=[q for q in D.get('pressure_routes',[]) if q['id']==e['id'] and q['drawing_index']==a.get('source_drawing')]
        if len(rr)!=1:return None
        q=rr[0];raw=sh.D[q['drawing_index']]['polys'][q['poly_index']]
        if sh.D[q['drawing_index']]['layer']!=q['layer']:return None
        raw_error=line(q['pdf_points']).hausdorff_distance(line(raw))*sh.reg['s']
        anchors=[(raw,sh.reg)];route=True;method='Original pressure-discharge / pump-common-route PDF stroke'
    elif a.get('source_kind')=='cleanout_actual_cap' and reference in ('MECH2:2','MECH2:3','MECH2:4','MECH2:5','MECH2:6','MECH2:7'):
        sh=pdf_sheet('MECH2',int(reference.split(':')[1]));D=read('cleanout_source_restore')
        q=D.get('source_anchors',{}).get(e['id']) or next((r for r in D.get('new_caps',[]) if r['id']==e['id']),None)
        if not q or q['drawing_index']!=a.get('source_drawing') or q['poly_index']!=a.get('source_poly_index'):return None
        d=sh.D[q['drawing_index']];raw_cap=d['polys'][q['poly_index']]
        if d['layer']!=q['layer'] or d.get('fill') or len(raw_cap) not in (4,5) or raw_cap[1]!=raw_cap[3]:return None
        # Independent original vectors establish the stem/arm junction; the
        # metadata cannot choose an arbitrary point elsewhere on this route.
        stem=[raw_cap[0][k]-raw_cap[1][k] for k in (0,1)]
        arm=[raw_cap[2][k]-raw_cap[1][k] for k in (0,1)]
        s_len,a_len=math.hypot(*stem),math.hypot(*arm)
        if s_len==0 or a_len==0 or abs(sum(s*u for s,u in zip(stem,arm)))/(s_len*a_len)>.1:return None
        w=sh.WD[q['label']['word_index']]
        if w['s'] not in ('CO','FCO') or w['s']!=q['label']['text']:return None
        if cleanout_raw_bindings(sh).get(q['label']['word_index'])!=(q['drawing_index'],q['poly_index']):return None
        lab=[w['x'],w['y']];raw=[raw_cap[1]]
        raw_error=max(line(q['cap_pdf_points']).hausdorff_distance(line(raw_cap)),math.dist(lab,q['label']['pdf_centre']))*sh.reg['s']
        anchors=[(raw,sh.reg)];method='Original CO word instance and actual four/five-vertex cap junction, full PDF primitive checked'
    elif a.get('source_kind')=='floortrap_actual_circle' and reference in ('MECH2:2','MECH2:4','MECH2:5','MECH2:6','MECH2:7'):
        sh=pdf_sheet('MECH2',int(reference.split(':')[1]));q=read('floortrap_source_restore').get('source_anchors',{}).get(e['id'])
        if not q or q['drawing_index']!=a.get('source_drawing') or q['inner_drawing']!=a.get('source_inner_drawing'):return None
        di,ii=q['drawing_index'],q['inner_drawing'];d,inner=sh.D[di],sh.D[ii]
        if d['layer']!='M_DR_WP' or inner['layer']!='M_DR_WP' or any(len(p['polys'])!=1 or len(p['polys'][0])!=41 or p.get('fill') for p in (d,inner)):return None
        r=d['rect'];ir=inner['rect'];raw=[[(r[0]+r[2])/2,(r[1]+r[3])/2]]
        centre_gap=math.dist(raw[0],[(ir[0]+ir[2])/2,(ir[1]+ir[3])/2])*sh.reg['s']
        width_delta=((r[2]-r[0])-(ir[2]-ir[0]))*sh.reg['s']
        if centre_gap>=.35 or not .5<width_delta<1.6:return None
        t=sh.TX[q['source_label']['text_index']]
        if t['layer']!='M_DR_TEXT' or t['s'].strip() not in ('FT','FW'):return None
        if floortrap_raw_bindings(sh).get(q['source_label']['text_index'])!=(di,ii):return None
        b=t['bbox'];lab=[(b[0]+b[2])/2,(b[1]+b[3])/2]
        raw_error=max(line(q['outer_pdf_points']).hausdorff_distance(line(d['polys'][0])),
                      line(q['inner_pdf_points']).hausdorff_distance(line(inner['polys'][0])),
                      math.dist(lab,q['source_label']['pdf_centre']))*sh.reg['s']
        anchors=[(raw,sh.reg)];method='Original FT label plus uniquely bound concentric-circle glyph; circle-centre XY only'
    elif a.get('sys')=='drain_legacy' and reference=='MECH2:2':
        sh=pdf_sheet('MECH2',2);di=a.get('source_drawing')
        if di is None or sh.D[di]['layer']!='M_DR_WP':return None
        d=sh.D[di]
        if a.get('source_anchor_kind')=='circle_centre':
            r=d['rect'];raw=[[(r[0]+r[2])/2,(r[1]+r[3])/2]]
        elif a.get('source_anchor_kind')=='cap_intersection':
            p=d['polys'][0]
            if len(p)!=4 or p[1]!=p[3]:return None
            raw=[p[1]]
        else:return None
        anchors=[(raw,sh.reg)];method='MECH2:2 actual FT circle / CO pipe cap in original PDF'
    else:return None
    if not anchors:return None
    raw,original=min(anchors,key=lambda q:line(pdf).hausdorff_distance(line(q[0])))
    return {'method':method,'anchor_deviation_cm':max(raw_error,line(pdf).hausdorff_distance(line(raw))*original['s']),
            'transform_deviation_cm':max(math.dist(p,q) for p,q in zip(source_transform(pdf,tr),source_transform(pdf,original))),
            'partial_source_route':partial,'source_is_route':route,'source_is_strip':strip,
            'source_is_polygon':polygon,'source_holes_world':holes,'reference':reference}

def outline_source_checks(AD,tolerance):
    """Verify two source outlines; derived assembly pieces remain outside exact XY."""
    result=[]
    for kind,q in AD.items():
        sh=pdf_sheet(q['set'],q['page']);raw=pdf_drawing_points(q['set'],q['page'],q['drawing_indices'])
        mapped=source_transform(raw,sh.reg)
        row={'id':'source:AD-'+kind,'suffix':'AD','method':'Original PDF drawing indices and page registration',
             'reference':f'{q["set"]}:{q["page"]}',
             'source_anchor_deviation_cm':line(q['source_pdf_points']).hausdorff_distance(line(raw))*sh.reg['s'],
             'source_xy_deviation_cm':line(q['source_xy']).hausdorff_distance(line(mapped)),
             'source_transform_deviation_cm':max(math.dist(p,r) for p,r in zip(source_transform(raw,q['source_transform']),mapped)),
             'geometry_claim':'Source outline only; derived assembly geometry is excluded'}
        for k in ('source_anchor_deviation_cm','source_xy_deviation_cm','source_transform_deviation_cm'):row[k]=round(row[k],5)
        row['pass']=max(row[k] for k in ('source_anchor_deviation_cm','source_xy_deviation_cm','source_transform_deviation_cm'))<=tolerance+1e-6
        result.append(row)
    return result

def architectural_derived_checks(M,review,tolerance):
    """Audit raw cladding references and cuts without promoting derived pieces.

    Source outlines/door anchors are checked directly against PDF primitives.
    Cladding contact and opening cuts are checked separately.  ARCH/STR face
    offsets remain measured coordination differences, outside exact XY claims.
    """
    raw_checks=[];piece_checks=[];opening_checks=[];LR=review.get('lobby_detail_review',{})
    eligible=[e for e in M['els'] if SUFFIX.search(e['id']) and SUFFIX.search(e['id']).group(1)=='AD']
    if not eligible:return raw_checks,piece_checks,opening_checks
    def primitive_lines(sh,di):
        return unary_union([line(p) for p in sh.D[di]['polys'] if len(p)>=2])
    for ref,source in LR.get('source_faces',{}).items():
        book,page=ref.split(':');sh=pdf_sheet(book,int(page));tr=source['registration']
        for q in source['faces']:
            raw=primitive_lines(sh,q['drawing_index']);saved=line(q['pdf_points'])
            anchor=max(saved.interpolate(k/16,normalized=True).distance(raw) for k in range(17))*sh.reg['s']
            world=source_transform(q['pdf_points'],sh.reg)
            errs={'source_anchor_deviation_cm':anchor,
                  'source_xy_deviation_cm':line(q['xy']).hausdorff_distance(line(world)),
                  'source_transform_deviation_cm':max(math.dist(p,r) for p,r in zip(source_transform(q['pdf_points'],tr),world))}
            row={'id':f'source:AD-face-{ref}-{q["drawing_index"]}','suffix':'AD','reference':ref,
                 'method':'Actual PDF wall-face primitive and page registration',
                 'geometry_claim':'Raw face reference only; cladding pieces remain derived',
                 **{k:round(v,5) for k,v in errs.items()}}
            row['pass']=sh.D[q['drawing_index']]['layer']==q['layer'] and max(errs.values())<=tolerance+1e-6
            raw_checks.append(row)
    for ref,source in LR.get('source_door_paths',{}).items():
        book,page=ref.split(':');sh=pdf_sheet(book,int(page));errors=[];layers=True
        for q in source['paths']:
            raw=primitive_lines(sh,q['drawing_index']);saved=unary_union([line(p) for p in q['pdf_polys']])
            errors.append(saved.hausdorff_distance(raw)*sh.reg['s'])
            layers=layers and sh.D[q['drawing_index']]['layer']==q['layer']
        err=max(errors,default=0)
        raw_checks.append({'id':'source:AD-doors-'+ref,'suffix':'AD','reference':ref,
            'method':'Original door-frame and swing PDF primitives; positions are independent of labels',
            'source_anchor_deviation_cm':round(err,5),'drawing_count':len(errors),
            'geometry_claim':'Raw opening glyphs only; cladding cuts remain derived',
            'pass':layers and err<=tolerance+1e-6})
    cal=LR.get('C_C_reversed_calibration',{})
    if cal:
        sh=pdf_sheet('ARCH2',35);sums=[];errs=[]
        for q in cal['anchor_pairs']:
            e=sh.D[q['elevation_drawing']]['rect']
            p=[sh.D[i]['rect'] for i in q['plan_drawing_indices']]
            ec=(e[0]+e[2])/2;pc=(min(r[0] for r in p)+max(r[2] for r in p))/2
            sums.append(ec+pc)
            errs.extend([abs(ec-q['elevation_center_pdf']),abs(pc-q['plan_frame_center_pdf'])])
        scale=cal['plan_registrations']['7']['s'];offset=sum(sums)/len(sums)
        err=max(errs+[abs(offset-cal['offset_pdf'])])*scale
        raw_checks.append({'id':'source:AD-C-C-reversed','suffix':'AD','reference':'ARCH2:35',
            'method':'Four actual door-frame PDF pairs prove reversed section direction',
            'source_anchor_deviation_cm':round(err,5),'anchor_count':len(sums),
            'fitted_offset_pdf_pt':offset,'max_fit_residual_cm':round(max(abs(s-offset) for s in sums)*scale,5),
            'geometry_claim':'Section calibration only; projected panel remains derived',
            'pass':len(sums)==4 and err<=tolerance+1e-6})
        # Compare the projected panel with its independently read two section
        # edges. This stays a section-derived placement, outside the raw count.
        rs=[sh.D[i]['rect'] for i in cal['panel_inner_drawings']]
        u0,u1=min(r[0] for r in rs),max(r[2] for r in rs)
        for e in eligible:
            if e.get('t')!='corridor_W13_detail':continue
            pg='6' if e['l']=='1' else '7';tr=cal['plan_registrations'][pg]
            x0,x1=sorted([(offset-u)*tr['s']+tr['ox'] for u in (u0,u1)])
            g=e['g'];err=max(abs(g[1]-x0),abs(g[3]-x1))
            piece_checks.append({'id':e['id'],'type':e['t'],'level':e['l'],'reference':'ARCH2:35 / ARCH1:'+pg,
                'method':'Panel X extents projected from actual section edges using independently verified reversed-door calibration',
                'geometry_claim':'Section-derived panel extent only; not a raw plan-piece position',
                'projected_extent_deviation_cm':round(err,5),'pass':err<=tolerance+1e-6})
    G=LR.get('G_mirror_section',{})
    if G:
        sh=pdf_sheet(G['set'],G['page']);ref=pdf_sheet(G['wall_ref_set'],G['wall_ref_page'])
        outer=line(G['outer_pdf']).hausdorff_distance(primitive_lines(sh,G['outer_drawing']))*G['scale_cm_per_pt']
        inner=line(G['mirror_pdf']).hausdorff_distance(primitive_lines(sh,G['inner_drawing']))*G['scale_cm_per_pt']
        wall_line=line(G['wall_ref_pdf_points']);wall_primitive=primitive_lines(ref,G['wall_ref_drawing'])
        wall=max(wall_line.interpolate(k/16,normalized=True).distance(wall_primitive) for k in range(17))*ref.reg['s']
        world=source_transform(G['wall_ref_pdf_points'],ref.reg)
        origin=sh.D[G['origin_dimension_drawing']]['rect'][0]
        err=max(outer,inner,wall,abs(origin-G['origin_pdf_u'])*G['scale_cm_per_pt'],
                abs(world[0][0]-G['wall_face_cm']),abs(max(p[1] for p in world)-G['front_anchor_y_cm']))
        raw_checks.append({'id':'source:AD-G-mirror','suffix':'AD','reference':'ARCH2:34 / ARCH1:5',
            'method':'Actual outer/inner mirror-frame outlines, margin dimension anchor and plan wall',
            'source_anchor_deviation_cm':round(err,5),
            'geometry_claim':'Section and wall references only; frame assembly remains derived','pass':err<=tolerance+1e-6})
        # Verify the opening in the complete four-part frame in the section
        # plane. Relative height checks the cut shape; it does not approve an
        # assumed mounting elevation or material thickness.
        scale=G['scale_cm_per_pt'];front=max(p[1] for p in world)
        ffl=next(q['ffl'] for q in M['levels'] if q['id']=='G')
        def section_rect(di):
            r=sh.D[di]['rect'];ys=sorted(front-scale*(u-origin) for u in (r[0],r[2]))
            hs=sorted(scale*(G['ffl_pdf_v']-v) for v in (r[1],r[3]))
            return box(ys[0],hs[0],ys[1],hs[1])
        expected_outer=section_rect(G['outer_drawing']);expected_inner=section_rect(G['inner_drawing'])
        frame=[e for e in eligible if e.get('t')=='entrance_W13_frame']
        mirror=[e for e in eligible if e.get('t')=='entrance_mirror']
        actual_frame=unary_union([box(e['g'][2],100*(e['g'][5]-ffl),e['g'][4],100*(e['g'][6]-ffl)) for e in frame])
        actual_mirror=unary_union([box(e['g'][2],100*(e['g'][5]-ffl),e['g'][4],100*(e['g'][6]-ffl)) for e in mirror])
        frame_err=actual_frame.boundary.hausdorff_distance(expected_outer.difference(expected_inner).boundary)
        mirror_err=actual_mirror.boundary.hausdorff_distance(expected_inner.boundary)
        hole_fill=actual_frame.intersection(expected_inner.buffer(-tolerance)).area
        piece_checks.append({'id':'source:AD-G-frame-cuts','reference':'ARCH2:34 / ARCH1:5',
            'method':'Union of four frame parts equals outer section outline minus actual mirror opening',
            'geometry_claim':'Derived assembly and local section-height cut shape only; not elevation acceptance',
            'frame_part_count':len(frame),'mirror_part_count':len(mirror),
            'frame_boundary_deviation_cm':round(frame_err,5),'mirror_boundary_deviation_cm':round(mirror_err,5),
            'filled_mirror_opening_cm2':round(hole_fill,5),
            'pass':len(frame)==4 and len(mirror)==1 and max(frame_err,mirror_err)<=tolerance+1e-6 and hole_fill<=1e-6})
    hosts={e['id']:e for e in M['els']}
    for e in eligible:
        a=e.get('a') or {}
        if a.get('source_kind')!='derived_from_model_face' or not a.get('host_ids'):continue
        g=e['g'];p=Polygon(g[1],g[4] or None) if g[0]=='p' else box(g[1],g[2],g[3],g[4])
        z0,z1=(g[2],g[3]) if g[0]=='p' else (g[5],g[6]);body=[];missing=[]
        for id in a['host_ids']:
            h=hosts.get(id)
            if not h:missing.append(id);continue
            hg=h['g'];hz0,hz1=(hg[2],hg[3]) if hg[0]=='p' else (hg[5],hg[6])
            if hz0<=z0+1e-6 and hz1>=z1-1e-6:
                body.append(Polygon(hg[1],hg[4] if len(hg)>4 else None) if hg[0]=='p' else box(hg[1],hg[2],hg[3],hg[4]))
        # Coating touches an actual host along one complete long side. Testing
        # the full line, rather than its centre, detects plates across openings.
        edges=[LineString([u,v]) for u,v in zip(p.exterior.coords,list(p.exterior.coords)[1:])]
        edge=max(edges,key=lambda q:q.length);long=[q for q in edges if q.length>=edge.length-1e-6]
        surface=unary_union([q.boundary for q in body]) if body else Polygon()
        losses=[q.difference(surface.buffer(.01)).length for q in long]
        loss=min(losses,default=float('inf'))
        row={'id':e['id'],'type':e.get('t'),'level':e['l'],'reference':a.get('source_reference'),
             'method':'Complete cladding contact edge and Z interval against recorded existing bodies',
             'geometry_claim':'Derived cut integrity only; excluded from exact drawn XY',
             'host_contact_uncovered_cm':round(loss,5),'missing_host_ids':missing,
             'pass':not missing and loss<=tolerance+1e-6}
        piece_checks.append(row)
    # Compare low cladding with gaps in the independently drawn wall faces.
    # A short door-frame edge can complete a jamb; a leaf/arc is never a wall.
    plans={};groups=collections.defaultdict(list)
    for e in eligible:
        a=e.get('a') or {}
        if e.get('t') not in ('corridor_W7_detail','entrance_W7_detail'):continue
        ref=(a.get('source_set'),a.get('source_page'))
        if ref[0]!='ARCH1' or not ref[1]:continue
        g=e['g'];p=Polygon(g[1],g[4] or None) if g[0]=='p' else box(g[1],g[2],g[3],g[4])
        z0=g[2] if g[0]=='p' else g[5]
        if z0>a.get('ffl_m',0)+.1:continue  # lintel pieces can bridge a plan opening above its head
        b=p.bounds;axis=a.get('face_axis') or ('y' if b[2]-b[0]<b[3]-b[1] else 'x')
        fixed=a.get('face_cm',b[0] if axis=='y' else b[3])
        groups[(e['l'],ref,axis,round(fixed,3))].append((e,b))
    for (lv,ref,axis,fixed),plates in groups.items():
        if ref not in plans:
            sh=pdf_sheet(*ref);segments=[]
            for di,d in enumerate(sh.D):
                layer=d['layer'] or '';wall=layer=='A-WALL' or layer.endswith('$A-WALL')
                door=layer=='A-Door' or layer.endswith('$A-Door')
                if not (wall or door):continue
                for p in d['polys']:
                    for u,v in zip(p,p[1:]):
                        x,y=source_transform([u,v],sh.reg)
                        L=math.dist(x,y)
                        if L<.1 or door and L>15:continue
                        if abs(x[1]-y[1])<.01:segments.append(('x',(x[1]+y[1])/2,sorted([x[0],y[0]]),wall,di))
                        elif abs(x[0]-y[0])<.01:segments.append(('y',(x[0]+y[0])/2,sorted([x[1],y[1]]),wall,di))
            plans[ref]=segments
        lo=min(b[0] if axis=='x' else b[1] for e,b in plates)
        hi=max(b[2] if axis=='x' else b[3] for e,b in plates)
        candidates=[q for q in plans[ref] if q[0]==axis and q[3] and q[2][1]>lo and q[2][0]<hi]
        if not candidates:continue
        face=min(candidates,key=lambda q:abs(q[1]-fixed))[1]
        # This .01 only groups coincident PDF faces after transform rounding.
        rr=sorted((max(lo,q[2][0]),min(hi,q[2][1])) for q in plans[ref]
                  if q[0]==axis and abs(q[1]-face)<.01 and q[2][1]>lo and q[2][0]<hi)
        merged=[]
        for a,b in rr:
            if merged and a<=merged[-1][1]+1e-6:merged[-1][1]=max(b,merged[-1][1])
            else:merged.append([a,b])
        gaps=[[a[1],b[0]] for a,b in zip(merged,merged[1:]) if b[0]-a[1]>20]
        blocked=[]
        for a,b in gaps:
            mid=(a+b)/2
            cover=[e['id'] for e,p in plates if (p[0] if axis=='x' else p[1])<mid<(p[2] if axis=='x' else p[3])]
            if cover:blocked.append({'raw_gap_cm':[a,b],'covered_by':cover})
        opening_checks.append({'id':f'source:AD-opening-cuts-{lv}-{axis}-{fixed}','level':lv,
            'reference':f'{ref[0]}:{ref[1]}','method':'Raw plan wall/jamb gaps at low level and complete existing-host contact',
            'geometry_claim':'Derived cut integrity; not an exact raw cladding-position pass',
            'raw_face_cm':round(face,5),'model_face_cm':fixed,
            'ARCH_STR_face_difference_cm':round(fixed-face,5),'raw_opening_gaps_cm':gaps,
            'opening_count':len(gaps),'blocked_openings':blocked,'pass':not blocked})
    return raw_checks,piece_checks,opening_checks

def legacy_anchor(e):
    """The five old records requested for a separate source audit."""
    id=e['id']
    if e['c']=='M.outlet' and '-R-S' in id and (e.get('a') or {}).get('sys')=='hvac_legacy':
        q=read('roof')['els'][int(id[-4:])-1]
        if q['t']!=e.get('t'):return None
        xy=q['g'][1:3]
        return {'method':'roof.json archived MECH1:6 grille symbol centre (independent extraction record)',
                'deviation_cm':deviation(e,xy),'source_xy':xy,'reference':'MECH1:6'}
    if id not in LEGACY_REVIEW:return None
    if id.startswith('M.pipe-R-S'):
        q=read('roof')['els'][int(id[-4:])-1]
        return {'method':'roof.json original geometry (stand added without moving the pipe)',
                'deviation_cm':deviation(e,[p[:2] for p in q['g'][1]],'path'),'source_xy':[p[:2] for p in q['g'][1]]}
    if id=='P.ff-R-M0007':
        rr=[q for q in read('mep_bg')['els'] if q.get('t')==e['t'] and q['l']==e['l']]
        return min(({'method':'mep_bg.json original roof route','deviation_cm':deviation(e,[p[:2] for p in q['g'][1]],'path'),'source_xy':[p[:2] for p in q['g'][1]]} for q in rr),key=lambda q:q['deviation_cm'])
    # Centred on the outer M_FF_SP circle, not its interior symbol strokes.
    xy={'P.ff-B-M0138':[4211.094713623047,1604.727899536133],
        'P.ff-B-M0148':[4211.094713623047,1304.5643164062499]}[id]
    return {'method':'MECH2:10 M_FF_SP circles 24604 / 24654','deviation_cm':deviation(e,xy),'source_xy':xy}

def candidate(e,rows,label):
    if not rows:return None
    p=centre(e['g']);best=min(rows,key=lambda q:math.dist(p,q))
    return {'method':label,'deviation_cm':math.dist(p,best),'source_xy':best}

def coords(rows):return [[q['x'],q['y']] for q in rows]
def rectcentre(r):return [(r[0]+r[2])/2,(r[1]+r[3])/2]
def levelkey(lv):return 'TY' if lv in ('2','3','4','5') else lv

def fallback(e,S,V,ST,FP,ELR):
    suffix=SUFFIX.search(e['id']);suffix=suffix.group(1) if suffix else None
    t=e.get('t','');a=e.get('a') or {};lv=e['l'];key=levelkey(lv)
    if suffix=='ST':
        site=ST.get('site',{});sh=ST.get('sheets',{}).get(key,{})
        if t=='site_mh':return candidate(e,coords(site.get('manholes',[])),'storm.json manhole symbol')
        if t=='drain_outlet':return candidate(e,coords([site['outlet']]),'storm.json western termination')
        if t=='pipe_site':return {'method':'storm.json drawn site pipe extent','deviation_cm':deviation(e,line(site['pipe_axis']),'linework'),'source_xy':site['pipe_axis']}
        if t=='storm_stack':
            rr=list(sh.get('risers',[]))+[q for q in sh.get('drains',[]) if q.get('vertical_label') and 'F/A' in q['vertical_label']['text']]
            return candidate(e,coords(rr),'storm.json vertical-pipe symbol')
        if t=='storm_rd':return candidate(e,coords(sh.get('drains',[])),'storm.json RD symbol')
        if t=='storm_co':return candidate(e,coords(sh.get('cleanouts',[])),'storm.json CO cap symbol')
        if t=='storm_outlet':return candidate(e,coords(sh.get('outlets',[])),'storm.json drawn free-discharge end')
        if t=='storm_pipe':
            rr=sh.get('pipes',[])
            if rr:return min(({'method':'storm.json drawn route','deviation_cm':deviation(e,q['points'],'path'),'source_xy':q['points']} for q in rr),key=lambda q:q['deviation_cm'])
    if suffix=='FP':
        if t in ('fp_electric','fp_diesel','fp_jockey'):
            return candidate(e,[rectcentre(p['bbox_cm']) for p in FP.get('pumps',[]) if 'fp_'+p['kind']==t],'fire_pumps.json pump symbol bounds')
        if t=='fp_pressure_vessel':return candidate(e,[FP['pressure_vessel']['xy_cm']],'fire_pumps.json vessel circle')
        if t in ('pipe_fp_header','pipe_fp_branch'):
            rr=[FP['header']['axis_cm']] if t=='pipe_fp_header' else FP.get('branches_cm',[])
            return min(({'method':'fire_pumps.json drawn assembly axis','deviation_cm':deviation(e,p,'path'),'source_xy':p} for p in rr),key=lambda q:q['deviation_cm']) if rr else None
    if suffix=='VT':
        sh=V.get(key,{})
        if a.get('bridge'):return {'derived':True,'reason':'Recorded bridge across a drawing break'}
        if t.startswith('duct_') and e['g'][0]=='d':
            rr=sh.get(a.get('sys'),[])
            if rr:return {'method':'vent.json source linework','deviation_cm':deviation(e,unary_union([LineString(p) for p in rr]),'linework')}
        if t=='diff_extract':return candidate(e,coords(sh.get('diffusers',[])),'vent.json diffuser symbol')
        if t.startswith('damper_'):return candidate(e,coords(sh.get('dampers',[])),'vent.json damper symbol')
        if t.startswith('grille_'):return candidate(e,coords([q for q in sh.get('grille_syms',[]) if ('ea' if q['layer'] in ('M_T.EX_DIFF','M_T.EX_DUCT') else 'fa')==a.get('sys')]),'vent.json grille bar')
        if t.startswith('fan_'):return candidate(e,coords(sh.get('fans',[])),'vent.json fan symbol')
        if t.startswith('riser_'):
            fam=a.get('sys');rr=[q for q in sh.get('shafts',[]) if q.get('kind')==fam]
            if lv=='B':
                if rr and min(math.dist(centre(e['g']),p) for p in coords(rr))<80:return candidate(e,coords(rr),'vent.json secondary shaft symbol')
                return {'derived':True,'reason':'Primary basement riser inherits ground-floor shaft face from VE-105; no primary shaft symbol in basement plan'}
            sx,sy={'ea':(864.9,1037.8),'fa':(864.6,760.3)}[fam]
            rr=[q for q in rr if abs(q['x']-sx)<130 and abs(q['y']-sy)<60]
            if rr:
                q=min(rr,key=lambda q:math.dist((q['x'],q['y']),(sx,sy)));p=[q['x1'],q['y']]
                return {'method':'vent.json drawn east face (section size is derived)','deviation_cm':deviation(e,p,'face'),'source_xy':p}
            return {'derived':True,'reason':'Riser section inherits a shaft face absent from this plan'}
        if t=='louver_intake':return {'derived':True,'reason':'Assumed louver on FAHU face; no independently drawn louver location'}
    if suffix=='SM':
        fam='fa' if a.get('sys','').endswith('fa') else 'ea';area='cp' if '_cp_' in a.get('sys','') else 'co';sh=S.get(key,{})
        if area=='cp':
            sh=S.get('B',{});f=sh.get(fam,{})
            if t.startswith(('riser_cp_','louver_cp_')):return candidate(e,[rectcentre(f['shaft'])],'smoke.json car-park shaft footprint')
            if t.startswith('duct_cp_') and e['g'][0]=='d':return {'method':'smoke.json car-park source routes','deviation_cm':deviation(e,unary_union([LineString(p) for p in f['paths']]),'linework')}
            if t.startswith('fan_cp_'):return candidate(e,[rectcentre(p) for p in sh['fans']],'smoke.json fan symbol')
            if t.startswith('grille_cp_'):return candidate(e,coords(f['grilles']),'smoke.json grille symbol')
            if t.startswith('damper_cp_'):return candidate(e,coords(sh['fd'] if e.get('mark')=='FD' else sh['vcd']),'smoke.json damper symbol')
        else:
            if lv=='G':return {'derived':True,'reason':'Ground riser inferred from SM-105; ground plan gives no independent XY'}
            if t.startswith('riser_co_'):return candidate(e,coords(sh.get(fam+'_riser',[])),'smoke.json corridor shaft symbol')
            if t.startswith('damper_co_'):return candidate(e,coords(sh.get('dampers',[])),'smoke.json corridor damper symbol')
            if t=='diff_co_ea':return candidate(e,coords(sh.get('ead',[])),'smoke.json EAD symbol')
            if t=='grille_co_fa':return candidate(e,coords([min(sh['fag_box'],key=lambda q:q['h'])]),'smoke.json FAG plate symbol')
            if t.startswith('fan_co_'):return candidate(e,coords(sh.get('fan_rects',[])),'smoke.json rooftop fan rectangle')
            if t.startswith('louver_co_'):
                q=sh['louvers'][fam];return candidate(e,[[(q['x0']+q['x1'])/2,(q['y0']+q['y1'])/2]],'smoke.json rooftop louver hatch')
            if t.startswith('duct_co_') and e['g'][0]=='d':
                if lv=='R':rr=sh.get(fam+'_duct',[])
                elif fam=='ea':rr=sh.get('ea_branch',[])+sh.get('ea_main',[])
                else:
                    q=sh['fa_riser'][0];end=min(sh['fag_box'],key=lambda r:r['h']);rr=[[[q['x'],q['y']],[end['x'],end['y']]]]
                if rr:return {'method':'smoke.json corridor source axis','deviation_cm':deviation(e,unary_union([LineString(p) for p in rr]),'linework')}
    if suffix=='ELR':
        p=a.get('source_page') or a.get('source_sheet');sh=ELR.get('sheets',{}).get(p,{})
        if sh:
            rr=[q for q in sh.get('items',[]) if q.get('kind')==t or t.endswith(q.get('kind','___'))]
            if e['g'][0] in ('t','d') and rr:
                return min(({'method':'electrical_remaining.json drawn route','deviation_cm':deviation(e,q['path'],'path'),'source_xy':q['path']} for q in rr if q.get('path')),key=lambda q:q['deviation_cm'],default=None)
            return candidate(e,[q['xy'] for q in rr if q.get('xy')],'electrical_remaining.json symbol')
    return None

SCR_CAP_IDS={'S.slab-T-0008','S.slab-T-0009'}
SCR_RETIREMENT_IDS={f'S.stair-R-{i:04d}'for i in range(148,169)}|{f'A.rail-R-X{i:04d}'for i in range(2037,2102)}|{'S.slab-T-0008-b'}
SCR_SOURCE_PAGES={'ARCH1:8','ARCH1:9','STR:24','ARCH2:1','ARCH2:2','ARCH2:3','ARCH2:4'}
D16_IDS={f'A.door-G-D16{i:04d}'for i in range(1,5)}
D16_SOURCE_PAGES={'ARCH1:5','ARCH2:5','BOQ:8'}

def _scr_scope_complete(r):
    s=r.get('summary',{});caps=r.get('checks',[]);retired=r.get('retirement_checks',[]);facts=r.get('source_facts',[])
    return (s.get('checked')==2 and s.get('retirement_checked')==87 and s.get('retired_exact_inventory')==87 and
        s.get('full_cap_source_checked')==0 and s.get('findings')==0 and s.get('uncovered')==0 and
        not r.get('global_findings')and len(caps)==2 and {q.get('id')for q in caps}==SCR_CAP_IDS and
        all(q.get('pass')is True and not q.get('errors')and q.get('body_source_checked')is False and
            q.get('absolute_Z_material_outer_source_accepted')is False for q in caps)and
        len(retired)==87 and {q.get('id')for q in retired}==SCR_RETIREMENT_IDS and
        all(q.get('pass')is True and not q.get('errors')and q.get('source_installation_quantity_acceptance')is False for q in retired)and
        len(facts)==7 and {q.get('source_page')for q in facts}==SCR_SOURCE_PAGES and
        all(q.get('whole_body_Z_material_accepted')is False for q in facts))

def _d16_scope_complete(r):
    s=r.get('summary',{});checks=r.get('checks',[]);facts=r.get('source_facts',[])
    return (s.get('checked')==4 and s.get('source_assemblies')==1 and s.get('source_plan_graphic_polygons')==4 and
        s.get('source_page_facts')==3 and s.get('findings')==0 and s.get('uncovered')==0 and
        s.get('numeric_physical_part_dimensions_checked')==0 and s.get('absolute_Z_installed_material_acceptance')is False and
        s.get('conditional_Z_envelope_guard_only')is True and not r.get('global_findings')and
        len(checks)==4 and {q.get('id')for q in checks}==D16_IDS and
        all(q.get('pass')is True and not q.get('errors')and q.get('numeric_physical_part_dimensions_checked')is False and
            q.get('absolute_Z_installed_material_acceptance')is False for q in checks)and
        len(facts)==3 and {q.get('source_page')for q in facts}==D16_SOURCE_PAGES and
        all(q.get('whole_physical_body_or_Z_accepted')is False for q in facts))

def audit(M,tolerance=TOL):
    # Rehydrate external audit inputs; geometry remains the live model.
    import sys as _audit_sys
    from pathlib import Path as _AuditPath
    _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
    from source_audit_sidecar import audit_model as _source_audit_model
    M = _source_audit_model(M)
    S,V,ST,FP,ELR=[read(n) for n in ('smoke','vent','storm','fire_pumps','electrical_remaining')]
    WS,SG=read('water_site'),read('signage_remaining')
    AR=read('arch_struct_review');AD=AR.get('detail_geometry',{})
    PG=read('pergola_remaining')
    boundary_result={};boundary_byid={}
    if any(re.search(r'-BND\d{4}$',e['id'])for e in M['els']):
        import check_boundary_source
        boundary_result=check_boundary_source.audit(M)
        boundary_byid={q['id']:q for q in boundary_result.get('checks',[])}
    raft_result={};raft_byid={}
    if M.get('meta',{}).get('raft_source_restore'):
        import check_raft_source
        raft_result=check_raft_source.audit(M)
        raft_byid={q['id']:q for q in raft_result.get('checks',[])}
    hvac_outlet_result={};hvac_outlet_byid={}
    hvac_outlet_ledger=read('restore_hvac_outlets_source')
    hvac_outlet_ids=set(hvac_outlet_ledger.get('records',{}))|set(hvac_outlet_ledger.get('retired_non_device_records',{}))
    if M.get('meta',{}).get('hvac_outlets_source_restore')or any(e['id']in hvac_outlet_ids for e in M['els']):
        import check_hvac_outlets_source
        hvac_outlet_result=check_hvac_outlets_source.audit(M)
        hvac_outlet_byid={q['id']:q for q in hvac_outlet_result.get('checks',[])}
    damper_result={};damper_byid={};damper_pending_byid={}
    damper_ledger=read('hvac_damper_source')
    damper_ids=set(damper_ledger.get('records',{}))|set(damper_ledger.get('additions',{}))|set(damper_ledger.get('pending',{}))
    if M.get('meta',{}).get('hvac_damper_source')or any(e['id']in damper_ids for e in M['els']):
        import check_hvac_dampers_source
        damper_result=check_hvac_dampers_source.audit(M)
        damper_byid={q['id']:q for q in damper_result.get('checks',[])}
        damper_pending_byid={q['id']:q for q in damper_result.get('pending',[])}
    valve_result={};valve_byid={}
    # The frozen original source inventory is the denominator. Removing all
    # marker flags or IDs cannot silently disable its independent gate.
    if os.path.exists(os.path.join(DATA,'water_valve_source.json')):
        import check_water_valves_source
        valve_result=check_water_valves_source.audit(M)
        valve_byid={q['id']:q for q in valve_result.get('checks',[])}
    top_roof_result={}
    top_roof_ids={'S.slab-T-0009','S.slab-T-0010'}
    top_roof_raw_ids={'STR24-SHAFT-'+str(i)for i in(2148,2149,2150,2151,2156,2157)}
    top_roof_clip_ids={('S.slab-T-0009','STR24-SHAFT-'+str(i))for i in(2148,2149,2151,2156)}|{
        ('S.slab-T-0010','STR24-SHAFT-'+str(i))for i in(2150,2151,2157)}
    top_roof_enabled=os.path.exists(os.path.join(DATA,'top_roof_shaft_openings_source.json'))
    # This gate proves six local opening profiles, not either slab's outer
    # footprint. Its fixed inventory must survive removal of all source flags.
    if top_roof_enabled:
        import check_top_roof_shaft_openings_source
        top_roof_result=check_top_roof_shaft_openings_source.audit(M)
    # Frozen inventories are mandatory even when every claimed ID/flag is removed.
    stair_result={};stair_enabled=True
    d16_result={};d16_enabled=True;d16_byid={}
    try:
        import check_stair01_roof_source_correction
        stair_result=check_stair01_roof_source_correction.audit(M)
    except Exception as ex:
        stair_result={'global_findings':[{'kind':'SCR_original_or_frozen_source_gate_error','reason':str(ex)}]}
    try:
        import check_d16_source_remaining
        d16_result=check_d16_source_remaining.audit(M)
        d16_byid={q['id']:q for q in d16_result.get('checks',[])}
    except Exception as ex:
        d16_result={'global_findings':[{'kind':'D16_original_or_frozen_source_gate_error','reason':str(ex)}]}
    window_result={};window_byid={}
    window_units=read('window_source_xy').get('units',{})
    window_member_ids={eid for unit in window_units.values()for eid in unit.get('model_member_ids',[])}
    if any(e['id']in window_member_ids or e.get('c')=='A.win'and e.get('grp')in window_units or
           (e.get('a')or{}).get('source_window_group')for e in M['els']):
        import check_window_source
        window_result=check_window_source.audit(M)
        window_byid={q['id']:q for q in window_result.get('derived',[])}
    drain_riser_result=drain_riser_generation_checks(M)
    rows=[];bad=[];derived=[];uncovered=[];count=collections.Counter();syscount=collections.Counter()
    for e in M['els']:
        a=e.get('a') or {};suffix=SUFFIX.search(e['id'])
        if (top_roof_enabled and e['id']in top_roof_ids)or(stair_enabled and e['id']in SCR_CAP_IDS):
            continue  # Partial void evidence is reported separately; no whole-slab XY promotion.
        suspicious_network=bool(a.get('guess_from') and (e['c'].startswith('P.') or e['c'] in ('M.pipe','M.duct','M.outlet','M.damper')))
        current_drain_riser=_current_drain_riser(e)
        if not a.get('sys') and not a.get('source_locked_xy') and not a.get('source_trace_review') and a.get('source_kind')!='drawn_pile_circle_derived_center' and not suffix and e['id'] not in LEGACY_REVIEW and e['id'] not in window_byid and e['id'] not in hvac_outlet_byid and e['id'] not in damper_byid and e['id'] not in damper_pending_byid and e['id']not in valve_byid and e['id']not in D16_IDS and not suspicious_network and not current_drain_riser:continue
        label=suffix.group(1) if suffix else 'legacy'
        row={'id':e['id'],'type':e.get('t'),'level':e['l'],'system':a.get('sys'),'suffix':label,
             'z_assumption':a.get('assumed') or None}
        if a.get('guess_from') and (a.get('sys') or e['id'] in LEGACY_REVIEW or suspicious_network):
            bad.append(dict(row,reason='Drawn network carries guess_from',guess_from=a['guess_from']))
        if e['id']in damper_pending_byid:
            continue  # Explicit roof registration gap is reported separately; no XY promotion.
        if e['id']in window_byid:
            q=window_byid[e['id']]
            derived.append(dict(row,reason='Procedural window part; original group anchor and relative schedule envelope are checked separately, not independent part geometry',
                source_group=q['source_group'],source_kind='derived_window_assembly_part',
                proof_scope='derived_assembly_member_not_raw_part_XY_absoluteZ_depth_material_mounting'));continue
        if current_drain_riser:
            binding=drain_riser_result['bindings'][e['id']]
            derived.append(dict(row,reason='Current risers.py drain output; endpoint-cluster position and vertical geometry remain derived',
                source_trace_status='derived_vertical_riser',reference='pipeline/risers.py',
                historical_id=binding['historical_id'],binding_status=binding['binding_status'],
                proof_scope='derived_generation_identity_only_not_drawn_XY_Z_or_contact'));continue
        if a.get('source_trace_status') in ('derived_vertical_riser','arc_glyph_composition_pending','derived_bridge_through_source_symbols','derived_from_water_dash_pattern','water_dash_glyph_gap_pending'):
            derived.append(dict(row,reason='Legacy source composition remains derived or semantically pending; no complete raw route asserted',
                                source_trace_status=a['source_trace_status'],reference=a.get('source_page')));continue
        if (a.get('connector') or a.get('derived') and label=='legacy')and e['id']not in hvac_outlet_byid and e['id']not in damper_byid and e['id']not in valve_byid and e['id']not in D16_IDS:
            derived.append(dict(row,reason='Tagged derived connector'));continue
        if label=='AD' and a.get('source_kind') in ('derived_from_outline','derived_from_model_face','derived_from_section'):
            derived.append(dict(row,reason='Assembly piece derived from an outline, model face or section; no independently drawn plan-piece position',reference=a.get('source_reference')));continue
        if label=='SRF' and a.get('source_kind')=='derived_from_architectural_boundary':
            derived.append(dict(row,reason='Architectural piece derived from original outer/inner boundary; structural footprint not independently proved',reference=a.get('source_page')));continue
        if label=='BND'and e['id']in boundary_byid and boundary_byid[e['id']]['proof_scope']=='derived_outline':
            derived.append(dict(row,reason='Boundary outline derived from independently audited raw faces/joints; remains derived',reference=a.get('source_page')));continue
        if e['id']in raft_byid and raft_byid[e['id']]['proof_scope']=='derived_raft_domain':
            derived.append(dict(row,reason='Raft domain derived from original outer outline minus separately drawn PC1; remains derived',reference='STR:11'));continue
        if e['id']in d16_byid:
            q=d16_byid[e['id']]
            r={'method':q['method'],'deviation_cm':q.get('deviation_cm')if q.get('deviation_cm')is not None else float('inf'),
               'external_source_pass':q.get('pass')is True and not q.get('errors'),
               'proof_scope':q['scope'],'reference':'ARCH1:5/A102 + ARCH2:5/A604 + BOQ:8',
               'numeric_physical_part_dimensions_checked':False,'absolute_Z_installed_material_acceptance':False,
               'spatial_basis':'Original open leaf or outerJAMB plan polygon; conditional opening envelope, not physical depth, individual part height/Z, installed material or mounting acceptance'}
        elif e['id']in valve_byid:
            q=valve_byid[e['id']]
            r={k:q.get(k)or 0 for k in('deviation_cm','metadata_deviation_cm','graphic_size_deviation_cm','graphic_full_bbox_deviation_cm')}
            r.update({'method':q['method'],'external_source_pass':q['pass'],
               'graphic_angle_deviation_deg':q.get('graphic_angle_deviation_deg')or 0,
               'proof_scope':q['scope'],'reference':q['reference'],'source_xy':q.get('source_xy'),
               'source_code':q['source_code'],'absolute_Z_source_accepted':False,
               'spatial_basis':'Original whole water-valve graphic centre/bbox/angle; subtype only with an explicit source tag. Physical housing dimensions, absolute Z, materials, mount, ports/contact, installation and operation remain unverified'})
        elif e['id']in hvac_outlet_byid:
            q=hvac_outlet_byid[e['id']]
            r={k:q.get(k)or 0 for k in('deviation_cm','metadata_deviation_cm','source_anchor_deviation_cm','source_transform_deviation_cm')}
            r.update({'method':q['method'],'external_source_pass':q['pass'],
               'proof_scope':q.get('proof_scope','body_graphic_XY_and_bbox_only'),'reference':q['reference'],'source_xy':q.get('source_xy'),
               'spatial_basis':'Original HVAC body graphic core, separated from flow arrows and open duct linework; graphic extent/axis orientation only, physical body dimensions/Z/rotation/material/mount/ports/contact remain unverified'})
        elif e['id']in damper_byid:
            q=damper_byid[e['id']]
            r={k:q.get(k)or 0 for k in('deviation_cm','metadata_deviation_cm')}
            r.update({'method':q['method'],'external_source_pass':q['pass'],
               'graphic_size_deviation_cm':q.get('graphic_size_deviation_cm')or 0,
               'graphic_angle_deviation_deg':q.get('graphic_angle_deviation_deg')or 0,
               'proof_scope':q['scope'],'reference':q['reference'],'source_xy':q.get('source_xy'),
               'spatial_basis':'Original closed L damper graphic anchor/extent/orientation; manufacturer body dimensions, absolute Z, material, mount, ports/contact and subtype remain unverified'})
        elif e['id']in raft_byid:
            q=raft_byid[e['id']]
            r={'method':'Independent original STR11 closed PC1 profile, raw axis registration and thickness literal',
               'deviation_cm':q['xy_deviation_cm'],'metadata_deviation_cm':q['metadata_xy_deviation_cm'],
               'source_anchor_deviation_cm':q['raw_metadata_deviation_cm'],'source_transform_deviation_cm':q['registration_deviation'],
               'source_thickness_deviation_cm':q['thickness_deviation_cm'],'external_source_pass':not q['errors'],
               'proof_scope':'original_closed_PC1_profile','reference':'STR:11',
               'spatial_basis':'Raw XY profile and numbered thickness only; absolute Z/material/rebar/bearing remain unverified'}
        elif label=='BND':
            q=boundary_byid.get(e['id'])
            r={'method':'Independent original STR32 closed C* profile and A101 project-axis registration',
               'deviation_cm':q['xy_deviation_cm'],'metadata_deviation_cm':q['metadata_xy_deviation_cm'],
               'source_anchor_deviation_cm':q['raw_metadata_deviation_cm'],'source_transform_deviation_cm':q['registration_deviation'],
               'external_source_pass':not q['errors'],'proof_scope':'raw_profile','reference':'STR:32',
               'spatial_basis':'Raw XY profile; above-grade Z derived; bearing, rebar, exact material grade/finish/colour remain unverified'}if q else None
        elif a.get('source_kind')=='centreline_from_two_pipe_faces':
            r=fire_centreline_check(e)
        elif a.get('source_kind')=='drawn_symbol_cluster_bbox_centre':
            r=electrical_legacy_check(e)
        elif a.get('source_kind') in ('drawn_symbol_glyph_bbox_centre','circle_bounds_centre'):
            r=electrical_semantic_check(e)
        elif a.get('source_kind') in ('thermostat_circle_graphic_anchor','fcu_plan_quad_anchor_angle'):
            r=hvac_source_check(e)
        elif a.get('source_kind') in ('raw_electrical_connection_polyline','raw_electrical_arrow_tip'):
            r=electrical_tail_check(e)
        elif a.get('source_kind') in ('raw_water_pipe_without_break_glyph','water_device_whole_glyph_bbox_anchor'):
            r=water_source_check(e)
        elif a.get('source_kind')=='water_layer_linear_trace':
            r=water_mixed_review_check(e,tolerance)
        elif a.get('source_kind')=='water_meter_circle_M_graphic_anchor':
            r=water_meter_source_check(e)
        elif a.get('source_kind')=='garbage_plan_graphic_anchor':
            r=garbage_source_check(e)
        elif a.get('source_kind')=='closed_structural_wall_outline':
            r=lift_head_wall_check(e)
        elif a.get('source_kind')=='drawn_layer_trace':
            r=drain_trace_check(e,tolerance)
        elif a.get('source_kind')=='drawn_pile_circle_derived_center':
            r=pile_source_check(e)
        else:
            proof=source_proof(e,WS,SG,ELR,ST,AD,PG)
            r=source_metadata(e,proof) or legacy_anchor(e) or fallback(e,S,V,ST,FP,ELR)
        if r and r.get('derived'):
            derived.append(dict(row,reason=r['reason']));continue
        if not r:
            uncovered.append(dict(row,reason='No independent drawing anchor available'));continue
        row.update(r)
        row['deviation_cm']=round(row['deviation_cm'],5)
        errors=['deviation_cm','metadata_deviation_cm','source_anchor_deviation_cm','source_transform_deviation_cm',
                'source_length_deviation_cm','source_diameter_deviation_cm','source_thickness_deviation_cm','graphic_size_deviation_cm']
        for field in errors:
            if row.get(field) is not None:row[field]=round(row[field],5)
        measured_errors=[row.get(field,0) for field in errors]
        row['pass']=all(math.isfinite(value) for value in measured_errors) and max(measured_errors)<=tolerance+1e-6 and row.get('whole_trace_source_covered',True) and row.get('review_geometry_unchanged',True) and row.get('source_rotation_matches_symbol',True)and row.get('external_source_pass',True)
        rows.append(row);count[label]+=1;syscount[a.get('sys') or 'no_sys']+=1
        if not row['pass']:bad.append(row)
    source_checks=outline_source_checks(AD,tolerance) if any(SUFFIX.search(e['id']) and SUFFIX.search(e['id']).group(1)=='AD' for e in M['els']) else []
    arch_sources,derived_checks,opening_checks=architectural_derived_checks(M,AR,tolerance)
    derived_checks.extend(lift_architectural_boundary_checks(M,tolerance))
    derived_checks.extend(dict(q,pass_=not q['errors'],**{'pass':not q['errors']})for q in boundary_result.get('checks',[])if q['proof_scope']=='derived_outline')
    derived_checks.extend(dict(q,**{'pass':not q['errors']})for q in raft_result.get('checks',[])if q['proof_scope']=='derived_raft_domain')
    derived_checks.extend(drain_riser_result['checks'])
    scope_exclusions=[{'id':e['id'],'type':e.get('t'),'level':e['l'],
                       'reason':'ARF finish footprint derived from existing model geometry; no independently drawn plan-piece position'}
                      for e in M['els'] if re.search(r'-ARF\d{4}$',e['id'])]
    top_roof_partial_reviews=[]
    if top_roof_enabled:
        current={e['id']:e for e in M['els']}
        preservation={q['id']:q for q in top_roof_result.get('slab_preservation_checks',[])}
        for eid in sorted(top_roof_ids):
            e=current.get(eid);q=preservation.get(eid,{})
            review={'id':eid,'type':(e or{}).get('t'),'level':'T','reference':'STR:24',
                'status':'whole_profile_unverified','partial_opening_subtraction_checked':q.get('pass')is True and not q.get('errors'),
                'whole_outer_source_checked':False,'absolute_Z_material_acceptance':False,
                'reason':'Six original SHAFT profiles are subtracted locally; preserved slab outer boundary, absolute Z and material remain unverified'}
            top_roof_partial_reviews.append(review);scope_exclusions.append(dict(review))
    # T9 has both a procedural-cut rollback and local source-void evidence.
    # Merge its reviews by identity instead of counting the slab twice.
    partial_byid={q['id']:q for q in top_roof_partial_reviews}
    scope_byid={q['id']:q for q in scope_exclusions}
    stair_caps={q['id']:q for q in stair_result.get('checks',[])}
    partial_elements={e['id']:e for e in M['els']}
    for eid in sorted(SCR_CAP_IDS):
        q=stair_caps.get(eid,{})
        review=partial_byid.get(eid,{'id':eid,'type':(partial_elements.get(eid)or{}).get('t'),'level':'T','status':'whole_profile_unverified',
            'whole_outer_source_checked':False,'absolute_Z_material_acceptance':False})
        review.update(stair01_roof_procedural_cut_rollback_checked=q.get('pass')is True and not q.get('errors'),
            reference='A600/A601/A105/A106/STR24; procedural cap rollback only',
            reason='Source-disproved extra roof flight retired; known procedural cap cut reversed. Whole slab outer boundary, absolute Z, thickness/material installation remain unverified; T9 source void masks are a separate partial review.')
        if eid not in partial_byid:top_roof_partial_reviews.append(review)
        partial_byid[eid]=review
        if eid in scope_byid:scope_byid[eid].update(review)
        else:scope_exclusions.append(dict(review))
    damper_pending_checks=[]
    elements_byid={e['id']:e for e in M['els']}
    for q in damper_result.get('pending',[]):
        e=elements_byid.get(q['id']);a=(e or{}).get('a')or{}
        unsafe=any(a.get(k)for k in('source_Z_verified','source_dimensions_verified','source_mount_verified',
            'source_material_verified','source_rotation_verified','source_contact_verified','source_ports_verified',
            'source_graphic_bbox_verified','source_glyph_bounds_verified','source_graphic_rotation_verified',
            'source_position_verified','source_locked_xy'))or a.get('source_geometry_review')=='body_graphic_only'
        check=dict(q,method='Preserved roof damper proxy; source transform gap remains explicit',
            proof_scope='unverified_roof_source_position_not_drawn_XY',
            **{'pass':q['geometry_preserved']and not unsafe})
        damper_pending_checks.append(check)
        scope_exclusions.append({'id':q['id'],'type':(e or{}).get('t'),'level':'R','reference':q['reference'],
            'status':q['status'],'reason':q['reason'],'source_position_verified':False})
    source_checks.extend(damper_pending_checks)
    source_checks.extend(arch_sources)
    semantic_reviews=electrical_semantic_reviews(M,tolerance)
    source_checks.extend(semantic_reviews)
    source_checks.extend(water_retirement_checks(M,tolerance))
    water_mixed_source,water_mixed_derived=water_mixed_source_checks(M,tolerance)
    source_checks.extend(water_mixed_source)
    derived_checks.extend(water_mixed_derived)
    source_checks.extend(water_meter_source_checks(M,tolerance))
    source_checks.extend(dict(q,method='Independent window assembly anchor and relative envelope: '+q['method'])
                         for q in window_result.get('checks',[]))
    source_checks.extend(dict(q,id='WINDOW-SCHEDULE-'+q['code'],method='Independent printed window schedule dimensions')
                         for q in window_result.get('schedule_checks',[]))
    source_checks.extend(dict(q,method='Independent HVAC body core source: '+q['method'])for q in hvac_outlet_result.get('checks',[])if not q['pass'])
    source_checks.extend(dict(q,method='Independent raw HVAC false-component retirement')
                         for q in hvac_outlet_result.get('retirement_checks',[]))
    source_checks.extend(dict(q,method='Independent closed L HVAC damper graphic: '+q['method'])
                         for q in damper_result.get('checks',[])if not q['pass'])
    source_checks.extend(dict(q,method='Independent original water-valve graphic: '+q['method'])
                         for q in valve_result.get('checks',[])if not q['pass'])
    for section in ('checks','source_opening_checks','slab_preservation_checks'):
        source_checks.extend(dict(q,method='Independent STR24 partial opening review: '+section,
            **{'pass':q.get('pass')is True and not q.get('errors')})for q in top_roof_result.get(section,[]))
    for section in ('checks','retirement_checks'):
        source_checks.extend(dict(q,method='Independent SCR partial rollback or retirement: '+section,
            **{'pass':q.get('pass')is True and not q.get('errors')})for q in stair_result.get(section,[]))
    source_checks.extend(dict(q,id='SCR-FACT-'+q['source_page'].replace(':','-'),
        method='Independent original multi-page stair end/cover evidence',
        **{'pass':not stair_result.get('global_findings')})for q in stair_result.get('source_facts',[]))
    source_checks.extend(dict(q,method='Independent D16 original plan polygon: '+q['method'])
        for q in d16_result.get('checks',[])if not q.get('pass')or q.get('errors'))
    source_checks.extend(dict(q,id='D16-FACT-'+q['source_page'].replace(':','-'),
        method='Independent original D16 plan/detail/BOQ literal context',
        **{'pass':not d16_result.get('global_findings')})for q in d16_result.get('source_facts',[]))
    bad.extend(q for q in source_checks if not q['pass'])
    bad.extend(q for q in derived_checks if not q['pass'])
    bad.extend(q for q in opening_checks if not q['pass'])
    bad.extend(boundary_result.get('findings',[]))
    bad.extend(dict(q,reason='Independent boundary source remains uncovered')for q in boundary_result.get('uncovered',[]))
    bad.extend(raft_result.get('findings',[]))
    bad.extend({'id':q,'reason':'Independent raft source remains uncovered'}for q in raft_result.get('uncovered',[]))
    bad.extend(dict(q,reason='Independent HVAC raw ledger binding failure')for q in hvac_outlet_result.get('findings',[]))
    bad.extend({'id':q,'reason':'Independent HVAC body source remains uncovered'}for q in hvac_outlet_result.get('uncovered',[]))
    bad.extend(dict(q,reason='Independent HVAC damper raw scope or procedural guard failure')
               for q in damper_result.get('global_findings',[]))
    bad.extend(dict(q,reason='Independent water-valve raw scope or procedural guard failure')
               for q in valve_result.get('global_findings',[]))
    bad.extend(dict(q,reason='Independent STR24 partial opening source or preservation failure')
               for q in top_roof_result.get('global_findings',[]))
    bad.extend(dict(q,reason='Independent SCR source scope or procedural guard failed')for q in stair_result.get('global_findings',[]))
    bad.extend(dict(q,reason='Independent D16 source scope or guarded proxy failed')for q in d16_result.get('global_findings',[]))
    if not _scr_scope_complete(stair_result):bad.append({'kind':'SCR_partial_scope_incomplete',
        'reason':'Exactly two unverified whole caps, 87 source-disproved retirements and seven original page facts are mandatory',
        'summary':stair_result.get('summary',{})})
    if not _d16_scope_complete(d16_result):bad.append({'kind':'D16_graphic_scope_incomplete',
        'reason':'Exactly four original plan proxies and three source contexts are mandatory; no physical part dimension/Z/material acceptance',
        'summary':d16_result.get('summary',{})})
    if top_roof_enabled:
        ts=top_roof_result.get('summary',{})
        complete=(ts.get('checked')==7 and ts.get('unique_raw_openings')==6 and
            ts.get('controlled_slab_preservation_checks')==2 and ts.get('body_source_checked')==0 and
            ts.get('outer_absolute_Z_material_acceptance')is False and
            len(top_roof_result.get('checks',[]))==7 and len(top_roof_result.get('source_opening_checks',[]))==6 and
            {(q.get('element_id'),q.get('source_opening_id'))for q in top_roof_result.get('checks',[])}==top_roof_clip_ids and
            all(q.get('id')==str(q.get('element_id')or'')+'::'+str(q.get('source_opening_id')or'')and q.get('body_source_checked')is False and
                q.get('physical_Z_material_acceptance')is False for q in top_roof_result.get('checks',[]))and
            {q.get('id')for q in top_roof_result.get('source_opening_checks',[])}==top_roof_raw_ids and
            all(q.get('absolute_Z_outer_material_acceptance')is False for q in top_roof_result.get('source_opening_checks',[]))and
            {q.get('id')for q in top_roof_result.get('slab_preservation_checks',[])}==top_roof_ids and
            len(top_roof_result.get('slab_preservation_checks',[]))==2 and
            all(q.get('full_outer_source_checked')is False for q in top_roof_result.get('slab_preservation_checks',[]))and
            ts.get('findings')==0 and ts.get('uncovered')==0 and ts.get('global_findings')==0)
        if not complete:bad.append({'kind':'top_roof_partial_source_scope_incomplete',
            'reason':'Six raw opening profiles, seven clipped voids and two preserved slab records are mandatory; no whole slab source acceptance',
            'summary':ts})
    return {'tolerance_cm':tolerance,'measured_axes':'X/Y positions; stated pile length/diameter separately checked; Z anchors remain unverified',
            'checked':len(rows),'derived_excluded':len(derived),'uncovered':len(uncovered),'findings':len(bad),
            'by_suffix':dict(count),'by_system':dict(syscount),'max_xy_deviation_cm':round(max((r['deviation_cm'] for r in rows),default=0),5),
            'checks':rows,'failures':bad,'derived':derived,'uncovered_elements':uncovered,'source_outline_checks':source_checks,
            'explicit_scope_excluded':len(scope_exclusions),'explicit_scope_exclusions':scope_exclusions,
            'derived_geometry_checked':len(derived_checks),'derived_geometry_checks':derived_checks,
            'derived_opening_reviews':opening_checks,'electrical_semantic_reviews':semantic_reviews,
            'boundary_source_audit':boundary_result,'raft_source_audit':raft_result,
            'hvac_outlets_source_audit':hvac_outlet_result,
            'hvac_dampers_source_audit':damper_result,
            'water_valve_source_audit':valve_result,
            'top_roof_shaft_openings_source_audit':top_roof_result,
            'stair01_roof_source_correction_audit':stair_result,
            'stair01_roof_caps_reviewed':len(stair_result.get('checks',[])),
            'stair01_roof_retirements_checked':len(stair_result.get('retirement_checks',[])),
            'stair01_roof_whole_caps_source_checked':0,
            'd16_source_remaining_audit':d16_result,
            'd16_plan_graphic_polygons_checked':len(d16_result.get('checks',[])),
            'd16_numeric_physical_part_dimensions_checked':0,
            'partial_source_element_reviews':top_roof_partial_reviews,
            'top_roof_source_opening_profiles_checked':len(top_roof_result.get('source_opening_checks',[])),
            'top_roof_source_opening_clips_checked':len(top_roof_result.get('checks',[])),
            'top_roof_whole_slab_source_checked':0,
            'source_position_pending_excluded':len(damper_pending_checks),
            'window_source_audit':window_result,
            'window_assembly_anchor_checked':len(window_result.get('checks',[])),
            'window_raw_part_positions_checked':0,
            'drain_riser_generation_audit':drain_riser_result}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',default=os.path.join(ROOT,'src','model.json'))
    p.add_argument('--output',default=os.path.join(DATA,'drawn_position_audit.json'))
    p.add_argument('--tolerance',type=float,default=TOL)
    args=p.parse_args();snapshot=open(args.model,'rb').read();M=json.loads(snapshot);report=audit(M,args.tolerance)
    report['model_path']=os.path.abspath(args.model)
    report['model_file_sha256']=hashlib.sha256(snapshot).hexdigest()
    geometry=sorted((e['id'],e['g']) for e in M['els'])
    report['model_geometry_sha256']=hashlib.sha256(json.dumps(geometry,separators=(',',':')).encode()).hexdigest()
    os.makedirs(os.path.dirname(os.path.abspath(args.output)),exist_ok=True)
    with open(args.output,'w',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print('drawn XY:',report['checked'],'checked,',report['derived_excluded'],'derived,',report['uncovered'],'uncovered,',report['findings'],'findings; max cm',report['max_xy_deviation_cm'])
    for f in report['failures'][:30]:print(' ',f.get('id')or f.get('kind')or 'source_scope',f.get('deviation_cm'),f.get('reason')or f.get('method')or f.get('errors'))
    return 1 if report['findings'] else 0

if __name__=='__main__':sys.exit(main())
