# HEngine 1.1.0 二进制 SDK 验收

验收日期：2026-10-15。C# 使用本仓库 `main`；Python 使用独立 `python` 分支（`580adbd`）。引擎实现基线为 `745f6b61`，验证安装目录不含原生引擎源码，不调用 Visual Studio 编译引擎。

## SDK 与首次打开

本次验证的 `HEngine-1.1.0-Windows-x64.zip` SHA256：

```text
3b151610980a35fc4d7fa837fcc21b4eae0b89b99c0f7afa5fb6847c478a7926
```

`Tools/Scripting/Api.schema.json` SHA256：

```text
fc21a0c4837c11f985131724f483e8c221608fd1c982e850845bb8c6c7063512
```

同为 1.1.0 的旧候选包不等同于此验收版本；发布时必须同时更新 SDK 附件和本仓库预编译脚本。用户无需下载引擎 C++ 源码。C# 的 `Scripts/CSharp/Prebuilt/` 已由此 SDK 的 `Export-Project.ps1 -PrecompileCSharp` 重新生成；首次游玩使用 SDK 内置 .NET 10.0.10，不执行脚本编译。修改 C# 或导出游戏仍需 SDK 文档列出的构建依赖。

## 编辑器游玩

| 分支 | 证据类型 | 结果与覆盖 |
| --- | --- | --- |
| C# `main` | `runtime-manual` | PASS；全新导出工程、初始无 Saved 缓存；F6 加载预编译 DLL，菜单开始战斗、敌人生成、自动攻击、击杀计数、升级、点击奖励后恢复战斗，F8 停止并再次 F6 返回菜单 |
| Python `python` | `runtime-manual` | PASS；SDK Editor 加载 MainMenu.he，F6 运行，开始后切换 MainGame.he，战斗、击杀升级、奖励选择正常，F8/F6 生命周期复验正常 |

两个编辑器进程均正常关闭；日志未发现脚本异常。以上是实际界面交互观察，不是自动测试或长时间稳定性保证。Python 本轮只验收编辑器，不扩展其独立 Player 或跨平台导出。

C# 实际加载的 `GameScripts.dll` SHA256：

```text
9d074fed36c82de86ea5ab039ae59c277d47a62d572d264de92d57211a69f2ff
```

## 四端导出

| 平台 | 证据类型 | 结果与覆盖 |
| --- | --- | --- |
| Windows | `build-only` + `test-layer` | PASS；C# Shipping 编译、资源 cook、依赖与发布策略检查、WARP 实际启动；原生 Player 与 SDK 模板 SHA256 相同 |
| Android | `build-only` + `test-layer` | PASS；ARM64 Vulkan APK、C# 依赖闭包、包内原生库哈希、开发签名、16 KiB 对齐检查；复用 SDK 原生模板，无 NDK/VS 编译 |
| Web | `build-only` + `test-layer` + `runtime-manual` | PASS；C# WebAssembly 发布与 517 项资源导出；浏览器实际进入战斗、击杀升级、选择奖励后继续，控制台无 error/warn |
| 微信 | `build-only` + `test-layer` | PASS；C# WebAssembly 与微信适配导出，入口、框架和 manifest 齐全；微信开发者工具预览未完成，返回需要重新登录（code 10） |

Android APK SHA256 为 `1b928dba664de3717197265a530a537bbc653c3688658e2989c504eb1e3d9398`，文件名为 `com.hengine.starbloomsurvivor-Signed.apk`。Android 真机游玩、微信工具内与真机游玩未执行；四端导出 PASS 不代表这些运行验收已完成。

原始验证使用引擎源码仓库中的测试驱动调用外部二进制 SDK。测试驱动只做检查，不为 SDK 提供原生源码或重建引擎。实际命令如下：

```powershell
$EngineSource = 'C:/WorkSpace/HEngineDev'
$SDK = 'C:/WorkSpace/HEngineReleases/1.1.0-scripting-20261014/HEngine-1.1.0-Windows-x64'
$Project = 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor'
$env:HE_ANDROID_TOOLCHAIN_ROOT = 'E:/HEngineSDKTools/Android'
powershell -NoProfile -ExecutionPolicy Bypass -File "$EngineSource/Tools/Distribution/Test-WindowsExporter.ps1" -Project $Project -ValidationRoot $SDK -SkipAssembly
powershell -NoProfile -ExecutionPolicy Bypass -File "$EngineSource/Tools/Distribution/Test-AndroidExporter.ps1" -Project $Project -Engine $SDK
powershell -NoProfile -ExecutionPolicy Bypass -File "$EngineSource/Tools/Distribution/Test-PortableExporter.ps1" -Project $Project -Engine $SDK -Profile web
powershell -NoProfile -ExecutionPolicy Bypass -File "$EngineSource/Tools/Distribution/Test-PortableExporter.ps1" -Project $Project -Engine $SDK -Profile wechat
```

四条命令均 PASS。SDK 内结果文件分别为：

- `out/agent/windows-validation/916c9ce0e24e4876a00c2feeb3e65450/result.json`
- `out/agent/android-validation/b2d358ab3f114b6599e919e6af841a47/result.json`
- `out/agent/portable-validation/bb5525224b8a4daeb196d7cb14e1c79e/result.json`
- `out/agent/portable-validation/c673889d71a64bd083c460385c440cee/result.json`

`static-check PASS`：预编译清单内 7 个程序集/元数据文件的 SHA256 全部匹配，`git diff --check` 通过。原始日志和界面截图保存在发布候选目录的 `Validation/StarbloomEvidence`，不作为游戏资源提交。

## 重现方法

在 SDK 根目录运行，路径替换为本机实际位置：

```powershell
# 生成不含旧 Saved/Dist 的独立 C# 工程及预编译程序集；输出必须为新目录。
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Distribution/Export-Project.ps1 -Project C:\Games\StarbloomSurvivor -Output C:\Games\StarbloomSurvivor-Test -PrecompileCSharp
.\HEngineEditor.exe --project=C:\Games\StarbloomSurvivor-Test --resolution=1280x720
.\HEngineEditor.exe --project=C:\Games\StarbloomSurvivor-Python --resolution=1280x720

# 在编辑器中执行上表交互；导出使用项目自带的四个配置。
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor -Profile windows -Action Build
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor -Profile android -Action Build
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor -Profile web -Action Build
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:\Games\StarbloomSurvivor -Profile wechat -Action Build
```

导出结果写入 `Dist/`，机器可读回执为 `Saved/Build/<profile>.json`；成功要求 `success: true`。Android 验收使用锁定工具链，未使用系统的 NDK 或 VS。开发签名 APK 与微信示例 appid 不代表完成商店发布手续；正式分发需使用自己的签名与平台配置。
