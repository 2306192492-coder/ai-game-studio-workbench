"""Fetch only official SD-Turbo fp16 inference weights, verifying upstream LFS hashes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, urllib.request, time, subprocess
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Models'/'diffusers'/'sd-turbo'
OUT.mkdir(parents=True,exist_ok=True)
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE='https://huggingface.co/stabilityai/sd-turbo/resolve/main/'
files={
 'unet/diffusion_pytorch_model.fp16.safetensors':'40ec400881e27d1376c7c95c5bd495f407b33756e80eb6365e301c33a07af6e5',
 'text_encoder/model.fp16.safetensors':'bc1827c465450322616f06dea41596eac7d493f4e95904dcb51f0fc745c4e13f',
 'vae/diffusion_pytorch_model.fp16.safetensors':'3e4c08995484ee61270175e9e7a072b66a6e4eeb5f0c266667fe1f45b90daf9a',
 'model_index.json':None,'LICENSE.md':None,'README.md':None,
 'unet/config.json':None,'text_encoder/config.json':None,'vae/config.json':None,
}
def download(item):
 name,expected=item; dest=OUT/name; dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists() and (not expected or hashlib.file_digest(dest.open('rb'),'sha256').hexdigest()==expected):
  print('already_verified',name,flush=True)
 else:
  temp=dest.with_suffix(dest.suffix+'.partial')
  for attempt in range(3):
   try:
    print('downloading',name,flush=True)
    log=ROOT/'Evidence'/('download-'+name.replace('/','-')+'.log')
    with log.open('a',encoding='utf-8') as stream:
     subprocess.run(['curl.exe','--noproxy','*','-fL','--retry','2','--connect-timeout','20','--max-time','1800','-C','-','--output',str(temp),BASE+name+'?download=true'],stdout=stream,stderr=stream,check=True)
    if expected and hashlib.file_digest(temp.open('rb'),'sha256').hexdigest()!=expected:raise ValueError('SHA256 mismatch: '+name)
    temp.replace(dest);break
   except Exception:
    if attempt==2:raise
    time.sleep(2)
  print('download_verified',name,dest.stat().st_size,flush=True)
 return dict(path=str(dest.relative_to(ROOT)),bytes=dest.stat().st_size,sha256=hashlib.file_digest(dest.open('rb'),'sha256').hexdigest(),upstream_sha256=expected,source=BASE+name)
with ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(download,files.items()))
(ROOT/'Evidence'/'sd-turbo-download.json').write_text(json.dumps(dict(provider='Stability AI',purpose='Local toolchain image-inference validation',files=records),indent=2),encoding='utf-8')
