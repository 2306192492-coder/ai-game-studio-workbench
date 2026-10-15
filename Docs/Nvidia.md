# NVIDIA App：两套引擎共用的可选诊断

NVIDIA App MCP 在 Codex 主机中配置一次，Unity 和 Unreal 工作台复用同一连接。工作台只增加检查入口、报告整理和操作规则，不内嵌另一个 MCP 客户端，不改用户全局配置，不启动 NVIDIA 服务。缺少 NVIDIA 环境或浮层未就绪时，不影响正常开发、构建、测试。

## 日常使用

在 Codex 中直接说“检查 Unity 的 NVIDIA 环境”或“检查虚幻 5 的 NVIDIA 环境”。Codex 先发现当前会话的原生工具，再按下面的只读流程查询并保存本机报告。普通启动、构建和测试不自动运行这项检查。

| 需求 | 使用方式与边界 |
|---|---|
| 查询驱动 | 原生 `nvapp_client_get_driver_status`；安装版本不等于渲染测试通过 |
| 查询可优化游戏 | 原生 `nvapp_client_get_applications`；自研游戏、Unity/UE 编辑器不默认支持 OPS |
| 查询浮层、运行游戏 | 原生 `nvapp_overlay_get_status` / `nvapp_overlay_get_current_game_info`；浮层准备状态和 MCP 连通状态分开判断 |
| 显示或隐藏统计 | 按需要调用 `nvapp_overlay_configure_stats`；只控制可见性，不返回帧率、显存、GPU 温度等测量序列 |
| 截图、录制、即时回放、Highlights | 用户明确要求时调用原生 capture 工具；媒体保存到 NVIDIA 浮层图库，不能指定格式、分辨率或输出目录 |
| 游戏画质预设 | 先读取准确的游戏标识、`opsSupported`、电源档位和 `availablePresets`；存在 `unavailableReason` 时连 `Revert` 也不能调用 |

本次轻量整合没有增加驱动安装、回退或桌面捕获入口。性能定位仍使用 Unity Profiler、UE Insights 等引擎工具；NVIDIA 统计浮层用于辅助观察。NullRHI 检查不能借用浮层或驱动查询作为 GPU 画面验证。

## 共用检查入口

```powershell
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unity -Action NvidiaCheck
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action NvidiaCheck
```

这两个命令调用同一个 Python 标准库模块，先于引擎路径分派，因此不需要安装引擎或填写引擎本机配置。**单独运行命令不会调用当前 Codex 会话的 MCP**：仅检测官方桥接程序和发现文件是否存在，并生成 `mcp.status=not_queried` 的报告。文件存在只证明本地文件存在，不证明服务正在运行、签名有效、当前会话已注册或浮层已就绪。发现文件只检查存在性，不读取其中的认证数据。

`-DryRun` 不读快照、不探测安装、不写文件；直接运行 Python 也可以：

```powershell
python Tools/nvidia_diagnostics.py --engine Unity --dry-run
```

## Codex 原生查询和报告

1. 发现当前会话的 NVIDIA 工具及实时参数结构。当前会话没有工具时报告不可用；检查已有主机注册配置及客户端重载情况，不暗中另开桥接或提升访问权限。
2. 只读查询上表中的四项。对本次检查，可独立调用这四项；某项失败时保留其他返回值，不猜测缺失字段。未发现的工具可省略。
3. 将本次真实返回值保存在忽略的 `Evidence/Nvidia/native-input-<unique-id>.json`。顶层格式如下，`results` 的键是未加宿主命名空间的准确工具名，值为工具原始返回对象（包含 `structuredContent` 或 `isError`）。不要把函数调用包装器、工具描述或示例数据当成查询结果。

```json
{
  "schema_version": 1,
  "source": "codex-native-tools",
  "collected_at": "2026-10-16T04:00:00+00:00",
  "results": {}
}
```

