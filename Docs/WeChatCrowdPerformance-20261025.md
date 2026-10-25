# 微信群怪性能与节奏调整（2026-10-25）

版本包：`Dist/WeChat-MobileTuned-20261025`。已上传微信开发版本 `1.1.0.20261025`，未提交审核或正式发布。引擎与游戏均在 `main`，开发基线分别为 `ce8bc88e3` 和 `d9ece27`。

用户确认上一版 iPhone 已不闪退。本轮保留该稳定基线，处理后期卡顿/发热、怪物重叠、初期太轻松、四区域难度突增和基础移动偏慢。

## 调整结果

| 项目 | 原先 | 本轮 |
| --- | --- | --- |
| 基础移动速度 | 4.25 | 5.1（+20%，角色/成长倍率照常叠加） |
| 最初探索目标怪量 | 30–45 | 40–58 |
| 第二档探索目标怪量 | 45–60 | 50–68 |
| 首分钟刷怪 | 0.65 秒/2 只，纯绿怪 | 0.55 秒/3 只，85% 绿怪、15% 粉怪 |
| 第一区域局部目标 | 50–85 | 38–60 |
| 第二区域局部目标 | 75–120 | 52–82 |
| 第三区域局部目标 | 105–160 | 70–108 |
| 第四区域局部目标 | 140–210 | 90–135 |
| 各区域突发波上限 | 14 / 20 / 28 / 36 | 8 / 12 / 16 / 20 |
| 各区域基础刷怪速率 | 5 / 8 / 11 / 15 | 4 / 6 / 8 / 10 |
| 各区域刷怪速率上限 | 8 / 12 / 16 / 22 | 6 / 9 / 12 / 15 |
| 各区域生命倍率 | 1 / 1.18 / 1.42 / 1.72 | 0.95 / 1.08 / 1.24 / 1.42 |
| 各区域伤害倍率 | 1 / 1.1 / 1.22 / 1.38 | 0.9 / 1 / 1.1 / 1.2 |
| 出圈宽限 | 1.25 秒 | 2 秒；守护时长仍为 60 秒 |
| 微信常规活动怪物上限 | 320 | 240；任务 Boss 可额外出场，避免任务被满额卡住 |

同时修复了区域开场的重复突发波：原条件 `active.Assault < dt * 2` 会在前两帧重新初始化刷怪信用和突发计时器。现在只在真正进入一次守护时初始化，出圈宽限内返回不会重置，失败后重新开始才重置。

## 性能与群怪处理

- 新增复用桶的空间网格，覆盖投射物碰撞候选、最近目标及范围武器的密集区域选点。保留精确距离检测和原生成顺序，避免因查询顺序改变命中或随机数消费。非常拥挤时退回复用的有序列表，避免对几乎全部怪物额外排序。
- 范围武器不再用 LINQ 对每只怪物遍历全体并排序选密集点；投射物不再为每次查询分配完整怪物数组。
- 局部分离以 20 Hz 更新，每只怪物最多检查 32 个邻居，每次位移有上限；检查地形，冻结怪物及 Boss 不被移动，蓄力/冲锋阶段保持稳定。新旧采样不依赖宿主随机数。40 只完全重叠的怪物能散开，数量不变。
- 区域刷怪改用黄金角与多圈半径分布，减少反复刷在同一组 8 个点的问题。
- 微信请求宿主 30 FPS，并用内部节拍器限制昂贵的战斗提交到 30 Hz、静止菜单到 15 Hz；摇镜输入合并到下一游戏帧。没有把游戏时间简单乘上慢速系数。
- 战斗像素预算默认 960×540，达到 200 只展示怪物时切到 800×450，降到 140 只以下恢复；菜单仍为 1280×720。上下阈值分开，避免分辨率来回抖动。动画采样由 20 Hz 调到 15 Hz。
- 微信友方装饰性范围效果/光束最多 128 个显示点，实际伤害、真实投射物和敌方危险提示不由这个预算裁掉；远离展示区域的效果不再生成显示点。100 个友方效果的测试中显示点从 2,400 降至 128，另有 48 个敌方提示全部保留，伤害结果相同。
- 任务数值读取优先使用 JsonValue 数值接口，避免反复序列化后再解析；空事件上下文复用。

