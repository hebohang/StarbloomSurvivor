# 微信开发版本 1.1.0.20261023

2026-10-23 按用户要求上传成功（微信 CLI `upload` 返回成功、退出码 0）。这是开发版本上传，未提交审核或正式发布，未自动设为体验版。

- 版本：`1.1.0.20261023`
- 上传目录：`Dist/WeChat-Upload-20261023`
- CLI 总包：18,907,473 字节；主包：273,056 字节。
- 配套引擎实现提交：`ce8bc88e300507628c97af35b3d593feb7bdbc34`；同步目标为引擎 `main` 与 `mechanic-girl-lab`。
- 内容包括 iOS Jiterpreter/原生函数参数信息兼容、菜单前完整预下载、加载/内存优化、地形查询优化、启动及好友榜原始错误诊断。
- 上传回执保存在引擎 `out/agent/starbloom-wechat-upload-1.1.0.20261023.json`。构建缓存、Dist、回执及本地 AppID 配置不提交。

验证：

- `build-only PASS`：由当前源文件重新导出微信包，18 个 ES2019 文件检查通过；C# 与资源未再改动，复用此前通过的 Wasm/内容产物。
- `static-check PASS`：新上传包的 manifest 570 项与已完成回归的 `WeChat-Friends-Final-20261023` 完全一致，并重新校验每个实际文件的字节数和 SHA256。因此复用该完全相同运行包的 `test-layer PASS`，不重复扩大测试。
- 既有 `test-layer PASS`：iOS 函数表/零 arity 条件下完整手机与战斗/四区回归，以及好友榜授权失败诊断和重试恢复。具体命令见 [iOS 兼容修复](WeChat-iOSInterop-20261023.md) 和 [好友榜诊断](WeChat-Friends-20261023.md)。
- 既有 `unit-test PASS`：地形边缘/坡道等 111,050 项与旧算法一致；下载、内存、运行时补丁、好友榜故障用例。
- `runtime-manual PASS`：此前用户反馈 iPhone 已能启动，记录见好友榜诊断文档；不代表所有机型覆盖。真实好友榜仍需完成平台隐私用途声明并真机复测，已记录错误码 1026，未把后台配置问题写成代码修复完成。

本次精确构建及上传命令（引擎根目录）：

```powershell
$env:HE_ENGINE_ROOT='C:/WorkSpace/HEngineDev'
$node='C:/Users/51906/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$project='C:/WorkSpace/HEngineProjects/StarbloomSurvivor'
$run='out/agent/build-publish/0B23D830D66A/wechat/content/20261023-020150-0305'
& $node "$project/Tools/ExportWeChat.cjs" "$run/content" "$run/managed/wwwroot/_framework" "$project/Dist/WeChat-Upload-20261023"
& $node Tools/Build/WeChatJavaScript.cjs "$project/Dist/WeChat-Upload-20261023"
& 'E:/Program Files (x86)/Tencent/微信web开发者工具/wechatidecli.cmd' upload --project 'C:/WorkSpace/HEngineProjects/StarbloomSurvivor/Dist/WeChat-Upload-20261023' --version '1.1.0.20261023' --desc '修复 iPhone 启动兼容、优化加载和地形查询，完善好友榜错误诊断' --info-output 'C:/WorkSpace/HEngineDev/out/agent/starbloom-wechat-upload-1.1.0.20261023.json'
```
