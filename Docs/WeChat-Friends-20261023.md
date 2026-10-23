# 好友排行榜不可用：保留真实错误与恢复流程

用户确认 iPhone 启动成功（`runtime-manual PASS`，用户反馈，未取得机型/版本覆盖数据），随后报告点击好友榜提示服务暂不可用。

已确认当前包 `leaderboard.enabled=true`，`game.json` 包含 `openDataContext: open-data`，目录入口 `open-data/index.js` 存在。旧代码在好友授权或开放数据域打开异常时统一显示“服务暂不可用”，且授权失败回调会丢弃微信原始错误，因此仅凭该提示**无法区分用户拒绝、平台/隐私配置、接口或画布异常**。空榜成功结果会显示“暂无好友成绩”，不走该提示。

本轮没有读取或修改微信公众平台权限/隐私设置，也没有绕过好友授权。后续真机截图已确认具体错误，见文末；尚未确认后台配置完成后的真实排行榜恢复情况。

修改：授权、能力缺失、开放数据域打开分别记录阶段；保留微信 `errMsg` 和错误码并显示弹窗；错误存入本地诊断的 `serviceError` 字段。仅对明确 auth deny/cancel 提示去小游戏设置允许好友互动；其他原因如实显示。打开失败时清理 context/visible，允许重试；授权成功后清除旧错误。开放数据域读取失败也显示实际原因，不再一律归因为权限。

候选包：`Dist/WeChat-Friends-Final-20261023`，包含上一轮已由用户确认可启动的 iOS 修复。

验证：

- `unit-test PASS`：好友榜尺寸/分页/异步隔离；授权拒绝、模拟隐私错误保留原码；能力缺失、context 异常清理状态。
- `test-layer PASS`：真实游戏包注入授权错误 103，验证弹窗与持久化错误；返回菜单后重试授权成功，可以打开真实开放域绘制脚本。测试好友数据为 fixture，并非真实好友信息。
- `test-layer PASS`：保留 iOS 函数表/零 arity 约束的完整手机、战斗与四区回归。
- `build-only PASS`：微信重新导出与 18 个 ES2019 文件；C# 未改，复用上轮 Wasm。
- `static-check PASS`：两仓库 diff 检查。

精确命令（引擎根目录）：

```powershell
$project='C:/WorkSpace/HEngineProjects/StarbloomSurvivor'
$node='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:HE_ENGINE_ROOT='C:/WorkSpace/HEngineDev'
$env:NODE_PATH='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$run='out/agent/build-publish/0B23D830D66A/wechat/content/20261023-020150-0305'
$package="$project/Dist/WeChat-Friends-Final-20261023"
& $node Tools/Build/TestWeChatLeaderboard.cjs
& $node "$project/Tools/ExportWeChat.cjs" "$run/content" "$run/managed/wwwroot/_framework" $package
& $node Tools/Build/WeChatJavaScript.cjs $package
& $node "$project/Tools/TestWeChatMobileGame.cjs" $package --ios-interop --leaderboard-failure
& $node "$project/Tools/TestWeChatMobileGame.cjs" $package --ios-interop
git diff --check
git -C $project diff --check
```

证据：引擎 `out/agent/starbloom-wechat-mobile-test/leaderboard-authorization-failure.json`、`out/agent/wechat-friends-20261023.log`。接下来需要真机弹窗的原始错误，才能确定是代码还是账号/用户侧配置。

扫码预览生成 PASS，总包 18,907,473 字节，未正式发布；二维码在引擎 `out/agent/starbloom-wechat-friends-preview-20261023.png`。

```powershell
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' preview --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Friends-Final-20261023' --qr-format image --qr-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-friends-preview-20261023.png' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-friends-preview-20261023.json'
```

## 真机原因确认：1026

用户提供新弹窗：`authorize:fail please go to mp to announce your privacy usage`，错误码 `1026`。这明确指出微信公众平台尚未声明所需个人信息用途，微信在好友互动授权之前就拒绝了调用。没有授权弹窗与此一致，不能归因为用户当次拒绝。

管理员需要在小游戏后台的“设置 / 基本设置 → 服务内容声明 → 用户隐私保护指引”更新实际用途；好友排行榜涉及“微信朋友关系”，当前绘制还使用好友昵称，按后台的信息类型分组如实声明。建议使用后台提供的“隐私授权弹窗”，保存并生效后重新进入小游戏复测。

用途建议：微信朋友关系用于识别同玩好友、展示和比较最长生存时间；昵称用于在好友榜中标识玩家。当前画面没有绘制头像，不应填写并不存在的头像展示用途。其他声明项依实际信息处理填写。

配置入口参考：[小游戏 SDK 提供方的后台配置说明](https://docs.open.17m3.com/v2/client/wxminigame/groundwork.html#用户隐私保护指引设置)。本任务此前访问 mp.weixin.qq.com 被浏览器站点安全策略拒绝，因此此后台操作由用户手动完成，未尝试绕过访问限制。本次仅更新诊断记录，未改运行时代码、未重建包。