空间网格使用整数键，不引入基于宿主熵的组合哈希。没有改动 iPhone 的 Jiterpreter 跳过、cwrap 零参数信息适配、单次原生实例化、启动低分辨率及诊断记录。没有重新启用实例化渲染，普通 drawElements/CPU 蒙皮路径保持使用。

## Megabonk 参考边界

参考了 [Megabonk 开发者的官方更新](https://steamcommunity.com/app/3405340/allnews/)：其后期优化包含对高频物品触发设上限、控制透明特效开销、限制无效延长的投射物生命周期，也强调移动和地图路线的价值。没有公开证据能确认其完整群怪分离算法，因此本轮空间网格和局部分离是本项目自己的实现，不宣称复制了 Megabonk 内部技术。

## 验证与测量

桌面 .NET Release 微基准，320 怪物、200 投射物；保存了改动前源文件作基线。下面为一组实际采样，数值有运行波动，**不能当作 iPhone 帧率**：

| 测项 | 基线 | 本轮 |
| --- | ---: | ---: |
| 投射物更新 | 3.72 ms | 3.02 ms |
| 100 次最近目标查询 | 1.17 ms | 0.69 ms |
| 密集区域选目标 | 0.49 ms | 0.15 ms |
| 完整逻辑步 + 快照 | 1.42 ms | 1.36 ms |

完整逻辑步在多次本机采样中约 1.35–1.55 ms，新增分离也有成本，不能把单项查询收益说成整帧提高数倍。主要持续负载控制来自帧率、像素、特效和活动怪量预算。

另用真实 C# Wasm、禁用 JIT/原生 EH 的受限浏览器宿主执行同一压力场景：320 怪物时完整步及快照约 22.7 ms；200 投射物反复命中的压力更新约 36.7 ms。这不是整场游戏帧耗时，也不是手机数据，说明极端数量下仍需预算控制。该 fixture 同时执行精确查询、区域开场和 240 上限/Boss 保留测试。

| 类型 | 结果 | 范围 |
| --- | --- | --- |
| `unit-test` | PASS | 500 组随机最近目标/碰撞集合和顺序与暴力参考一致；密集点选择一致；分离确定性、位移上限、冻结保持；友方显示预算伤害不变且敌方提示保留；基础速度；区域开场不重复；240 上限与 Boss 出场 |
| `unit-test` | PASS | 30/60/120 Hz 回调宿主得到 30 战斗/15 菜单提交，原生限帧提示、切模式/恢复/时钟回退；154 组手机布局/触控；已有 iOS runtime transform 回归 |
| `build-only` | PASS | 新游戏 C# Wasm、独立 CombatWasm fixture、最终微信导出、18 个 ES2019 文件 |
| `test-layer` | PASS | 最终包完整手机流程、购买/升级/后台/存档/多指操作、300 怪物可见性、四区地形、同深度道路；分辨率 200→199→150→139 怪的滞回；开局无新增下载 |
| `test-layer` | PASS | 游戏在 native Module 禁止、JIT 大表扩容禁止、导出函数 length=0、宿主 crypto 缺失时运行；真实 C# fixture 在更多 globals 缺失/原生 EH 禁用条件下通过异常及密集战斗验证 |
| `runtime-manual` | PASS | 逐张检查 40 怪重叠/分离截图；仅浏览器画面 |
| `static-check` | PASS | 两仓库 diff 检查；目录数据仅 waves/objective/encounterTiers/globalThreatBands 改变；最终包 manifest SHA256；iPhone 核心修复源码相对稳定基线无改动 |

未测真实手机的持续帧率、温度、功耗；没有执行 Windows/Android 原生游戏运行回归。共享 C# 的移动/战斗/难度逻辑会影响其他使用该会话的端，微信帧率/画质/活动上限设置仅在微信入口启用。

## 命令与证据

环境变量：

```powershell
$engine='C:/WorkSpace/HEngineDev'
$project='C:/WorkSpace/HEngineProjects/StarbloomSurvivor'
$node='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$python='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:HE_ENGINE_ROOT=$engine
$env:NODE_PATH='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$env:HE_SCRIPT_NODE=$node
$env:HE_BUILD_PYTHON=$python
$scratch="$engine/out/agent/scratch/wechat-crowd"
$run="$engine/out/agent/build-publish/0B23D830D66A/wechat/content/20261025-061419-7076"
$package="$project/Dist/WeChat-MobileTuned-20261025"
```

构建先调用 `powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Publish.ps1 -Project $project -Profile wechat`：C# 编译与兼容检查 PASS，资源处理受既有 Python/Pillow 版本路径冲突影响 FAIL。随后用隔离 Python 完成资源处理；最终 C# 小改动后单独重编译并通过标准导出器生成新目录，没有改写失败回执。

```powershell
# 引擎根目录
$env:PYTHONPATH=$null
& $python -E Tools/Build/OptimizePortableAssets.py "$run/content"
Push-Location "$engine/Engine/Managed"
dotnet run --project "$project/Tools/Tests/Combat/CombatTests.csproj" -c Release -p:HEngineRoot=$engine --artifacts-path "$scratch/tests" -- "$project/Config/GameplayCatalog.json" "$scratch/evidence"
dotnet run --project "$project/Tools/Tests/Combat/CombatTests.csproj" -c Release -p:HEngineRoot=$engine -p:GameplaySources=$scratch/baseline -p:Baseline=true --artifacts-path "$scratch/baseline-test" -- "$scratch/baseline/catalog.json"
dotnet publish "$project/Build/Web/Starbloom.Web.csproj" -c Release -p:HEngineRoot=$engine -p:HEPlatform=WeChat -p:HEQuality=Portable -p:PublishTrimmed=true -p:InvariantGlobalization=true -p:WasmEnableExceptionHandling=false -p:WasmEnableSIMD=false -p:WasmEnableThreads=false -p:WasmBuildNative=true --artifacts-path "$engine/out/agent/build-publish/0B23D830D66A/wechat/artifacts" -o "$scratch/mobile-managed"
dotnet publish "$project/Tools/Tests/CombatWasm/CombatWasm.csproj" -c Release -p:HEngineRoot=$engine -p:HEPlatform=WeChat -p:PublishTrimmed=true -p:InvariantGlobalization=true --artifacts-path "$scratch/wasm-tests/artifacts" -o "$scratch/wasm-tests/publish"
Pop-Location
& $node "$project/Tools/ExportWeChat.cjs" "$run/content" "$scratch/mobile-managed/wwwroot/_framework" $package
& $node Tools/Build/WeChatJavaScript.cjs $package
& $node Tools/Build/TestWeChatFramePacer.cjs
& $node Tools/Build/TestWeChatRuntimeTransform.cjs
& $node "$project/Tools/TestWeChatMobile.cjs"
& $node "$project/Tools/TestWeChatMobileGame.cjs" $package --ios-interop --previous-startup --no-crypto
& $node Tools/Build/TestManagedWeChat.cjs "$scratch/wasm-tests/publish/wwwroot/_framework" $package "$project/Config/GameplayCatalog.json"
git diff --check
git -C $project diff --check
```

新 fixture 首次缺少 Platform.props 导入导致编译失败，补齐后通过；原手机测试同步断言摇镜变化，与改为下一帧合并输入的行为不符，改为 500 ms 内必须变化并通过。新分辨率策略下，300 怪像素对比固定同一 framebuffer 大小后比较，避免把尺寸变化当作角色可见性的证据。

主要日志：`out/agent/scratch/wechat-crowd/current-tests.log`、`baseline-tests.log`、`mobile-tuned.log`、`wasm-benchmark-final.log`。Wasm fixture 结果：`out/agent/wechat-compatibility-test/1792910556613/`。群怪前后截图：`out/agent/starbloom-wechat-mobile-test/crowd-separation-before.png`、`crowd-separation-after.png`。

预览生成 PASS，总包 18,914,773 字节，主包 274,710 字节；二维码为引擎 `out/agent/starbloom-wechat-mobile-tuned-preview-20261025.png`。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-MobileTuned-20261025' --qr-format image --qr-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-mobile-tuned-preview-20261025.png' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-mobile-tuned-preview-20261025.json'
```

用户授权后，以下开发版本上传命令 PASS。回执为引擎 `out/agent/starbloom-wechat-upload-20261025.json`，上传总量 18,914,773 字节；上传前 570 项 manifest SHA256 核验 PASS。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' upload --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-MobileTuned-20261025' --version '1.1.0.20261025' --desc '微信性能与平衡优化：移速提升20%，群怪分离与帧率特效预算，调整四区域难度，保留iPhone兼容修复' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-upload-20261025.json'
```
