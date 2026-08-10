# 建议的安装方法（macOS） / Recommended Installation Method (macOS)

You can use AI to translate this file into your language if needed.

## 适用范围 / Scope

本文档面向一台全新的 macOS 机器，说明如何从当前发布源码目录正确安装并启动项目。  
This document targets a fresh macOS machine and explains how to install and start the project from the current release source directory.

本文档按下面这台机器环境编写：

- macOS `26.5.1`
- Kernel: `Darwin 25.5.0`
- CPU architecture: `x86_64`
- Python: `3.13.5`
- 安装根目录 / Install root: `/Users/hx/git`

当前文档适配的发布结构是：

```text
/Users/hx/git/nanoorabot
|-- INSTALL.md
|-- INSTALL_mac.md
|-- runtime
|   |-- config.webui.json
|   |-- oracle_config.json
|   |-- tool_policy.json
|   |-- dangerous_tool_policy.json
|   `-- webui_config.json
|-- nanobot-main3.0
|-- nanobot-webui-main2.0
|   |-- start_cli_dba1.bat
|   `-- start_webui_dba1_main3.bat
|-- SenseVoice-main
`-- dba1
```

如果你把目录放到别的位置，也可以，下面命令中的路径按你的实际位置替换即可。  
If you place the package in another folder, simply replace the example paths below with your real paths.

## 项目说明 / Package Overview

当前发布包由两个源码目录组成：

- `nanobot-main3.0`
  - nanobot 核心源码
  - 当前包版本是 `nanobot-ai==0.3.0`
- `nanobot-webui-main2.0`
  - WebUI 源码
  - 当前包版本是 `nanobot-webui==0.2.6`

说明：

- 本包是源码安装方式，不是单文件 app。
- 首次部署需要安装 Python 和 Node.js。
- 本文档推荐使用 `python -m venv`，因为更贴近当前发布包结构和启动方式。
- 当前发布包根目录中虽然带有 Windows 的 `.bat` 文件，但它们不适用于 macOS；本文档主线采用命令行手工安装与启动，最稳妥。

## 前置要求 / Prerequisites

建议自行提前安装好以下环境：  
It is recommended to install the following software beforehand:

- Python `>= 3.11`
- Node.js `>= 20`
- npm
- SQLcl
- Xcode Command Line Tools

如未安装 Xcode Command Line Tools，可先执行：

```bash
xcode-select --install
```

例如，先确认版本：

```bash
python3 --version
node --version
npm --version
```

如果你已经把 SQLcl 放到了例如 `/Users/hx/sqlcl`，建议把它加入当前用户的 `PATH`，这样可以直接执行 `sql` 命令。  
If SQLcl is installed at a path such as `/Users/hx/sqlcl`, it is recommended to add it to the current user's `PATH` so that you can run `sql` directly.

例如：

```bash
echo 'export PATH=/Users/hx/sqlcl/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
which sql
sql -version
```

如果你使用的是 `bash`，把上面的 `~/.zshrc` 改成 `~/.bash_profile` 或 `~/.bashrc` 即可。

本文档假设你当前 `python3 --version` 返回的是：

```text
Python 3.13.5
```

## 推荐安装方式：venv / Recommended Method: venv

下面示例假设发布包根目录为 `/Users/hx/git/nanoorabot`。  
The examples below assume the release package root is `/Users/hx/git/nanoorabot`.

### 1. 创建 Python 虚拟环境

推荐把两个项目共用的虚拟环境创建在 `nanobot-webui-main2.0` 目录下，与当前 3.0 启动结构保持一致。

```bash
cd /Users/hx/git/nanoorabot/nanobot-webui-main2.0
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip setuptools wheel
```

### 2. 安装 Python 依赖

按下面顺序安装：

1. 先安装核心源码
2. 再安装 WebUI 源码

```bash
cd /Users/hx/git/nanoorabot/nanobot-main3.0
/Users/hx/git/nanoorabot/nanobot-webui-main2.0/.venv/bin/python -m pip install -e .

