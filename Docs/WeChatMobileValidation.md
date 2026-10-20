# 微信小游戏手机适配

**最新版本见 [2026-10-21 四区地形与普通绘制优化](WeChatAreaPerformance-20261021.md)**，试玩包为 `Dist/WeChat-Areas-Final-20261021`。以下保留先前各轮验证历史。

2026-10-20。引擎 `C:/WorkSpace/HEngineDev` 与独立游戏工程均使用 `main`。

**当前应试玩 `Dist/WeChat-Compatible`。** 用户真机反馈实例化版本开局后场景、角色不可见，仅 UI/投射物可见。已撤回实例化实现，恢复原有 CPU 蒙皮与显式属性绑定的 `drawElements` 路径。下文“88% 绘制调用减少”仅为已撤回版本的浏览器历史数据，不适用于当前兼容包。

## 行为

- 默认进入冒险大厅，突出当前伙伴和开始按钮；伙伴、军械、成长、任务使用底部导航，难度和武器槽放在设置中。
- 横屏手机按可用安全区域布局，触控目标至少 44 个屏幕逻辑像素；窄屏保留竖排升级选项，背景覆盖整个画布。
- 整卡可点，菜单操作抬手确认；移动超过 12 个屏幕逻辑像素即取消点击。跳跃按下立即响应，可与移动、转向同时使用。
- 购买、强化与离开战斗使用确认弹窗。价格读取公共商品表，未解锁、余额不足和未购买的武器槽不可点。
- 暂停、复活、升级和结算使用微信手机布局；升级显示等级变化及剩余重抽、跳过次数。
- 切后台暂停且回前台需要主动继续。异步开局完成时若已进入后台，仍保持暂停。升级、取消触控及尺寸变化清理旧手势。

战斗、任务、解锁、货币与存档继续由公共 C# `WebGameSession` 负责，手机层仅处理展示和触控流程。未改原生 Windows/Android 菜单或公共战斗规则。

## 验证命令

以下从 `C:/WorkSpace/HEngineDev` 执行；Node 与依赖路径为本机环境。

```powershell
$env:HE_ENGINE_ROOT='C:/WorkSpace/HEngineDev'
$env:NODE_PATH='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$mobileNode='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'

& $mobileNode C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Tools/TestWeChatMobile.cjs
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:/WorkSpace/HEngineProjects/StarbloomSurvivor -Profile wechat
& $mobileNode C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Tools/TestWeChatMobileGame.cjs
git -C C:/WorkSpace/HEngineProjects/StarbloomSurvivor diff --check
```

| 证据类型 | 结果 | 覆盖 |
| --- | --- | --- |
| `unit-test` | PASS | 154 组手机尺寸/状态/确认弹窗布局；安全区、44 像素目标、无目标重叠；商品表价格、武器槽锁定、拖动取消、抬手提交、多指和取消触控 |
| `build-only` | PASS | 真实微信包导出；C# Wasm 手机兼容检查与 17 个 JavaScript 文件的 ES2019 检查 |
| `test-layer` | PASS | 最终导出包与真实 C# Wasm，在 Chrome 模拟微信宿主中运行；购买取消/确认/扣款、强化、开局、好友榜、多指移动/转向/跳跃、暂停恢复、后台暂停、异步开局后台保护、自然战斗升级、升级后旧触点失效、离开确认、结算与存档；568×320、667×375、844×390 横屏及 390×844 竖屏 |
| `runtime-manual` | PASS | 人工检查上述浏览器宿主截图中的大厅、伙伴、暂停及升级；属于画面观察，不是手机真机证据 |
| `static-check` | PASS | `git diff --check` |

集成测试仅在模拟宿主内存中预置 1000 星币和一个可购买伙伴，用于验证确认与扣款。随后运行真实 C# 战斗并自然触发升级，没有改写关卡状态或用户存档。

## 产物与限制

