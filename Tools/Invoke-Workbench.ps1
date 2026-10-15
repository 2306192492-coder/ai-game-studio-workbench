param(
 [ValidateSet('Unity','Unreal')][string]$Engine='Unity',
 [ValidateSet('Status','Start','Prepare','Probe','Import','Build','Test','Verify','Run')][string]$Action='Status',
 [string]$AssetId,[string]$Source,[string]$Destination,[string]$Filter,[string]$BuildReport,[switch]$DryRun
)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
if($Engine -eq 'Unreal'){
 $arguments=@((Join-Path $PSScriptRoot 'unreal_adapter.py'),$Action.ToLowerInvariant())
 foreach($pair in @(@('--asset-id',$AssetId),@('--source',$Source),@('--destination',$Destination),@('--filter',$Filter),@('--build-report',$BuildReport))){
  if($pair[1]){$arguments+=@($pair[0],$pair[1])}
 }
 if($DryRun){$arguments+='--dry-run'}
 & python @arguments
 if($LASTEXITCODE -ne 0){throw "Unreal adapter failed with exit code $LASTEXITCODE"}
 return
}
$unityWorkspace=$root
$workstationFile=Join-Path $root 'Config\workstation.local.json'
if(Test-Path -LiteralPath $workstationFile){
 $workstation=Get-Content -LiteralPath $workstationFile -Raw|ConvertFrom-Json
 if($workstation.unity_workspace){
  $unityWorkspace=if([IO.Path]::IsPathRooted($workstation.unity_workspace)){[IO.Path]::GetFullPath($workstation.unity_workspace)}else{[IO.Path]::GetFullPath((Join-Path $root $workstation.unity_workspace))}
 }
}
if($Action -eq 'Status'){
 if($DryRun){@{engine='Unity';command=@('unity','status','--project-path',(Join-Path $unityWorkspace 'Project'),'--json')}|ConvertTo-Json;return}
 & unity status --project-path (Join-Path $unityWorkspace 'Project') --json
 if($LASTEXITCODE -ne 0){throw 'Unity status failed'}
 return
}
$scripts=@{Start='Start-AIStudio.ps1';Build='Build-Studio.ps1';Verify='Verify-AIStudio.ps1';Run='Run-WindowsQA.ps1'}
if(!$scripts.ContainsKey($Action)){throw "Unity action $Action has no shared mapping; use the existing Unity project tools"}
$script=Join-Path (Join-Path $unityWorkspace 'Tools') $scripts[$Action]
if($DryRun){@{engine='Unity';script=$script}|ConvertTo-Json;return}
if(!(Test-Path -LiteralPath $script -PathType Leaf)){throw 'Selected Unity workspace does not contain the required AIStudio tool'}
& $script
