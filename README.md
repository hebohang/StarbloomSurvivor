# 小树保卫者 · Python · HEngine 1.1.0

`python` 分支是独立的纯 Python 玩法工程，不包含 C# 游戏脚本、预编译托管 DLL、C# 场景、WebAssembly 工程或 C++ 游戏模块。C# 四端版本位于 [`main`](https://github.com/hebohang/StarbloomSurvivor/tree/main)。

## 打开和游玩

```powershell
git clone --branch python https://github.com/hebohang/StarbloomSurvivor.git StarbloomSurvivor-Python
```

解压 [HEngine 1.1.0 Windows x64 SDK](https://github.com/hebohang/HEngineDev/releases/tag/v1.1.0)，运行 `ProjectManager.exe`，打开本目录的 `Project.heproject`。Editor 默认进入 `Assets/Scenes/MainMenu.he`，按 `F6` 启动 Python 主菜单，再点击开始进入 `MainGame.he`，按 `F8` 停止。编辑器内游玩使用 SDK 自带的 Python 后端，不需要 C# 或重新编译引擎。项目配置只启用 Python 脚本后端。

当前引擎先在私有 `HEngineDev` 发布，需要访问权限或作者提供 SDK。本游戏仓库公开。工程目录可改名，但 `Project.heproject` 文件名保持不变。

推荐两个分支分别克隆到不同目录。Python 工程有独立项目身份和默认存档目录，避免与 C# 版混用缓存和存档。

## 开发目录

| 路径 | 内容 |
| --- | --- |
| `Scripts/SurvivorGame.py`、`SurvivorHub.py` | 游戏入口与主菜单 |
| `Scripts/Survivor*.py` | 战斗、成长、目录、存档、表现及对应契约测试 |
| `Scripts/HEngineUI/`、`Scripts/DevOnly/` | UI 辅助与开发 GM 命令 |
| `Assets/Scenes/` | Python 主菜单和游戏场景 |
| `Assets/`、`Config/` | 游戏资源与 Python 工程配置 |
| `Tools/` | 可从独立工程运行的 Python 平衡检查 |
| `Legal/Assets/` | 素材许可证 |
| `Saved/`、`Dist/` | 忽略提交的本机产物 |

修改脚本后在 Editor 中停止、重新运行。资源已随工程提供；旧的素材生成草稿从本分支移除，可从拆分前的 Git 历史恢复。平衡检查使用 Python 3.11，可直接执行：

```powershell
py -3.11 Tools/RunSurvivorBalance.py --check
```

源码引擎运行本分支时显式传入工程路径：

```powershell
.\hectl.bat game check -Project C:\Games\StarbloomSurvivor-Python -Frames 120
.\hectl.bat package -Project C:\Games\StarbloomSurvivor-Python
```

本分支保留 `windows-python` 源码版 Windows 导出配置。标准 1.1.0 SDK 的独立 Game/Shipping 模板为 C#，不支持该配置；Python 在二进制 Editor 内可运行。Android、Web、微信的 C# 导出配置已从本分支移除；四端发布使用 C# 主干。
