"""Reusable Hunyuan3D-2 / Mini prop adapter. Existing Comfy core is read-only.

Hunyuan uses installed Comfy core checkpoint/conditioning/sampling/VAE, with
CPU scikit-image marching cubes (0.5 decoded field = zero raw isosurface).
No custom Comfy nodes, web service, user config or existing outputs are touched.
"""
import argparse,os,sys,time,json,hashlib,threading,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
config=json.loads((ROOT/"machine.json").read_text(encoding="utf-8"))
p=argparse.ArgumentParser()
p.add_argument('--model',choices=['hunyuan-mini','hunyuan-full'],default='hunyuan-full')
p.add_argument('--input',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--latent',type=Path,help='Reuse archived latent for surface-extraction refinement without repainting or new diffusion')
p.add_argument('--surface-smoothing',type=float,default=0,help='Gaussian sigma in volume voxels; use only after checking raw form')
p.add_argument('--run',default='r1');p.add_argument('--seed',type=int,default=1992)
p.add_argument('--resolution',type=int,default=256);p.add_argument('--steps',type=int,default=30)
p.add_argument('--chunks',type=int,default=8000);p.add_argument('--import-only',action='store_true')
args=p.parse_args(); OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=False)
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
os.environ['HF_HOME']=str(ROOT/'runtime/hf-cache');os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['NUMBA_CACHE_DIR']=str(ROOT/'runtime/numba-cache')
os.environ['TORCH_HOME']=str(ROOT/'runtime/torch-cache')
metrics=dict(model=args.model,run=args.run,parameters={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},started=time.strftime('%Y-%m-%dT%H:%M:%S%z'),success=False,stages={})
def sha(path):
 with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
input_path=args.input.resolve();metrics['input_sha256']=sha(input_path)
if args.latent:
 previous=json.loads((args.latent.parent/'metrics.json').read_text(encoding='utf8'))
 if previous['model']!=args.model or previous['input_sha256']!=metrics['input_sha256']:
  raise ValueError('Archived latent model/input differs from this request; preserve and generate a new candidate')
metrics['license_holds']=['EU','UK','South Korea'];metrics['release_approval']=False
metrics['backend']='installed Comfy core modules; no API/UI/server started'
stop=threading.Event();samples=[];begin=time.perf_counter()
def monitor():
 while not stop.is_set():
  try:
   s=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free,utilization.gpu,temperature.gpu','--format=csv,noheader,nounits'],creationflags=0x08000000,text=True).strip().split(',')
   samples.append(dict(t_s=round(time.perf_counter()-begin,3),used_mib=int(s[0]),free_mib=int(s[1]),util_pct=int(s[2]),temp_c=int(s[3])))
  except Exception:pass
  stop.wait(2)
thread=threading.Thread(target=monitor,daemon=True);thread.start()
stage_start=begin
def stage(name):
 global stage_start
 if 'torch' in sys.modules and torch.cuda.is_initialized():torch.cuda.synchronize()
 now=time.perf_counter();metrics['stages'][name]=round(now-stage_start,3);stage_start=now
 print('STAGE',name,metrics['stages'][name],flush=True)
def prepare_rgb():
 # Same deterministic native-style input preparation for all three models.
 # No repainting, detail synthesis or model-specific image enhancement.
 from PIL import Image
 import numpy as np
 rgba=np.array(Image.open(input_path).convert('RGBA'));mask=rgba[...,3]>0
 yy,xx=np.where(mask);fg=rgba[yy.min():yy.max()+1,xx.min():xx.max()+1]
 side=int(max(fg.shape[:2])/0.85);canvas=np.zeros((side,side,4),dtype=np.uint8)
 y=(side-fg.shape[0])//2;x=(side-fg.shape[1])//2;canvas[y:y+fg.shape[0],x:x+fg.shape[1]]=fg
 a=canvas[...,3:4].astype(np.float32)/255.0
 rgb=(canvas[...,:3].astype(np.float32)*a+127.5*(1-a)).round().clip(0,255).astype(np.uint8)
 im=Image.fromarray(rgb);im.save(OUT/'prepared-input.png')
 metrics['prepared_input_sha256']=sha(OUT/'prepared-input.png');metrics['preprocessing']='alpha bbox >0; square; foreground ratio .85; alpha over 50% gray; identical across candidates'
 return im
