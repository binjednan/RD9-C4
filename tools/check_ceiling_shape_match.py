"""Reopen A500 and independently check the 281 bounded thickness corrections."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'pipeline'))
import ceiling_shape_match as CS


def audit(M):
    import fitz
    D = CS.data()
    pdf = Path(os.environ.get('C4_ARCH_SCHEDULE_PDF', D['source_pdf']['path']))
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == D['source_pdf']['sha256'], 'A500 PDF changed'
    page = fitz.open(pdf)[D['source_pdf']['page']-1]
    words = page.get_text('words')
    literal = {}
    evidence = {}
    for code,r in D['source_rows'].items():
        x0,y0,x1,y1 = r['cell_window_pdf']
        fresh = [{'word_index':i,'word':list(w)} for i,w in enumerate(words)
                 if x0 <= w[0] <= x1 and y0 <= w[1] and w[3] <= y1]
        assert fresh == r['source_words'], 'A500 table cell source changed: '+code
        labels = [w for w in fresh if w['word'][4] == code]
        assert len(labels) == 1 and labels[0]['word'][2] < 1050
        text = ' '.join(w['word'][4] for w in fresh if w['word'][0] > 1050)
        if code == 'C1':
            assert 'gypsum board' in text
            literal[code] = int(re.search(r'(\d+)mm thk gypsum', text).group(1))
        else:
            assert 'plain aluminum' in text
            literal[code] = int(re.search(r'600x600x(\d+)mm', text).group(1))
        assert literal[code] == r['thickness_mm']
        evidence[code] = {'row_text':text,'thickness_mm':literal[code],
                          'word_indices':[w['word_index'] for w in fresh]}
    by = {}
    for e in M['els']:
        by.setdefault(e['id'],[]).append(e)
    records = []
    for eid,r in D['records'].items():
        assert len(by.get(eid,[])) == 1, 'Ceiling identity missing/duplicate: '+eid
        e = by[eid][0]; g = e['g']; mm = literal[r['ceiling_code']]
        assert (e['c'],e['t'],e['l'],e['m'],e['mark']) == (r['category'],r['type'],r['level'],r['material_code'],r['mark'])
        assert g[0] == 'p' and len(g) in (4,5)
        assert CS.digest(g) == r['after_geometry_sha256']
        assert g[2] == r['lower_face_z_m'] and g[3] == round(g[2]+mm/1000,3)
        assert abs((g[3]-g[2])*1000-mm) < 1e-8
        assert CS.digest([g[1],g[4] if len(g)>4 else None]) == r['unchanged_xy_rings_sha256']
        before = copy.deepcopy(g); before[3] = r['before_upper_z_m']
        assert CS.digest(before) == r['before_geometry_sha256']
        assert e['a']['ceiling_source_thickness_verified'] is True
        assert e['a']['ceiling_location_shape_fully_verified'] is False
        for k,v in r['retained_source_assignment'].items():
            assert e['a'].get(k) == v
        records.append({'id':eid,'type':e['t'],'lower_z_m':g[2],
                        'before_upper_z_m':r['before_upper_z_m'],'after_upper_z_m':g[3],
                        'thickness_mm':mm,'xy_and_lower_face_unchanged':True})
    for r in D['excluded_vertical_risers']:
        assert len(by.get(r['id'],[])) == 1
        assert CS.digest(by[r['id']][0]['g']) == r['geometry_sha256']
    assert len(records) == 281 and sum(r['type']=='ceil_C1' for r in records) == 192
    return {'schema':'c4.ceiling-shape-match-source-audit.v1','pass':True,
            'data_sha256':CS.DATA_SHA256,'source_pdf_sha256':D['source_pdf']['sha256'],
            'source_rows':evidence,'checked_count':len(records),'records':records,
            'excluded_vertical_risers_unchanged':2,'xy_or_absolute_Z_newly_accepted':0,
            'location_shape_fully_verified':0}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,default=REPO/'src/model.json')
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    M = json.loads(args.model.read_text())
    D = CS.data(); controlled=set(D['records'])
    unrelated = {e['id']:CS.digest(e) for e in M['els'] if e['id'] not in controlled}
    current = [copy.deepcopy(e) for e in M['els'] if e['id'] in controlled or e['t']=='ceil_riser']
    # Exercise a baseline even when checking a model that already contains the correction.
    for e in current:
        if e['id'] in controlled:
            r=D['records'][e['id']]; e['g'][3]=r['before_upper_z_m']
            e['a']=copy.deepcopy(r['retained_source_assignment'])
    baseline={'els':current,'meta':{'unrelated':'retained'}}
    assert CS.apply(baseline)['changed']==281
    snapshot=copy.deepcopy(baseline)
    assert CS.apply(baseline)['changed']==0 and baseline==snapshot
    guards=[]
    for mode in ('missing','duplicate','xy_changed','lower_z_changed','type_changed','source_zone_changed','extra_ceiling','riser_changed'):
        bad=copy.deepcopy(snapshot); first=bad['els'][0]
        if mode=='missing':bad['els'].remove(first)
        elif mode=='duplicate':bad['els'].append(copy.deepcopy(first))
        elif mode=='xy_changed':first['g'][1][0][0]+=.1
        elif mode=='lower_z_changed':first['g'][2]+=.001
        elif mode=='type_changed':first['t']='ceil_C3' if first['t']=='ceil_C1' else 'ceil_C1'
        elif mode=='source_zone_changed':first['a']['fcl_m']+=.1
        elif mode=='extra_ceiling':
            extra=copy.deepcopy(first);extra['id']='A.ceil-G-UNEXPECTED';bad['els'].append(extra)
        else:
            next(e for e in bad['els'] if e['t']=='ceil_riser')['g'][3]+=.001
        frozen=copy.deepcopy(bad)
        try:CS.apply(bad)
        except ValueError:
            assert bad==frozen,'Partial mutation on failed guard: '+mode
            guards.append(mode)
        else:raise AssertionError('Missing guard: '+mode)
    applied=CS.apply(M)
    proof=audit(M)
    assert {e['id']:CS.digest(e) for e in M['els'] if e['id'] not in controlled}==unrelated
    issues=CS.issue_records(M)
    proof.update(guards_passed=guards,idempotence_passed=True,unrelated_objects_unchanged=len(unrelated),
                 issue_ids=[r['id'] for r in issues],changed_on_input=applied['changed'])
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in proof.items() if k not in ('records','source_rows')},ensure_ascii=False))
