#!/bin/bash
# Buddy-AI 前端启动脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Buddy-AI Frontend 启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Node.js 版本
node_version=$(node --version 2>&1)
echo -e "\n📌 Node.js 版本: $node_version"

# 检查 npm 版本
npm_version=$(npm --version 2>&1)
echo -e "📌 npm 版本: $npm_version"

# 检查依赖
echo -e "\n📌 检查依赖..."
if [ ! -d "node_modules" ]; then
    echo -e "   ${YELLOW}安装依赖...${NC}"
    npm install
fi

# 检查环境变量
echo -e "\n📌 检查环境变量..."
if [ ! -f .env.development ]; then
    echo -e "   ${YELLOW}⚠${NC} .env.development 文件不存在，使用默认配置"
fi

# 启动应用
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  启动 Buddy-AI Frontend${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "   开发服务器: http://localhost:3000"
echo -e "   后端 API: ${VITE_API_BASE_URL:-http://localhost:8000}"
echo -e "${GREEN}========================================${NC}\n"

npm run dev