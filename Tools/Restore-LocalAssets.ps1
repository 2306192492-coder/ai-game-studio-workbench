param([string]$MixamoSource)
$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
if(!$MixamoSource){$MixamoSource=Join-Path $studio 'AssetsSource\Mixamo\XBot-Walking.fbx'}
$expected=(Get-Content -Raw -LiteralPath (Join-Path $studio 'Config\asset-sources.json')|ConvertFrom-Json).mixamo.sha256
if(!(Test-Path -LiteralPath $MixamoSource)){throw 'Supply the locally retained, licensed XBot-Walking.fbx using -MixamoSource. Raw Mixamo files are not distributed in Git.'}
if((Get-FileHash -LiteralPath $MixamoSource -Algorithm SHA256).Hash -ne $expected){throw 'Mixamo source hash differs from the verified asset'}
$destination=Join-Path $studio 'Project\Assets\ThirdParty\Mixamo\XBot-Walking.fbx'
if(Test-Path -LiteralPath $destination){
 if((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $expected){throw 'Existing destination differs; preserve it and resolve manually'}
 Write-Output 'Verified local Mixamo asset already present';return
}
New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force|Out-Null
Copy-Item -LiteralPath $MixamoSource -Destination $destination
Write-Output 'Local Mixamo restored. Run Build-Studio.ps1 to recreate scene references and build.'
