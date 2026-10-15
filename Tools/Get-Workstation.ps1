$root=Split-Path -Parent $PSScriptRoot
$file=Join-Path $root 'Config\workstation.local.json'
if(!(Test-Path -LiteralPath $file)){throw 'Run Tools/Initialize-Workstation.ps1 and edit Config/workstation.local.json first'}
Get-Content -LiteralPath $file -Raw|ConvertFrom-Json