try:
 import numpy as np,torch,trimesh
 from skimage.measure import marching_cubes
 torch.manual_seed(args.seed);np.random.seed(args.seed)
 torch.set_grad_enabled(False)
 metrics['runtime']=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0))
 torch.cuda.reset_peak_memory_stats()
 image=prepare_rgb()
 if args.model.startswith('hunyuan'):
  COMFY=Path(config['comfy_core'])
  sys.path.insert(0,str(COMFY))
  sys.argv=[str(__file__),'--base-directory',str(ROOT/'runtime/comfy'),'--lowvram','--disable-dynamic-vram','--reserve-vram','1.0','--use-pytorch-cross-attention','--preview-method','none','--disable-all-custom-nodes','--disable-api-nodes']
  import comfy.options
  comfy.options.enable_args_parsing()
  import comfy.sd,comfy.model_management as mm
  import nodes
  from comfy_extras.nodes_model_advanced import ModelSamplingAuraFlow
  from comfy_extras.nodes_hunyuan3d import EmptyLatentHunyuan3Dv2,Hunyuan3Dv2Conditioning
  stage('imports_and_preprocessing')
  if args.import_only:metrics['success']=True
  else:
   checkpoint=Path(config['checkpoint'] if args.model=='hunyuan-mini' else config['checkpoint_full'])
   metrics['checkpoint']=str(checkpoint)
   model,_,vae,vision=comfy.sd.load_checkpoint_guess_config(str(checkpoint),output_clip=False,output_clipvision=True)
   metrics['detected_model_class']=type(model.model).__name__;metrics['detected_model_config']=type(model.model.model_config).__name__
   stage('checkpoint_load')
   it=torch.from_numpy(np.asarray(image).astype(np.float32)/255.0)[None]
   encoded=vision.encode_image(it,crop=False)
   pos,neg=Hunyuan3Dv2Conditioning.execute(encoded).result
   mm.unload_all_models();torch.cuda.empty_cache()
   stage('image_conditioning')
   model=ModelSamplingAuraFlow().patch_aura(model,1.0)[0]
   latent=EmptyLatentHunyuan3Dv2.execute(3072,1).result[0]
   with torch.inference_mode():
    result={'samples':torch.load(args.latent,map_location='cpu',weights_only=True)} if args.latent else nodes.common_ksampler(model,args.seed,args.steps,5.0,'euler','normal',pos,neg,latent)[0]
   torch.save(result['samples'].cpu(),OUT/'latent.pt')
   stage('diffusion')
   mm.unload_all_models();torch.cuda.empty_cache()
   with torch.inference_mode():
    grid=vae.decode(result['samples'],vae_options={'num_chunks':args.chunks,'octree_resolution':args.resolution})
   # ShapeVAE returns XZY, generic VAE.decode moves X to the last axis -> ZYX.
   # Its generic process_output also maps raw logits with (x+1)/2 and clamps.
   field=grid[0].float().cpu().numpy().transpose(2,1,0)
   metrics['field_percentiles']=np.nanpercentile(field,[0,10,50,90,100]).tolist()
   if args.surface_smoothing:
    from scipy.ndimage import gaussian_filter
    field=gaussian_filter(field,args.surface_smoothing)
   # Keep exported source mesh; density cache deliberately not retained.
   stage('vae_volume_decode')
   v,f,_,_=marching_cubes(field,level=0.5,allow_degenerate=False)
   v=v/(np.array(field.shape)-1)*2.02-1.01
   mesh=trimesh.Trimesh(v,f,process=False)
   if mesh.volume<0:mesh.invert()
   stage('cpu_surface_extraction')
 if not args.import_only:
  mesh.export(OUT/'raw.glb');mesh.export(OUT/'raw.ply')
  metrics['mesh']=dict(vertices=len(mesh.vertices),triangles=len(mesh.faces),bounds=mesh.bounds.tolist(),watertight=bool(mesh.is_watertight),winding_consistent=bool(mesh.is_winding_consistent),volume=float(mesh.volume),uv_present=hasattr(mesh.visual,'uv'),vertex_color=mesh.visual.kind=='vertex',armature=False)
  stage('export_and_mesh_checks');metrics['output_sha256']=sha(OUT/'raw.glb');metrics['success']=True
except Exception as e:
 metrics['error']=dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc());traceback.print_exc()
finally:
 try:
  metrics['torch_peak_allocated_mib']=round(torch.cuda.max_memory_allocated()/1048576,2)
  metrics['torch_peak_reserved_mib']=round(torch.cuda.max_memory_reserved()/1048576,2)
 except Exception:pass
 stop.set();thread.join(timeout=4)
 metrics['total_s']=round(time.perf_counter()-begin,3)
 if samples:
  metrics['gpu_baseline_used_mib']=samples[0]['used_mib'];metrics['gpu_peak_device_used_mib']=max(x['used_mib'] for x in samples)
 (OUT/'gpu-samples.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
 (OUT/'metrics.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False),encoding='utf-8')
 print(json.dumps(metrics,indent=2,ensure_ascii=False),flush=True)
sys.exit(0 if metrics['success'] else 1)
