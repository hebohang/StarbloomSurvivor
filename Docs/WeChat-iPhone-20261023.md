# iPhone 启动退出排查与怪物性能优化

日期：2026-10-23。引擎 `C:/WorkSpace/HEngineDev` 与游戏仓库均在 `main`，修改尚未提交。

**用户已确认 iOS 运行时修复版可以启动。最新候选包为 `Dist/WeChat-Friends-Final-20261023`，用于 [好友排行榜错误诊断](WeChat-Friends-20261023.md)。仍在菜单前下载完全部分包；下文保留前几轮验证历史。**

本次候选包：`Dist/WeChat-iPhone-Final-20261023`（17.94 MiB）。直接导入微信开发者工具；旧的 `Dist/WeChat` 未替换。按用户后续要求已生成临时扫码预览，未正式发布。

## 已知现象与判断边界

用户反馈 iPhone 在加载条结束、主菜单出现前直接退出。尚无机型、iOS/微信版本或设备崩溃日志，因此**不能确认根因，也不能将浏览器通过写成真机闪退已修复**。

代码及新旧包测量确认了启动阶段不必要的场景资源分配、全屏 HUD 像素读回、抗锯齿/保留缓冲、重复 JSON 文件读取。先针对这些降低菜单首帧之前的资源峰值。iOS 小游戏内存压力值得排查，参考 [Cocos 官方 iOS 微信小游戏内存与性能指南](https://docs.cocos.com/creator/4.0/manual/zh/editor/publish/wechat-ios-optimize.html)；该资料不是本项目崩溃的证明。

Chrome 模拟微信宿主、960×540 逻辑视口，首次进入菜单的资源统计：

| 指标 | 历史四区包 | 本次候选包 |
| --- | ---: | ---: |
| 已加载网格 | 58 | 1 |
| 已分配网格的场景物体 | 228 | 0 |
| CPU 几何数组引用的缓冲字节 | 2,201,408 | 145,376 |
| framebuffer | 1920×1080 | 1280×720 |
| HUD 每次像素读回/上传字节 | 8,294,400 | 3,686,400 |
| Wasm 线性内存 | 33,554,432 | 33,554,432 |

这些是资源计数，**不是进程总内存、iPhone 峰值内存或手机帧率**。

## 修改

- 微信将战斗场景加载推迟到点击开始之后，开始按钮在准备过程中防止重复提交，切后台后异步开局仍保持暂停。
- 微信渲染像素预算为 1280×720，像素密度上限 1.5；关闭 MSAA 和 `preserveDrawingBuffer`。普通 `drawElements`、CPU 蒙皮及原属性绑定保持使用，不重新引入此前真机失败的实例化。
- HUD 独立限制像素总量；内存告警时降到 960×540、像素密度 1，并清理可重新读取的 JSON 缓存。仍保持完整逻辑布局和触控坐标。
- 资源 JSON 只读取一次 UTF-8 文本；CPU 几何只保留所需数组，不引用完整模型二进制；场景在途加载总数最多两个，跨帧不会无限追加。
- 菜单/暂停/升级等非战斗状态复用当前快照，避免重复调用 C# 序列化。
- 怪物包围盒使用等价的中心/半径变换，减少每只怪物的视锥计算；公共 C# 地形查询先排除范围外的板块，再执行原多边形测试。边界容差、坡道与重叠高度规则不变。
- 增加启动阶段和内存告警记录；诊断存储键为 `HEngine.StarbloomSurvivor.WeChat.diagnostic`，与游戏存档分开。开发者工具控制台可用 `wx.getStorageSync('HEngine.StarbloomSurvivor.WeChat.diagnostic')` 读取最近阶段。系统直接终止进程不保证来得及触发告警。

公共 Web 渲染器新增可选宿主参数，默认行为不变。C# 地形优化属于共享逻辑。未修改怪物数量、伤害、生成、AI 或存档规则。

## 验证

| 类型 | 结果 | 范围 |
| --- | --- | --- |
| `unit-test` | PASS | 111,050 个真实地形随机点、顶点、边缘、容差内外和坡道采样与旧完整扫描结果严格一致；桌面 .NET 中位耗时 79.27 → 15.25 ms，仅为查询微基准 |
| `unit-test` | PASS | 单次按需资源读取、CPU 数组保留范围、HUD 缓存/像素上限/全屏合成、100 帧慢加载并发上限、加载失败释放槽位 |
| `unit-test` | PASS | 1,000 组旋转/负缩放/剪切的包围盒与八角点算法一致；四区地形范围；154 组手机 UI 布局及触控规则 |
| `build-only` | PASS | C# Wasm 编译、JavaScript EH/无 SIMD/无线程兼容检查；候选包导出及 17 个 ES2019 文件检查 |
| `test-layer` | PASS | 实际导出包与真实 C# Wasm，Chrome 模拟微信：菜单、购买、确认/取消、成长、好友榜、开局、多指移动/转向/跳跃、暂停、后台异步开局、自然升级、结算存档、横竖屏；300 怪物可见性；四区地形与道路深度；模拟内存告警后继续运行 |
| `runtime-manual` | PASS | 逐张检查模拟宿主的菜单、战斗截图；不是 iPhone 验收 |
| `static-check` | PASS | 两仓库 `git diff --check`；569 个候选包 manifest SHA256 匹配；无实例化绘制/divisor 调用 |

300 怪物密集/铺开的兼容绘制检查分别为 654/334 次 draw，WebGL error=0。此优化之前已有材质排序/裁剪，不能把本次测试里的“普通基线 vs 排序路径”差异归因于这次提交。未测真实手机帧率、功耗或崩溃恢复；未执行 Windows/Android 原生运行回归。

### 精确命令与构建环境问题

引擎根目录执行，除地形测试明确指定工作目录：

```powershell
$engine='C:/WorkSpace/HEngineDev'
$project='C:/WorkSpace/HEngineProjects/StarbloomSurvivor'
$node='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$python='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:HE_ENGINE_ROOT=$engine
$env:NODE_PATH='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$env:HE_SCRIPT_NODE=$node
$env:HE_BUILD_PYTHON=$python

# 首次整链命令 FAIL：C# Wasm 编译与兼容检查 PASS，资源处理阶段的
# PYTHONPATH 注入了另一 Python 版本的 Pillow，导入 _imaging 失败。
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project $project -Profile wechat

# 复用这次已成功编译的 Wasm 和内容；隔离 Python 包环境后，余下阶段 PASS。
# 未手改生成文件，也未把失败的 Saved/Build/wechat.json 改写成成功。
$run="$engine/out/agent/build-publish/0B23D830D66A/wechat/content/20261023-020150-0305"
$env:PYTHONPATH=$null
& $python -E Tools/Build/OptimizePortableAssets.py "$run/content"
& $node "$project/Tools/ExportWeChat.cjs" "$run/content" "$run/managed/wwwroot/_framework" "$project/Dist/WeChat-iPhone-Final-20261023"
& $node Tools/Build/WeChatJavaScript.cjs "$project/Dist/WeChat-iPhone-Final-20261023"

& $node Tools/Build/TestWeChatMemory.cjs $project
& $node Tools/Build/TestWeChatVisibility.cjs $project
& $node "$project/Tools/TestWeChatMobile.cjs"
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-iPhone-Final-20261023"
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-Areas-Final-20261021" --startup-only
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-iPhone-Final-20261023" --startup-only

Push-Location "$engine/Engine/Managed"
dotnet run --project "$project/Tools/Tests/TerrainSurface/TerrainSurfaceTests.csproj" -c Release --artifacts-path "$engine/out/agent/scratch/wechat-iphone/terrain-tests" -- "$project/Config/GameplayCatalog.json"
Pop-Location
git diff --check
git -C $project diff --check
```

导出器要求空目标，重跑导出请选择新的目录。主机默认 `node` 是 16.13，首次测试因 Playwright 要求 Node 20+ 未启动；改用上述 Node 路径后通过。测试编写时同步 esbuild 不支持插件，已改为异步构建并重新通过。完整候选包运行日志：引擎 `out/agent/wechat-iphone-final.log`；启动资源统计、内存告警及截图：`out/agent/starbloom-wechat-mobile-test/`。

下一步真机重点：冷启动能否进入菜单；开始战斗后能否持续游玩；怪物密集时体验；后台返回。若仍在菜单前退出，需取上述阶段记录和 iPhone 机型、iOS/微信版本，进一步区分 Wasm 初始化、菜单首次绘制、音频启动和系统内存终止。

## 手机扫码预览

2026-10-23 用户明确要求立即在手机运行。首次 CLI 启动连接超时，打开现有微信开发者工具后恢复连接，`islogin` 返回 `login:true`。以下预览命令 PASS；服务回执总包 18.0 MB、主包 252.9 KB。只证明预览上传和二维码生成成功，不代表 iPhone 运行验收。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' islogin
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-iPhone-Final-20261023' --qr-format image --qr-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-iphone-preview-20261023.png' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-iphone-preview-20261023.json'
```

二维码：引擎 `out/agent/starbloom-wechat-iphone-preview-20261023.png`；同名 JSON 为预览回执。

## 真机反馈：12% 分包下载失败

用户随后提供截图，显示 `failed:packages`，加载条 12%。这是原生分包加载失败触发了错误弹窗，尚未进入 C# 运行时；不能将这张截图归因于前述内存压力。旧错误处理没有保留 `errMsg` / 错误码，因此还无法确定具体是哪个包、网络错误还是平台拒绝。

旧流程并发下载所有约 18.8 MB 的包，任意一次失败都会终止初始化。新流程：

- 菜单必需内容单独归入 `boot0/boot1`：配置、场景/模型元数据、默认角色、界面图片、菜单音效。进入菜单前所需包文件合计约 7.7 MB；其余约 11 MB 在点击开始时下载。数字是本地包文件量，不能换算为真实网络耗时。
- 新增平台 `Subpackages` 下载队列，串行、同包请求合并、成功缓存；暂时失败自动重试，最多 3 次。60 秒没有实际进度时判为超时；迟到回调不能把失败请求变成成功。失败缓存被清除，战斗准备失败后可以重新点开始。
- `onProgressUpdate` 驱动真实包内进度，显示当前包序号、百分比和重试次数。资源文件及图片必须等所属包成功之后才能读取。
- 保留失败分包名、原生错误消息和错误码，既显示在下载失败弹窗，也写入既有诊断存储；不再只有 `failed:packages`。
- 不改 C# 或资源内容，复用前一轮通过的 Wasm/资源暂存产物，通过源码导出器重新打包。

验证：`unit-test PASS`（下载队列的并发合并、暂时/永久失败、超时、迟到回调和重新请求，以及内存测试）；`test-layer PASS`（真实最终包注入首次 managed 分包失败，自动恢复并走完整手机/300 怪物/四区回归；未下载的包禁止文件读取；菜单只用启动包）；`test-layer PASS`（连续失败恰好重试三次，弹窗和持久化诊断均保留 managed、错误消息和 1001）；`build-only PASS`（导出及 18 个 ES2019 文件）；`static-check PASS`（两仓库 diff 检查）。真机下载结果仍待新预览复测。

沿用上文 `$node/$engine/$project/$run` 与环境变量：

```powershell
& $node Tools/Build/TestWeChatSubpackages.cjs
& $node Tools/Build/TestWeChatMemory.cjs $project
& $node "$project/Tools/ExportWeChat.cjs" "$run/content" "$run/managed/wwwroot/_framework" "$project/Dist/WeChat-Download-Final-20261023"
& $node Tools/Build/WeChatJavaScript.cjs "$project/Dist/WeChat-Download-Final-20261023"
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-Download-Final-20261023"
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-Download-Final-20261023" --package-failure
git diff --check
git -C $project diff --check
```

日志为引擎 `out/agent/wechat-download-final-20261023.log`，持续失败证据为 `out/agent/starbloom-wechat-mobile-test/package-failure.json`。

新预览生成 PASS，回执总量 18,898,126 字节，主包+runtime+boot0+boot1 合计 7,817,505 字节（约减少 59% 的菜单前必需包文件量）。570 项 manifest SHA256 检查 PASS。二维码为引擎 `out/agent/starbloom-wechat-download-preview-20261023.png`。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Download-Final-20261023' --qr-format image --qr-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-download-preview-20261023.png' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-download-preview-20261023.json'
```

## 真机启动成功后：恢复菜单前完整下载

用户确认下载修复版可以启动、进度显示良好，并明确要求菜单前基本下载好，避免点击开始后再次下载。

`WeChat-Preload-20261023` 在显示菜单前串行下载全部分包，保留最多三次重试、超时、原生错误诊断；下载覆盖总加载条的 2%–70%，其后读取内容、界面与启动 C#。点击开始只准备本地场景及调用既有服务，不再发起分包下载。网格/贴图实例化仍延后，菜单首次只保留一个角色网格，避免把完整下载与完整显存分配混在一起。

`build-only PASS`：复用未变的 C# Wasm/资源，源码重新导出及 18 个 ES2019 文件检查。`test-layer PASS`：进入菜单时已加载全部分包；点击开始后下载请求计数不增加；注入首次失败仍能恢复；连续失败恰好三次并保留诊断；完整手机交互、300 怪物、四区地形回归通过。`static-check PASS`：570 项 manifest SHA256 与两仓库 diff 检查。此版本尚待真机复测。

精确命令（变量与环境沿用上文）：

```powershell
& $node "$project/Tools/ExportWeChat.cjs" "$run/content" "$run/managed/wwwroot/_framework" "$project/Dist/WeChat-Preload-20261023"
& $node Tools/Build/WeChatJavaScript.cjs "$project/Dist/WeChat-Preload-20261023"
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-Preload-20261023"
& $node "$project/Tools/TestWeChatMobileGame.cjs" "$project/Dist/WeChat-Preload-20261023" --package-failure
git diff --check
git -C $project diff --check
```

运行日志：引擎 `out/agent/wechat-preload-20261023.log`。

扫码预览生成 PASS，总包 18,897,757 字节，主包 263,566 字节。二维码：引擎 `out/agent/starbloom-wechat-preload-preview-20261023.png`。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Preload-20261023' --qr-format image --qr-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-preload-preview-20261023.png' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-preload-preview-20261023.json'
```
