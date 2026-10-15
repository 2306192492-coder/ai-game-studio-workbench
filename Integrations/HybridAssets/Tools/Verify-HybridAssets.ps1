$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $root 'machine.json') -Raw|ConvertFrom-Json
$checks=@()
foreach($case in @(@{asset='shell-lamp';scope='local';ai=$false;expected=0},@{asset='fab-harbor';scope='local';ai=$false;expected=0},@{asset='shell-lamp';scope='global';ai=$false;expected=2},@{asset='fab-harbor';scope='local';ai=$true;expected=2},@{asset='unregistered';scope='local';ai=$false;expected=2})){
 $argsList=@((Join-Path $PSScriptRoot 'asset_gate.py'),'--asset',$case.asset,'--scope',$case.scope)
 if($case.ai){$argsList+='--ai-input'}
 $raw=(& $config.python @argsList|Out-String);$exit=$LASTEXITCODE
 if($exit -ne $case.expected){throw "Unexpected gate verdict: $raw"}
 $checks+=@{asset=$case.asset;scope=$case.scope;aiInput=$case.ai;exit=$exit;passed=$true;verdict=($raw|ConvertFrom-Json)}
}
$run=Get-Content -LiteralPath (Join-Path $root 'Evidence\latest-windows-run.json') -Raw|ConvertFrom-Json
$runtime=Get-Content -LiteralPath $run.report -Raw|ConvertFrom-Json
if(!$runtime.passed -or $runtime.errors -ne 0){throw 'Actual Windows runtime did not pass'}
if((Get-FileHash -LiteralPath (Join-Path $root 'Builds\Windows\HybridAssetLab.exe')).Hash.ToLower() -ne $run.executable_sha256){throw 'Player differs from verified build'}
$guard=Get-Content -LiteralPath (Join-Path $root 'Evidence\unity-release-guard.json') -Raw|ConvertFrom-Json
if(!$guard.blocked){throw 'Unity shell release guard did not reject uncleared scope'}
$artifact=Join-Path $root 'Generated\shell-full-refined-v1\ShellLamp.fbx'
$import=Join-Path $config.unity_project 'Assets\HybridAssets\Models\ShellLamp.fbx'
if((Get-FileHash $artifact).Hash -ne (Get-FileHash $import).Hash){throw 'Unity model differs from verified Blender export'}
[ordered]@{passed=$true;date=[DateTime]::UtcNow.ToString('o');scope='Private local prototype; no blanket public/global approval';licenseChecks=$checks;windowsReport=$run.report;unityReleaseGuardBlocked=$guard.blocked;gptPrimary=$true;comfyStarted=$false;model='Hunyuan3D-2 full'}|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $root 'Evidence\integration-verdict.json') -Encoding utf8NoBOM
Write-Output 'Hybrid integration gates and actual Windows evidence verified.'
