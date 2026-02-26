@echo off
REM Buddy-AI Backend 启动脚本 (Windows)

echo ========================================
echo   Buddy-AI Backend 启动脚本
echo ========================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装或未添加到 PATH
    exit /b 1
)

REM 检查环境变量文件
if not exist .env (
    echo [WARN] .env 文件不存在，从 .env.example 创建...
    copy .env.example .env
    echo [WARN] 请编辑 .env 文件填入正确的 API Keys
)

REM 创建必要的目录
if not exist uploads mkdir uploads
if not exist chroma_db mkdir chroma_db
if not exist logs mkdir logs

REM 创建虚拟环境
if not exist venv (
    echo [INFO] 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
echo [INFO] 安装依赖...
pip install -q -r requirements.txt

REM 启动应用
echo ========================================
echo   启动 Buddy-AI Backend
echo ========================================
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause