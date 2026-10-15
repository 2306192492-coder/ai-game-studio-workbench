$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
foreach($relative in @('Config\workstation','Integrations\HybridAssets\machine')){
 $target=Join-Path $root ($relative+'.json')
 if($relative -eq 'Config\workstation'){$target=Join-Path $root 'Config\workstation.local.json'}
 $example=Join-Path $root ($relative+'.example.json')
 if(Test-Path -LiteralPath $target){Write-Output "Preserved existing config: $target";continue}
 $config=Get-Content -LiteralPath $example -Raw|ConvertFrom-Json
 if($relative -like '*machine'){$config.unity_project=Join-Path $root 'Project'}
 $config|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $target -Encoding utf8NoBOM
 Write-Output "Created config; edit before use: $target"
}
foreach($relative in @('Evidence','Runtime','AssetsSource','Project\Assets\Studio\Textures','Project\Assets\Studio\Models')){
 New-Item -ItemType Directory -Path (Join-Path $root $relative) -Force|Out-Null
}
