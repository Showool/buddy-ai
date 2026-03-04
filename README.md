# Buddy-AI 智能问答助手

基于 LangGraph 和 RAG 的中文智能问答系统，支持混合检索（向量+全文）、重排序、异步向量化进度追踪、网络搜索和长期记忆功能。

## 界面预览

![界面截图1](docs/chat-interface-1.png)

![界面截图2](docs/chat-interface-2.png)

## LangGraph 工作流程

![LangGraph 工作流程图](docs/langgraph_workflow.png)

## 项目架构

- **后端**: FastAPI + LangGraph
- **前端**: Vue3 + TypeScript + Pinia + Element Plus
- **LLM**: 阿里云 DashScope (Qwen 模型)
- **向量库**: PostgreSQL+pgvector (主推) / Chroma (可选)
- **记忆**: PostgreSQL
- **会话**: Redis (Checkpointing)
- **检索**: 混合检索（向量 + 全文搜索 + RRF融合 + Qwen Rerank）
- **包管理**: pip + conda

## 核心特性

- 🤖 **智能对话**: 基于 LangGraph 的多轮对话工作流
- 📚 **混合检索**: 向量检索 + PostgreSQL 全文搜索 + RRF 融合
- 🎯 **重排序**: 阿里云 Qwen Rerank 模型优化结果
- 🔍 **网络搜索**: Tavily API 实时网络搜索
- 💾 **长期记忆**: 用户偏好和历史记录自动保存
- 💾 **异步向量化**: 文件上传后后台向量化，带实时进度追踪
- 📄 **智能切分**: 根据文件类型自适应切分策略
- 🔍 **增量更新**: 基于内容哈希的增量向量化，避免重复处理
- 💬 **多会话**: 支持多个对话会话管理
- 🎨 **现代化UI**: Vue3 + Element Plus 响应式设计

## 技术亮点

### 混合检索架构

- **向量检索**: 基于 pgvector 的语义相似度搜索
- **全文搜索**: PostgreSQL tsvector 的关键词匹配
- **RRF 融合**: Reciprocal Rank Fusion 算法合并结果
- **智能 Rerank**: 超过阈值时自动触发 Qwen Rerank 优化

### 记忆系统

- **短期记忆**: Redis Checkpointing 保存对话上下文
- **长期记忆**: PostgreSQL Store 保存用户偏好和历史
- **智能保存**: 自动判断对话内容是否值得保存
- **记忆检索**: 基于查询的相关记忆检索

### 文件处理

- **支持格式**: PDF, DOCX, TXT, MD, CSV
- **智能切分**: 根据文件类型自动选择分隔符和块大小
- **元数据丰富**: 包含文件ID、用户ID、块索引、内容哈希
- **摘要生成**: 自动生成文档摘要用于快速预览

### 存储设计

- **文件内容**: PostgreSQL BLOB 存储
- **向量数据**: pgvector 或 Chroma
- **任务状态**: 独立表跟踪向量化进度
- **记忆存储**: LangChain PostgresStore

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Conda
- Redis (用于会话状态持久化)
- PostgreSQL 15+ (带 pgvector 扩展)
- 阿里云 DashScope API Key
- Tavily API Key (网络搜索)
- 阿里云 Qwen Rerank API Key (可选，用于结果重排序)

### 安装

1. 克隆项目
```bash
git clone https://github.com/your-repo/buddy-ai.git
cd buddy-ai
```

2. 创建并激活 conda 环境
```bash
conda create -n buddy-ai python=3.11 -y
conda activate buddy-ai
```

3. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt
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

2. 初始化数据库（首次运行）
```bash
cd backend
python init_db.py
```

3. 编辑 `.env` 文件，填入必要配置
```env
# 阿里云 API 配置
DASHSCOPE_API_KEY=your_dashscope_api_key

# Tavily 网络搜索（可选）
TAVILY_API_KEY=your_tavily_api_key

# 数据库连接
REDIS_URL=redis://localhost:6379/0
POSTGRESQL_URL=postgresql://user:pass@localhost:5432/buddy-ai

# 向量数据库配置（推荐使用 PostgreSQL+pgvector）
VECTOR_DB_TYPE=postgresql
PGVECTOR_COLLECTION_NAME=buddy_kb

# 可选：Chroma 向量库
# VECTOR_DB_TYPE=chroma
# CHROMA_PERSIST_DIR=./chroma_db

# 文件上传配置
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=5
```

