@echo off
REM Buddy-AI Frontend 启动脚本 (Windows)

echo ========================================
echo   Buddy-AI Frontend 启动脚本
echo ========================================

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 未安装或未添加到 PATH
    exit /b 1
)

REM 检查依赖
if not exist node_modules (
    echo [INFO] 安装依赖...
    call npm install
)

REM 启动应用
echo ========================================
echo   启动 Buddy-AI Frontend
echo ========================================
echo.

npm run dev

pause