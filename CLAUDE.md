# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供本项目代码工作的指导。

## 语言要求

**重要：请始终使用中文回答用户的问题和解释。** 本项目是一个中文智能问答系统，所有与用户的沟通应使用中文。

## 项目概述

Buddy-AI 是一个基于 LangGraph 构建的中文智能问答系统，采用并行 RAG（检索增强生成）架构。项目包括：

1. **后端 API** - FastAPI + LangGraph 并行智能体
2. **前端 UI** - Vue3 + TypeScript + Pinia

## 常用命令

### 后端开发 (FastAPI)

**包管理 (pip + conda)**:
```bash
cd backend

# 确保已激活 conda 环境
conda activate buddy-ai

# 从 requirements.txt 安装依赖
pip install -r requirements.txt

# 安装新依赖
pip install package_name

# 查看已安装包
pip list
```

**运行服务器**:
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**健康检查**: `curl http://localhost:8000/health`

**API 文档**: http://localhost:8000/docs (仅 DEBUG 模式)

### 前端开发 (Vue3)

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (运行在 http://localhost:3000)
npm run dev

# 构建生产版本
npm run build
```

### 配置

创建或编辑 `backend/.env`:
- `DASHSCOPE_API_KEY` - 阿里云 DashScope API 密钥（用于 Qwen LLM 和 embeddings）
- `TAVILY_API_KEY` - Tavily 搜索 API 密钥
- `REDIS_URL` - Redis 连接字符串（用于 checkpointing）
- `POSTGRESQL_URL` - PostgreSQL 连接字符串（用于记忆和向量存储，需要 pgvector 扩展）

## 架构

### 后端 (FastAPI + LangGraph)

**入口文件**: [backend/app/main.py](backend/app/main.py)

后端实现了一个带有 WebSocket 支持的 FastAPI 应用，用于实时聊天。

**智能体框架 (LangGraph)**:

核心智能体工作流定义在 [backend/app/agent/graph.py](backend/app/agent/graph.py)，采用**并行检索架构**。

**状态定义** ([backend/app/agent/state.py](backend/app/agent/state.py)):
- `AgentState` 继承 LangGraph 的 `MessagesState`，包含并行结果、循环控制等字段
- `GradeDocuments` 是一个 Pydantic 模型，用于二进制相关性评分

**节点流程**（并行架构）:
1. `route` ([backend/app/agent/parallel_routing_node.py](backend/app/agent/parallel_routing_node.py)) - 使用 LLM 判断需要并行检索哪些来源（记忆/文档）
2. `memory_retrieval` ([backend/app/agent/memory_retrieval_node.py](backend/app/agent/memory_retrieval_node.py)) - 从 PostgreSQL Store 检索用户长期记忆
3. `document_retrieval` ([backend/app/agent/document_retrieval_node.py](backend/app/agent/document_retrieval_node.py)) - 执行混合检索（向量+全文搜索）
4. `grade_documents` ([backend/app/agent/grade_documents.py](backend/app/agent/grade_documents.py)) - LLM 评估检索到的文档相关性
5. `rewrite_question` ([backend/app/agent/rewrite_question_node.py](backend/app/agent/rewrite_question_node.py)) - 智能重写问题（关键词提取/简化策略，最多3次迭代）
6. `generate_response` ([backend/app/agent/generate_response_node.py](backend/app/agent/generate_response_node.py)) - 根据并行检索结果生成最终响应

**工具系统** ([backend/app/tools/](backend/app/tools/)):
- **系统工具** ([system_tool.py](backend/app/tools/system_tool.py)): `clear_conversation`, `update_user_name`, `retrieve_context`, `retriever_tool`
- **用户工具** ([user_tool.py](backend/app/tools/user_tool.py)): `get_weather_for_location`, `retrieve_memory`, `save_memory`, `save_conversation_memory`
- **搜索工具** ([web_search_tool.py](backend/app/tools/web_search_tool.py)): `tavily_search` 用于网络搜索集成

**API 路由** ([backend/app/api/v1/](backend/app/api/v1/)):
- `/api/v1/chat/ws/{user_id}` - WebSocket 聊天端点
- `/api/v1/files/` - 文件上传和向量化
- `/api/v1/sessions/` - 会话管理
- `/api/v1/memory/` - 记忆 CRUD 操作

**配置** ([backend/app/config.py](backend/app/config.py)):
使用 Pydantic Settings 进行基于环境的配置，支持开发、测试和生产环境。

**核心组件**:
- **LLM 工厂** ([backend/app/llm/llm_factory.py](backend/app/llm/llm_factory.py)): 通过 DashScope OpenAI 兼容 API 使用 Qwen 模型
- **Embeddings** ([backend/app/retriever/embeddings_model.py](backend/app/retriever/embeddings_model.py)): DashScope 文本嵌入用于向量化
- **Prompts** ([backend/app/prompt/prompt.py](backend/app/prompt/prompt.py)): 各种智能体操作的系统提示词
- **PGVector Store** ([backend/app/retriever/pgvector_store.py](backend/app/retriever/pgvector_store.py)): PostgreSQL 向量存储实现（带 pgvector）
- **检索器** ([backend/app/retriever/get_retriever.py](backend/app/retriever/get_retriever.py)): 使用 PostgreSQL 向量搜索和网络搜索的检索设置
- **记忆** ([backend/app/memory/memory_factory.py](backend/app/memory/memory_factory.py)): PostgreSQL 记忆存储

### 前端 (Vue3 + TypeScript)

**入口文件**: [frontend/src/main.ts](frontend/src/main.ts)

前端是一个使用 TypeScript 的 Vue3 SPA，使用 Vite 作为构建工具。

**状态管理 (Pinia)**:
- [frontend/src/stores/chat.ts](frontend/src/stores/chat.ts) - 聊天消息和状态管理
- [frontend/src/stores/session.ts](frontend/src/stores/session.ts) - 会话管理
- [frontend/src/stores/user.ts](frontend/src/stores/user.ts) - 用户状态

**通信层**:
- **WebSocket**: [frontend/src/composables/useWebSocket.ts](frontend/src/composables/useWebSocket.ts) - 与后端的实时聊天连接
- **REST API**: [frontend/src/api/](frontend/src/api/) - 通过 Axios 进行文件上传、会话和记忆操作

### 向量数据库配置

**PostgreSQL+pgvector**:
- 使用与记忆存储相同的 PostgreSQL 连接
- 需要 pgvector 扩展: `CREATE EXTENSION IF NOT EXISTS vector;`
- 通过 `.env` 中的 `PGVECTOR_COLLECTION_NAME` 配置（默认: `buddy_ai_docs`）

### 检索策略

实现了混合检索：
- 从 PostgreSQL+pgvector 进行向量检索，使用 DashScope embeddings
- 通过 Tavily API 进行网络搜索（最多 3 个结果）
- 结果组合时知识库优先

### 记忆和状态管理

- **Checkpointing**: Redis 用于对话状态持久化
- **记忆存储**: PostgreSQL 通过 PostgresStore 存储用户特定记忆
- **WebSocket**: 用于聊天流式传输的实时双向通信

## 文档处理

支持的格式：PDF, DOCX, TXT, MD, CSV（每个文件最大 5MB）
- 文件通过后端 API 上传并向量化
- 持久存储在配置的向量数据库中

## 重要说明

- Python 3.11+ 必需
- 系统专为中文问答设计
- 每次查询最多 3 次工具调用
- 修改智能体工作流时，请保持 [backend/app/agent/graph.py](backend/app/agent/graph.py) 中的条件边结构
- 工具配置可以通过修改智能体配置中的工具列表来调整
- WebSocket 连接需要 user_id 和可选的 thread_id 用于会话管理
- 向量存储使用 PostgreSQL+pgvector 扩展

## 依赖

**后端**:
- `pyproject.toml` - 主要依赖规范
- `requirements.txt` - 用于直接安装的简化列表

**版本约束**:
- `langgraph-checkpoint==3.0.1`（必须 <4.0.0 以兼容 langgraph-checkpoint-redis）
- `fastapi==0.109.0` with `starlette<0.36.0`