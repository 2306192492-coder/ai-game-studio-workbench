"""Search the preserved Fab catalog; candidate results are never import approval."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('query',nargs='?',default='');p.add_argument('--type',default='');a=p.parse_args()
root=Path(__file__).resolve().parent.parent
catalog=json.loads((root/'Registry/fab-catalog.json').read_text(encoding='utf8'))
for x in catalog['assets']:
 if a.query.lower() not in x['title'].lower() or (a.type and a.type.lower() not in x['type'].lower()):continue
 print(json.dumps({k:x[k] for k in ('title','type','url','status')},ensure_ascii=False))
