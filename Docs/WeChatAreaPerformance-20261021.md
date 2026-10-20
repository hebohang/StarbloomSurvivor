# 微信四区地形与普通绘制优化

日期：2026-10-21。当前试玩包：`Dist/WeChat-Areas-Final-20261021`。

## 原因与修改

原有可见距离判断使用对象原点，但地形顶点已经烘焙为世界坐标，对象原点仍为零。四个净化区域的中心距原点均大于 55 米，因此进入区域后会把仍覆盖玩家位置的整块地形裁掉，跨过阈值时还会反复出现/消失。

微信渲染器现在按实际网格范围进行加载与距离判断，并按视锥保守裁剪。导入模型的 min/max 为空时，从已加载顶点计算范围；动画模型额外留出肢体运动余量。未知范围保持可见。四区地形不再依赖地图中心距离。

道路中另有约 60 个向下的三角形；双面绘制时会与上表面竞争，出现深色碎片。只对微信的道路和地形板块/坡道启用背面剔除，保留之前的道路深度偏移。原始网格、碰撞高度、地图资源均未改变。

性能优化继续使用原有 shader、CPU 蒙皮、属性 0–4 和普通 `drawElements`：

- 不透明物体按相同网格、材质和动画姿态组织绘制；每个物体仍单独提交矩阵与 drawElements，减少重复材质/属性绑定。
- 遇到透明物体先提交已有不透明绘制，保留原透明顺序。
- 蒙皮数组复用，原尺寸顶点缓冲通过 `bufferSubData` 更新。
- 仅跳过屏幕外的展示，公共 C# 战斗逻辑、怪物数量与 AI 更新未改。

没有实例化 shader、额外矩阵属性、divisor 或 instanced draw 调用。改动限于项目 `WeChat/`、引擎 `Runtime/Platform/WeChat/` 及验证文件；PC、Web、Android 的源码与行为入口不变。

## 验证结果

| 证据类型 | 结果 | 覆盖 |
| --- | --- | --- |
| `unit-test` | PASS | 真实四区中心均复现旧原点裁剪条件；对应地形范围包含区域；变换范围、视锥、空 min/max 与顶点范围回退 |
| `build-only` | PASS | 最终微信导出和 17 个文件的 ES2019 检查；C# 与内容未改，复用上轮已验证的 Wasm 和内容构建产物 |
| `test-layer` | PASS | 所有实例化接口直接抛错时完整手机流程仍通过；角色、300 怪物实际 framebuffer 像素可见，WebGL error=0 |
| `test-layer` | PASS | 四区 × 四个镜头方向保留基础地形和区域地面；每区穿过 54.8/55/55.2 米旧边界，地形不消失 |
| `test-layer` | PASS | 同深度覆盖层的 8192 个采样像素保持正确层次；地形背面剔除状态不泄漏到角色与 UI |
| `test-layer` | PASS | 300 怪物密集/铺开两种分布，优化前后可见像素平均差均小于 0.002/255 |
| `runtime-manual` | PASS | 逐一检查四区浏览器截图，地形完整，先前道路深色反向三角形不再显示；不代表手机实测 |
| `static-check` | PASS | 最终包不含实例化绘制/divisor 调用，569 项 manifest SHA256 匹配；两仓库 diff 空白检查通过 |

桌面 Chrome 模拟微信宿主、1920×1080 framebuffer、12 帧采样并使用 `gl.finish` 的渲染对照：

| 300 怪物场景 | 原普通路径 | 优化后普通路径 |
| --- | --- | --- |
| 屏幕内密集：绘制次数 | 778 | 654 |
| 屏幕内密集：材质绑定 | 778 | 45 |
| 屏幕内密集：中位耗时 / P95 | 2.7 / 3.1 ms | 1.4 / 1.8 ms |
| 怪物铺开：绘制次数 | 778 | 334 |
| 怪物铺开：材质绑定 | 778 | 45 |
| 怪物铺开：中位耗时 / P95 | 2.5 / 2.9 ms | 1.1 / 1.3 ms |

铺开场景跳过 160 只屏幕外怪物的绘制，密集场景未裁掉怪物。上述数字仅为模拟宿主渲染耗时，不是手机帧率，也不包含完整 C# 游戏帧耗时。新包的真机卡顿与闪烁表现待用户扫码反馈。

证据位于引擎 `out/agent/starbloom-wechat-mobile-test/`：
`ordinary-render-performance.json`、`compatible-visibility.json`、`region-visibility.json`、`depth-seams.json`，
以及 `region-star.png`、`region-thunder.png`、`region-water.png`、`region-wind.png`。

## 精确命令

从 `C:/WorkSpace/HEngineDev` 执行：

```powershell
$env:HE_ENGINE_ROOT='C:/WorkSpace/HEngineDev'
$env:NODE_PATH='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$mobileNode='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
& $mobileNode Tools/Build/TestWeChatVisibility.cjs C:/WorkSpace/HEngineProjects/StarbloomSurvivor
& $mobileNode C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Tools/ExportWeChat.cjs C:/WorkSpace/HEngineDev/out/agent/build-publish/0B23D830D66A/wechat/content/20261020-154457-5625/content C:/WorkSpace/HEngineDev/out/agent/build-publish/0B23D830D66A/wechat/content/20261020-154457-5625/managed/wwwroot/_framework C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Areas-Final-20261021
& $mobileNode Tools/Build/WeChatJavaScript.cjs C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Areas-Final-20261021
& $mobileNode C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Tools/TestWeChatMobileGame.cjs C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Areas-Final-20261021
git diff --check
git -C C:/WorkSpace/HEngineProjects/StarbloomSurvivor diff --check
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Areas-Final-20261021 --qr-format image --qr-output C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-areas-preview-20261021.png --info-output C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-areas-preview-20261021.json
```

导出目标必须为空；复跑时应选择新的输出目录。临时微信预览不等于正式发布。
