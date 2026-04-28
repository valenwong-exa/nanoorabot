# 建议的安装方法 / Recommended Installation Method

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

## 项目配置 / Project Configuration

1. **指定主目录 / Set the Home Directory**  
   指定好项目的主目录路径。  
   Specify the home directory path for your project.

2. **提供环境信息 / Provide Environment Info**  
   将上述环境信息告知 AI，并明确确认你要使用 **uv** 还是 **conda** 作为包管理工具。  
   Share the above environment details with the AI, and explicitly confirm whether you want to use **uv** or **conda** as your package manager.

3. **制定安装步骤 / Generate Installation Steps**  
   让 AI 阅读项目的 `README` 文件后，为你制定详细的安装步骤。  
   Have the AI read the project's `README` and formulate detailed installation steps for you.

## 使用 Vibe Coding 工具来进行安装/ Using Vibe Coding Tools to install

如果你正在使用 vibe coding 工具，直接让 AI 工具帮你完成安装即可!!! 尤其是DBA
If you are using a vibe coding tool, simply let the AI tool handle the installation for you. Especially for DBA !

把目录准备好，安装好基础软件后，把基础软件的配置（python，conda..）准备好环境文本。
用AI编程软件打开根目录。
让AI编程软件阅读，你的环境文本，阅读INSTALL.md 
然后进行安装。
当然，你如果想手工安装也可以。

# 安装与启动说明

本文档面向一台全新的 Windows 机器，说明如何从当前源码包正确安装并启动项目。

适用目录结构：

```text
E:\nanobot-main
|-- INSTALL.md
|-- nanobot-runtime
|-- nanobot-015post1
`-- nanobot-webui-main
```

如果你把发布包放到别的盘符或目录，也可以，下面命令中的路径按你的实际位置替换即可。

## 1. 项目说明

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
- `start_015post_webui.bat` 里带有原机器的固定路径。
- 在异机上，建议先按本文档使用命令行完成安装和启动；如果要继续用这些 bat，请先把里面的路径改成新机器的实际路径。

## 2. 前置条件

请先准备：

1. Windows 10 或 Windows 11
2. Python 3.12
3. Node.js 20 LTS 或更高版本
4. 以下二选一：
   - `uv`
   - `conda` 或 `miniconda`

建议额外检查：

```powershell
python --version
node --version
npm --version
uv --version
conda --version
```

说明：

- `uv` 和 `conda` 只需要选择一种方式。
- 前端构建使用 `npm`，因此无论用 `uv` 还是 `conda`，都需要 Node.js。

## 3. 建议准备的目录

建议单独准备一个运行时目录，用来放配置文件和工作区，不要直接写进源码目录。

示例：

```text
E:\nanobot-runtime
|-- config
|   `-- config.json
`-- workspace
```

后续本文档默认使用：

- 配置文件：`E:\nanobot-runtime\config\config.json`
- 工作区：`E:\nanobot-runtime\workspace`

你也可以换成自己的目录。

## 4. 首次部署前要知道的事

### 4.1 WebUI 需要先构建前端

当前源码模式下，WebUI 运行时读取的是：

```text
nanobot-webui-main\webui\web\dist
```

因此首次部署必须先执行前端构建，并把 `web\dist` 同步到 `webui\web\dist`。

### 4.2 配置文件建议用 `nanobot onboard` 生成

如果新机器上没有现成的 `config.json`，建议先执行：

```powershell
nanobot onboard --config E:\nanobot-runtime\config\config.json --workspace E:\nanobot-runtime\workspace
```

该命令会初始化配置和工作区模板。

初始化完成后，请手工编辑 `config.json`，填入实际要使用的模型提供商配置，例如：

- OpenAI
- Azure OpenAI
- DeepSeek
- Anthropic
- GitHub Copilot

如果没有可用模型配置，WebUI 虽然可能能启动，但实际对话能力不可用。

## 5. 方案 A：使用 uv 安装

### 5.1 创建虚拟环境

在 `nanobot-webui-main` 目录下创建独立环境：

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
uv venv .venv --python 3.12
```

### 5.2 安装 WebUI 和本地 nanobot 源码

```powershell
uv pip install --python .venv\Scripts\python.exe -e .
uv pip install --python .venv\Scripts\python.exe -e ..\nanobot-015post1
```

说明：

- 第一条安装 WebUI 源码。
- 第二条把 `nanobot-ai` 绑定到本地 `nanobot-015post1`。
- 如果日志里出现“先卸载再安装同版本”的提示，这是正常现象。

如果你想避免 `uv` 的硬链接 warning，可以额外加上：

```powershell
set UV_LINK_MODE=copy
```

或者把上面的安装命令改成带 `--link-mode=copy`。

### 5.3 构建前端

```powershell
cd /d E:\nanobot-main\nanobot-webui-main\web
npm ci
npm run build
```

### 5.4 同步前端产物到后端静态目录

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
if exist webui\web\dist rmdir /s /q webui\web\dist
powershell -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -Recurse -Force 'web\dist' 'webui\web\'"
```

### 5.5 配置初始化（重要）

**情况 A：全新安装**
> **注意**：`config.json` 必须先通过 `nanobot onboard` 初始化。如果不初始化直接启动，程序将缺少基础配置，导致无法正常调用模型。

执行以下命令，按照提示输入 API Key 等信息，完成初始化：
```cmd
.venv\Scripts\nanobot.exe onboard --config E:\nanobot-runtime\config\config.json --workspace E:\nanobot-runtime\workspace\mydba1
```

（如果是异机部署，请根据新机器的实际盘符和路径替换 `E:\nanobot-runtime\...`）

**情况 B：复用已有配置**
> 如果你已经有备份好的 `config.json` 和 `workspace`（如 `dba1`）目录，**请直接将它们拷贝到目标机器的对应路径下，完全跳过此 `onboard` 步骤**，直接进入下一步启动 WebUI。

### 5.6 启动 WebUI

推荐先以前台方式启动：

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
.venv\Scripts\nanobot.exe webui start --host 127.0.0.1 --port 18780 --workspace E:\nanobot-runtime\workspace\dba1 --config E:\nanobot-runtime\config\config.json --webui-only --log-level INFO
```

