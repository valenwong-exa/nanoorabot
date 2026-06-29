# 建议的安装方法 / Recommended Installation Method

You can use AI to translate this file into your language if needed.

## 适用范围 / Scope

本文档面向一台全新的 Windows 机器，说明如何从当前发布源码包正确安装并启动项目。  
This document targets a fresh Windows machine and explains how to install and start the project from the current release source package.

当前文档适配的发布结构是：

```text
E:\nanoorabot
|-- INSTALL.md
|-- runtime
|   |-- config.webui.json
|   |-- oracle_config.json
|   |-- tool_policy.json
|   |-- dangerous_tool_policy.json
|   `-- webui_config.json
|-- start_webui_dba1.bat
|-- start_cli_dba1.bat
|-- nanobot-main2.2
`-- nanobot-webui-main2.0
```

如果你把发布包放到别的盘符或目录，也可以，下面命令中的路径按你的实际位置替换即可。  
If you put the release package in another drive or folder, simply replace the example paths below with your real paths.

## 项目说明 / Package Overview

当前发布包由两个源码目录组成：

- `nanobot-main2.2`
  - nanobot 核心源码
  - 当前包版本是 `nanobot-ai==0.2.2`
- `nanobot-webui-main2.0`
  - WebUI 源码
  - 当前包版本是 `nanobot-webui==0.2.6`

说明：

- 本包是源码安装方式，不是单文件 exe。
- 首次部署需要安装 Python 和 Node.js。
- 本文档推荐使用 `python -m venv`，因为更贴近当前发布包结构和启动方式。
- 当前发布仓库中虽然带有 bat 文件，但不同机器和不同目录结构下往往仍需调整路径；因此本文档主线采用命令行手工安装与启动，最稳妥。

## 前置要求 / Prerequisites

建议自行提前安装好以下环境：  
It is recommended to install the following software beforehand:

- Python `>= 3.11`
- Node.js `>= 20`
- npm

例如：

```powershell
python --version
node --version
npm --version
```

## 推荐安装方式：venv / Recommended Method: venv

下面示例假设发布包根目录为 `D:\nanoorabot`。  
The examples below assume the release package root is `D:\nanoorabot`.

### 1. 创建 Python 虚拟环境

推荐把虚拟环境创建在 `nanobot-main2.2` 目录下，这样更贴近当前脚本约定。

```powershell
cd /d D:\nanoorabot\nanobot-main2.2
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
```

### 2. 安装 Python 依赖

先安装核心源码，再安装 WebUI 源码：

```powershell
cd /d D:\nanoorabot\nanobot-main2.2
.\.venv\Scripts\python.exe -m pip install -e .

cd /d D:\nanoorabot\nanobot-webui-main2.0
D:\nanoorabot\nanobot-main2.2\.venv\Scripts\python.exe -m pip install -e .
```

说明：

- `nanobot-webui` 的依赖里声明了 `nanobot-ai==0.2.0`，但你随后使用本地 `nanobot-main2.2` 的 editable 安装，最终会绑定到本地源码版本 `0.2.2`，这是正常行为。
- 推荐这两个项目共用同一个 `.venv`，避免环境分裂。

### 3. 验证 Python 包绑定

执行：

```powershell
D:\nanoorabot\nanobot-main2.2\.venv\Scripts\python.exe -m pip show nanobot-ai
D:\nanoorabot\nanobot-main2.2\.venv\Scripts\python.exe -m pip show nanobot-webui
```

重点确认：

- `nanobot-ai` 的 `Editable project location` 指向 `D:\nanoorabot\nanobot-main2.2`
- `nanobot-webui` 的 `Editable project location` 指向 `D:\nanoorabot\nanobot-webui-main2.0`

### 4. 构建前端

```powershell
cd /d D:\nanoorabot\nanobot-webui-main2.0\web
npm install --legacy-peer-deps
npm run build
```

### 5. 同步前端产物到后端静态目录

当前工程约定使用 `robocopy /MIR` 同步前端产物：

