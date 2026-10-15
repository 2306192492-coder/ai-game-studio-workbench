param([switch]$SkipWindowsQA)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $root 'machine.json') -Raw|ConvertFrom-Json
function Invoke-HybridCode([string]$Code){
 $raw=(& $config.unity_cli command eval $Code --project-path $config.unity_project --caller plugin --skill unity-cli --json|Out-String)
 if($LASTEXITCODE -ne 0){throw $raw}
 $reply=$raw|ConvertFrom-Json
 if(!$reply.success -or !$reply.data.result.success){throw $raw}
 return $reply.data.result.result
}
# This script never starts ComfyUI or another Editor, and never changes old build scenes.
$null=Invoke-HybridCode 'UnityEditor.AssetDatabase.Refresh(); return "refreshed";'
$ready=$false
for($i=0;$i -lt 40;$i++){
 Start-Sleep -Seconds 2
 $raw=(& $config.unity_cli command console_status --project-path $config.unity_project --caller plugin --skill unity-cli --json|Out-String)
 if($LASTEXITCODE -ne 0){continue}
 $state=($raw|ConvertFrom-Json).data.result.groundTruth
 if($state.compilationFailed){throw 'Unity compilation failed; inspect console'}
 if(!$state.compiling){$ready=$true;break}
}
if(!$ready){throw 'Editor did not become ready; owned state retained'}
Write-Output (Invoke-HybridCode 'return AIStudio.Hybrid.HybridSetup.Create();')
$before=[DateTime]::UtcNow
Write-Output (Invoke-HybridCode 'UnityEditor.EditorApplication.delayCall += ()=>AIStudio.Hybrid.HybridSetup.Build(); return "private_local_build_queued";')
$file=Join-Path $root 'Evidence\build-report.json'
$complete=$false
for($i=0;$i -lt 100;$i++){
 Start-Sleep -Seconds 3
 if((Test-Path -LiteralPath $file) -and (Get-Item -LiteralPath $file).LastWriteTimeUtc -ge $before){$complete=$true;break}
}
if(!$complete){throw 'Build wait timed out. Inspect Editor/report before any retry; do not terminate existing editors.'}
$build=Get-Content -LiteralPath $file -Raw|ConvertFrom-Json
if($build.result -ne 'Succeeded' -or $build.errors -ne 0){throw 'Private local build failed'}
if($SkipWindowsQA){$build|ConvertTo-Json;return}
$evidence=Join-Path $root ('Evidence\windows-'+(Get-Date -Format 'yyyyMMdd-HHmmss'));New-Item -ItemType Directory -Path $evidence|Out-Null
$exe=Join-Path $root 'Builds\Windows\HybridAssetLab.exe'
$argsList=@('-batchmode','-force-d3d11','-screen-fullscreen','0','-screen-width','1280','-screen-height','720','--hybrid-qa','--evidence-root',('"'+$evidence+'"'),'-logFile',('"'+(Join-Path $evidence 'player.log')+'"'))
$proc=Start-Process -FilePath $exe -ArgumentList $argsList -WorkingDirectory (Split-Path -Parent $exe) -WindowStyle Hidden -PassThru
if(!$proc.WaitForExit(60000)){throw "Owned QA timed out; inspect PID $($proc.Id); retained evidence $evidence"}
$proc.Refresh();if($proc.ExitCode -ne 0){throw "Windows QA failed: $($proc.ExitCode); $evidence"}
$result=Get-Content -LiteralPath (Join-Path $evidence 'runtime-verdict.json') -Raw|ConvertFrom-Json
if(!$result.passed){throw "Runtime gates failed: $evidence"}
[ordered]@{completedUtc=[DateTime]::UtcNow.ToString('o');passed=$true;report=(Join-Path $evidence 'runtime-verdict.json');evidence=$evidence;executable_sha256=(Get-FileHash -LiteralPath $exe).Hash.ToLower();scope='Private local Windows static asset validation only'}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'Evidence\latest-windows-run.json') -Encoding utf8NoBOM
$result|ConvertTo-Json