**PostgreSQL 准备**：

确保 PostgreSQL 安装了 pgvector 扩展：
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

创建数据库和表（运行 `init_db.py` 自动完成）：
```sql
CREATE DATABASE buddy_ai;

\c buddy_ai

-- 表将在 init_db.py 中创建，包括：
-- - langchain_pg_collection (向量集合)
-- - langchain_pg_embedding (向量数据)
-- - user_files (用户文件)
-- - vectorization_tasks (向量化任务)
-- - store_postgres (LangGraph 记忆存储)
```

### 运行

#### 使用启动脚本（推荐）

**Windows:**
```bash
# 后端
.\backend\start_server.bat

# 前端（新终端）
cd frontend
npm run dev
```

**Linux/macOS:**
```bash
# 后端
./backend/start_server.sh

# 前端（新终端）
cd frontend
npm run dev
```

#### 手动运行

**重要：启动前必须激活 conda 环境！**

1. 激活 conda 环境
```bash
conda activate buddy-ai
```

2. 启动后端
```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

3. 启动前端（新终端）
```bash
cd frontend
npx vite
```

#### 直接指定 Python 路径（跨平台兼容）

如果不想每次激活 conda 环境，可以直接指定 Python 路径：

```bash
cd backend
"D:/Miniconda3/envs/buddy-ai/python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 访问

- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 项目结构

