#!/bin/bash
# Buddy-AI 项目启动脚本 (Linux/Mac)

echo "========================================"
echo "  Buddy-AI 项目启动"
echo "========================================"

# 激活 conda 虚拟环境
eval "$(conda shell.bash hook)"
conda activate buddy-ai

if [ $? -ne 0 ]; then
    echo "[ERROR] 无法激活 conda 虚拟环境 buddy-ai"
    exit 1
fi

echo "[INFO] 已激活 conda 虚拟环境 buddy-ai"

# 启动后端服务（在后台）
echo "[INFO] 启动后端服务..."
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 3

# 启动前端服务
echo "[INFO] 启动前端服务..."
cd frontend
npx vite &
FRONTEND_PID=$!
cd ..

echo "========================================"
echo "  Buddy-AI 项目已启动"
echo "  后端: http://127.0.0.1:8000"
echo "  前端: http://localhost:3000"
echo "========================================"

# 等待进程
wait $BACKEND_PID $FRONTEND_PID