cd /Users/hx/git/nanoorabot/nanobot-webui-main2.0
./.venv/bin/python -m pip install -e .
```

说明：

- `nanobot-webui` 与核心项目现在统一声明使用 `nanobot-ai==0.3.0`，不再需要重复安装核心源码。
- 仍建议先安装本地核心，再安装 WebUI，确保使用发布包内的定制源码。
- 推荐这两个项目共用同一个 `.venv`，避免环境分裂。

关于语音功能：

- 默认安装只包含 `nanobot` 和 `WebUI` 的必要依赖，**不包含语音识别相关依赖**。
- 如果客户当前机器不需要语音功能，保持默认安装即可，`nanobot` 与 `WebUI` 主功能不会受影响。
- 如果后续需要启用语音功能，再按需额外安装 voice 依赖即可：

```bash
cd /Users/hx/git/nanoorabot/nanobot-webui-main2.0
./.venv/bin/python -m pip install -e ".[voice]"
```

- 启用语音时，还需要额外准备 `SenseVoice-main` 目录。
- 请使用 `nanobot-webui-main2.0/.venv` 安装 voice 依赖，详细步骤请参考发布包中的 `nanobot-webui-main2.0/INSTALL_voice.md`。

### 3. 验证 Python 包绑定

执行：

```bash
/Users/hx/git/nanoorabot/nanobot-webui-main2.0/.venv/bin/python -m pip show nanobot-ai
/Users/hx/git/nanoorabot/nanobot-webui-main2.0/.venv/bin/python -m pip show nanobot-webui
```

重点确认：

- `nanobot-ai` 的 `Editable project location` 指向 `/Users/hx/git/nanoorabot/nanobot-main3.0`
- `nanobot-webui` 的 `Editable project location` 指向 `/Users/hx/git/nanoorabot/nanobot-webui-main2.0`

再执行 `python -m pip check`，应显示 `No broken requirements found.`。如果仍显示旧的 `0.2.2` 依赖，请确认使用的是当前发布包中的 WebUI 源码并重新执行 editable 安装。

### 4. 构建前端

```bash
cd /Users/hx/git/nanoorabot/nanobot-webui-main2.0/web
npm install --legacy-peer-deps
npm run build
```

### 5. 同步前端产物到后端静态目录

macOS 下推荐使用 `rsync` 同步前端产物：

```bash
cd /Users/hx/git/nanoorabot/nanobot-webui-main2.0
rsync -a --delete web/dist/ webui/web/dist/
```

同步完成后，至少确认以下文件存在：

```text
/Users/hx/git/nanoorabot/nanobot-webui-main2.0/web/dist/index.html
/Users/hx/git/nanoorabot/nanobot-webui-main2.0/webui/web/dist/index.html
```

## 运行时配置 / Runtime Configuration

当前发布包的运行时配置位于根目录 `runtime` 下，而不是旧版本的 `nanobot-runtime/config.json`。

需要重点确认以下文件：

- `/Users/hx/git/nanoorabot/runtime/config.webui.json`
- `/Users/hx/git/nanoorabot/runtime/oracle_config.json`
- `/Users/hx/git/nanoorabot/runtime/tool_policy.json`
- `/Users/hx/git/nanoorabot/runtime/dangerous_tool_policy.json`
- `/Users/hx/git/nanoorabot/runtime/webui_config.json`

GitHub 发布目录中的敏感字段已经清空。首次启动前，请在本机补充模型 API Key、频道 Secret/Token 和 Oracle 密码等实际值，并避免把填写后的凭据重新提交到 Git。

其中最重要的是：

- `config.webui.json`
  - 模型配置
  - `agents.defaults.model`
  - `workspace` 相关路径
  - WebUI 端口和基础配置
- `oracle_config.json`
  - Oracle 连接配置
- `tool_policy.json`
  - 工具策略配置
- `dangerous_tool_policy.json`
  - 危险命令策略配置

在 macOS 上部署时，`runtime/config.webui.json` 里的路径也必须全部检查一遍，不能保留 Windows 路径。  
When deploying on macOS, review every path in `runtime/config.webui.json` and replace any Windows path with the actual macOS path.

今天实测最容易遗漏的就是：

- `agents.defaults.workspace`
- `tools.mcpServers.oracle-sqlcl.command`
- 其他 `mcpServers` 中脚本文件的 `command` / `args`

例如下面这些 Windows 路径都必须改成 macOS 路径：

```text
E:\sqlcl\bin\sql.exe
E:\nanobot-main\dba1\skills\ora-rag-server\doc_vector_search.py
E:\nanobot-main\dba1\skills\linux-hardware-check\server.py
```

对应 macOS 上应改成类似：

```text
/Users/hx/sqlcl/bin/sql
/Users/hx/git/nanoorabot/dba1/skills/ora-rag-server/doc_vector_search.py
/Users/hx/git/nanoorabot/dba1/skills/linux-hardware-check/server.py
```

如果 `config.webui.json` 中仍然保留 Windows 路径，WebUI 虽然可能能启动，但相关 MCP 服务会在启动时直接报错。

另外，建议保证当前用户的 `PATH` 中能直接找到 SQLcl：

```bash
which sql
sql -version
```

如果你的工作区不在默认位置，请务必把下面启动命令中的 `--workspace` 改成你自己的实际工作区路径。  
If your workspace is not in the default location, make sure to replace the `--workspace` path in the startup command below.

## 启动 WebUI / Start the WebUI

推荐直接使用命令行启动，这样可以在控制台实时看到日志。  
It is recommended to start the WebUI from the command line so that you can see live logs in the console.

```bash
cd /Users/hx/git/nanoorabot/nanobot-webui-main2.0
export PYTHONPATH="/Users/hx/git/nanoorabot/nanobot-main3.0${PYTHONPATH:+:$PYTHONPATH}"

./.venv/bin/python -m webui \
  --host 0.0.0.0 \
  --port 18780 \
  --workspace "/Users/hx/git/nanoorabot/dba1" \
  --config "/Users/hx/git/nanoorabot/runtime/config.webui.json" \
  --oracle-config "/Users/hx/git/nanoorabot/runtime/oracle_config.json" \
  --tool-policy "/Users/hx/git/nanoorabot/runtime/tool_policy.json" \
  --log-level DEBUG