```powershell
cd /d D:\nanoorabot\nanobot-webui-main2.0
robocopy web\dist webui\web\dist /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP
```

同步完成后，至少确认以下文件存在：

```text
D:\nanoorabot\nanobot-webui-main2.0\web\dist\index.html
D:\nanoorabot\nanobot-webui-main2.0\webui\web\dist\index.html
```

## 运行时配置 / Runtime Configuration

当前发布包的运行时配置位于根目录 `runtime` 下，而不是旧版本的 `nanobot-runtime\config.json`。

需要重点确认以下文件：

- `D:\nanoorabot\runtime\config.webui.json`
- `D:\nanoorabot\runtime\oracle_config.json`
- `D:\nanoorabot\runtime\tool_policy.json`
- `D:\nanoorabot\runtime\dangerous_tool_policy.json`
- `D:\nanoorabot\runtime\webui_config.json`

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

如果你的工作区不在默认位置，请务必把下面启动命令中的 `--workspace` 改成你自己的实际工作区路径。  
If your workspace is not in the default location, make sure to replace the `--workspace` path in the startup command below.

## 启动 WebUI / Start the WebUI

推荐直接使用命令行启动，这样可以在控制台实时看到日志。  
It is recommended to start the WebUI from the command line so that you can see live logs in the console.

```powershell
cd /d D:\nanoorabot\nanobot-webui-main2.0

D:\nanoorabot\nanobot-main2.2\.venv\Scripts\python.exe -m webui `
  --host 0.0.0.0 `
  --port 18780 `
  --workspace "D:\nanoorabot\dba1" `
  --config "D:\nanoorabot\runtime\config.webui.json" `
  --oracle-config "D:\nanoorabot\runtime\oracle_config.json" `
  --tool-policy "D:\nanoorabot\runtime\tool_policy.json" `
  --log-level DEBUG
```

如果你不使用 PowerShell 的反引号续行，也可以写成一行命令。  
If you do not want to use PowerShell line continuation, you can write the command in one line.

浏览器访问：

```text
http://127.0.0.1:18780
```

默认登录账号：

```text
admin / nanobot
```

## 启动 CLI（可选） / Start the CLI (Optional)

如果你只想启动命令行 agent，可以执行：

```powershell
cd /d D:\nanoorabot\nanobot-main2.2

.\.venv\Scripts\nanobot.exe agent `
  --config "D:\nanoorabot\runtime\config.webui.json" `
  --workspace "D:\nanoorabot\dba1"
```

## 关于 bat 文件 / About the bat Files

当前发布包中带有以下 bat 文件：

- `start_webui_dba1.bat`
- `start_cli_dba1.bat`

但请注意：

- 这些 bat 文件在不同机器、不同目录结构下通常仍需手工检查和修改路径。
- 建议先按本文档使用命令行安装和启动，确认完全正常后，再根据自己的机器路径调整 bat 文件。

## 常见问题 / FAQ

### 1. 打开页面只有后端，没有前端界面

原因通常是没有完成以下步骤之一：

- 没有执行 `npm run build`
- 没有把 `web\dist` 同步到 `webui\web\dist`

### 2. 启动时报端口占用

说明 `18780` 已被其他进程占用。

解决方法：

- 改用其他端口
- 或手工结束占用该端口的进程

### 3. 启动后可以登录，但聊天不可用

通常是配置文件中缺少有效模型配置，或者 API Key / Base URL 不正确。

请重点检查：

- `runtime\config.webui.json`
- `providers`
- `agents.defaults.model`
- 网络连通性

### 4. Oracle 相关功能不可用

请重点检查：

- `runtime\oracle_config.json` 是否存在且内容正确
- SQLcl 是否已按你的环境正确安装
- 相关数据库连接名是否配置正确

### 5. bat 文件不能直接在新机器运行

这是因为 bat 文件中的路径、工作区、端口、Python 解释器位置，经常和新机器不一致。

在新机器上建议：

- 先按本文档中的命令手动启动
- 等手工命令已经完全跑通后，再回头修改 bat 文件


