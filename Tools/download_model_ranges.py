"""Bounded range downloads, resumed parts and final upstream SHA-256 validation."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,hashlib,json,time,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Models'/'diffusers'/'sd-turbo'
BASE='https://huggingface.co/stabilityai/sd-turbo/resolve/b261bac6fd2cf515557d5d0707481eafa0485ec2/'
SPEC=[('unet/diffusion_pytorch_model.fp16.safetensors',1731904736,'40ec400881e27d1376c7c95c5bd495f407b33756e80eb6365e301c33a07af6e5'),('text_encoder/model.fp16.safetensors',680820392,'bc1827c465450322616f06dea41596eac7d493f4e95904dcb51f0fc745c4e13f'),('vae/diffusion_pytorch_model.fp16.safetensors',167335342,'3e4c08995484ee61270175e9e7a072b66a6e4eeb5f0c266667fe1f45b90daf9a')]
CHUNK=16*1024*1024
jobs=[]
for name,size,expected in SPEC:
 dest=OUT/name
 if dest.exists() and hashlib.file_digest(dest.open('rb'),'sha256').hexdigest()==expected:continue
 parts=dest.parent/(dest.name+'.parts');parts.mkdir(exist_ok=True,parents=True)
 old=dest.with_suffix(dest.suffix+'.partial')
 if old.exists():
  with old.open('rb') as src:
   for i in range(size//CHUNK+1):
    data=src.read(CHUNK)
    if len(data)!=min(CHUNK,size-i*CHUNK):break
    p=parts/str(i)
    if not p.exists():p.write_bytes(data)
 for i,start in enumerate(range(0,size,CHUNK)):
  end=min(size-1,start+CHUNK-1);part=parts/str(i)
  if not part.exists() or part.stat().st_size!=end-start+1:jobs.append((name,part,start,end))
def fetch(job):
 name,path,start,end=job
 for retry in range(20):
  temporary=path.with_suffix('.tmp')
  offset=temporary.stat().st_size if temporary.exists() else 0
  if offset==end-start+1:
   temporary.replace(path);print('part_verified_length',name,path.name,flush=True);return
  if offset>end-start+1:raise RuntimeError('Oversize partial part')
  remaining=path.with_suffix('.next');headers=path.with_suffix('.headers')
  p=subprocess.run(['curl.exe','--noproxy','*','-fLsS','--connect-timeout','15','--max-time','90','--speed-time','15','--speed-limit','2048','--range',f'{start+offset}-{end}','-D',str(headers),'-o',str(remaining),BASE+name+f'?download=true&range_start={start+offset}'],capture_output=True)
  header=headers.read_text(errors='replace') if headers.exists() else ''
  ranges=re.findall(r'(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)',header)
  if ranges and int(ranges[-1][0])==start+offset and remaining.exists():
   data=remaining.read_bytes()
   if 0<len(data)<=end-start+1-offset:
    with temporary.open('ab') as output:output.write(data)
    print('range_progress',name,path.name,temporary.stat().st_size,flush=True)
  time.sleep(1)
 raise RuntimeError(f'Range download failed: {name} {start}-{end}: {p.stderr[-300:]}')
print('remaining_parts',len(jobs),flush=True)
with ThreadPoolExecutor(max_workers=8) as pool:
 for result in as_completed([pool.submit(fetch,j) for j in jobs]):result.result()
records=[]
for name,size,expected in SPEC:
 dest=OUT/name
 if not(dest.exists() and hashlib.file_digest(dest.open('rb'),'sha256').hexdigest()==expected):
  assembled=dest.with_suffix('.assembling')
  with assembled.open('wb') as dst:
   for i,start in enumerate(range(0,size,CHUNK)):dst.write((dest.parent/(dest.name+'.parts')/str(i)).read_bytes())
  if hashlib.file_digest(assembled.open('rb'),'sha256').hexdigest()!=expected:raise ValueError('Final upstream SHA256 mismatch: '+name)
  assembled.replace(dest)
 records.append(dict(path=str(dest.relative_to(ROOT)),bytes=size,sha256=expected,source=BASE+name))
 print('MODEL_VERIFIED',name,flush=True)
(ROOT/'Evidence'/'sd-turbo-download.json').write_text(json.dumps(dict(provider='Stability AI',revision='b261bac6fd2cf515557d5d0707481eafa0485ec2',files=records),indent=2),encoding='utf-8')
