"""Scoped persistence for one source-plan wall; no physical acceptance."""
import collections,copy
import d16_host_source_correction as G
ID='S.wall-G-RS002'
def refresh(M,report):
 import check_component_coverage as CC
 from source_batch import cc_geometry_sha
 D=G.data();e=next(e for e in M['els']if e['id']==ID)
 if e!=G._after(D['records'][ID]):raise ValueError('D16 host CC geometry/identity mismatch')
 if report['model_geometry_sha256']!=cc_geometry_sha(M):raise ValueError('D16 host CC stale input')
 R=copy.deepcopy(report);r=next(r for r in R['rows']if r['id']==ID)
 r.update(status='source_checked',xy_basis='حد الجدار المعماري من A102 رسم37188 وA604 رسم4780',z_basis='assumed_or_derived',source='ARCH1:5 A102 / ARCH2:5 A604',findings=['XY فقط؛ الجسم الرأسي والمادة والتثبيت غير معتمدة'])
 R['details'][ID]={'category':e['c'],'type':e['t'],'level':e['l'],'geometry_kind':'p','xy_cm':CC.xy(e['g']),'z_m':CC.z_range(e['g']),'source_refs':CC.references(M,e),'height_assumptions':['نطاق العرض القديم محفوظ؛ Z غير معتمد'],'evidence':{'source_data_sha256':G.DATA_SHA},'needs_original_xy_proof':False,'needs_height_proof':True,'needs_dimension_semantic_review':True,'whole_physical_body_source_accepted':False}
 by={e['id']:e for e in M['els']};fam=collections.defaultdict(collections.Counter)
 for q in R['rows']:fam[by[q['id']]['c'][0]][q['status']]+=1
 R['counts']=dict(collections.Counter(q['status']for q in R['rows']));R['by_family']={k:dict(v)for k,v in fam.items()};R['height_counts']=dict(collections.Counter(q['z_basis']for q in R['rows']));M['componentReview']=CC.compact(R);return R

def update_material_review(M):
 mid='wall_source_unknown';R=M['materialReview'];materials=R['materials']
 materials[mid]={'id':mid,'status':'unknown','source_material_literal':'unknown','source_finish_literal':'unknown','physical_color_literal':'unknown','physical_color_hex':None,'source_refs':['ARCH1:5 A102','ARCH2:5 A604'],'assignment_limit':'Architectural plan identity only; RC, material, finish and colour unproved','display_color_only':True,'expected_element_ids':[ID]}
 C=R['counts'];C['physical_material_ids']=len(materials);C['counts']=dict(collections.Counter(r['status']for r in materials.values()));M['meta']['source_material_review']=copy.deepcopy(C)
