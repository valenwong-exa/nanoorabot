# 可选安装：语音功能

本文档说明如何在 `nanobot-webui` 默认安装完成后，按需补装语音识别支持。

## 目标

- 默认安装：只安装 `nanobot` 和 `WebUI` 的必要依赖
- 默认状态：不启用语音功能，不要求存在 SenseVoice 模型目录
- 后续启用：客户需要语音时，再单独安装 voice 依赖并准备 `SenseVoice-main`

## 默认安装

平台安装文档中的 WebUI 源码安装命令默认不包含语音依赖：

```powershell
Set-Location "D:\nanoorabot\nanobot-webui-main2.0"
.\.venv\Scripts\python.exe -m pip install -e .
```

macOS / Linux：

```bash
cd /path/to/nanoorabot/nanobot-webui-main2.0
./.venv/bin/python -m pip install -e .
```

此时：

- `nanobot` 与 `WebUI` 正常可用
- 未安装语音依赖不会影响普通聊天、会话、数据库面板、配置页面等功能
- WebUI 前端不会显示语音录音入口
- 调用语音 CLI 时会给出明确提示，而不是因为缺少依赖导致主程序启动失败

## 启用语音功能

### 1. 安装 voice 依赖

请务必复用主安装阶段已经创建好的那个 Python 虚拟环境，不要另外新建一个新的 Python 环境。

本发布包的 3.0 结构默认约定：

- `nanobot-main3.0` 和 `nanobot-webui-main2.0` 共用同一个 Python 环境
- 共享虚拟环境固定放在 `nanobot-webui-main2.0/.venv`
- 安装 voice 依赖时，也安装到这个共享 `.venv` 中
- 不要装到系统 Python
- 不要装到另外单独新建的 `.venv`

通常应复用：

```text
nanobot-webui-main2.0/.venv
```

推荐做法是使用这个虚拟环境里的 `python -m pip` 安装。

Windows 示例：

```powershell
Set-Location "D:\nanoorabot\nanobot-webui-main2.0"
.\.venv\Scripts\python.exe -m pip install -e ".[voice]"
```

macOS 示例：

```bash
cd /Users/hx/git/nanoorabot/nanobot-webui-main2.0
./.venv/bin/python -m pip install -e ".[voice]"
```

OCI / Linux 示例：

```bash
cd /u01/nanoorabot/nanobot-webui-main2.0
./.venv/bin/python -m pip install -e ".[voice]"
```

如果你当前已经激活的就是这个 `.venv`，也可以直接执行：

```bash
pip install "nanobot-webui[voice]"
```

如果是源码方式，同样要确保当前使用的就是上面这个共享 `.venv`：

```bash
pip install -e ".[voice]"
```

### 2. 准备 SenseVoice-main

默认约定目录为：

```text
../SenseVoice-main
```

以当前项目目录为例，通常是：

```text
D:\nanoorabot\SenseVoice-main
```

至少需要存在以下文件：

- `SenseVoice-main/mic_test.py`
- `SenseVoice-main/model.py`

如果目录不在默认位置，可通过环境变量指定：

```powershell
$env:NANOBOT_SENSEVOICE_DIR = "D:\your-path\SenseVoice-main"
```

Linux/macOS:

```bash
export NANOBOT_SENSEVOICE_DIR=/path/to/SenseVoice-main
```

### 3. 重启 WebUI

安装完 voice 依赖并准备好 `SenseVoice-main` 后，重启 WebUI 服务。

## 安装后的验证

### WebUI 验证

- 打开 Chat 页面
- 如果语音依赖和 SenseVoice 目录都准备完成，输入框左侧会出现语音按钮
- 如果未准备完成，语音按钮不会显示

### API 验证

可访问：

```text
GET /api/voice/health
```

返回 `ok: true` 表示语音转写运行环境已就绪。

### CLI 验证

```powershell
Set-Location "D:\nanoorabot\nanobot-webui-main2.0"
D:\nanoorabot\nanobot-webui-main2.0\.venv\Scripts\python.exe -m webui.voice_cli --list-devices
```

macOS / Linux：

```bash
cd /path/to/nanoorabot/nanobot-webui-main2.0
/path/to/nanoorabot/nanobot-webui-main2.0/.venv/bin/python -m webui.voice_cli --list-devices
```

如果缺少 voice 依赖或 `SenseVoice-main`，CLI 会直接提示原因。

## 说明

- 当前 `voice` extra 包含浏览器上传转写与 SenseVoice 相关依赖
- 如果客户不需要语音功能，建议不要安装 `voice` extra
- 未安装 `voice` extra 时，主程序不会因为 `torch`、`funasr`、`sounddevice` 等缺失而启动失败
