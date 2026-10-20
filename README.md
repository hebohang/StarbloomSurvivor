# 小树保卫者 · C# · HEngine 1.1.0

`main` 是独立的 C# 游戏工程，玩法源码全部位于 `Scripts/CSharp/`，没有 Python 玩法、Python 场景或 C++ 游戏模块。纯 Python 实现在独立的 [`python` 分支](https://github.com/hebohang/StarbloomSurvivor/tree/python)，两边分别维护自己的脚本和默认配置。

## 打开和游玩

下载或克隆本分支，解压 [HEngine 1.1.0 Windows x64 SDK](https://github.com/hebohang/HEngineDev/releases/tag/v1.1.0)，运行 SDK 的 `ProjectManager.exe`，选择本目录的 `Project.heproject`。Editor 默认打开 `Assets/Scenes/MainGameCSharp.he`，按 `F6` 游玩，按 `F8` 停止。项目插件配置只启用 C# 脚本后端。

当前引擎 1.1.0 先在私有 `HEngineDev` 发布，需要该仓库访问权限或作者提供的 SDK。游戏仓库公开；公开引擎 release 发布后会更新下载地址。

`Project.heproject` 是引擎规定的描述文件名；工程目录可改名，也可与引擎放在不同位置。`Scripts/CSharp/Prebuilt/` 提供预编译示例，首次打开和游玩无需引擎源码或 Visual Studio。

预编译脚本已更新到本次 1.1.0 SDK 契约。候选包校验值、C#/Python 编辑器验收及四端导出记录见 [二进制 SDK 验收](Docs/SDKValidation-1.1.0.md)；请使用其中对应的 SDK，旧版同名附件不代表通过本次验收。

```powershell
git clone --branch main https://github.com/hebohang/StarbloomSurvivor.git StarbloomSurvivor-CSharp
```

推荐把两个分支分别克隆到不同目录，避免分支切换复用 `Saved/`、旧构建结果或 Editor 个性设置。

## 修改游戏

| 目录 | 内容 |
| --- | --- |
| `Scripts/CSharp/SurvivorNative*.cs` | 原生场景、主菜单、设置与特效适配 |
| `Scripts/CSharp/Survivor/` | 战斗、成长、任务、存档与便携端共享玩法 |
| `Config/GameplayCatalog.json` | 角色、武器、关卡、地形、文本与资源路径，可直接编辑 |
| `Assets/` | 本分支场景、美术、UI、音频与特效 |
| `Build/Web/`、`Web/` | C# WebAssembly 入口与浏览器表现层 |
| `Tools/` | Node.js 内容导出和微信平台适配工具 |
| `Legal/Assets/` | 素材许可证 |
| `Saved/`、`Dist/` | 忽略提交的缓存、存档与导出产物 |

修改 C# 需要 SDK 锁定的 .NET SDK 10.0.302 和 Node.js，随后在 Editor 脚本面板重新编译。引擎提供的通用资源工具可能使用 Python；本工程不依赖 Python 游戏脚本或另一分支的数据。

构建工具自动传入引擎路径；直接调用 `dotnet` 时使用 `-p:HEngineRoot=<引擎根目录>`。`Tools/ExportContent.cjs` 根据 JSON 生成目录和资源依赖，生成内容写入构建缓存。更新仓库中的预编译示例时，使用引擎 `Tools/Distribution/Export-Project.ps1 -PrecompileCSharp` 导出到新目录并同步 `Scripts/CSharp/Prebuilt/`，无需提交个人缓存。

## 导出四个平台

Editor 构建/发布面板可选择 `windows`、`android`、`web` 或 `wechat`。本分支的 Node.js 内容导出需要含该支持的 1.1.0 维护版 SDK；源码引擎 `main` 和 `release-1.1.0` 同步维护。在引擎根目录也可运行：

```powershell
.\hectl.bat deps check -Profile SDK -Project C:\Games\StarbloomSurvivor-CSharp -Json
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor-CSharp -Profile windows
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor-CSharp -Profile android
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor-CSharp -Profile web
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor-CSharp -Profile wechat
```

输出位于本工程 `Dist/Windows`、`Dist/Android`、`Dist/Web`、`Dist/WeChat`。Windows 与 Android 复用 SDK 原生模板，无需 VS；脚本编译、资源 cook 和各平台组装仍需要对应工具。依赖版本以 SDK 和 `Docs/ReleaseSDK-1.1.0.md` 为准。

Web 用 HTTP 服务打开，微信用微信开发者工具导入。微信公共配置 `Config/WeChat.json` 的 `appid` 保持为空；导出前在 Git 忽略的 `Config/WeChat.local.json` 中填写 `{"appid":"你的小游戏 AppID"}`，或设置优先级更高的环境变量 `HE_WECHAT_APPID`。未提供有效 AppID 时导出会停止，避免上传到错误账号。导出包 `Dist/` 也不提交。Android 默认开发签名，正式发布需配置自己的签名和包名。Web/微信使用便携表现适配；打包通过不等同于真机或商店验收通过。
