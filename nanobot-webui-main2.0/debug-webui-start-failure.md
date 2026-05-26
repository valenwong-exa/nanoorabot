[OPEN] webui-start-failure

## 用户症状
- 运行 `start_webui_dba1.bat` 后前端构建成功，脚本输出 `Done. Open http://127.0.0.1:18780/`
- 但 WebUI 实际没有成功启动

## 当前环境
- OS: Windows
- Project: `e:\nanobot-main\nanobot-webui-main2.0`

## 初始假设
- 假设 1: `start` 启动的新进程立即退出，批处理没有等待或暴露错误信息
- 假设 2: `nanobot-webui.exe` 启动时因配置、依赖或导入错误崩溃
- 假设 3: 端口检查逻辑没有发现旧进程冲突，导致新服务启动失败
- 假设 4: 工作目录或相对路径在 `start` 子进程中不一致，导致运行时找不到资源
- 假设 5: 启动脚本本身成功返回，但服务监听在别的地址/端口，页面访问目标不对

## 证据计划
- 先复现并检查 `18780` 端口监听情况
- 直接运行 `nanobot-webui.exe` 收集前台报错
- 如有必要，再对 bat 增加最小化启动日志/错误落盘