- 最终包：`C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat`，可在微信开发者工具中导入。已按用户要求上传临时扫码预览，未发布正式版本。
- 构建回执：`Saved/Build/wechat.json`；详细日志位于引擎 `out/agent/build-publish/0B23D830D66A/wechat/build.log`。
- 截图：引擎 `out/agent/starbloom-wechat-mobile-test/`，包括 `menu-568x320.png`、`menu-844x390.png`、`landscape-characters.png`、`landscape-paused.png`、`landscape-upgrade.png`、`portrait-result.png`。
- 初次 `islogin` 返回 `{"login":false}`；用户扫码登录后再次返回 `{"login":true}`。下列临时预览命令 PASS，生成 470×470 二维码；包总计 18.0 MB，主包 251.7 KB。二维码位于引擎 `out/agent/starbloom-wechat-mobile-preview.png`。这仅证明预览生成成功，手机实际游玩仍待用户反馈。
- 未执行真实广告、真实好友数据、手机帧率/温度/功耗验证。广告 ID 当前为空，测试不声称广告服务可用。
- 本次未执行 Windows/Android 原生构建；改动仅限微信表现层与项目测试。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat --qr-format image --qr-output C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-mobile-preview.png --info-output C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-mobile-preview.json
```

首轮平台范围静态核对 PASS：运行时代码修改为项目 `WeChat/Hud.js`、`WeChat/game.js`、`WeChat/MobileUI.js`；其他新增文件为项目测试与本文。后续优化范围见下节，不将静态检查声称为其他平台运行回归。

## 真机反馈后的排行榜、性能与地面优化

用户已体验首轮预览并反馈排行榜压扁、怪物较多时卡顿、地面接缝闪烁。

- 排行榜由固定 720×640 画布改为显示区域的实际长宽比，文字使用逻辑尺寸绘制，高密度栅格仅提升清晰度。每页行数随可用高度变化，异步旧请求不会覆盖旋转/尺寸变化后的新布局。
- 微信渲染器合并相同网格、颜色与动画姿态的实例，保留透明绘制顺序和不支持实例化时的原绘制路径。CPU 蒙皮缓存复用，减少分配和重复上传。
- 微信场景像素密度上限设为 2、总像素预算 1920×1080；HUD 根据可见内容变化缓存，变化时至多约 20 Hz 更新，按钮与页面切换即时刷新。静止大厅不会持续读取/上传整张 HUD。
- 微信相机近裁面从 0.1 调整到 0.75，远裁面 180；道路、事件圆环使用独立深度偏移，缓解接缝处重叠面的深度竞争。没有改变场景资源或游戏地形高度。

| 证据类型 | 结果 | 范围 |
| --- | --- | --- |
| `unit-test` | PASS | 排行榜横竖屏比例、像素密度、响应式行数/页码、尺寸未变时不重复清空、旧请求隔离 |
| `unit-test` | PASS | 前述 154 组手机 UI 布局与触控检查 |
| `build-only` | PASS | 最终微信包、C# Wasm 兼容检查及 17 个 ES2019 文件 |
| `test-layer` | PASS | 原手机交互回归；运行真实开放数据域绘制代码配合虚构好友数据；比例断言、静止 HUD 缓存、实例化渲染对照、同深度地面覆盖层测试 |
| `runtime-manual` | PASS | 检查浏览器模拟宿主的排行榜、游戏画面截图；未将其记作手机真机帧率或接缝验收 |
| `static-check` | PASS | 两仓库 `git diff --check`；Web、公共 C# 和原生 UI 未改 |

300 只同类怪物、同一渲染分辨率和固定状态的浏览器对照：逐对象绘制 763 次，实例化 92 次，减少约 88%；像素平均绝对差约 0.0009/255。桌面测试中 12 帧采样中位数约 2.1 ms → 1.1 ms（含 `gl.finish`），不是手机帧率数据，也不覆盖完整 C# 游戏帧耗时。结果保存在引擎 `out/agent/starbloom-wechat-mobile-test/render-stress.json`。

地面测试使用同深度重叠面与 8 个轻微变化的相机位置，原路径 8192/8192 个采样像素显示底层，新深度策略 0/8192 个采样像素显示底层。结果位于同目录 `depth-seams.json`，这是合成回归测试，手机实际接缝仍需复验。最初用 3 毫米间距的测试未在桌面 GPU 上复现冲突，前置复现断言 FAIL；随后改用确实存在歧义的同深度重叠条件，最终命令 PASS。

本轮精确命令（引擎目录执行，环境变量沿用上文）：

```powershell
& $mobileNode Tools/Build/TestWeChatLeaderboard.cjs
& $mobileNode C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Tools/TestWeChatMobile.cjs
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:/WorkSpace/HEngineProjects/StarbloomSurvivor -Profile wechat
& $mobileNode C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Tools/TestWeChatMobileGame.cjs
git diff --check
git -C C:/WorkSpace/HEngineProjects/StarbloomSurvivor diff --check
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat --qr-format image --qr-output C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-optimized-preview.png --info-output C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-optimized-preview.json
```

优化代码仅增加或修改项目 `WeChat/` 和引擎 `Runtime/Platform/WeChat/` 下的运行时代码；共享 `Runtime/Platform/Web/`、项目 `Web/`、公共 C#、原生 PC/Android 入口与资源均未修改。新增测试不进入运行包。新版二维码为引擎 `out/agent/starbloom-wechat-optimized-preview.png`。

## 实例化真机回归的兼容修复

用户真机反馈为 `runtime-manual FAIL`：实例化预览开始冒险后场景和角色不可见。浏览器测试没有覆盖到这一设备兼容问题，不能依据 shader 编译成功认定真机绘制可用。

已移除 `InstancedRenderer.js`，微信入口使用 `CompatibleRenderer.js`，只保留近裁面和道路深度偏移；完整使用之前的逐对象绘制路径。排行榜自适应、HUD 缓存及像素预算仍保留。PC、Web、Android 不变。

- `build-only`：`Publish.ps1` 的编译、资源导出、Wasm 兼容和 ES2019 检查 PASS；替换 `Dist/WeChat` 阶段因旧预览目录被占用 FAIL。因此复用同一次已导出的暂存包，经标准 `Publish-HEBuildOutput` 发布到独立 `Dist/WeChat-Compatible`，PASS。没有关闭用户进程。
- `static-check PASS`：兼容包 `game.js` 不含 `drawElementsInstanced` / `vertexAttribDivisor` 调用；569 个 manifest 条目的 SHA256 全部匹配。
- `test-layer PASS`：测试宿主让所有实例化绘制及 divisor 接口直接抛错，完整手机流程仍通过。普通场景 163 次绘制，300 怪物场景 763 次绘制；加入怪物后 286410 个实际 framebuffer 像素变化，隔离场景与投射物后角色有 4203 个可见像素，WebGL 错误为 0。证据为引擎 `out/agent/starbloom-wechat-mobile-test/compatible-visibility.json`。同深度覆盖层回归仍通过。
- `runtime-manual PASS`：人工检查兼容包浏览器截图，场景、角色、HUD 可见。手机修复效果待用户扫码确认。
- 微信 CLI 预览 PASS：新二维码为引擎 `out/agent/starbloom-wechat-compatible-preview.png`，只生成临时预览。

```powershell
# 在引擎目录执行，环境变量和 $mobileNode 沿用上文。
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project C:/WorkSpace/HEngineProjects/StarbloomSurvivor -Profile wechat
. ./Tools/Build/OutputDirectory.ps1
Publish-HEBuildOutput -Stage 'C:/WorkSpace/HEngineDev/out/agent/build-publish/0B23D830D66A/wechat/content/20261020-154457-5625/site' -OutputPath 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Compatible' -ProjectRoot 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor' -Profile wechat
& $mobileNode C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Tools/TestWeChatMobileGame.cjs C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Compatible
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Compatible --qr-format image --qr-output C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-compatible-preview.png --info-output C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-compatible-preview.json
```
