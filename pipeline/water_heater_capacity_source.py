"""Property-only correction of21 heater50L source glyphs, with82 capacity facts.

apply(M,els=None) is intended after actual body/ceiling generation is complete.
It preserves every existing ID/category/level/geometry/material and changes
only the source-defined capacity/type/mark plus scoped property metadata.
No physical body dimensions, Z, materials, mounts, ports or connections pass.
"""
from pathlib import Path
import copy,hashlib,json,sys
HERE=Path(__file__).resolve().parent
if str(HERE)not in sys.path:sys.path.insert(0,str(HERE))
TOOLS=HERE.parent/'tools'
if TOOLS.is_dir()and str(TOOLS)not in sys.path:sys.path.insert(0,str(TOOLS))
import check_water_heater_capacity_source as G
DATA_PATH=HERE/'data'/'water_heater_capacity_source.json'
TYPES={}
def type_cards(M):
 # Inherit the current original card including installation detail mt/WS-106.
 # Only the obsolete all80L fallback and the capacity-specific additions change.
 base=copy.deepcopy(M['types']['heater80']);result={}
 own_labels={'السعة المثبتة بالرمز','القدرة في مفتاحWS','الكمية المرجعيةBOQ:12'}
 limits='مقاس جسم العرض وارتفاعه وZ والمادة والتركيب والمنافذ كما كانت غير معتمدة بهذا الإثبات'
 for cap,power in[(50,1.2),(80,1.5)]:
  card=copy.deepcopy(base)
  card['n']=f'سخان مياه كهربائي أفقي معلّق بالسقف — {cap}لتر من المصدر'
  card['sp']=[r for r in card.get('sp',[])if not r or r[0]not in own_labels]
  card['sp'] += [['السعة المثبتة بالرمز',f'{cap}L مكتوبة بخطوط الرمز الأصلي؛ لا تمثل أبعاد جسم الجهاز'],['القدرة في مفتاحWS',f'{power}kW'],['الكمية المرجعيةBOQ:12',f'{21 if cap==50 else 61} سخانًا؛ ربط الأفراد من أرقام الرسم لا تقسيم الكمية']]
  card['asm']=[r for r in card.get('asm',[])if 'تعذّر ربط وسم السعة برمز كل سخان'not in r]
  if limits not in card['asm']:card['asm'].append(limits)
  card['sr']=list(card.get('sr',[]))
  for ref in ['MECH2:19–22 رموزWATER وMECH2:20مفتاح50L/80L','BOQ:12 بنود10.1.13.3/4']:
   if ref not in card['sr']:card['sr'].append(ref)
  result['heater'+str(cap)]=card
 return result
def apply(M,els=None):
 els=M['els']if els is None else els
 if G.sha(DATA_PATH)!=G.FROZEN_SHA:raise ValueError('Frozen heater-capacity data changed')
 D=json.loads(DATA_PATH.read_text());raw=G.verify_source(D)
 if not raw['pass']:raise ValueError('Original heater-capacity source proof failed: '+str(raw['global_findings']))
 es=[e for e in els if e['c']=='P.heater'];by={e['id']:e for e in es};records=D['records']
 if len(es)!=82 or len(by)!=82 or set(by)!=set(records):raise ValueError('Exact heater82 inventory guard failed')
 cards=type_cards(M)
 # Validate all guards before any mutation.
 for eid,r in records.items():
  e=by[eid];a=e.get('a')or{}
  if(e['c'],e['l'],e['g'])!=(r['category'],r['level'],r['before_g']):raise ValueError('Heater preservation guard: '+eid)
  states=[(r['before_type'],r['before_mark'],r['before_capacity_l'],r['before_cap_known']),(r['after_type'],r['after_mark'],r['source_capacity_l'],True)]
  if(e['t'],e.get('mark'),a.get('cap_l'),a.get('cap_known'))not in states:raise ValueError('Heater property guard: '+eid)
  prior=a.get('source_heater_capacity_review')
  if prior is not None and(prior.get('data_sha256')!=G.FROZEN_SHA or prior.get('source_key')!=r['source_key']):raise ValueError('Heater metadata revision guard: '+eid)
 changed=[]
 for eid,r in records.items():
  e=by[eid];a=e.setdefault('a',{})
  if e['t']!=r['after_type']:changed.append(eid)
  e['t']=r['after_type'];e['mark']=r['after_mark'];a['cap_l']=r['source_capacity_l'];a['cap_known']=True
  a['source_heater_capacity_review']={'source_key':r['source_key'],'data_sha256':G.FROZEN_SHA,'capacity_literal_l':r['source_capacity_l'],'power_literal_kw':r['source_power_kw'],'property_scope':'capacity_and_power_literal_only','whole_body_source_checked':False,'physical_dimensions_Z_material_mount_ports_accepted':False,'source_before_g_sha256':hashlib.sha256(json.dumps(r['before_g'],separators=(',',':')).encode()).hexdigest()}
 M.setdefault('types',{}).update(cards)
 stats={**D['summary'],'changed_type_ids_this_apply':changed,'changed_types_this_apply':len(changed),'source_data_sha256':G.FROZEN_SHA,'scope':'partial_capacity_power_property_only; g/c/l/m/ID preserved'}
 M.setdefault('meta',{})['water_heater_capacity_source']=stats
 return stats
build=apply
