2026-05-22
适配 nanobot-webui-main2.0 接入 nanobot-main2.0，完成 session、subagent、ws 第一批兼容，调整 CLI/WebUI 启动脚本，接入 win_ssh_linux 与 open_html 工具，修复配置模型重建、MCP 清理阶段 CancelledError；修复 CLI 流式回答问题，包括累计快照去重，以及 Windows 终端下关闭 Rich Live 重绘、改为直写增量以消除长回答时的重复刷屏。
