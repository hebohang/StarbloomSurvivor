# 小树保卫者 · HEngine 1.1.0

这是“小树保卫者”的独立游戏工程，使用 HEngine 1.1.0。引擎与项目可以放在任意目录，不需要引擎源码或复制引擎资源。

从 [HEngine 1.1.0 Release](https://github.com/hebohang/HEngineDev/releases/tag/v1.1.0) 下载并解压 Windows x64 二进制 SDK，再下载或克隆 [本工程](https://github.com/hebohang/StarbloomSurvivor)。

当前引擎 1.1.0 先在私有 `HEngineDev` 发布，需要该仓库访问权限或作者提供的 SDK。此游戏工程已公开；公开引擎 release 发布后会更新下载地址。

运行 SDK 内的 `ProjectManager.exe`，选择本目录的 `Project.heproject`，打开 `Assets/Scenes/MainGameCSharp.he` 后按 `F6` 游玩，按 `F8` 停止。`Project.heproject` 是引擎规定的描述文件名；工程目录名可以任意更换。

发行示例提供 `Scripts/CSharp/Prebuilt`，首次打开和游玩不需要编译引擎。修改 C# 脚本后需要 .NET SDK，按 SDK 的依赖检查结果安装工具。
源码版引擎可以使用 `hectl editor open -Project <本目录>`。

## 两套玩法实现

| 实现 | 在 Editor 中打开的场景 | Windows 导出配置 |
| --- | --- | --- |
| C# | `Assets/Scenes/MainGameCSharp.he`（含主菜单） | `windows` |
| Python | `Assets/Scenes/MainMenu.he` → `MainGame.he` | `windows-python` |

C# 入口是 `Scripts/CSharp/SurvivorNativeGame.cs`，共享玩法在
`Scripts/CSharp/Survivor/`。Python 入口是 `Scripts/SurvivorHub.py` 和
`Scripts/SurvivorGame.py`。两套实现共用美术、音频和玩法目录，便于对照学习。
Web 使用 C#，选择 `web` 导出配置。
在 Editor 中按 `F6` 运行当前场景，按 `F8` 停止并返回编辑；游戏捕获鼠标时也可以停止。

编辑 C# 需要 .NET SDK 10.0.302；游戏目录生成还需要 Python 3.11 和 Node.js。
通过引擎构建工具编译时自动传入引擎路径；直接调用 dotnet 时传入
`-p:HEngineRoot=<引擎根目录>`。可分发的预编译示例附带
`Scripts/CSharp/Prebuilt`，普通打开无需重新编译；修改脚本后在 Editor 的脚本面板重新编译。
预编译目录可随独立仓库保留，使下载工程的用户能直接运行；更新发行示例时用引擎的
`Tools/Distribution/Export-Project.ps1 -PrecompileCSharp` 重新生成。个人编译缓存保存在 `Saved/`。

## 使用二进制 SDK 导出四个平台

在 Editor 的构建/发布面板选择 `windows`、`android`、`web` 或 `wechat`，或在 SDK 根目录运行：

```powershell
.\hectl.bat deps check -Profile SDK -Project C:\Games\StarbloomSurvivor -Json
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor -Profile windows
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor -Profile android
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor -Profile web
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor -Profile wechat
```

输出分别在本工程 `Dist/Windows`、`Dist/Android`、`Dist/Web` 和 `Dist/WeChat`。Windows 和 Android 复用 SDK 的预编译原生模板，无需 VS 或重新编译引擎；C#、资源 cook、APK 组装及 Web/微信 Wasm 构建仍需要相应工具。以 SDK 内锁定的依赖版本及 `Docs/ReleaseSDK-1.1.0.md` 为准。

Web 输出通过 HTTP 服务打开；微信输出用微信开发者工具导入。发布自己的小游戏时替换 `Config/WeChat.json` 的 AppID、广告及排行榜配置。Android 默认使用开发签名，商店发布前配置自己的签名和包名。打包验证不等同于 Android/微信真机或商店审核通过。

四平台主路径为 C#。`windows-python` 保留作源码版对照学习，不属于标准二进制 SDK 的四端导出承诺。Web/微信使用便携视图适配，显示能力与原生 PC/Android 有差异。

资源位于 `Assets/`；项目配置在 `Config/`；生成目录 `Saved/`、`Dist/` 不加入版本控制。
项目素材许可证集中在 `Legal/Assets/`。原始导入素材和渲染测试属于引擎的
`Examples/RenderingTests`，运行本游戏不需要它们。
