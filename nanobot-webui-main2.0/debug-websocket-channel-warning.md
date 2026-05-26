[CLOSED] websocket-channel-warning

## 用户症状
- 运行 WebUI 时日志出现告警：
- `WARNING | nanobot.channels.manager:_dispatch_outbound - Unknown channel: websocket`

## 预期
- WebUI 的 `websocket` 通道应被正确处理，不应再落入未知通道告警

## 初始假设
- 假设 1: 某处把 `websocket` 当成普通 outbound channel 发给了 `ChannelManager`，但 manager 并未注册该通道
- 假设 2: `webui` 兼容层已把输入会话切到 `websocket`，但输出路径仍沿用旧的 channel dispatch 逻辑
- 假设 3: 子任务或系统消息完成后，回传分支没有命中 WebUI 的直推 callback，而是错误回落到 manager
- 假设 4: `channel_compat` 只兼容了 session key / callback key，没有兼容 outbound dispatch 层的 channel 名称
- 假设 5: warning 来自非 WebUI 主聊天链路，而是 cron / audit / 其他辅助路径错误复用了 `websocket`

## 证据计划
- 先定位 `Unknown channel` 的唯一调用点和所有传入 `websocket` 的发送路径
- 在最小范围内对 dispatch 前的调用栈和关键参数插桩
- 复现一次告警，基于运行时证据再决定最小修复

## 运行时证据
- 已在 `nanobot.bus.queue.publish_outbound()` 和 `nanobot.channels.manager._dispatch_outbound()` 增加调试插桩。
- 最小复现脚本证明：`WebuiTurnCoordinator.handle_turn_end()` 会发布 `OutboundMessage(channel="websocket", chat_id="web:42:abc12345", metadata={"_turn_end": True, "webui": True, ...})`
- 当前 `runtime/config.webui.json` 中不存在 `channels.websocket` 配置块，因此 WebUI 进程的 `ChannelManager` 不会注册 `websocket` channel。
- 结论：WebUI turn-end / goal-state / session-update 这类 websocket outbound 在 WebUI 进程内会落到 `ChannelManager`，但 manager 没有对应 channel，于是触发 `Unknown channel: websocket`。

## 修复
- 在 `nanobot.channels.manager._dispatch_outbound()` 中，将“未注册 websocket channel 时忽略 `_runtime_model_updated`”扩展为“未注册 websocket channel 时忽略所有 websocket outbound”。
- 基于用户复现日志，又在 `unknown channel` 分支入口加了第二道保护：若当前分支已确认没有匹配 channel，且 `msg.channel == "websocket"` 且 manager 未注册 websocket，则直接跳过，不再打 warning。
- 新增回归测试，覆盖“manager 未注册 websocket channel 时，websocket outbound 被静默忽略”。

## 验证
- `tests/channels/test_channel_manager_delta_coalescing.py` 全量通过：`17 passed`

## 收尾
- 已移除 `nanobot.bus.queue.publish_outbound()` 和 `nanobot.channels.manager._dispatch_outbound()` 中为本次定位临时加入的 debug-point 插桩。
- 当前保留的仅是正式修复逻辑：当 manager 未注册 `websocket` channel 时，静默忽略对应 websocket outbound，不再打印 `Unknown channel: websocket`。
