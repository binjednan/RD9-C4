# -*- coding: utf-8 -*-
"""Add two literally traced POWER-CONN. tails missed by CONNE filtering.

The drawn arrow is the boundary of the documented circuit. It is never joined
to a board by proximity. Symbol-to-proxy-centre connections are explicitly
derived inside the selected glyph; height and tube diameter are display values.
"""
import copy, hashlib, json, math, re
from pathlib import Path

DATA_PATH=Path(__file__).with_name('data')/'electrical_trace_restore.json'
ID_RE=re.compile(r'-ETR\d{4}$')
TYPES={}


def _sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def build(M, els=None, verbose=False):
    """Add 4 raw XY traces, 2 arrow markers and 2 derived glyph connections."""
    els=M['els']if els is None else els
    els[:]=[e for e in els if not ID_RE.search(e['id'])]
    review=json.loads(DATA_PATH.read_text());byid={e['id']:e for e in els}
    added=[];bindings=[]
    for row in review['records']:
        device=byid.get(row['id'])
        if device is None or(device['c'],device.get('t'),device['l'],device['g'][0])!=(row['category'],row['type'],row['level'],'b'):
            raise ValueError('Source-tail device identity missing or changed: '+row['id'])
        if math.dist(device['g'][1:3],row['source_anchor_xy'])>.2 or not device.get('a',{}).get('source_locked_xy'):
            raise ValueError('Source-tail symbol anchor has not been restored: '+row['id'])
        level=row['level'];z=round((device['g'][6]+device['g'][7])/2,4)
        common={'sys':'power','source_locked_xy':True,'source_page':row['source'],
            'source_pdf_sha256':row['source_pdf_sha256'],'source_transform':copy.deepcopy(row['registration']),
            'source_trace_record':row['id'],'source_trace_record_sha256':_sha(row),
            'source_original_tag_words':copy.deepcopy(row['source_tag_words']),
            'tag':row['tag_literal'],'dest':row['board_name'],'source_device_id':row['id'],
            'source_Z_verified':False,'source_dimensions_verified':False,'source_material_verified':False,
            'assumed':'منسوب العرض هو وسط جسم الجهاز الحالي والقطر16مم افتراض عرض؛ المصدر يرسم XY والسهم فقط، ولا يعطي مسار المغذي إلى اللوحة أو منسوب التمديد أو تفاصيل الجهاز.',
            'source_limit_ar':row['limit_ar']}
        ref='مسار قوى من '+row['source']+' طبقة POWER-CONN.؛ المنحنى والخط والسهم ووسم '+row['tag_literal']+' من الرسم الأصلي، المنسوب والقطر افتراض عرض.'
        if ref not in M['sp']:M['sp'].append(ref)
        source_index=M['sp'].index(ref)
        def add(number,g,type_name,attrs):
            eid='E.tray-'+level+'-ETR'+str(number).zfill(4)
            element={'id':eid,'c':'E.tray','t':type_name,'l':level,'g':g,'m':'m_wire','s':[source_index],
                'a':{**copy.deepcopy(common),**attrs}}
            if device.get('u'):element['u']=device['u']
            added.append(element);return eid
        raw_ids=[]
        for n,key in enumerate(('curve','straight'),1):
            path=row[key]
            points=[[round(x,4),round(y,4),z]for x,y in path['xy_cm']]
            raw_ids.append(add(n,['t',points,1.6],'wire_power',{
                'kind':'ساق دائرة قوى مرسومة — '+key,'source_kind':'raw_electrical_connection_polyline',
                'source_layer':path['layer'],'source_primitives':[[path['drawing'],path['poly']]],
                'source_pdf_points':copy.deepcopy(path['pdf_points']),'source_xy':copy.deepcopy(path['xy_cm']),
                'source_curve_flatten_segments':100,'source_raw_items':copy.deepcopy(path['raw_items']),
                'source_curve_approximation_cm':row['curve_100_vs_1000_segment_hausdorff_cm']if key=='curve'else 0,
                'source_graphic_stroke_contact':copy.deepcopy(row['stroke_contact_proof']),
                'source_geometry_role':'raw_source_plan_centreline_with_assumed_display_height_and_diameter'}))
        arrow=row['arrow'];x,y=row['arrow_tip_xy']
        boundary_id=add(3,['cyl',round(x,4),round(y,4),.8,round(z-.01,4),round(z+.01,4)],'wire_circuit_end',{
            'kind':'حد الدائرة عند رأس السهم المرسوم','source_kind':'raw_electrical_arrow_tip',
            'source_layer':arrow['layer'],'source_primitives':[[arrow['drawing'],arrow['poly']]],
            'source_pdf_points':[copy.deepcopy(row['arrow_tip_pdf'])],'source_xy':copy.deepcopy(row['arrow_tip_xy']),
            'source_raw_items':copy.deepcopy(arrow['raw_items']),'from':raw_ids[-1],
            'source_geometry_role':'graphic_boundary_marker_at_literal_arrow_tip',
            'assumed':'أسطوانة صغيرة لعرض حد الدائرة عند رأس السهم المصدر؛ حجمها ومنسوبها للعرض فقط. لا يوجد خط من السهم إلى اللوحة.'})
        p=row['source_port_xy'];q=row['source_anchor_xy']
        connector_id=add(4,['t',[[round(p[0],4),round(p[1],4),z],[round(q[0],4),round(q[1],4),z]],1.6],'wire_drop',{
            'kind':'وصلة تمثيل مشتقة داخل رمز العازل','source_kind':'derived_graphic_terminal_connector',
            'connector':True,'derived':True,'from':raw_ids[0],'to':row['id'],
            'source_port_xy':copy.deepcopy(p),'source_symbol_anchor_xy':copy.deepcopy(q),
            'source_symbol_primitives':copy.deepcopy(row['source_symbol_primitives']),
            'source_geometry_role':'derived_symbol_port_to_proxy_anchor_inside_the_source_glyph',
            'assumed':'وصلة تمثيل من طرف الساق المرسوم داخل glyph إلى مركز جسم العرض الأصغر؛ ليست مسار كابل مرسومًا أو منفذًا تنفيذيًا. المنسوب والقطر ومقاس الجهاز ووجه تثبيته غير مثبتة.'})
        bindings.append({'device':row['id'],'raw_path_ids':raw_ids,'boundary_id':boundary_id,
            'derived_proxy_connector_id':connector_id,'tag':row['tag_literal'],
            'source_trace_record_sha256':_sha(row),'source':row['source']})
    els.extend(added)
    stats={**review['summary'],'bindings':bindings,'source_data_sha256':hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
        'source_data':'pipeline/data/electrical_trace_restore.json',
        'scope_limit':'Two source-identified graphic tails only. XY curves/lines and arrow tips are literal; connection inside proxy glyph, Z, diameter and physical mount are derived/unverified. No feeder path is generated.'}
    M.setdefault('meta',{})['electrical_trace_restore']=stats
    if verbose:print('electrical source tails:',stats['elements'],'rawXY',stats['raw_path_elements'],'derived',stats['derived_proxy_connectors'])
    return stats


apply=build
