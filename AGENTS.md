# AIStudio operating rules

- Use Codex's built-in GPT image generation as the primary image creation/editing route. Read the available imagegen skill. Do not require an API key for the built-in route.
- ComfyUI is an optional local fallback. Do not start it by default, silently substitute it for GPT, or overwrite GPT assets with fallback outputs.
- Preserve existing projects, original resources, downloaded models, and source images. This is an independent validation workspace; do not modify sibling projects.
- Copy project-bound generated images into this workspace with distinct filenames. Retain prompt, provider, dimensions, SHA-256, and visual inspection notes. Import into Unity and validate the actual Windows build.
- Use the installed official Unity plugin and current Unity CLI. Specify this Project's absolute path for CLI calls. Check Application.dataPath before MCP mutations if more than one Editor is open.
- URP is the selected validation pipeline. Do not migrate existing games to HDRP. This project disables GPU Resident Drawer after a verified D3D11 render-request material issue.
- Start-AIStudio.cmd starts Unity only. Tools/Start-AIStudio.ps1 -WithComfyUI opts into the backup service. Tools/Verify-AIStudio.ps1 validates Unity/GPT and runs the Windows probe; -CheckComfyUI additionally checks the fallback API.
- Build with Tools/Build-Studio.ps1. Run Tools/Run-WindowsQA.ps1 and inspect its screenshots. Automated rendering/animation/physics evidence is not a manual playtest or commercial release acceptance.
- Keep accounts, credentials, config backups, models, caches, raw Mixamo assets and standalone builds out of Git. No cloud publication without user instruction.

## Hybrid mature/original assets

- Read Integrations/HybridAssets/README.txt and policy.json for the asset workflow. Search Registry/fab-catalog.json before making routine assets; mature high-quality compatible assets take priority where they fit the game's art direction, era, style and license.
- Original forms use GPT built-in imagegen first, Hunyuan3D-2 full as the preferred local shape candidate after the verified shell comparison, and Blender for durable geometry, UVs, materials and runtime exports. Mini remains optional; compare actual outputs and choose other modeling methods when better. No default ComfyUI API startup; Hunyuan uses installed core Python modules without starting the server.
- Catalogued/owned is not downloaded, imported or production approved. Verify each acquisition's license, formats, scale, materials, pivots and gameplay needs. UE format alone does not imply a UE-only license; explicitly UE-only assets cannot enter Unity. NoAI-marked vendor assets are used directly through ordinary authoring/import, not passed as generative AI inputs in this workflow.
- Retain original packages, generated input pixels, raw outputs and failed candidates. Record hashes, dependencies, source URLs and license holds in Registry/asset-manifest.json. Blender refinement does not clear Tencent output territory restrictions.
- Use Tools/asset_gate.py before promoting registered assets. Hunyuan-derived prototypes and this asset-only showroom are private local validation, not global/public release approval. HybridReleaseGuard rejects builds containing the currently registered shell outside the explicit local validation build method; use a project-specific manifest gate for future assets and release scope.
- Tools/Build-HybridLab.ps1 builds and runs only the additive HybridAssetLab validation scene; old game scenes and EditorBuildSettings remain unchanged. Inspect the actual Windows screenshots as well as the JSON checks.
