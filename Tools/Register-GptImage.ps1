param([Parameter(Mandatory=$true)][string]$Asset)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$inputFile=(Resolve-Path -LiteralPath $Asset).Path
$relative='Project/Assets/Studio/Textures/GPT-primary-landscape.png'
$target=Join-Path $root $relative
if($inputFile -ne [IO.Path]::GetFullPath($target)){
 if(Test-Path -LiteralPath $target){throw 'Existing GPT image preserved; choose how to archive it before replacing'}
 New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force|Out-Null
 Copy-Item -LiteralPath $inputFile -Destination $target
}
New-Item -ItemType Directory -Path (Join-Path $root 'Evidence') -Force|Out-Null
[ordered]@{asset=$relative;sha256=(Get-FileHash -LiteralPath $target).Hash.ToLower();provider='Codex built-in GPT imagegen';status='Hash registered only; visual and Windows checks still required'}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'Evidence/gpt-image-verdict.json') -Encoding utf8NoBOM
Write-Output 'Image hash registered. Preserve its prompt and inspect the actual Windows rendering.'
