$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
$project=Join-Path $studio 'Project'
$statusRaw=& unity status --project-path $project --json
try{$status=$statusRaw|ConvertFrom-Json;if($status.success -and $status.data.count -gt 0){Write-Output 'Studio Unity Pipeline already running';return}}catch{}
$editor=(& (Join-Path $PSScriptRoot 'Get-Workstation.ps1')).unity_editor
if(!(Test-Path -LiteralPath $editor -PathType Leaf)){throw 'Configured Unity Editor was not found'}
$stateFile=Join-Path $studio 'Runtime\unity-process.json'
if(Test-Path -LiteralPath $stateFile){
 $owned=Get-Content -Raw -LiteralPath $stateFile|ConvertFrom-Json
 if(Get-Process -Id $owned.pid -ErrorAction SilentlyContinue){Write-Output "Recorded Studio Editor PID $($owned.pid) is still running; wait for Pipeline readiness before retrying.";return}
}
New-Item -ItemType Directory -Path (Join-Path $studio 'Runtime') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $studio 'Evidence') -Force | Out-Null
$arguments=@('-batchmode','-projectPath',('"'+$project+'"'),'-logFile',('"'+(Join-Path $studio 'Evidence\unity-editor.log')+'"'))
$proc=Start-Process -FilePath $editor -ArgumentList $arguments -WindowStyle Hidden -PassThru
[pscustomobject]@{pid=$proc.Id;project=$project;startedUtc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $studio 'Runtime\unity-process.json') -Encoding utf8
Write-Output "Started owned Unity Editor PID $($proc.Id)"
