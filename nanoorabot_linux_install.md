# Linux Quick Install Guide

You can use AI to translate this file into your language if needed.

## Scope

This document targets a fresh Linux machine and explains how to install and start the current release source package.

The release layout assumed by this guide is:

```text
/home/opc/nanoorabot
|-- INSTALL.md
|-- nanoorabot_linux_install.md
|-- runtime
|   |-- config.webui.json
|   |-- oracle_config.json
|   |-- tool_policy.json
|   |-- dangerous_tool_policy.json
|   `-- webui_config.json
|-- nanobot-main2.2
`-- nanobot-webui-main2.0
```

If your release package is stored in another directory, replace the example paths below with your actual paths.

## Package Overview

The current release contains two source folders:

- `nanobot-main2.2`
  - nanobot core source
  - current local package version: `nanobot-ai==0.2.2`
- `nanobot-webui-main2.0`
  - WebUI source
  - current local package version: `nanobot-webui==0.2.6`

Notes:

- This is a source installation, not a single binary package.
- First deployment requires Python and Node.js.
- This guide recommends `python3 -m venv` and editable install because it matches the current release structure.
- The main workflow below uses shell commands directly so you can see real-time logs in the terminal.

## Prerequisites

Install or verify:

- Python `>= 3.11`
- Node.js `>= 20`
- npm

Example:

```bash
python3 --version
node --version
npm --version
```

## 1. Create a Shared venv

It is recommended to create the virtual environment under `nanobot-main2.2` and let both projects share it.

```bash
cd /home/opc/nanoorabot/nanobot-main2.2
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip setuptools wheel
```

## 2. Install Python Packages

Install the core package first, then install WebUI with the same Python interpreter:

```bash
cd /home/opc/nanoorabot/nanobot-main2.2
./.venv/bin/python -m pip install -e .

cd /home/opc/nanoorabot/nanobot-webui-main2.0
/home/opc/nanoorabot/nanobot-main2.2/.venv/bin/python -m pip install -e .
```

Verify editable locations:

```bash
/home/opc/nanoorabot/nanobot-main2.2/.venv/bin/python -m pip show nanobot-ai
/home/opc/nanoorabot/nanobot-main2.2/.venv/bin/python -m pip show nanobot-webui
```

Confirm:

- `nanobot-ai` points to `/home/opc/nanoorabot/nanobot-main2.2`
- `nanobot-webui` points to `/home/opc/nanoorabot/nanobot-webui-main2.0`

## 3. Build the Frontend

```bash
cd /home/opc/nanoorabot/nanobot-webui-main2.0/web
npm install --legacy-peer-deps
npm run build
```

## 4. Sync Frontend Assets to Backend Static Directory

If `rsync` is available, use:

```bash
cd /home/opc/nanoorabot/nanobot-webui-main2.0
rsync -a --delete web/dist/ webui/web/dist/
```

If `rsync` is not available, use:

```bash
cd /home/opc/nanoorabot/nanobot-webui-main2.0
rm -rf webui/web/dist
mkdir -p webui/web/dist
cp -r web/dist/. webui/web/dist/
```

At minimum, confirm these files exist:

```text
/home/opc/nanoorabot/nanobot-webui-main2.0/web/dist/index.html
/home/opc/nanoorabot/nanobot-webui-main2.0/webui/web/dist/index.html
```

## 5. Runtime Configuration

The current release uses the root `runtime` directory, not the old `nanobot-runtime/config.json` layout.

Check these files carefully:

- `/home/opc/nanoorabot/runtime/config.webui.json`
- `/home/opc/nanoorabot/runtime/oracle_config.json`
- `/home/opc/nanoorabot/runtime/tool_policy.json`
- `/home/opc/nanoorabot/runtime/dangerous_tool_policy.json`
- `/home/opc/nanoorabot/runtime/webui_config.json`

Most important items:

- `config.webui.json`
  - model settings
  - `agents.defaults.model`
  - workspace related paths
  - WebUI base settings
- `oracle_config.json`
  - Oracle connection settings
- `tool_policy.json`
  - tool policy
- `dangerous_tool_policy.json`
  - dangerous command policy

If your workspace is not at the default path, replace `--workspace` in the startup commands below with your actual workspace path.

## 6. Start the WebUI

Recommended foreground mode with real-time console logs:

```bash
cd /home/opc/nanoorabot/nanobot-webui-main2.0

/home/opc/nanoorabot/nanobot-main2.2/.venv/bin/python -m webui \
  --host 0.0.0.0 \
  --port 18780 \
  --workspace "/home/opc/nanoorabot/dba1" \
  --config "/home/opc/nanoorabot/runtime/config.webui.json" \
  --oracle-config "/home/opc/nanoorabot/runtime/oracle_config.json" \
  --tool-policy "/home/opc/nanoorabot/runtime/tool_policy.json" \
  --log-level DEBUG
```

Browser URL:

```text
http://<your_server_ip>:18780/
```

Default login:

```text
admin / nanobot
```

Optional background mode:

```bash
cd /home/opc/nanoorabot/nanobot-webui-main2.0
nohup /home/opc/nanoorabot/nanobot-main2.2/.venv/bin/python -m webui \
  --host 0.0.0.0 \
  --port 18780 \
  --workspace "/home/opc/nanoorabot/dba1" \
  --config "/home/opc/nanoorabot/runtime/config.webui.json" \
  --oracle-config "/home/opc/nanoorabot/runtime/oracle_config.json" \
  --tool-policy "/home/opc/nanoorabot/runtime/tool_policy.json" \
  --log-level DEBUG > webui.log 2>&1 &
```

Check logs:

```bash
tail -f /home/opc/nanoorabot/nanobot-webui-main2.0/webui.log
```

## 7. Start the CLI (Optional)

If you only need the CLI agent:

```bash
cd /home/opc/nanoorabot/nanobot-main2.2

./.venv/bin/python -m nanobot agent \
  --config "/home/opc/nanoorabot/runtime/config.webui.json" \
  --workspace "/home/opc/nanoorabot/dba1"
```

## 8. Open Port 18780 (If Needed)

For systems using `firewalld`:

```bash
sudo firewall-cmd --permanent --add-port=18780/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

## FAQ

### 1. Web backend starts, but the page has no frontend UI

Usually one of these steps is missing:

- `npm run build`
- syncing `web/dist` to `webui/web/dist`

### 2. Port `18780` is already in use

Either:

- use another port
- or stop the process currently using `18780`

### 3. Login works, but chat does not work

Usually this means model configuration is incomplete or invalid.

Check:

- `/home/opc/nanoorabot/runtime/config.webui.json`
- `providers`
- `agents.defaults.model`
- network connectivity

### 4. Oracle related functions are unavailable

Check:

- `/home/opc/nanoorabot/runtime/oracle_config.json`
- SQLcl installation on the Linux machine
- configured database connection names


