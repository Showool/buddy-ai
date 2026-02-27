@echo off
REM Buddy-AI 项目启动脚本 (Windows)

echo ========================================
echo   Buddy-AI 项目启动
echo ========================================

REM 激活 conda 虚拟环境
call conda activate buddy-ai
if errorlevel 1 (
    echo [ERROR] 无法激活 conda 虚拟环境 buddy-ai
    pause
    exit /b 1
)
echo [INFO] 已激活 conda 虚拟环境 buddy-ai

REM 启动后端服务
echo [INFO] 启动后端服务...
start "Buddy-AI Backend" cmd /k "cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

REM 等待几秒让后端启动
timeout /t 3 /nobreak >nul

REM 启动前端服务
echo [INFO] 启动前端服务...
start "Buddy-AI Frontend" cmd /k "cd frontend && npx vite"

echo ========================================
echo   Buddy-AI 项目已启动
echo   后端: http://127.0.0.1:8000
echo   前端: http://localhost:3000
echo ========================================