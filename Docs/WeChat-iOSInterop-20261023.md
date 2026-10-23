# iPhone 的 native-ready 后退出：Jiterpreter 表与函数参数信息兼容

最新包：`Dist/WeChat-iOSInterop-20261023`。沿用菜单前完整下载、低分辨率加载界面、一次原生 Wasm 实例化。引擎与游戏仍在 `main`，尚未提交。

## 本轮证据

用户的新截图显示上次记录为 `wasm:native-ready / boot1`。这说明宿主实例化已返回，尚未完成 .NET 运行时初始化。`boot1` 只是最近成功下载的包，不能据此归因下载失败。新版只在下载阶段的提示中附加包名。

检查实际锁定的 .NET 10.0.10 loader，发现虽然三个动态 JIT 开关都关闭，初始化仍无条件执行 Jiterpreter 函数表准备，包括 `Table.grow`、`Table.set` 和原生占位函数注册。原始运行包在本机对照中扩容 6,182 个表项。

原始 C# 微信移植作者报告过 iOS 上该初始化引起闪退，以及原生 Wasm 函数 `length` 恒为零的问题：[原作者记录](https://www.cnblogs.com/BaiCai/p/18877189)。上游的 [Mono 运行时选项定义](https://raw.githubusercontent.com/dotnet/runtime/v10.0.10/src/mono/mono/utils/options-def.h) 也区分 JIT 功能开关和函数表大小。这是定位线索，不单独作为本项目真机根因证明。

**旧包负向对照已复现同一停点**：在测试宿主拒绝大于 64 项的 Table.grow 时，旧包请求 6,182 项扩容、无法进入菜单，最后持久化记录恰为 `wasm:native-ready`，下载记录仍为已完成的 boot1，与用户截图一致。这里模拟的是不兼容 API 的拒绝，不是声称在本机复现了 iPhone 原生进程崩溃。

## 修复

- 在源码导出器中新增 `WeChatManagedRuntimeTransform.cjs`。只对锁定 loader 的单个 Jiterpreter 初始化入口插入提前返回，跳过已关闭功能的函数表准备。
- 前提是无 AOT、三个 JIT 开关均明确关闭；开启 JIT/AOT、补丁入口重复或 SDK 结构变化都会停止导出，不能静默生成缺少适配的包。
- 处理原生函数不可靠的 `length=0`：cwrap 不再用零值判定参数数量错误；非零的真实不匹配仍保留原校验和回退。
- 增加 `pre-init`、`pre-run`、`mono-load-runtime`、`mono-loaded`、`jiterpreter-disabled`、`bindings-ready`、`post-run` 定位点，以及 abort/exit/运行时错误文本。继续保存上次启动记录。
- 没有手改 `Dist` 或已生成的 .NET 文件，没有修改 ThirdParty 或 .NET SDK。补丁由标准导出器每次自动应用。

## 验证

| 类型 | 结果 | 内容 |
| --- | --- | --- |
| `test-layer` | PASS，旧包预期失败 | 真实旧包在拒绝大规模 Table.grow 的宿主中请求 6,182 项扩容，停在 `wasm:native-ready`，未进入菜单 |
| `unit-test` | PASS | 原初始化调用表操作后失败；适配后完全跳过；零参数信息兼容；非零错误参数数量仍回退；JIT/AOT 开启、SDK 匹配数/结构变化拒绝 |
| `test-layer` | PASS | 真实 C# fixture：192 个导出函数全部包装为 length=0，原生特性探测均拒绝、关键浏览器 globals 缺失、构造器不可枚举、大规模表扩容被禁止时，异常/finally/JSON/跨 JS 异常及恢复均正确 |
| `test-layer` | PASS | 最终真实游戏包在同类受限宿主中完成菜单、购买、开始、后台、升级、结算、300 怪物和四区地形；菜单前下载全部包、开局不追加下载、旧阶段提示及归档仍正确 |
| `build-only` | PASS | 使用未改动且此前通过的 C# Wasm/内容重新导出；18 个 ES2019 文件检查 |
| `static-check` | PASS | 两仓库 diff 检查；最终包 manifest SHA256 检查 |

新包启动统计：`Table.grow` 调用数组为空，零 length 导出函数 192 个，同步 Module 构造 0 次、原生实例化 1 次。不是通过把 Table.grow 替换成“假成功”来绕过；原生表对象仍正常，测试只是拒绝不应出现的大扩容。

负向对照证据：引擎 `out/agent/starbloom-wechat-mobile-test/ios-table-negative-control.json`。兼容性 fixture：`out/agent/wechat-compatibility-test/1792737498092/result.json`。完整游戏日志：`out/agent/wechat-ios-interop-20261023.log`。fixture 回执沿用历史 `runtime-manual-browser-harness` 标签，这里按自动断言实际性质归类 `test-layer`。

## 精确命令

引擎根目录执行：

```powershell
$project='C:/WorkSpace/HEngineProjects/StarbloomSurvivor'
$node='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:HE_ENGINE_ROOT='C:/WorkSpace/HEngineDev'
$env:NODE_PATH='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$run='out/agent/build-publish/0B23D830D66A/wechat/content/20261023-020150-0305'
$package="$project/Dist/WeChat-iOSInterop-20261023"
& $node "$project/Tools/ExportWeChat.cjs" "$run/content" "$run/managed/wwwroot/_framework" $package
& $node Tools/Build/TestWeChatRuntimeTransform.cjs
& $node Tools/Build/TestManagedWeChat.cjs out/agent/scratch/wechat-iphone-runtime/publish/wwwroot/_framework $package
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-iOSStartup-Final-20261023" --ios-interop --expect-table-failure
& $node "$project/Tools/TestWeChatMobileGame.cjs" $package --ios-interop --previous-startup
& $node Tools/Build/WeChatJavaScript.cjs $package
git diff --check
git -C $project diff --check
```

尚未执行 iPhone 真机复测、Xcode 终止日志采集或 Windows/Android 原生回归。该修复比前面的内存优化更直接对应这次停点，但最终是否解决设备退出仍需扫码验证。

预览生成 PASS，总量 18,905,318 字节；570 项 manifest SHA256 匹配。新二维码为引擎 `out/agent/starbloom-wechat-ios-interop-preview-20261023.png`。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-iOSInterop-20261023' --qr-format image --qr-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-ios-interop-preview-20261023.png' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-ios-interop-preview-20261023.json'
```
