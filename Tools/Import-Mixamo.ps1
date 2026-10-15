param([Parameter(Mandatory=$true)][string]$FbxPath,[string]$ClipName='MixamoAction',[ValidateSet(24,30,60)][int]$Fps=30)
$ErrorActionPreference='Stop'
if(!(Test-Path -LiteralPath $FbxPath -PathType Leaf)){throw 'FBX source not found'}
if([IO.Path]::GetExtension($FbxPath)-ne'.fbx'){throw 'Expected an FBX file'}
if($ClipName-notmatch'^[A-Za-z0-9_-]+$'){throw 'Use letters, numbers, underscores and hyphens for ClipName'}
$studio=Split-Path -Parent $PSScriptRoot
$destination=Join-Path $studio ('AssetsSource\Mixamo\'+$ClipName+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $destination|Out-Null
$sourceCopy=Join-Path $destination ($ClipName+'.fbx');Copy-Item -LiteralPath $FbxPath -Destination $sourceCopy
$workstation=& (Join-Path $PSScriptRoot 'Get-Workstation.ps1')
$script=$workstation.mixamo_import_script
foreach($required in @($workstation.blender,$script)){if(!(Test-Path -LiteralPath $required)){throw "Missing configured dependency: $required"}}
& $workstation.blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python $script -- --input $sourceCopy --output-dir (Join-Path $destination 'Blender') --clip-name $ClipName --fps $Fps
if($LASTEXITCODE-ne0){throw 'Blender Mixamo import failed'}
Write-Output "Imported copy: $destination"
Write-Output 'This preserves the source skeleton. Retargeting to another character needs a separate rig/deformation validation.'
