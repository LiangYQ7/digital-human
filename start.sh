#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "🏯 灵山胜境 · 数字人智能导览系统"
echo ""

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "[❌] 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi
echo "[✓] Python3 就绪"

# 检查 .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[⚠] 已创建 .env，请编辑填入你的 API Key"
fi

# 安装依赖
echo "[⏳] 检查依赖..."
pip install -r requirements.txt -q 2>/dev/null
echo "[✓] 依赖就绪"

# 启动服务
echo ""
echo "[⏳] 启动 Brain 服务 (8011)..."
python3 -m uvicorn brain.server:app --host 0.0.0.0 --port 8011 &
PID_BRAIN=$!

echo "[⏳] 启动 Admin 服务 (8012)..."
python3 -m uvicorn admin.backend.app.main:app --host 0.0.0.0 --port 8012 &
PID_ADMIN=$!

echo ""
echo "┌────────────────────────────────────────────┐"
echo "│  游客端    http://localhost:8011           │"
echo "│  管理后台  http://localhost:8012/admin      │"
echo "│  Brain API http://localhost:8011/docs       │"
echo "│  Ctrl+C 停止所有服务                       │"
echo "└────────────────────────────────────────────┘"

trap "kill $PID_BRAIN $PID_ADMIN 2>/dev/null; echo '服务已停止'; exit" INT TERM
wait
