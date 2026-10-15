$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
$env:PATH=(Join-Path $studio 'Tools\git-lfs-3.8.0\git-lfs-3.8.0')+';'+$env:PATH
$run=Join-Path $studio ('Runtime\lfs-test-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
$source=Join-Path $run 'source';$remote=Join-Path $run 'remote.git';$checkout=Join-Path $run 'checkout'
New-Item -ItemType Directory -Path $source -Force|Out-Null
function CheckedGit([string[]]$Arguments){ & git @Arguments; if($LASTEXITCODE -ne 0){throw "git failed: $Arguments"} }
CheckedGit @('init','-b','main',$source)
CheckedGit @('-C',$source,'config','user.name','AIStudio Validation')
CheckedGit @('-C',$source,'config','user.email','aistudio-validation@localhost')
CheckedGit @('-C',$source,'lfs','install','--local')
Copy-Item -LiteralPath (Join-Path $studio 'AssetsSource\Blender\calibration.glb') -Destination (Join-Path $source 'calibration.glb')
Set-Content -LiteralPath (Join-Path $source '.gitattributes') -Value '*.glb filter=lfs diff=lfs merge=lfs -text' -Encoding ascii
CheckedGit @('-C',$source,'add','.gitattributes','calibration.glb')
CheckedGit @('-C',$source,'commit','-m','Verify local Git LFS transfer')
$pointer=(& git -C $source show HEAD:calibration.glb) -join "`n"
if(!$pointer.StartsWith('version https://git-lfs.github.com/spec/v1')){throw 'Git stored binary instead of LFS pointer'}
CheckedGit @('init','--bare',$remote)
CheckedGit @('-C',$source,'remote','add','origin',$remote)
CheckedGit @('-C',$source,'push','-u','origin','main')
CheckedGit @('-C',$remote,'symbolic-ref','HEAD','refs/heads/main')
CheckedGit @('clone',$remote,$checkout)
$expected=(Get-FileHash -LiteralPath (Join-Path $source 'calibration.glb')).Hash
$actual=(Get-FileHash -LiteralPath (Join-Path $checkout 'calibration.glb')).Hash
if($expected -ne $actual){throw 'LFS checkout asset checksum differs'}
CheckedGit @('-C',$checkout,'lfs','fsck')
[pscustomobject]@{passed=$true;version=(& git lfs version);sha256=$actual;pointerStored=$true;pushAndFreshCloneVerified=$true;remoteType='Local bare repository; no cloud publication';evidence=$run}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $studio 'Evidence\git-lfs-verdict.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $studio 'Evidence\git-lfs-verdict.json') -Raw