浏览器访问：

```text
http://127.0.0.1:18780
```

说明：

- `--webui-only` 适合“只启动 WebUI 面板和 WebSocket 聊天”的场景。
- 如果你希望同一个进程同时启动 IM 通道和 heartbeat，不要加 `--webui-only`。

## 6. 方案 B：使用 conda 安装

### 6.1 创建 conda 环境

```powershell
conda create -n nanobot-webui python=3.12 -y
conda activate nanobot-webui
```

### 6.2 安装 Python 依赖

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
python -m pip install -e ..\nanobot-015post1
```

说明：

- 这里同样会把 `nanobot-ai` 切换为本地源码版本。
- 如果 pip 先装了依赖里的同版本，再被本地 editable 覆盖，属于正常行为。

### 6.3 构建前端

```powershell
cd /d E:\nanobot-main\nanobot-webui-main\web
npm ci
npm run build
```

### 6.4 同步前端产物到后端静态目录

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
if exist webui\web\dist rmdir /s /q webui\web\dist
powershell -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -Recurse -Force 'web\dist' 'webui\web\'"
```

### 6.5 配置初始化（重要）

**情况 A：全新安装**
> **注意**：`config.json` 必须先通过 `nanobot onboard` 初始化。如果不初始化直接启动，程序将缺少基础配置，导致无法正常调用模型。

执行以下命令，按照提示输入 API Key 等信息，完成初始化：

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
nanobot onboard --config E:\nanobot-runtime\config\config.json --workspace E:\nanobot-runtime\workspace\mydba1
```

（如果是异机部署，请根据新机器的实际盘符和路径替换 `E:\nanobot-runtime\...`）

**情况 B：复用已有配置**
> 如果你已经有备份好的 `config.json` 和 `workspace`（如 `dba1`）目录，**请直接将它们拷贝到目标机器的对应路径下，完全跳过此 `onboard` 步骤**，直接进入下一步启动 WebUI。

### 6.6 启动 WebUI

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
nanobot webui start --host 127.0.0.1 --port 18780 --workspace E:\nanobot-runtime\workspace\mydba1 --config E:\nanobot-runtime\config\config.json --webui-only --log-level INFO
```

浏览器访问：

```text
http://127.0.0.1:18780
```

## 7. 推荐的首次验证

安装完成后，建议依次验证：

1. Python 环境创建成功
2. `nanobot-ai` 来自本地 `nanobot-015post1`
3. `npm run build` 成功
4. `webui\web\dist\index.html` 已生成
5. `nanobot onboard` 能生成配置和工作区
6. `nanobot webui start` 能正常启动
7. 浏览器可打开登录页

## 8. 如何确认当前绑定的是本地 015post1

### uv 环境

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
uv pip show --python .venv\Scripts\python.exe nanobot-ai
```

### conda 环境

```powershell
pip show nanobot-ai
```

如果输出里看到类似：

```text
Location: ...
Editable project location: E:\nanobot-main\nanobot-015post1
```

说明绑定正确。

## 9. 常见问题

### 9.1 打开页面只有后端，没有前端界面

原因通常是没有完成以下步骤之一：

- 没有执行 `npm ci`
- 没有执行 `npm run build`
- 没有把 `web\dist` 同步到 `webui\web\dist`

### 9.2 启动报端口占用

说明 `18780` 已被其他进程占用。

可改成别的端口，例如：

```powershell
nanobot webui start --port 18781 ...
```

### 9.3 启动后可以登录，但聊天不可用

通常是配置文件中缺少有效模型配置，或者 API Key / Base URL 不正确。

请检查：

- `providers`
- `agents.defaults.model`
- 网络连通性

### 9.4 旧 bat 文件不能直接在新机器运行

这是因为现有 bat 文件写死了原机器路径，例如：

- `E:\nanobot-main\nanobot-015post1`
- `E:\nanobot-main\nanobot-webui-main`
- `E:\nanobot-main\dba1`

在新机器上需要先改成新路径，或者直接按本文档中的命令手动启动。

## 10. 推荐启动命令汇总

### 内置的workspace dba1 - Danny

可以放置在E:\nanobot-runtime\workspace\dba1

### uv

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
.venv\Scripts\nanobot.exe webui start --host 127.0.0.1 --port 18780 --workspace E:\nanobot-runtime\workspace\dba1 --config E:\nanobot-runtime\config\config.json --webui-only --log-level INFO
```

### conda

```powershell
cd /d E:\nanobot-main\nanobot-webui-main
nanobot webui start --host 127.0.0.1 --port 18780 --workspace E:\nanobot-runtime\workspace\dba1 --config E:\nanobot-runtime\config\config.json --webui-only --log-level INFO
```

## 11. 如果要继续使用现成 bat

可修改以下文件中的路径后再使用：

- `nanobot-015post1\start_015post_webui.bat`
- `nanobot-webui-main\switch_webui_to_015post.bat`
- `nanobot-webui-main\start_webui_dba1.bat`

建议修改项包括：

- 源码根目录
- 虚拟环境目录
- 工作区路径
- 配置文件路径
- 端口号

## 12. 登录

默认密码 admin/nanobot

## 13. 申请API KEY

自行申请API KEY 配置并使用
