# 安装与使用

UE5 的独立工程、统一入口及配置见 [Unity / Unreal 共用工作台](Unreal.md)。以下原 Unity 验证流程继续保留，不因新增 UE5 而更换工程或渲染管线。

NVIDIA App MCP 为可选的两引擎共用模块，见 [共用诊断与试玩辅助](Nvidia.md)。已有 Codex 主机连接直接复用，不重复注册；`NvidiaCheck` 不需要引擎配置，缺少 NVIDIA 环境不阻塞工作流。

## 已跑通的版本组合

2026-10-14 原机记录：Unity 6000.6.3f1、URP 17.6.0、Unity CLI 1.0.0-beta.13、Pipeline 0.8.0-exp.1、官方 Unity Codex 插件 0.1.8-beta、Blender 5.2.2 LTS、Git LFS 3.8.0。依赖锁定在 `Project/Packages`。更换版本后重新验证；工具安装位置按自己的机器填写。

基础脚本使用 Windows PowerShell。Python 素材工具按需依赖 `mcp`、`Pillow`、`numpy`、`trimesh`、`torch` 等；混元通道还需要独立的兼容 Python/GPU 环境和本机 Comfy 核心模块。这里只保存调用脚本，不自动下载或启动模型。

## 配置本机路径

```powershell
git clone https://github.com/2306192492-coder/ai-game-studio-workbench.git
cd ai-game-studio-workbench
git lfs install
pwsh -File Tools/Initialize-Workstation.ps1
```

编辑忽略的 `Config/workstation.local.json`：Unity Editor、Blender、可选 ComfyUI 的 Python/目录/共享模型目录、Mixamo 导入辅助脚本。需要混元时再填写忽略的 `Integrations/HybridAssets/machine.json`；字段说明来自同目录 `machine.example.json`。

初始化不会覆盖现有配置，不启动软件，也不改用户全局配置。Unity CLI 需已在 PATH；多编辑器时每次指定本仓库 `Project` 的绝对路径。

## 准备验证素材

- Mixamo：自行取得有权使用的 X Bot + Walking FBX。原验证素材的参数和哈希在 `Config/asset-sources.json`。`Restore-LocalAssets.ps1 -MixamoSource <文件>` 对应原哈希；使用不同动作时，需要改自己的清单和验证条件。
- GPT：按 `Config/gpt-validation-prompt.txt` 生成并检查图片，放入 `Project/Assets/Studio/Textures/GPT-primary-landscape.png`，然后运行 `Tools/Register-GptImage.ps1 -Asset <图片路径>` 登记本次哈希。默认会保留已有同名素材。
- 校准模型：使用 Blender `--background --factory-startup --python Tools/make_probe_asset.py` 运行制作脚本，它会保存 `.blend`、GLB 和 Unity 所需的 `Calibration.fbx`。该命令用于新的空白 Blender 进程。
- Poly Haven：从 `Config/asset-sources.json` 记录的 CC0 页面取得纹理，导入相应 Unity 纹理目录。

本仓库不附带这些二进制文件。原工作台完整资源仍留在原机；新机器需要重新准备。混合素材展台也需自行登记和导入素材；空清单会拒绝尚未准备的案例。

原案例的 `StudioTests.cs` 和 `StudioProbe.cs` 对 GPT 图片固定检查 **1254×1254**。要复现原测试需使用此尺寸；新项目使用其他尺寸时，更新自己的断言和运行探针，再记录新结果，不能沿用旧通过记录。图片登记只验证文件哈希，不证明图片提供方或视觉质量。

## Unity 与 Windows 验证

```powershell
pwsh -File Tools/Start-AIStudio.ps1
pwsh -File Tools/Build-Studio.ps1
pwsh -File Tools/Run-WindowsQA.ps1
pwsh -File Tools/Verify-AIStudio.ps1 -SkipWindowsRun
```

运行前安装所需工具并等待 Unity 导入完成。构建仍调用原来的 Unity CLI/Pipeline 入口，图片哈希不符或素材缺失会停止；不要为通过检查伪造资源或历史证据。`Run-WindowsQA.ps1` 保存新的报告和画面，需要逐项检查。

可选 ComfyUI：`Start-AIStudio.ps1 -WithComfyUI`，使用本机配置，不默认启动。可选 MCP 探针：`python Tools/verify_unity_mcp.py`，需要安装 Python `mcp` 包。

## 无 Unity 的仓库检查

```powershell
python Tools/check_repository.py
python -m unittest discover -s Tests -v
```

这些检查验证公开导出边界、Python 语法和源码结构，不运行 Unity、模型、渲染或游戏。CI 同样只做这类轻量检查和 PowerShell 语法解析。