```

浏览器访问：

```text
http://127.0.0.1:18780
```

也可以直接在 macOS 中打开：

```bash
open http://127.0.0.1:18780
```

默认登录账号：

```text
admin / nanobot
```

## 启动 CLI（可选） / Start the CLI (Optional)

如果你只想启动命令行 agent，可以执行：

```bash
cd /Users/hx/git/nanoorabot/nanobot-main3.0
export PYTHONPATH="/Users/hx/git/nanoorabot/nanobot-main3.0${PYTHONPATH:+:$PYTHONPATH}"

/Users/hx/git/nanoorabot/nanobot-webui-main2.0/.venv/bin/python -m nanobot agent \
  --config "/Users/hx/git/nanoorabot/runtime/config.webui.json" \
  --workspace "/Users/hx/git/nanoorabot/dba1"
```

如果 `nanobot` 可执行文件没有生成，也可以直接使用：

```bash
/Users/hx/git/nanoorabot/nanobot-webui-main2.0/.venv/bin/python -m nanobot agent \
  --config "/Users/hx/git/nanoorabot/runtime/config.webui.json" \
  --workspace "/Users/hx/git/nanoorabot/dba1"
```

## 关于根目录中的 bat 文件 / About the bat Files in the Package Root

当前发布结构在 `nanobot-webui-main2.0` 中带有以下 Windows 专用启动模板：

- `nanobot-webui-main2.0/start_webui_dba1_main3.bat`
- `nanobot-webui-main2.0/start_cli_dba1.bat`

但请注意：

- 这些 `.bat` 文件不适用于 macOS。
- 在 macOS 上请按本文档中的 `bash/zsh` 命令手工安装和启动。

## 常见问题 / FAQ

### 1. 打开页面只有后端，没有前端界面

原因通常是没有完成以下步骤之一：

- 没有执行 `npm run build`
- 没有把 `web/dist` 同步到 `webui/web/dist`

### 2. 启动时报端口占用

说明 `18780` 已被其他进程占用。

解决方法：

- 改用其他端口
- 或手工结束占用该端口的进程

例如：

```bash
lsof -iTCP:18780 -sTCP:LISTEN
kill <PID>
```

### 3. 启动后可以登录，但聊天不可用

通常是配置文件中缺少有效模型配置，或者 API Key / Base URL 不正确。

请重点检查：

- `runtime/config.webui.json`
- `providers`
- `agents.defaults.model`
- 网络连通性

### 4. Oracle 相关功能不可用

请重点检查：

- `runtime/oracle_config.json` 是否存在且内容正确
- SQLcl 是否已按你的环境正确安装
- 相关数据库连接名是否配置正确

### 5. `oracle-sqlcl` MCP 启动失败，提示 `Connection closed`

如果日志里出现类似下面的错误：

```text
mcp.shared.exceptions.McpError: Connection closed
```

请优先检查两件事：

- `runtime/config.webui.json` 中 `oracle-sqlcl.command` 是否还是 Windows 路径
- 当前 `sqlcl` 启动 MCP 模式时使用的 Java 是否为 17 或以上

实测 `sqlcl -R 0 -mcp` 在 macOS 上同样要求 Java 17+。如果仍使用 Java 11，会报类似下面的错误：

```text
Error: SQLcl -mcp requires Java 17 and above to run.
       Found Java version 11.
       Please set JAVA_HOME to appropriate version.
```

可以先检查：

```bash
java -version
sql -version
sql -R 0 -mcp
```

如果你的机器上已经装了 Java 17，可以先显式设置：

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH="$JAVA_HOME/bin:$PATH"
```

然后再启动 WebUI。

### 6. `python3` 不是你想用的版本

如果系统里存在多个 Python，建议明确指定 `python3.13`：

```bash
cd /Users/hx/git/nanoorabot/nanobot-webui-main2.0
python3.13 -m venv .venv
./.venv/bin/python --version
```

### 7. `npm install` 失败

请优先检查：

- Node.js 版本是否太低
- 网络是否能访问 npm registry
- 是否缺少 Xcode Command Line Tools

必要时可重新执行：

```bash
xcode-select --install
```

### 8. 页面里没有语音按钮，或者语音接口返回不可用

这通常不是主系统故障，而是当前机器没有启用语音依赖。

当前发布包默认策略是：

- 默认安装不包含 voice 依赖
- 未安装语音依赖时，聊天、配置、Oracle、会话等主功能仍然正常
- 只有语音功能会保持关闭状态

如果你确实需要启用语音，请额外完成两件事：

- 安装 `nanobot-webui` 的 voice 依赖
- 准备 `SenseVoice-main` 目录

详细步骤请参考：

- `nanobot-webui-main2.0/INSTALL_voice.md`，并请使用 `nanobot-webui-main2.0/.venv` 安装 voice 依赖
