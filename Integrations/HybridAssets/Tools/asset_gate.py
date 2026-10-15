"""Validate registered assets and inherited restrictions before promotion or release."""
import argparse,json,hashlib,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--asset',required=True);p.add_argument('--scope',choices=['local','public','global'],default='local');p.add_argument('--engine',default='Unity');p.add_argument('--ai-input',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parent.parent;reg=json.loads((root/'Registry/asset-manifest.json').read_text(encoding='utf8'));records={x['id']:x for x in reg['assets']};problems=[];seen=set()
def check(id):
 if id in seen:return
 seen.add(id)
 x=records.get(id)
 if x is None:problems.append('Unknown asset '+id);return
 if not x.get('license_verified'):problems.append(id+': license unverified')
 if a.engine=='Unity' and x.get('ue_only'):problems.append(id+': UE-only cannot enter Unity')
 if a.ai_input and not x.get('ai_input_allowed',False):problems.append(id+': AI input is not cleared')
 if a.scope!='local' and not x.get('public_release_approved',False):problems.append(id+': public release scope not approved')
 if a.scope=='global' and x.get('territory_exclusions'):problems.append(id+': inherited territory exclusions '+', '.join(x['territory_exclusions']))
 for f in x.get('files',[]):
  path=(root/f['path']).resolve()
  if not path.is_file():problems.append(id+': missing '+f['path']);continue
  with path.open('rb') as source:actual=hashlib.file_digest(source,'sha256').hexdigest()
  if actual!=f['sha256']:problems.append(id+': file hash changed '+f['path'])
 for dep in x.get('derived_from',[]):check(dep)
check(a.asset)
if records.get(a.asset,{}).get('quality_status')!='prototype_verified':problems.append(a.asset+': not verified as a runtime prototype')
out={'asset':a.asset,'scope':a.scope,'engine':a.engine,'checked_dependencies':sorted(seen),'allowed':not problems,'problems':problems}
print(json.dumps(out,indent=2,ensure_ascii=False));sys.exit(0 if not problems else 2)
