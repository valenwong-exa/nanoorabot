# OCI Linux Step provided by Qiong Wu
## 创建虚拟环境环境 | Create venv
python3 -m venv .nanobot-webui
. .nanobot-webui/bin/activate

## 安装 Python 依赖 | Install py lib
cd nanoorabot
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e nanobot-015post1
python -m pip install -e nanobot-webui-main

安装完成后，可立刻执行下面命令验证 nanobot-ai 是否来自本地 nanobot-015post1：  | Verify
python -m pip show nanobot-ai

## 构建前端 | build front
cd ~/nanoorabot/nanobot-webui-main
npm install --legacy-peer-deps
npm run build

## 同步前端产物到后端静态目录 | Copy static resource 
切换到项目根目录 | switch to root 
cd /home/opc/nanoorabot-main/nanobot-webui-main
rm -rf webui/web/dist
mkdir -p webui/web/dist
cp -rn web/dist/* webui/web/dist/


## 配置初始化（重要）| initial config
本次手工安装方式，建议直接修改已有运行时配置。
需要重点确认以下两个文件：| two important files
    ~/nanoorabot/nanobot-runtime/config.json
    ~/nanoorabot/nanobot-webui-main/s.sh
 config.json ：
    Model APY
    workspace path


s.sh 里建议至少确认这些变量已经改成你的实际路径：

#!/bin/bash

# --- config variable ---
# 请根据实际路径修改，建议使用绝对路径 | modify path as your env, suggest to use direct path
ROOT="/home/opc/nanoorabot/nanobot-webui-main"
WEB="$ROOT/web"
WEB_DIST="$WEB/dist"
SERVER_DIST="$ROOT/webui/web/dist"
CONFIG="/home/opc/nanoorabot/nanobot-runtime/config.json"
WORKSPACE="/home/opc/nanoorabot/nanobot-runtime/workspace/dba1"
PORT=18780

# 确保脚本在出错时停止
set -e

echo "[1/4] Building frontend..."
cd "$WEB"
# 使用 npm run build
npm run build

echo "[2/4] Syncing static assets..."
# 如果目录存在则清理，mkdir -p 确保父目录存在
rm -rf "$SERVER_DIST"
mkdir -p "$(dirname "$SERVER_DIST")"
# 使用 cp -r 将编译产物同步到后端静态目录
cp -r "$WEB_DIST" "$(dirname "$SERVER_DIST")"

echo "[3/4] Checking port $PORT..."
# 获取占用端口的 PID
PID=$(lsof -t -i:$PORT || true)

# 检查 PID 是否不为空
if [ -n "$PID" ]; then
    echo "Killing PID $PID on port $PORT..."
    # 使用 xargs 确保即使有多个 PID 也能处理，且 kill 前确认进程确实存在
    echo "$PID" | xargs kill -9 2>/dev/null || true
else
    echo "Port $PORT is free."
fi

echo "[4/4] Starting WebUI..."
cd "$ROOT"
##  active venv
*注意：Linux 下可执行文件通常在 bin/ 目录下，而不是 Scripts/*
source ~/nanoorabot/.nanobot-webui/bin/activate

##   nohup running
nohup python3 -m webui \
    --host 0.0.0.0 \
    --port $PORT \
    --workspace "$WORKSPACE" \
    --config "$CONFIG" \
    --webui-only \
    --log-level INFO > webui.log 2>&1 &

echo "------------------------------------------------"
echo "Done. WebUI is running in background."
echo "Access at: http://<Your_Server_IP>:$PORT/"
echo "Check logs with: tail -f webui.log"
echo "------------------------------------------------"

----------------------------------------------------------------------
## 开放18780 | Open 18780 port
sudo firewall-cmd --permanent --add-port=18780/tcp 
sudo firewall-cmd --reload 
sudo firewall-cmd --list-ports 