```
buddy-ai/
├── backend/                      # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py            # 配置管理（Pydantic Settings）
│   │   ├── init_db.py           # 数据库初始化脚本
│   │   ├── api/v1/              # API 路由
│   │   │   ├── chat.py          # WebSocket 聊天
│   │   │   ├── files.py         # 文件上传与管理
│   │   │   ├── sessions.py      # 会话管理
│   │   │   └── memory.py        # 记忆管理
│   │   ├── agent/               # LangGraph Agent
│   │   │   ├── graph.py         # Agent 工作流图
│   │   │   ├── node.py          # Agent 节点
│   │   │   ├── state.py         # Agent 状态定义
│   │   │   ├── retrieval_node.py # 检索节点
│   │   │   ├── rag_agent.py     # RAG Agent
│   │   │   └── agent_context.py # Agent 上下文
│   │   ├── tools/               # 工具
│   │   │   ├── system_tool.py   # 系统工具
│   │   │   ├── user_tool.py     # 用户工具（记忆相关）
│   │   │   ├── web_search_tool.py # Tavily 网络搜索
│   │   │   └── __init__.py
│   │   ├── services/            # 业务服务层（新增）
│   │   │   ├── fulltext_search_service.py  # PostgreSQL 全文搜索
│   │   │   ├── qwen_rerank_service.py      # Qwen Rerank 服务
│   │   │   ├── retrieval_orchestrator.py   # 混合检索编排
│   │   │   ├── vectorization_service.py    # 异步向量化服务
│   │   │   ├── user_file_service.py        # 用户文件管理
│   │   │   └── pgvector_singleton.py       # pgvector 单例
│   │   ├── retriever/           # 检索模块
│   │   │   ├── vector_store.py  # 向量存储抽象层
│   │   │   ├── pgvector_store.py # PostgreSQL 向量存储
│   │   │   ├── get_retriever.py # 检索器配置
│   │   │   ├── vectorize_files.py # 文件向量化
│   │   │   ├── embeddings_model.py # DashScope 嵌入模型
│   │   │   └── get_db.py        # 数据库连接
│   │   ├── memory/              # 记忆管理
│   │   │   └── memory_factory.py # 记忆存储工厂
│   │   ├── llm/                 # LLM 工厂
│   │   │   └── llm_factory.py   # Qwen 模型工厂
│   │   ├── prompt/              # 提示词
│   │   │   └── prompt.py        # 系统提示词模板
│   │   ├── utils/               # 工具函数
│   │   │   ├── datetime_utils.py   # 日期时间工具
│   │   │   └── document_processing.py # 文档处理工具
│   │   └── models/              # Pydantic 模型
│   │       ├── chat.py          # 聊天消息模型
│   │       ├── session.py       # 会话模型
│   │       ├── memory.py        # 记忆模型
│   │       ├── file.py          # 文件模型
│   │       └── user_file.py     # 用户文件模型
│   ├── requirements.txt         # Python 依赖
│   ├── .env.example             # 环境变量示例
│   └── .env                     # 环境变量（需自行创建）
├── frontend/                    # Vue3 前端
│   ├── src/
│   │   ├── main.ts              # 入口文件
│   │   ├── App.vue              # 根组件
│   │   ├── components/          # 组件
│   │   │   ├── ChatMessage.vue  # 聊天消息组件
│   │   │   ├── ChatInput.vue    # 输入框组件
│   │   │   ├── FileUpload.vue   # 文件上传组件
│   │   │   ├── VectorizationProgress.vue # 向量化进度组件
│   │   │   ├── KnowledgeBaseSidebar.vue # 知识库侧边栏
│   │   │   ├── Sidebar.vue      # 会话侧边栏
│   │   │   └── DebugPanel.vue   # 调试面板
│   │   ├── views/               # 页面
│   │   │   └── ChatView.vue     # 聊天主视图
│   │   ├── stores/              # Pinia 状态
│   │   │   ├── chat.ts          # 聊天状态
│   │   │   ├── session.ts       # 会话状态
│   │   │   └── user.ts          # 用户状态
│   │   ├── api/                 # API 客户端
│   │   │   ├── index.ts         # API 基础配置
│   │   │   ├── files.ts         # 文件 API
│   │   │   └── sessions.ts      # 会话 API
│   │   ├── composables/         # 组合式函数
│   │   │   ├── useWebSocket.ts  # WebSocket 连接
│   │   │   └── useTheme.ts      # 主题管理
│   │   ├── router/              # 路由配置
│   │   │   └── index.ts
│   │   └── types/               # TypeScript 类型定义
│   │       └── index.ts
│   └── package.json
├── docs/                        # 文档
│   ├── chat-interface-1.png
│   ├── chat-interface-2.png
│   ├── RAG-Plan.md              # RAG 架构设计文档
│   └── plan.md                  # 项目规划文档
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

响应格式:
```json
{
  "type": "assistant_message",
  "content": "你好！我是你的智能助手...",
  "metadata": {
    "retrieval_strategy": "hybrid",
    "retrieval_time_ms": 150,
    "sources": ["doc1.pdf", "doc2.docx"]
  }
}
```

### REST API

| 端点 | 方法 | 说明 |
|------|------|------|
| /api/v1/files/upload | POST | 上传文件（存储到 PostgreSQL） |
| /api/v1/files/vectorize/{file_id} | POST | 启动向量化任务（异步） |
| /api/v1/files/progress/{file_id} | GET | 获取向量化进度 |
| /api/v1/files | GET | 获取用户文件列表 |
| /api/v1/files/{file_id} | DELETE | 删除文件 |
| /api/v1/sessions | GET | 获取会话列表 |
| /api/v1/sessions | POST | 创建新会话 |
| /api/v1/sessions/{session_id} | DELETE | 删除会话 |
| /api/v1/memory | GET | 获取用户记忆 |
| /api/v1/memory | POST | 保存记忆 |

### 向量化进度追踪

向量化过程会返回实时进度：
```json
{
  "status": "processing",
  "progress": 45,
  "total_chunks": 120,
  "processed_chunks": 54,
  "error_message": null
}
```

状态值：
- `pending`: 等待处理
- `processing`: 处理中
- `completed`: 完成
- `failed`: 失败

## 开发指南

### 后端开发

**重要：确保使用 buddy-ai conda 环境中的 Python 解释器**

```bash
cd backend

# 激活环境（如果尚未激活）
conda activate buddy-ai

