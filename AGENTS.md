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

- Read Integrations/HybridAssets/README.md and policy.json for the asset workflow. Search Registry/fab-catalog.json before making routine assets; mature high-quality compatible assets take priority where they fit the game's art direction, era, style and license.
- Original forms use GPT built-in imagegen first, Hunyuan3D-2 full as the preferred local shape candidate after the verified shell comparison, and Blender for durable geometry, UVs, materials and runtime exports. Mini remains optional; compare actual outputs and choose other modeling methods when better. No default ComfyUI API startup; Hunyuan uses installed core Python modules without starting the server.
- Catalogued/owned is not downloaded, imported or production approved. Verify each acquisition's license, formats, scale, materials, pivots and gameplay needs. UE format alone does not imply a UE-only license; explicitly UE-only assets cannot enter Unity. NoAI-marked vendor assets are used directly through ordinary authoring/import, not passed as generative AI inputs in this workflow.
- Retain original packages, generated input pixels, raw outputs and failed candidates. Record hashes, dependencies, source URLs and license holds in Registry/asset-manifest.json. Blender refinement does not clear Tencent output territory restrictions.
- Use Tools/asset_gate.py before promoting registered assets. Hunyuan-derived prototypes and this asset-only showroom are private local validation, not global/public release approval. HybridReleaseGuard rejects builds containing the currently registered shell outside the explicit local validation build method; use a project-specific manifest gate for future assets and release scope.
- Tools/Build-HybridLab.ps1 builds and runs only the additive HybridAssetLab validation scene; old game scenes and EditorBuildSettings remain unchanged. Inspect the actual Windows screenshots as well as the JSON checks.

## Shared Unreal adapter

- Read Docs/Unreal.md. Keep Unity in Project and Unreal in UnrealProject; never convert existing games as a side effect of choosing an engine.
- Invoke-Workbench.ps1 selects the engine. Config/unreal.local.json is local-only. The Unreal adapter uses a new process with an explicit project path and no remote execution service.
- Prepare/Probe use NullRHI and prove only editor map/asset data. A saved map, imported asset, successful UAT process or Automation report does not certify GPU rendering or human gameplay.
- Shared asset imports require the selected registered source file and valid hash. Import and promotion are separate stages; runtime_verified_engines must include the target engine for promotion.
- Keep Unreal Content, Saved, Intermediate, Binaries, DDC and package outputs local. Publish source/configuration and sanitized evidence summaries only.

## Optional shared NVIDIA diagnostics

- Read Docs/Nvidia.md before using NVIDIA App. Reuse the current Codex host's native MCP tools for both engines; inspect the live catalog/schema. No embedded server/client, automatic registration, access-tier change or default background polling.
- For an NVIDIA check, query the available native driver, applications, Overlay status and current-game tools read-only. Save fresh actual tool envelopes and a timezone-aware collection timestamp under ignored Evidence/Nvidia; pass that snapshot to Invoke-Workbench.ps1 -Engine Unity|Unreal -Action NvidiaCheck -NvidiaSnapshot <file>. Do not relabel old results as fresh.
- NvidiaCheck without a snapshot only inspects file presence; it must not be reported as a successful MCP connection. MCP readiness, Overlay readiness, GPU rendering and gameplay acceptance are separate. Missing fields stay unknown; stats visibility does not provide performance measurements.
- NvidiaCheck is optional and never a Build/Test/Verify prerequisite. No NVIDIA environment or Overlay failure must not block engine workflows. Raw snapshots, game lists, media, discovery files and host MCP configuration stay local; publish only deliberately sanitized summaries.
- Use stats visibility controls when the task needs them. Capture, recording, replay and Highlights require an explicit capture request; general test/diagnostic requests do not authorize them. No implicit Desktop Capture, resolution change or filter mutation. Preserve returned error codes; do not post-read Overlay just to verify a mutation message.
- Launch only exact identifiers from a fresh successful app list. Apply optimization only with opsSupported, a supported power profile/preset, and no unavailableReason (including Revert). Do not assume self-built Unity/Unreal executables support NVIDIA optimization. No driver install/rollback tools are provided by this integration.
