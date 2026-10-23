# iPhone 加载中退出：第二轮排查

最新包：`Dist/WeChat-iOSStartup-Final-20261023`。引擎与游戏均在 `main`，修改尚未提交。

用户反馈最新完整预下载版在 iPhone 上加载条未结束即直接退出。本轮没有 iPhone 连接、系统终止日志、机型或精确退出阶段，因此**没有确认唯一根因，也不宣称真机问题已解决**。前一轮“分包失败弹窗”和这次“进程直接退出”应分开分析。

## 已确认的代码问题与处理

1. **启动画面反复读取整张画布。** 旧 `showLoading` 每次都强制更新 1280×720 的 HUD，分包完成会重复通知，场景初始化也可能连续触发。每次 `getImageData` 创建 3,686,400 字节的像素数组。改为独立的 640×360 启动预算，由 `LoadingPresenter` 合并回调，常规更新间隔至少 200 ms；阶段切换先呈现一帧，再执行后续初始化。退出加载后取消待执行刷新，恢复正常游戏分辨率。
2. **.NET 预编译结果被丢弃。** 原适配器先调用原生 `WXWebAssembly.Module/compile`，随后实际实例化又传入文件路径，之前的 Module 未被复用。现在 pinned .NET loader 的 compile 阶段只保存经过路径映射校验的内部句柄，真实验证/编译在一次 `WXWebAssembly.instantiate(path, imports)` 中完成；动态、未知字节仍拒绝。可选特性检测仍执行真实宿主操作，没有伪造支持结果。
3. **原生 API 枚举性假设。** 原 `Object.assign({}, WXWebAssembly)` 可能漏掉不可枚举的 `Memory/Table` 等构造器，而 Mono 存在 `instanceof Memory` 检查。现在显式转发构造器，测试宿主故意把它们设为不可枚举。
4. **Wasm 与图像初始化峰值重叠。** 原流程创建 72 张图片后才开始原生实例化。现在先下载全部包、读取目录、启动 Wasm，然后才加载角色和界面图片；图片成功/失败后清除原生回调引用。菜单前完整下载的用户要求保持不变，开局不再下载资源。
5. **闪退记录会被下一次启动覆盖。** 新 `StartupDiagnostics` 在写新记录前归档上一次记录，保留最多 24 条阶段/分包轨迹和有限长度错误信息，记录机型、系统、微信/基础库版本。保存位置仍是手机本地，不上传。上次加载未完成时，下次进入先显示最后阶段，用户可以截图再继续。另记录宿主异常、未处理拒绝、WebGL context loss、内存告警；没有收到告警不代表没有系统内存终止。
6. **绘制错误可能被误报为分包错误。** 下载进度回调如果抛出 Canvas/WebGL 异常，原队列可能重试下载或等到超时。现将其作为 `LoadingProgressError` 传播，不混成网络失败，也不重复下载。

内存告警不会把启动期的 640×360 预算反而提高到 960×540。菜单前继续保留低预算，完成启动后根据是否告警选择正常/保守预算。

## 排除与尚未确认

