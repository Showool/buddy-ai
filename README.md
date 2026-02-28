# Buddy-AI 智能问答助手

基于 LangGraph 和 RAG 的中文智能问答系统，支持向量数据库检索、网络搜索和长期记忆功能。

## 界面预览

![界面截图1](docs/chat-interface-1.png)

![界面截图2](docs/chat-interface-2.png)

## 项目架构

- **后端**: FastAPI + LangGraph
- **前端**: Vue3 + TypeScript + Pinia
- **LLM**: 阿里云 DashScope (Qwen 模型)
- **向量库**: Chroma / PostgreSQL+pgvector
- **记忆**: PostgreSQL
- **会话**: Redis
- **包管理**: uv

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

- Python 3.11+
- Node.js 18+
- uv (Python 包管理器)
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

2. 安装 uv（如果尚未安装）
```bash
pip install uv
```

3. 安装后端依赖
```bash
cd backend
uv pip install -r requirements.txt
# 或使用 pyproject.toml
uv add -e .
```

4. 安装前端依赖
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
POSTGRESQL_URL=postgresql://user:pass@localhost:5432/buddy-ai

# 向量数据库类型: chroma 或 postgresql
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIR=./chroma_db
```

如果使用 PostgreSQL 作为向量数据库，需要：
```env
VECTOR_DB_TYPE=postgresql
```

并在 PostgreSQL 数据库中安装 pgvector 扩展：
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 运行

#### 手动运行

1. 启动后端
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. 启动前端
```bash
cd frontend
npm run dev
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
│   │   ├── main.py         # FastAPI 应用入口
│   │   ├── config.py       # 配置管理
│   │   ├── api/v1/         # API 路由
│   │   │   ├── chat.py     # WebSocket 聊天
│   │   │   ├── files.py    # 文件上传
│   │   │   ├── sessions.py # 会话管理
│   │   │   └── memory.py   # 记忆管理
│   │   ├── agent/          # LangGraph Agent
│   │   │   ├── graph.py    # Agent 工作流图
│   │   │   ├── node.py     # Agent 节点
│   │   │   ├── state.py    # Agent 状态
│   │   │   └── create_agent.py
│   │   ├── tools/          # 工具
│   │   │   ├── system_tool.py    # 系统工具
│   │   │   ├── user_tool.py      # 用户工具
│   │   │   └── web_search_tool.py # 搜索工具
│   │   ├── retriever/      # 检索模块
│   │   │   ├── vector_store.py   # 向量存储
│   │   │   ├── pgvector_store.py # PostgreSQL 向量存储
│   │   │   ├── get_retriever.py  # 检索器
│   │   │   ├── vectorize_files.py # 文件向量化
│   │   │   └── embeddings_model.py # 嵌入模型
│   │   ├── memory/         # 记忆管理
│   │   ├── llm/            # LLM 工厂
│   │   ├── prompt/         # 提示词
│   │   └── models/         # Pydantic 模型
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .env
├── frontend/               # Vue3 前端
│   ├── src/
│   │   ├── main.ts         # 入口文件
│   │   ├── App.vue         # 根组件
│   │   ├── components/     # 组件
│   │   ├── views/          # 页面
│   │   ├── stores/         # Pinia 状态
│   │   ├── api/            # API 客户端
│   │   ├── composables/    # 组合式函数
│   │   └── router/         # 路由
│   └── package.json
└── README.md
```

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger API 文档。

### WebSocket 聊天

```
ws://localhost:8000/api/v1/chat/ws/{user_id}
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

# 添加新依赖到 pyproject.toml
uv add package_name

# 或更新 requirements.txt 后安装
uv pip install -r requirements.txt
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

## 向量数据库配置

### Chroma（默认）

```env
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIR=./chroma_db
```

### PostgreSQL+pgvector

```env
VECTOR_DB_TYPE=postgresql
POSTGRESQL_URL=postgresql://user:pass@localhost:5432/buddy-ai
```

确保 PostgreSQL 数据库安装了 pgvector 扩展：
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 许可证

MIT License