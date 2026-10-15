param([Parameter(Mandatory=$true)][string]$InputImage,[string]$RunName=('prop-'+(Get-Date -Format 'yyyyMMdd-HHmmss')),[ValidateSet('hunyuan-mini','hunyuan-full')][string]$Model='hunyuan-full',[int]$Seed=1992,[int]$Resolution=256)
$ErrorActionPreference='Stop'
$integration=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $integration 'machine.json') -Raw | ConvertFrom-Json
if($RunName -notmatch '^[A-Za-z0-9_-]+$'){throw 'RunName must be a simple new directory name'}
$checkpoint=if($Model -eq 'hunyuan-full'){$config.checkpoint_full}else{$config.checkpoint}
foreach($path in @($config.python,$checkpoint,$config.comfy_core,$InputImage)){if(!(Test-Path -LiteralPath $path)){throw "Missing dependency: $path"}}
$output=Join-Path $integration ('Generated\'+$RunName)
if(Test-Path -LiteralPath $output){throw 'Output already exists; preserve previous candidate and use a new RunName'}
& $config.python (Join-Path $PSScriptRoot 'hunyuan_prop.py') --model $Model --input $InputImage --output $output --seed $Seed --resolution $Resolution
if($LASTEXITCODE -ne 0){throw "Generation failed; retained evidence at $output"}
Write-Output $output
