$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
$build=Join-Path $studio 'Builds\Windows'
$files=@(Get-ChildItem -LiteralPath $build -Recurse -File|Sort-Object FullName|ForEach-Object{
 [pscustomobject]@{file=$_.FullName.Substring($build.Length+1).Replace('\','/');bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
})
if(!$files.Count){throw 'Build folder contains no files'}
$path=Join-Path $studio 'Evidence\windows-build-files.json'
[pscustomobject]@{utc=[DateTime]::UtcNow.ToString('o');files=$files}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $path -Encoding utf8
Write-Output "Recorded $($files.Count) build files, including player data and managed code: $path"
