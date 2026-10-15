param([switch]$WithComfyUI)
$ErrorActionPreference='Stop'
$studio=Split-Path -Parent $PSScriptRoot
if($WithComfyUI){& (Join-Path $PSScriptRoot 'Start-ComfyUI.ps1')}
& (Join-Path $PSScriptRoot 'Start-UnityPipeline.ps1')
Write-Output "Studio root: $studio"
Write-Output 'Primary images: built-in GPT image generation in Codex. ComfyUI is optional (-WithComfyUI).'
Write-Output 'Unity runs in background. Verify the official Unity plugin/MCP separately on this workstation.'
Write-Output 'Use Tools\Verify-AIStudio.ps1 to check readiness and run the Windows smoke test.'
