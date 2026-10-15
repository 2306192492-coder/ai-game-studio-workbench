"""Real ComfyUI submit -> WebSocket -> history -> view -> Unity texture import."""
import asyncio,json,time,hashlib,uuid,sys,shutil
from pathlib import Path
import aiohttp
from PIL import Image,ImageStat
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8188'
PROMPT={
 '1':{'class_type':'DiffusersLoader','inputs':{'model_path':'sd-turbo'}},
 '2':{'class_type':'CLIPTextEncode','inputs':{'clip':['1',1],'text':'A beautiful painted landscape concept art for a video game, blue mountains, golden sunrise, lush green pine forest, small peaceful stone cottage, soft painterly brushwork, no text, no logos'}},
 '3':{'class_type':'CLIPTextEncode','inputs':{'clip':['1',1],'text':''}},
 '4':{'class_type':'EmptyLatentImage','inputs':{'width':512,'height':512,'batch_size':1}},
 '5':{'class_type':'KSampler','inputs':{'model':['1',0],'positive':['2',0],'negative':['3',0],'latent_image':['4',0],'seed':20261014,'steps':4,'cfg':1.0,'sampler_name':'euler','scheduler':'normal','denoise':1.0}},
 '6':{'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},
 '7':{'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':'AIStudio/landscape'}}}
async def main():
 transport='--transport-only' in sys.argv
 workflow=PROMPT
 if transport:
  shutil.copyfile(ROOT/'AssetsSource'/'PolyHaven'/'american_walnut_veneer'/'american_walnut_veneer_diffuse_1k.jpg',ROOT/'Runtime'/'ComfyUI'/'input'/'walnut-probe.jpg')
  workflow={'1':{'class_type':'LoadImage','inputs':{'image':'walnut-probe.jpg'}},'2':{'class_type':'ImageScale','inputs':{'image':['1',0],'upscale_method':'bilinear','width':512,'height':512,'crop':'disabled'}},'7':{'class_type':'SaveImage','inputs':{'images':['2',0],'filename_prefix':'AIStudio/transport-test'}}}
 client=str(uuid.uuid4());start=time.monotonic();events=[]
 async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=900),trust_env=False) as session:
  if not transport:
   async with session.get(BASE+'/object_info/DiffusersLoader') as r:info=await r.json()
   assert 'sd-turbo' in info['DiffusersLoader']['input']['required']['model_path'][0],info
  async with session.ws_connect(BASE+'/ws',params={'clientId':client}) as ws:
   async with session.post(BASE+'/prompt',json={'client_id':client,'prompt':workflow}) as r:
    queued=await r.json();assert r.status==200,queued
   prompt_id=queued['prompt_id'];print('PROMPT_ID',prompt_id,flush=True)
   async for message in ws:
    if message.type!=aiohttp.WSMsgType.TEXT:continue
    payload=json.loads(message.data);kind=payload.get('type');data=payload.get('data',{})
    if data.get('prompt_id')!=prompt_id:continue
    if kind in ('execution_start','executing','execution_success','execution_error','execution_interrupted'):events.append(payload)
    if kind in ('execution_error','execution_interrupted'):raise RuntimeError(payload)
    if kind=='execution_success' or (kind=='executing' and data.get('node','not-null') is None):break
  async with session.get(BASE+'/history/'+prompt_id) as r:history=(await r.json())[prompt_id]
  assert history['status']['status_str']=='success',history['status']
  output=history['outputs']['7']['images'][0]
  async with session.get(BASE+'/view',params=output) as r:binary=await r.read();assert r.status==200
  destination=ROOT/'Project'/'Assets'/'Studio'/'Textures'/('Pipeline-preview.png' if transport else 'ComfyUI-backup-generated.png');destination.parent.mkdir(exist_ok=True,parents=True);destination.write_bytes(binary)
  image=Image.open(destination);image.load();std=ImageStat.Stat(image.convert('RGB')).stddev
  assert image.size==(512,512) and max(std)>(1 if transport else 15),(image.size,std)
  prefix='comfy-transport' if transport else 'comfy'
  (ROOT/'Evidence'/(prefix+'-prompt.json')).write_text(json.dumps(workflow,indent=2),encoding='utf-8')
  report=dict(passed=True,modelInference=not transport,prompt_id=prompt_id,seconds=round(time.monotonic()-start,3),resolution=list(image.size),standardDeviation=std,sha256=hashlib.sha256(binary).hexdigest(),output=str(destination),history=history,websocketEvents=events)
  (ROOT/'Evidence'/(prefix+'-verdict.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ('history','websocketEvents')}),flush=True)
  async with session.post(BASE+'/free',json={'unload_models':True,'free_memory':True}) as r:await r.read()
asyncio.run(main())
