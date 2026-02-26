#!/bin/bash
# Buddy-AI 后端启动脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Buddy-AI Backend 启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Python 版本
python_version=$(python --version 2>&1 | awk '{print $2}')
required_version="3.10"

echo -e "\n📌 检查 Python 版本..."
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo -e "   ${GREEN}✓${NC} Python 版本: $python_version"
else
    echo -e "   ${RED}✗${NC} Python 版本过低，需要 3.10+，当前: $python_version"
    exit 1
fi

# 检查环境变量文件
echo -e "\n📌 检查环境配置..."
if [ ! -f .env ]; then
    echo -e "   ${YELLOW}⚠${NC} .env 文件不存在，从 .env.example 创建..."
    cp .env.example .env
    echo -e "   ${YELLOW}⚠${NC} 请编辑 .env 文件填入正确的 API Keys"
fi

# 检查必需的环境变量
echo -e "\n📌 检查必需的环境变量..."
source .env

if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo -e "   ${RED}✗${NC} DASHSCOPE_API_KEY 未设置"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} DASHSCOPE_API_KEY 已设置"

if [ -z "$TAVILY_API_KEY" ]; then
    echo -e "   ${RED}✗${NC} TAVILY_API_KEY 未设置"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} TAVILY_API_KEY 已设置"

# 创建必要的目录
echo -e "\n📌 创建必要的目录..."
mkdir -p uploads chroma_db logs

# 安装依赖
echo -e "\n📌 检查依赖..."
if [ ! -d "venv" ]; then
    echo -e "   ${YELLOW}创建虚拟环境...${NC}"
    python -m venv venv
fi

source venv/bin/activate

echo -e "   安装依赖..."
pip install -q -r requirements.txt

# 启动应用
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  启动 Buddy-AI Backend${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "   环境: ${ENVIRONMENT:-development}"
echo -e "   端口: ${PORT:-8000}"
echo -e "   调试模式: ${DEBUG:-false}"
echo -e "${GREEN}========================================${NC}\n"

# 启动服务
if [ "$DEBUG" = "true" ]; then
    uvicorn app.main:app --reload --host ${HOST:-0.0.0.0} --port ${PORT:-8000}
else
    uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers 4
fi