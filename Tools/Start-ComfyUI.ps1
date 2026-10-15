param([int]$Port=8188)
$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
$workstation=& (Join-Path $PSScriptRoot 'Get-Workstation.ps1')
$python=$workstation.comfy_python
$comfy=$workstation.comfy_root
foreach($required in @($python,(Join-Path $comfy 'main.py'),$workstation.comfy_models)){
 if(!(Test-Path -LiteralPath $required)){throw "Configured ComfyUI dependency missing: $required"}
}
try { $existing=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 2; if($existing.system){ Write-Output "ComfyUI already responds on $Port; existing service reused."; return } } catch {}
$runtime=Join-Path $studio 'Runtime\ComfyUI'
foreach($name in @('input','output','user','temp')){New-Item -ItemType Directory -Path (Join-Path $runtime $name) -Force | Out-Null}
$paths=@"
shared:
  base_path: $($workstation.comfy_models.Replace('\','/'))
  checkpoints: checkpoints
  diffusion_models: diffusion_models
  text_encoders: text_encoders
  vae: vae
  loras: loras
studio:
  base_path: $($studio.Replace('\','/'))/Models
  diffusers: diffusers
"@
$config=Join-Path $studio 'Config\comfy-model-paths.yaml'
[IO.File]::WriteAllText($config,$paths,[Text.UTF8Encoding]::new($false))
$argList=@('-u',('"'+(Join-Path $comfy 'main.py')+'"'),'--listen','127.0.0.1','--port',"$Port",'--disable-auto-launch','--disable-all-custom-nodes','--extra-model-paths-config',('"'+$config+'"'),'--input-directory',('"'+(Join-Path $runtime 'input')+'"'),'--output-directory',('"'+(Join-Path $runtime 'output')+'"'),'--user-directory',('"'+(Join-Path $runtime 'user')+'"'),'--temp-directory',('"'+(Join-Path $runtime 'temp')+'"'))
$argList+=@('--disable-dynamic-vram','--database-url',('"sqlite:///'+(Join-Path $runtime 'user\comfyui.db').Replace('\','/')+'"'))
$proc=Start-Process -FilePath $python -ArgumentList $argList -WorkingDirectory $comfy -WindowStyle Hidden -RedirectStandardOutput (Join-Path $studio 'Evidence\comfy-stdout.log') -RedirectStandardError (Join-Path $studio 'Evidence\comfy-stderr.log') -PassThru
[pscustomobject]@{pid=$proc.Id;port=$Port;executable=$python;startedUtc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $studio 'Runtime\comfy-process.json') -Encoding utf8
Write-Output "Started owned ComfyUI PID $($proc.Id) on 127.0.0.1:$Port"