- 使用实际输出 Wasm 检查：JavaScript EH、无 SIMD、无线程；测试 VM 关闭原生 Wasm EH 后仍能编译运行。未把桌面支持当成 iPhone 支持的证明。
- 模拟宿主中 Wasm 线性内存为 32 MiB。链接器的最大内存配置不等于实际分配了该最大值；本轮没有贸然压缩 Wasm 堆或改玩法。
- 未重新启用实例化渲染。仍使用普通 drawElements、CPU 蒙皮和显式属性绑定。
- 全部包仍在菜单前下载到宿主包存储，但没有在菜单前实例化全部场景 GPU 资源。
- 真实 iPhone 的基础库、原生图片/Canvas、GPU、Wasm 编译缓存与下载解压峰值无法从桌面 JS 堆推断；没有设备日志，不能断言其为 jetsam/内存终止。
- 官方参考：[Cocos iOS 微信小游戏内存与性能指南](https://docs.cocos.com/creator/3.8/manual/zh/editor/publish/ios/optimize.html) 区分 Canvas、Wasm、图像、GPU 等内存；[微信官方 WXWebAssembly 类型定义](https://github.com/wechat-miniprogram/minigame-api-typings/blob/master/types/wx/lib.wx.wasm.d.ts) 描述路径实例化接口。这些资料用于核对平台契约，不是此次设备崩溃证据。

## 新旧实际包对照

Chrome 模拟 WX 宿主，均注入第一次 managed 下载失败并自动重试，执行完整启动；这是累计分配/接口调用统计，**不是 iPhone 总内存或峰值内存**。

| 项目 | 上一版 WeChat-Preload | 本轮最终包 |
| --- | ---: | ---: |
| 加载期像素读回次数 | 40 | 14 |
| 加载期累计像素字节 | 147,456,000 | 12,902,400 |
| 原生同步 Module 调用 | 1 | 0 |
| 原生运行时路径实例化 | 1 | 1 |
| 原生实例化前创建图片 | 72 | 0 |
| 菜单阶段已加载场景物体 | 0 | 0 |
| 游戏 framebuffer | 1280×720 | 1280×720 |
| Wasm 线性内存 | 33,554,432 | 33,554,432 |

## 验证结果

| 类型 | 结果 | 证据 |
| --- | --- | --- |
| `unit-test` | PASS | 1,000 次进度回调在模拟时钟下合并为 51 次刷新；取消迟到刷新；归档上次记录、轨迹/错误长度上限、存储失败隔离 |
| `unit-test` | PASS | 下载串行/合并/重试/超时、迟到回调；绘制回调失败只尝试一次且不标记为分包错误；既有内存/加载并发回归 |
| `build-only` | PASS | 独立 C# 兼容性 fixture 重新编译；最终小游戏重新导出、18 个 ES2019 文件检查。游戏 C# 未变，复用此前通过的 Wasm |
| `test-layer` | PASS | 原生同步 Module 被禁止、Memory/Table/Global 不可枚举、performance/TextEncoder/TextDecoder/crypto/WX compile 缺失、三个可选特性均拒绝时，真实 C# 异常/finally/JSON/跨边界异常及恢复仍通过；原生实例化恰好一次 |
| `test-layer` | PASS | 实际最终游戏包：菜单、触控、购买、开局、后台、自然升级、结算、300 怪物和四区地形；菜单前全部包完成且开局不增加请求；上次 wasm 阶段记录先提示、随后启动成功并保留归档 |
| `test-layer` | PASS | 持续下载失败恰好三次，保留分包名及原生错误码 |
| `runtime-manual` | PASS | 人工检查新的 75% 加载画面截图，进度、标题、文字可见；仅浏览器截图 |
| `static-check` | PASS | 两仓库 diff 检查、最终包 manifest SHA256 |

运行日志：引擎 `out/agent/wechat-ios-startup-final-20261023.log`。兼容性结果：`out/agent/wechat-compatibility-test/1792736216950/result.json`。该回执的历史标签仍叫 `runtime-manual-browser-harness`，这里按实际自动断言归类为 `test-layer`；日志中的 favicon 404 不影响测试。

启动对照：`out/agent/starbloom-wechat-mobile-test/startup-WeChat-Preload-20261023.json` 和 `startup-WeChat-iOSStartup-Final-20261023.json`。加载截图：同目录 `ios-startup-loading.png`。

## 精确命令

引擎根目录执行（fixture 构建在 `Engine/Managed` 目录，以使用锁定的 .NET SDK）：

```powershell
$engine='C:/WorkSpace/HEngineDev'
$project='C:/WorkSpace/HEngineProjects/StarbloomSurvivor'
$node='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:HE_ENGINE_ROOT=$engine
$env:NODE_PATH='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$run="$engine/out/agent/build-publish/0B23D830D66A/wechat/content/20261023-020150-0305"
$package="$project/Dist/WeChat-iOSStartup-Final-20261023"

Push-Location "$engine/Engine/Managed"
dotnet publish "$engine/Tools/Build/Fixtures/WeChatCompatibility/Fixture.csproj" -c Release -p:HEngineRoot=$engine -p:HEPlatform=WeChat -p:PublishTrimmed=true -p:InvariantGlobalization=true --artifacts-path "$engine/out/agent/scratch/wechat-iphone-runtime/artifacts" -o "$engine/out/agent/scratch/wechat-iphone-runtime/publish"
Pop-Location
& $node "$project/Tools/ExportWeChat.cjs" "$run/content" "$run/managed/wwwroot/_framework" $package
& $node Tools/Build/WeChatJavaScript.cjs $package
& $node Tools/Build/TestWeChatStartup.cjs
& $node Tools/Build/TestWeChatSubpackages.cjs
& $node Tools/Build/TestWeChatMemory.cjs $project
& $node Tools/Build/TestManagedWeChat.cjs "$engine/out/agent/scratch/wechat-iphone-runtime/publish/wwwroot/_framework" $package
& $node "$project/Tools/TestWeChatMobileGame.cjs" $package --previous-startup
& $node "$project/Tools/TestWeChatMobileGame.cjs" $package --package-failure
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-Preload-20261023" --baseline --startup-only
& $node "$project/Tools/TestWeChatMobileGame.cjs" $package --loading-capture --startup-only
git diff --check
git -C $project diff --check
```

未执行 iPhone 真机/Xcode/Perfdog 采样，未做 Windows/Android 原生运行回归。没有新改动或失败后不扩大重复测试。

## 手机复测

新版仍先下载全部资源再显示菜单。大致阶段：2–70% 下载，72% 目录，75% Wasm，83–87% 角色，88–93% 图片，96% 游戏状态，100% 菜单首帧。

如果重进时出现“上次加载未完成”，请先截图记录，再点“继续加载”。上次记录另存在 `HEngine.StarbloomSurvivor.WeChat.diagnostic.previous`，当前记录在不带 `.previous` 的同名键中。

预览生成 PASS，总包 18,904,380 字节；二维码：引擎 `out/agent/starbloom-wechat-ios-startup-preview-20261023.png`。未正式发布。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-iOSStartup-Final-20261023' --qr-format image --qr-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-ios-startup-preview-20261023.png' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-ios-startup-preview-20261023.json'
```
