# Buddy-AI 智能问答助手

基于 LangGraph 和 RAG 的中文智能问答系统，支持向量数据库检索、网络搜索和长期记忆功能。

## 项目架构

- **后端**: FastAPI + LangGraph + Chroma Vector DB
- **前端**: Vue3 + TypeScript + Pinia
- **LLM**: 阿里云 DashScope (Qwen 模型)
- **向量库**: Chroma
- **记忆**: PostgreSQL
- **会话**: Redis

## 功能特性

- 🤖 **智能对话**: 基于 LangGraph 的多轮对话
- 📚 **知识库检索**: 支持文件上传和向量检索
- 🔍 **网络搜索**: Tavily API 实时搜索
- 💾 **长期记忆**: 用户偏好和历史记录存储
- 📁 **文件支持**: PDF, DOCX, TXT, MD, CSV
- 💬 **多会话**: 支持多个对话会话管理
- 🎨 **现代化UI**: 参考豆包设计风格

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Redis
- PostgreSQL
- 阿里云 DashScope API Key
- Tavily API Key

### 安装

1. 克隆项目
```bash
git clone https://github.com/your-repo/buddy-ai.git
cd buddy-ai
```

2. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt
```

3. 安装前端依赖
```bash
cd ../frontend
npm install
```

### 配置

1. 复制环境变量文件
```bash
cd backend
cp .env.example .env
```

2. 编辑 `.env` 文件，填入 API Keys
```env
DASHSCOPE_API_KEY=your_dashscope_api_key
TAVILY_API_KEY=your_tavily_api_key
REDIS_URL=redis://localhost:6379/0
POSTGRESQL_URL=postgresql://user:pass@localhost:5432/buddyai
```

### 运行

#### 使用 Docker Compose (推荐)

```bash
docker-compose up -d
```

#### 手动运行

1. 启动后端
```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

2. 启动前端
```bash
cd frontend
npx vite
```

### 访问

- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 项目结构

```
buddy-ai/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/         # API 路由
│   │   ├── agent/          # LangGraph Agent
│   │   ├── tools/          # 工具
│   │   ├── memory/         # 记忆
│   │   ├── retriever/      # 检索
│   │   └── models/         # Pydantic 模型
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Vue3 前端
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── views/          # 页面
│   │   ├── stores/         # Pinia 状态
│   │   ├── api/            # API 客户端
│   │   └── composables/    # 组合式函数
│   └── package.json
├── docker-compose.yml
└── README.md
```

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger API 文档。

### WebSocket 聊天

```
ws://localhost:8000/ws/chat/{user_id}
```

发送消息:
```json
{
  "type": "user_message",
  "content": "你好",
  "thread_id": "可选的会话ID"
}
```

### REST API

| 端点 | 方法 | 说明 |
|------|------|------|
| /api/v1/files/upload | POST | 上传文件 |
| /api/v1/files/vectorize | POST | 向量化文件 |
| /api/v1/sessions | GET | 获取会话列表 |
| /api/v1/sessions | POST | 创建会话 |
| /api/v1/memory | GET | 获取记忆 |
| /api/v1/memory | POST | 保存记忆 |

## 开发指南

### 后端开发

```bash
cd backend
# 添加新依赖
pip install package_name
# 更新 requirements.txt
pip freeze > requirements.txt
```

### 前端开发

```bash
cd frontend
# 添加新依赖
npm install package_name
# 开发模式
npm run dev
# 构建
npm run build
```

## 许可证

MIT License