# 验证 Python 版本（应显示 Python 3.11+）
python --version

# 安装新依赖
pip install package_name

# 或更新 requirements.txt 后安装
pip install -r requirements.txt
```

**VSCode 配置：**
项目已配置 `.vscode/settings.json`，会自动使用 conda 环境中的 Python 解释器。

### 核心模块说明

#### 工具层 ([app/tools/](backend/app/tools/))

| 工具 | 功能 | 说明 |
|------|------|------|
| `system_tool.py` | 系统工具 | 清空对话、更新用户名、检索上下文 |
| `user_tool.py` | 用户工具 | 天气查询、记忆检索/保存、对话记忆 |
| `web_search_tool.py` | 网络搜索 | Tavily API 实时搜索 |

#### 服务层 ([app/services/](backend/app/services/))

| 服务 | 功能 | 关键方法 |
|------|------|----------|
| `fulltext_search_service.py` | PostgreSQL 全文搜索 | `search(query, user_id, k)` |
| `qwen_rerank_service.py` | Qwen Rerank 结果重排序 | `rerank(query, documents, top_k)` |
| `retrieval_orchestrator.py` | 混合检索编排 | `retrieve()` 整合向量+全文+RRF+Rerank |
| `vectorization_service.py` | 异步向量化服务 | `vectorize_file()` 带进度追踪 |
| `user_file_service.py` | 用户文件管理 | `save_file()`, `delete_file()` |

#### 检索流程

1. **并行检索**: 向量检索 + 全文搜索同时执行
2. **RRF 融合**: 合并两种结果，使用 Reciprocal Rank Fusion 算法
3. **智能 Rerank**: 结果数量超过阈值时触发 Qwen Rerank
4. **返回结果**: 返回 Top-K 最相关文档

#### 向量化流程

1. 文件上传到 PostgreSQL BLOB
2. 创建向量化任务记录
3. 异步处理：文档加载 → 智能切分 → 向量化 → 摘要生成
4. 实时进度更新（每 10% 一次）
5. 增量更新：基于内容哈希判断是否需要重新向量化

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

**技术栈**:
- Vue 3 Composition API
- TypeScript
- Pinia 状态管理
- Element Plus UI 组件
- Axios HTTP 客户端
- WebSocket 实时通信

**组件说明**:
- `ChatMessage.vue`: 聊天消息展示，支持 Markdown 渲染
- `VectorizationProgress.vue`: 向量化进度追踪组件，自动轮询状态
- `FileUpload.vue`: 文件上传组件，支持拖拽上传
- `KnowledgeBaseSidebar.vue`: 知识库文件管理侧边栏
- `Sidebar.vue`: 会话管理侧边栏

## 向量数据库配置

### PostgreSQL+pgvector（推荐）

```env
VECTOR_DB_TYPE=postgresql
POSTGRESQL_URL=postgresql://user:pass@localhost:5432/buddy-ai
PGVECTOR_COLLECTION_NAME=buddy_kb
```

**优势**:
- 统一的数据库基础设施
- 支持全文搜索（tsvector）
- 可与向量检索并行执行
- 更好的数据一致性和事务支持

**初始化**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

运行 `python init_db.py` 自动创建所需表结构。

### Chroma（可选）

```env
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIR=./chroma_db
```

**优势**:
- 无需额外数据库
- 快速启动和开发
- 适合本地测试

## 架构设计文档

详细的架构设计请参考：

- [RAG 架构设计文档](docs/RAG-Plan.md) - 混合检索、重排序、向量化流程
- [项目规划文档](docs/plan.md) - 功能规划和实现路线图

## 常见问题

### 向量化进度卡住

检查 Redis 连接是否正常：
```bash
redis-cli ping
# 应返回 PONG
```

### 检索结果不准确

1. 确认 pgvector 扩展已安装
2. 检查文件是否成功向量化
3. 尝试调整 `RERANK_THRESHOLD` 配置

### 内存占用过高

- 减小 `CHUNK_SIZE` 和 `CHUNK_OVERLAP`
- 限制并发向量化任务数量

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License