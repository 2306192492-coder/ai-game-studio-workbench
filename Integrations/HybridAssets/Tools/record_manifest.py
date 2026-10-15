"""Record exact adopted files; preserve source ancestry and local-only release scope."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent.parent
def file(path):
 p=(root/path).resolve()
 with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 return {'path':path,'bytes':p.stat().st_size,'sha256':h}
assets=[
 {'id':'gpt-shell-reference','provider':'Codex built-in imagegen','source':'Sources/GPT/prompt.txt','license':'Original image generated for the user; provider service terms apply','license_verified':True,'ai_input_allowed':True,'public_release_approved':False,'quality_status':'design_reference','files':[file('Sources/GPT/shell-reference-v1.png'),file('Sources/GPT/prompt.txt')]},
 {'id':'hunyuan-full-form','provider':'Tencent Hunyuan3D-2 full','source':'https://huggingface.co/tencent/Hunyuan3D-2','license':'Tencent Hunyuan 3D 2.0 Community License','license_verified':True,'license_archive':'Evidence/Licenses/hunyuan-full-current.txt','territory_exclusions':['EU','UK','South Korea'],'ai_input_allowed':False,'public_release_approved':False,'quality_status':'raw_form_only','derived_from':['gpt-shell-reference'],'files':[file('Generated/shell-full-v1/raw.glb'),file('Generated/shell-full-v1/metrics.json')]},
 {'id':'shell-lamp','provider':'GPT + Hunyuan3D-2 full + Blender','license':'Inherited Tencent output restrictions; Blender does not clear them','license_verified':True,'territory_exclusions':['EU','UK','South Korea'],'ai_input_allowed':False,'public_release_approved':False,'quality_status':'prototype_verified','derived_from':['hunyuan-full-form'],'runtime_scope':'static prop, coarse BoxCollider; no rig or gameplay acceptance','files':[file('Generated/shell-full-refined-v1/'+n) for n in ['ShellLamp.blend','ShellLamp.fbx','ShellLamp.glb','shell-glaze.png','refinement.json']]},
 {'id':'fab-harbor','provider':'heavycross / Fab','source':'https://www.fab.com/listings/0c437b11-4734-44cb-b644-9a37abcb6234','ownership_verified':'2026-10-14 authenticated My Library and owned Download dialog','acquisition_date':'not independently recovered; owned license displayed as Standard License','license':'Fab Standard License','license_verified':True,'license_archive':'Evidence/Licenses/fab-full-current.txt','ue_only':False,'formats':['Unity','FBX','GLB'],'noai_displayed':True,'ai_input_allowed':False,'public_release_approved':False,'release_note':'Can be incorporated into a qualifying game subject to EULA. This asset-only showroom and raw source package are local validation, not a public redistribution product. NoAI restriction archived; do not feed vendor assets into generation in this workflow.','quality_status':'prototype_verified','files':[file('Sources/Fab/harbor_props_pack_vol_1.unitypackage')]}
]
result={'version':1,'verified':'2026-10-14','preserve_failed_candidates':True,'scope':'Private local pipeline validation; none is blanket commercial/global release approval','assets':assets}
(root/'Registry/asset-manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8',newline='\n')
paths=['Evidence/full-authored-metrics.json','Evidence/full-imported-metrics.json','Evidence/unity-import-report.json','Evidence/build-report.json','Evidence/latest-windows-run.json','Evidence/environment-verdict.json','Evidence/Licenses/fab-full-current.txt','Evidence/Licenses/hunyuan-mini-current.txt','Evidence/Licenses/hunyuan-full-current.txt']
(root/'Evidence/integration-file-hashes.json').write_text(json.dumps([file(p) for p in paths],indent=2),encoding='utf8',newline='\n')
print('Registered 4 source/adopted records; inherited restrictions retained; evidence hashes recorded')
