"""Extract only reviewed art folders; keep GUID metadata, reject scripts and collisions."""
import argparse,hashlib,json,tarfile
from pathlib import Path,PurePosixPath
p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
project=a.project.resolve(); prefix='Assets/Harbor Props Pack vol.1/'
def sha(b):return hashlib.sha256(b).hexdigest()
report={'package_sha256':sha(a.package.read_bytes()),'project':str(project),'files':[],'excluded':[]}
planned=[]
with tarfile.open(a.package) as t:
 members={m.name:m for m in t.getmembers()}
 for m in t.getmembers():
  if not m.name.endswith('/pathname'):continue
  name=t.extractfile(m).read().decode('utf8').strip(); pos=PurePosixPath(name)
  if pos.is_absolute() or '..' in pos.parts or '\\' in name:raise ValueError('Unsafe path')
  suffix=name[len(prefix):] if name.startswith(prefix) else ''
  if not suffix or suffix.split('/')[0] not in {'Models','Prefabs','Materials','Textures'}:
   report['excluded'].append(name);continue
  if pos.suffix.lower() in {'.cs','.dll','.exe','.shader','.unitypackage'}:raise ValueError('Unreviewed executable asset '+name)
  folder=m.name.rsplit('/',1)[0]
  for part,extension in [('asset',''),('asset.meta','.meta')]:
   key=folder+'/'+part
   if key not in members:continue
   data=t.extractfile(members[key]).read(); target=(project/(name+extension)).resolve()
   if not target.is_relative_to(project/'Assets'):raise ValueError('Outside Assets')
   if target.exists() and (not target.is_file() or target.read_bytes()!=data):raise FileExistsError(target)
   planned.append((target,data))
 for target,data in planned:
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  report['files'].append({'path':str(target.relative_to(project)),'bytes':len(data),'sha256':sha(data)})
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'imported':len(planned),'excluded':len(report['excluded']),'report':str(a.report)}))
