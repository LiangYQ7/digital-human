@echo off
chcp 65001 >nul
title 灵山胜境 · 数字人导览系统

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║     🏯 灵山胜境 · 数字人智能导览系统       ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ── 检查 Python ──
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [❌] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)
echo [✓] Python 已就绪

:: ── 检查 .env ──
if not exist ".env" (
    echo [⚠] .env 文件不存在，从 .env.example 复制...
    copy .env.example .env
    echo [⚠] 请编辑 .env 填入你的 API Key！
)

:: ── 安装依赖（增量） ──
echo [⏳] 检查依赖...
pip install -r requirements.txt -q 2>nul
echo [✓] 依赖已就绪

:: ── 检查 LiveTalking 是否在运行 ──
echo.
echo  ── 启动服务 ──
echo [ℹ] 请确保 LiveTalking 已在 8010 端口运行 (start_livetalking.bat)

:: ── 启动 Brain (port 8011) ──
echo [⏳] 启动 Brain 服务 (8011)...
start "灵山-Brain" cmd /k "cd /d "%~dp0" && python -m uvicorn brain.server:app --host 0.0.0.0 --port 8011 --reload"

:: ── 启动 Admin (port 8012) ──
echo [⏳] 启动 Admin 服务 (8012)...
start "灵山-Admin" cmd /k "cd /d "%~dp0" && python -m uvicorn admin.backend.app.main:app --host 0.0.0.0 --port 8012 --reload"

:: ── 等待启动 ──
timeout /t 4 /nobreak >nul

:: ── 打开浏览器 ──
echo [✓] 启动完成！
start http://localhost:8011

echo.
echo  ┌────────────────────────────────────────────┐
echo  │  游客端    http://localhost:8011           │
echo  │  管理后台  http://localhost:8012/admin      │
echo  │  Brain API http://localhost:8011/docs       │
echo  └────────────────────────────────────────────┘
echo.
echo  按任意键停止所有服务...
pause >nul

:: ── 停止 ──
taskkill /fi "WINDOWTITLE eq 灵山-*" /t >nul 2>&1
echo [✓] 服务已停止
