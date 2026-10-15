# Unity / Unreal 共用工作台

同一套设计、GPT 图片、Blender、混元候选、素材来源登记和 Git 流程，分别接到两个引擎。Unity 工程在 `Project`，UE 工程在 `UnrealProject`。选择引擎不会迁移或转换现有游戏工程。

## 配置与统一入口

```powershell
pwsh -File Tools/Initialize-Workstation.ps1
# 填写 Config/unreal.local.json 中的 engine_root；project 默认指向独立验证工程
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action Status
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action Prepare
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action Probe
```

UE5 独立工程启用 PythonScriptPlugin、EditorScriptingUtilities。使用 UE 自带 Python 执行编辑器脚本；外层调度仅需系统 Python 标准库。Python 用于编辑器资产生产，不作为打包游戏的运行时玩法脚本。

如果已有完整的本地 AIStudio Unity 工作台，可在 `Config/workstation.local.json` 设置 `unity_workspace` 指向它的根目录（相对本仓库或绝对路径）。统一入口将调用原工作台的 Tools 和 Project，复用其本地素材与验证环境；默认 `.` 使用仓库内工程。这样接入 UE5 时不必搬迁或复制现有 Unity 工程。

此 Windows 校准工程关闭 AndroidFileServer 服务功能和 Python 远程执行；保留引擎默认插件集合以使用预编译的蓝图项目运行程序，不额外触发 C++ 目标编译。配置显式清空 Android 服务令牌，公开检查拒绝非空 SecurityToken 等字段。

默认配置针对 UE 5.8，实际本机检测到 5.8.3。其他 UE5 版本需要更改 EngineAssociation、检查插件/API 后重跑验证。

| 动作 | Unity | Unreal |
|---|---|---|
| `Status` | CLI/Pipeline 状态 | 编辑器、UAT、版本和工程文件检查 |
| `Start` | 原后台 Unity 启动入口 | 显式打开 UE Editor |
| `Prepare` | 使用原 Build 流程准备场景 | 新建独立校准场景；同名已存在时只加载检查 |
| `Probe` / `Verify` | 原 `Verify` 入口运行 Windows QA | NullRHI 下读取已保存场景并检查对象 |
| `Import` | 保留原素材工具 | 经共用素材清单检查后导入 FBX/图片 |
| `Build` | 原 Unity Windows 构建入口 | UAT BuildCookRun，独立输出目录和文件哈希 |
| `Run` | 原 Windows QA | 校验指定包的哈希后，短暂启动并检查地图加载，使用 NullRHI |
| `Test` | 使用 Unity 工程内现有测试 | UE Automation，必须指定真实测试过滤条件 |

Unity 统一入口提供 `Status/Start/Build/Verify/Run`；其他 Unity 任务继续使用已有脚本。`-DryRun` 只输出调用计划，不启动引擎或写入证据，不能当作验证通过。

```powershell
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unity -Action Build -DryRun
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action Build -DryRun
```

## UE 校准工程

`Prepare` 创建 `/Game/AIStudio/Maps/WorkbenchValidation`：地面、立方体、方向光、相机和 PlayerStart。只引用引擎内置基础形体，没有携带商店或混元生成资产。同名地图存在时不会重建；若它不符合校准条件会停止，保留原内容。

创建后保存、重新加载并检查对象与变换。`Probe` 在新的编辑器进程中再次读取。两者均使用 `-NullRHI`；检查通过说明编辑器数据链路成功，不能证明 GPU 画面、游戏运行、碰撞手感或性能。

## 共用素材，分别验证

素材登记在 `Integrations/HybridAssets/Registry/asset-manifest.json`。每项包含 `id`、来源、许可证检查、文件 `path/sha256`、依赖和用途限制。路径相对 HybridAssets 目录。不要把受限资源提交公开仓库。

```powershell
python Integrations/HybridAssets/Tools/asset_gate.py --asset YOUR_ASSET --engine Unreal --stage import
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action Import -AssetId YOUR_ASSET -Source YOUR_REGISTERED_FILE
```

导入默认写到 `/Game/AIStudio/Imports`，只接受登记项对应的 FBX 或图片文件，并保留已存在同名资产。首次导入不要求已有实机验证；进入正式采用阶段时运行 `--stage promote`，要求 `quality_status: prototype_verified` 和相应的 `runtime_verified_engines`。

例如某素材在 Unity 中验证后写 `runtime_verified_engines: ["Unity"]`，不能据此批准 Unreal。UE-only 素材会被 Unity 通道拒绝；其他授权、哈希、依赖和公开范围检查仍共用。导入成功不自动更新为实机验证通过。

## 构建和测试

```powershell
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action Build
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action Run -BuildReport Evidence/Unreal/build-YOUR_ID/result.json
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action Test -Filter YOUR_REAL_TEST_NAME
```

本机已跑通纯蓝图校准工程的预编译 Windows 运行程序打包。新增 C++ 或改变默认运行插件集合后，UE 可能要求重新编译目标；本机尚缺 UBT 要求的 Windows SDK 10.0.19041.0，未验证 C++ 项目构建，也没有自动安装庞大工具链。准备相应 SDK/编译环境后可使用同一 UAT 入口。

独立包输出到 `Evidence/Unreal/build-<id>/package`。仅在 UAT 返回 0、归档存在 EXE 和 PAK 时标记构建结果通过，并记录文件 SHA-256。此结果不代表打包后的游戏已运行。

`Run` 要求明确指定构建报告，逐一复核包文件 SHA-256，再启动该项目的 Development 程序。使用 NullRHI、固定帧率基准和三秒模拟时长；必须正常退出并在日志中完成目标地图加载才通过。此检查不生成 GPU 画面，不证明物理输入、碰撞手感或视觉质量。Shipping 不支持这条有限时长检查。

Automation 使用新的报告目录；非空测试数量、失败数、未运行数和进行中数量共同决定结果，不能靠退出码或空报告通过。示例中的过滤条件需替换为工程里存在的测试。当前校准工程自身使用 Python 场景探针，没有虚构同名 Automation 测试。

运行记录保存在忽略的 `Evidence/Unreal`；每次使用唯一 ID 防止旧报告冒充新结果。超时只终止本次直接启动的进程；UAT 可能留有子任务，应检查本次日志与进程后再重试，不关闭其他用户应用。

## 后续游戏项目

本适配提供编辑器任务、素材导入、构建和测试入口。具体游戏仍需蓝图/C++、材质、动画重定向、输入、玩法测试和真实 Windows 试玩。默认验证地图不代表一款完整游戏；Unity 的 C# 玩法代码和 URP 材质不会自动变为 UE 蓝图或材质。

官方参考：[编辑器 Python](https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python)、[UAT 构建](https://dev.epicgames.com/documentation/en-us/unreal-engine/build-operations-cooking-packaging-deploying-and-running-projects-in-unreal-engine)、[Automation 测试](https://dev.epicgames.com/documentation/unreal-engine/run-automation-tests-in-unreal-engine?lang=en-US)。
