$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
$project=Join-Path $studio 'Project'
function Invoke-Studio([string[]]$Arguments){
 $raw=(& unity command @Arguments --project-path $project --caller plugin --skill unity-cli --json|Out-String)
 if($LASTEXITCODE -ne 0){throw $raw}
 $response=$raw|ConvertFrom-Json
 if(!$response.success){throw $raw}
 return $response.data.result
}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $studio 'Evidence\gpt-image-verdict.json')|ConvertFrom-Json
if((Get-FileHash -LiteralPath (Join-Path $studio $manifest.asset) -Algorithm SHA256).Hash -ne $manifest.sha256){throw 'GPT primary image differs from verified source'}
$null=Invoke-Studio @('eval','UnityEditor.AssetDatabase.Refresh(); return "refresh_requested";')
$ready=$false
for($i=0;$i-lt60;$i++){
 Start-Sleep -Seconds 2
 try{$state=Invoke-Studio @('console_status')}catch{
  if($_.Exception.Message -match 'Connection reset|ECONNRESET|ECONNREFUSED|not ready|No running'){continue}
  throw
 }
 if($state.groundTruth.compilationFailed){throw 'Unity script compilation failed'}
 if(!$state.groundTruth.compiling){$ready=$true;break}
}
if(!$ready){throw 'Compilation did not become ready'}
$setup=Invoke-Studio @('eval','return AIStudio.StudioSetup.Create();')
Write-Output $setup
$build=Invoke-Studio @('build','--target','StandaloneWindows64','--outputPath',(Join-Path $studio 'Builds\Windows\AIStudioValidation.exe'),'--confirm','true')
Write-Output "Build queued: $($build.buildId)"
$deadline=(Get-Date).AddMinutes(15)
do{
 Start-Sleep -Seconds 5
 $status=Invoke-Studio @('build_status')
 if((Get-Date)-gt$deadline){throw 'Build status wait timed out; inspect the owned Editor before restarting'}
}while($status.status-ne'completed')
$status|ConvertTo-Json -Depth 30|Set-Content -LiteralPath (Join-Path $studio 'Evidence\final-build-status.json') -Encoding utf8
if($status.result-ne'Succeeded' -or $status.totalErrors-ne0){throw "Windows build failed: $($status.result); errors $($status.totalErrors)"}
Write-Output 'Build completed. Read Evidence\final-build-status.json and run Run-WindowsQA.ps1.'
