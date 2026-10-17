"""Independent native-PDF replay of six named electrical-room equipment envelopes."""
import hashlib,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
import fitz
from lib import Sheet
from electrical_room_source_corrections import data,DATA_SHA256
def serial(v):
    if isinstance(v,(str,int,float,bool))or v is None:return v
    return [serial(x)for x in v]
def audit(M):
    # Rehydrate external audit inputs; geometry remains the live model.
    import sys as _audit_sys
    from pathlib import Path as _AuditPath
    _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
    from source_audit_sidecar import audit_model as _source_audit_model
    M = _source_audit_model(M)
    D=data();P=Path(D['original_pdf']['path']);globals=[];checks=[]
    if hashlib.sha256(P.read_bytes()).hexdigest()!=D['original_pdf']['sha256']:globals.append({'reason':'Original PDF SHA changed'})
    doc=fitz.open(P);p10=doc[9];p17=doc[16];drawings=p10.get_drawings();tt10=p10.get_texttrace();tt17=p17.get_texttrace();reg=Sheet('ELEC1',10).reg
    by={}
    for e in M['els']:by.setdefault(e['id'],[]).append(e)
    for id,r in D['records'].items():
        errors=[];s=r['source'];matched=by.get(id,[]);e=matched[0]if len(matched)==1 else None
        if len(matched)!=1:errors.append('missing_or_duplicate_element')
        for q in s['plan_drawings']+s.get('label_leaders',[]):
            raw=drawings[q['drawing_index']]
            if {k:serial(raw.get(k))for k in ('layer','type','fill','color','closePath','rect','items')}!={k:q[k]for k in ('layer','type','fill','color','closePath','rect','items')}:errors.append('native_plan_operator_changed')
        lbl=s['plan_label'];t=tt10[lbl['trace_index']]
        if ''.join(chr(c[0])for c in t['chars'])!=lbl['text']or serial(t['chars'])!=lbl['chars']:errors.append('native_plan_label_changed')
        ds=[drawings[q['drawing_index']]['rect']for q in s['plan_drawings']]
        b=[min(q.x0 for q in ds),min(q.y0 for q in ds),max(q.x1 for q in ds),max(q.y1 for q in ds)]
        xy=[(b[0]+b[2])/2*reg['s']+reg['ox'],-(b[1]+b[3])/2*reg['s']+reg['oy']]
        dim=s['dimension_evidence'];frags=dim['fragments']
        for f in frags:
            t=tt17[f['trace_index']];chars=t['chars'][f['char_start']:f['char_end']]
            if ''.join(chr(c[0])for c in chars)!=f['text']or serial(chars)!=f['chars']:errors.append('native_literal_dimension_or_heading_changed')
        if dim['mode']=='dimension_table_mm':
            values=[float(re.fullmatch(k+r'(\d+)mm',f['text']).group(1))/10 for k,f in zip(('LENGTH','WIDTH','HEIGHT'),frags[1:])]
        else:values=[float(frags[1]['text']),float(frags[3]['text']),float(frags[2]['text'])]
        if values!=dim['dims_cm']:errors.append('literal_dimensions_mismatch')
        deviation=math.dist(e['g'][1:3],xy)if e else None
        if e:
            if e['g']!=r['after_g']:errors.append('literal_extent_geometry_mismatch')
            if e['g'][3:5]!=values[:2]or abs((e['g'][7]-e['g'][6])*100-values[2])>1e-9:errors.append('literal_overall_dimensions_mismatch')
            if e['g'][6:]!=r['before_e']['g'][6:]:errors.append('absolute_Z_changed')
            if deviation>.0001:errors.append('raw_plan_anchor_mismatch')
            a=e.get('a',{})
            if a.get('source_record_sha256')!=r['source_record_sha256']or a.get('source_data_sha256')!=DATA_SHA256:errors.append('source_record_binding_missing')
            if a.get('source_transform')!=reg or s['registration']!=reg:errors.append('source_transform_mismatch')
            if a.get('source_xy')!=xy:errors.append('metadata_raw_plan_anchor_mismatch')
            for k in ('source_Z_verified','source_absolute_Z_verified','source_material_verified','source_mount_verified','source_ports_verified','source_contact_verified','source_colour_verified','source_physical_body_verified','source_front_face_verified'):
                if a.get(k)is not False:errors.append('unsupported_promotion:'+k)
        checks.append({'id':id,'reference':['ELEC1:10','ELEC1:17'],'source_xy':xy,'literal_dimensions_cm':values,'deviation_cm':deviation,'errors':errors,'pass':not errors,'proof_scope':'drawn_plan_anchor_axis_and_literal_overall_extent_only'})
    doc.close()
    return {'schema':'c4.electrical-room-native-source-audit.v1','checks':checks,'global_findings':globals,'summary':{'checked':6,'findings':sum(not c['pass']for c in checks)+len(globals),'uncovered':sum('missing_or_duplicate_element'in c['errors']for c in checks),'max_deviation_cm':max((c['deviation_cm']or 0 for c in checks),default=0),'absolute_Z_verified':0,'installed_material_verified':0,'ports_verified':0}}
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('model');ap.add_argument('--output');args=ap.parse_args();result=audit(json.loads(Path(args.model).read_text()))
    payload=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:Path(args.output).write_text(payload)
    else:print(payload)
    sys.exit(bool(result['summary']['findings']or result['summary']['uncovered']))