上例仅展示封套结构，空结果不代表连接成功。时间需使用真实采集时间；仅接受十五分钟内、带时区的快照，允许三十秒时钟偏差。不要改旧快照的时间充当新查询。工具失败的 `isError`、结构化 `code` 和 `retryable` 应保留；异常传输可记录 `isError=true`、`structuredContent.code=transport_error`。只有文字的返回值不会被当成成功的结构化数据。

4. 通过同一入口整理快照，按当前引擎标注报告：

```powershell
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unity -Action NvidiaCheck -NvidiaSnapshot Evidence/Nvidia/native-input-<unique-id>.json
pwsh -File Tools/Invoke-Workbench.ps1 -Engine Unreal -Action NvidiaCheck -NvidiaSnapshot Evidence/Nvidia/native-input-<unique-id>.json
```

脚本生成独立的 `Evidence/Nvidia/<unique-id>/result.json`，只保留已知、类型有效的诊断字段，不复制原始工具文字、认证头、元数据或进程 ID。快照来自调用者提供的文件，脚本不验证文件来源或真实性；报告的 `source=supplied_native_mcp_snapshot` 不能当作签名证据。

| 报告状态 | 含义 |
|---|---|
| `not_queried` | 未提供本次原生查询快照；不宣称已连接 |
| `ready` | 本次快照包含四项有效结构化返回；逐项查看实际状态 |
| `partial` | 部分返回有效；浮层失败不抹掉成功的驱动查询 |
| `unavailable` | 快照没有有效成功项；原因保存在各项状态中 |

`ready` 也可以是“没有正在运行的游戏”。字段遗漏保持未知，`running=false` 时不保留游戏名称。可选模块不可用返回退出码 0；显式指定的快照缺失、过期或结构损坏返回 2，让操作者修正输入。模块从未接入 Build/Test/Verify 的前置条件。

## 设置操作规则

常规查询按任务需要直接执行。需要显示/隐藏统计时使用明确的目标布尔值；只有真正的“切换”请求才读一次现状并取反。字段缺失不能当作 false。设置工具返回什么就报告什么，不额外查询浮层来证明设置成功。

截图、录制、即时回放与 Highlights 需要用户明确要求；一般“检查”“测试好”不构成开启捕获的请求。启用即时回放或 Highlights 后说明后台捕获会持续运行。不要为解决失败隐式开启桌面捕获、改变分辨率、提高 MCP 访问权限或启动别的软件。失败保留工具错误代码，例如 `overlay_not_available`。

游戏启动必须先从当前成功的应用列表取得准确 `game` 标识；不能传路径或猜名字。优化必须符合前述 OPS 条件；笔记本电池档还需本机支持。不要批量修改无关游戏。截图、录像和游戏列表保留在本机，不自动上传。

## 新机器的可选安装

已有原生工具时无需重复注册。新 Windows 主机需要支持 MCP 的 NVIDIA App、对应的服务和所需访问级别；浮层工具另外需要 In-Game Overlay 就绪。

确认官方安装目录与签名后，可由操作者在 Codex 中注册官方 stdio 桥接。以下是手动设置示例，工作台不会自动运行：

```powershell
$nvidiaBridge = Join-Path $env:ProgramFiles 'NVIDIA Corporation/NVIDIA App/McpServer/NvAppMcpServer.exe'
Get-AuthenticodeSignature -LiteralPath $nvidiaBridge
codex mcp add nvidia-app -- $nvidiaBridge
```

按客户端需要重载/重启后，以当前会话原生工具实际查询验证。不要把用户全局 Codex 配置、NVIDIA `server.json`、认证数据或桥接二进制加入公开仓库。

官方来源：[OpenAI Docs：MCP 主机配置复用](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)、[NVIDIA App 官方技能及调用边界](https://github.com/NVIDIA/skills/blob/main/skills/nvidia-app/SKILL.md)、[通用工具约束](https://github.com/NVIDIA/skills/blob/main/skills/nvidia-app/references/general-tools.md)、[统计与浮层边界](https://github.com/NVIDIA/skills/blob/main/skills/nvidia-app/references/overlay-state.md)。接口可能随版本变化，以本次发现的工具结构为准。
