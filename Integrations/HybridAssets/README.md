# 混合素材通道

先检索成熟素材；原创形体使用 GPT 参考图、混元候选和 Blender 整理。整体流程见根目录 `Docs/Workflow.md`。

本目录只公开工具代码、策略、配置样例和空登记表。原机 Fab 账号收藏、下载包、GPT 输入图片、混元模型输出和展台构建没有上传。

## 入口

| 工具 | 用途 | 需要自行准备 |
|---|---|---|
| `find_assets.py` | 搜索本地素材目录 | `Registry/fab-catalog.json` 的素材条目 |
| `import_fab_package.py` | 检查并暂存取得的素材包 | 自己有权使用的包及参数 |
| `New-HunyuanProp.ps1` | 调用混元 full 或 Mini 生成候选 | `machine.json`、兼容环境、权重、允许作为输入的图片 |
| `refine_shell*.py` | 原 shell 案例的 Blender 整理参考 | 原案例输入；用于新资产时需适配 |
| `record_manifest.py` | 原案例登记脚本参考 | 该案例的文件与元数据 |
| `asset_gate.py` | 检查依赖、哈希、用途和发布范围 | 已登记的资产及实际文件 |
| `Build-HybridLab.ps1` | 原 shell 展台的本地验证入口 | 全部案例资产与有效登记记录 |

`refine_shell*.py`、`record_manifest.py` 和展台脚本保留为经过实际工作的案例实现，并非任意模型的一键通用转换器。先查看参数与资源路径，再针对新项目适配。

```powershell
python Integrations/HybridAssets/Tools/find_assets.py lamp
python Integrations/HybridAssets/Tools/asset_gate.py --asset YOUR_ASSET --scope local
```

空清单查询没有结果，未知素材准入会失败，这是正常初始状态。`policy.json` 保存当时工作台的策略记录；正式采用新资产时核对自己取得的版本、来源、条款和使用范围。
