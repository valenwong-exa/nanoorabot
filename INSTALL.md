# 建议的安装方法 / Recommended Installation Method
You can use AI to translate to Your language !!!
## 前置要求 / Prerequisites

建议自行提前安装好以下环境：  
It is recommended to install the following environments beforehand:
python >= 3.11 is OK

```powershell
C:\Users\Administrator&gt; python --version
Python 3.12.0

C:\Users\Administrator&gt; node --version
v24.4.1

C:\Users\Administrator&gt; npm --version
11.11.0

C:\Users\Administrator&gt; conda --version
conda 24.7.1
```



# 安装与启动说明

本文档面向一台全新的 Windows 机器，说明如何从当前源码包正确安装并启动项目。

适用目录结构：

```text
E:\nanoorabot-main
|-- INSTALL.md
|-- nanobot-runtime
|-- nanobot-015post1
`-- nanobot-webui-main
```

如果你把发布包放到别的盘符或目录，也可以，下面命令中的路径按你的实际位置替换即可。

## 项目说明

当前发布包由两个源码目录组成：

- `nanobot-015post1`
  - 本地 nanobot 核心源码
  - 当前版本固定为 `nanobot-ai==0.1.5.post1`
- `nanobot-webui-main`
  - WebUI 源码
  - 运行时会绑定到本地 `nanobot-015post1`

说明：

- 本包是源码安装方式，不是单文件 exe。
- 首次部署需要安装 Python 和 Node.js。
- 在异机上，建议先按本文档使用命令行完成安装和启动；如果要继续用这些 bat，请先把里面的路径改成新机器的实际路径。

## 使用 conda 安装
如果你要使用venv，请让AI帮你把命令转换为venv方式
### 创建 conda 环境
本案例ROOT目录为 D:\nanoorabot-main

```
conda create -n nanobot-webui python=3.12 -y
conda activate nanobot-webui
```

### 安装 Python 依赖

```
cd /d D:\nanoorabot-main\nanobot-webui-main
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
python -m pip install -e ..\nanobot-015post1
```

说明：

- 这里同样会把 `nanobot-ai` 切换为本地源码版本。
- 如果 pip 先装了依赖里的同版本，再被本地 editable 覆盖，属于正常行为。

安装完成后，可立刻执行下面命令验证 `nanobot-ai` 是否来自本地 `nanobot-015post1`：

```
conda activate nanobot-webui
python -m pip show nanobot-ai
```

如果输出中看到类似以下内容：
```
(nanobot-webui) C:\Users\valenwang>python -m pip show nanobot-ai
Name: nanobot-ai
Version: 0.1.5.post1
Summary: A lightweight personal AI assistant framework
Home-page:
Author: nanobot contributors
Author-email:
License: MIT
Location: C:\Users\valenwang\.conda\envs\nanobot-webui\Lib\site-packages
Editable project location: D:\nanoorabot-main\nanobot-015post1
```
说明当前 WebUI 使用的就是本地源码版 `nanobot-015post1`，绑定正确。

### 构建前端

```
cd /d D:\nanoorabot-main\nanobot-webui-main\web
npm install --legacy-peer-deps
npm run build
```

### 同步前端产物到后端静态目录

两种方法，任选其一。

```powershell
cd /d D:\nanoorabot-main\nanobot-webui-main
if exist webui\web\dist rmdir /s /q webui\web\dist
powershell -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -Recurse -Force 'web\dist' 'webui\web\'"
```

```bat
@echo off
cd /d D:\nanoorabot-main\nanobot-webui-main
if exist webui\web\dist rmdir /s /q webui\web\dist
xcopy "web\dist" "webui\web\dist\" /E /I /Y
```

### 6.5 配置初始化（重要）

本次手工安装方式，建议直接修改已有运行时配置。

需要重点确认以下两个文件：

- `D:\nanoorabot-main\nanobot-runtime\config.json`
- `D:\nanoorabot-main\nanobot-webui-main\start_webui_dba1.bat`

其中最重要的是：

- 模型配置
- `workspace` 路径
- WebUI 启动路径和端口

`start_webui_dba1.bat` 里建议至少确认这些变量已经改成你的实际路径：

```bat
set "ROOT=D:\nanoorabot-main\nanobot-webui-main"
set "WEB=%ROOT%\web"
set "WEB_DIST=%WEB%\dist"
set "SERVER_DIST=%ROOT%\webui\web\dist"
set "CONFIG=D:\nanoorabot-main\nanobot-runtime\config.json"
set "WORKSPACE=D:\nanoorabot-main\nanobot-runtime\workspace\dba1"
set "PORT=18780"
set "CONDA_ENV=nanobot-webui"
```

### 启动 WebUI

双击运行：

- `D:\nanoorabot-main\nanobot-webui-main\start_webui_dba1.bat`

浏览器访问：

```text
http://127.0.0.1:18780
```

默认登录账号：

```text
admin / nanobot
```



## 常见问题

### 打开页面只有后端，没有前端界面

原因通常是没有完成以下步骤之一：

- 没有执行 `npm run build`
- 没有把 `web\dist` 同步到 `webui\web\dist`

### 启动报端口占用

说明 `18780` 已被其他进程占用。
修改端口，或者KILL进程。

### 启动后可以登录，但聊天不可用

通常是配置文件中缺少有效模型配置，或者 API Key / Base URL 不正确。

请检查：

- `providers`
- `agents.defaults.model`
- 网络连通性

### bat 文件不能直接在新机器运行

这是因为现有 bat 文件写死了原机器路径，例如：

- `E:\nanobot-main\nanobot-015post1`
- `E:\nanobot-main\nanobot-webui-main`
- `E:\nanobot-main\dba1`

在新机器上需要先改成新路径，或者直接按本文档中的命令手动启动。


