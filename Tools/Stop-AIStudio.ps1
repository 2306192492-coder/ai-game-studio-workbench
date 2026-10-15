$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
foreach($component in @('comfy','unity')){
 $stateFile=Join-Path $studio ('Runtime\'+$component+'-process.json')
 if(!(Test-Path -LiteralPath $stateFile)){continue}
 $state=Get-Content -LiteralPath $stateFile -Raw|ConvertFrom-Json
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)"
 if(!$proc){continue}
 if($proc.CommandLine -notlike ('*'+$studio+'*')){throw "PID $($state.pid) no longer belongs to this studio; not stopped"}
 if($component -eq 'unity'){
  & unity command eval 'UnityEditor.AssetDatabase.SaveAssets(); UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes(); UnityEditor.EditorApplication.delayCall += () => UnityEditor.EditorApplication.Exit(0); return "owned_studio_shutdown_requested";' --project-path (Join-Path $studio 'Project') --caller plugin --skill unity-cli --json
  if($LASTEXITCODE -ne 0){throw 'Unity graceful shutdown failed; process left running'}
 } else {Stop-Process -Id $state.pid}
 Write-Output "Stopped/requested shutdown of owned $component process $($state.pid)"
}
