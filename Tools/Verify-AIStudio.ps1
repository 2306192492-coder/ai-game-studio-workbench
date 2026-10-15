param([switch]$SkipWindowsRun,[switch]$CheckComfyUI)
$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
& unity --version
& git lfs version
$unity=(& unity status --project-path (Join-Path $studio 'Project') --json) -join "`n" | ConvertFrom-Json
if(!$unity.success){throw 'Unity Pipeline not ready; run Start-AIStudio.ps1 and wait for import'}
if($CheckComfyUI){
 $comfy=Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 5
 if(!$comfy.system){throw 'Optional ComfyUI service not ready'}
}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $studio 'Evidence\gpt-image-verdict.json')|ConvertFrom-Json
$asset=Join-Path $studio $manifest.asset
if((Get-FileHash -LiteralPath $asset -Algorithm SHA256).Hash -ne $manifest.sha256){throw 'GPT primary image differs from verified source'}
[pscustomobject]@{unity=$unity.data.instances;primaryImage='GPT built-in imagegen';gptAssetVerified=$true;comfyChecked=[bool]$CheckComfyUI}|ConvertTo-Json -Depth 5
if(!$SkipWindowsRun){& (Join-Path $PSScriptRoot 'Run-WindowsQA.ps1')}
