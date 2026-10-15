$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
$exe=Join-Path $studio 'Builds\Windows\AIStudioValidation.exe'
if(!(Test-Path -LiteralPath $exe)){throw 'Build AIStudioValidation first'}
$evidence=Join-Path $studio ('Evidence\windows-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $evidence|Out-Null
$argsList=@('-batchmode','-screen-fullscreen','0','-screen-width','1280','-screen-height','720','--studio-qa','--evidence-root',('"'+$evidence+'"'),'-logFile',('"'+(Join-Path $evidence 'player.log')+'"'))
$process=Start-Process -FilePath $exe -ArgumentList $argsList -WorkingDirectory (Split-Path -Parent $exe) -WindowStyle Hidden -PassThru
if(!$process.WaitForExit(120000)){Stop-Process -Id $process.Id;throw "Owned QA timed out; evidence retained at $evidence"}
$process.Refresh();$exitCode=$process.ExitCode
if($exitCode -ne 0){throw "Windows QA exit $exitCode; evidence $evidence"}
$file=Join-Path $evidence 'runtime-verdict.json';if(!(Test-Path -LiteralPath $file)){throw 'No runtime verdict'}
$report=Get-Content -LiteralPath $file -Raw|ConvertFrom-Json
if(!$report.passed){throw "Runtime gates failed: $file"}
& (Join-Path $PSScriptRoot 'Record-BuildHashes.ps1')
[pscustomobject]@{exitCode=$exitCode;verdict=$file;executableSha256=(Get-FileHash -LiteralPath $exe).Hash;completedUtc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $studio 'Evidence\latest-windows-run.json') -Encoding utf8
$report|ConvertTo-Json -Depth 5
