# Buddy-AI 智能问答助手

基于 LangGraph 和 RAG 的中文智能问答系统，支持混合检索（向量+全文）、重排序、异步向量化进度追踪、网络搜索和长期记忆功能。

## 界面预览

![界面截图1](docs/chat-interface-1.png)

![界面截图2](docs/chat-interface-2.png)

## LangGraph 工作流程

![LangGraph 工作流程图](docs/langgraph_workflow.png)


#### 节点说明

| 节点 | 文件 | 功能 |
|------|------|------|
| `route` | `parallel_routing_node.py` | 使用 LLM 判断查询类型，决定并行检索哪些来源（记忆/文档） |
| `memory_retrieval` | `memory_retrieval_node.py` | 从 PostgreSQL Store 检索用户长期记忆 |
| `document_retrieval` | `document_retrieval_node.py` | 执行混合检索（向量+全文搜索） |
| `grade_documents` | `grade_documents.py` | LLM 评估检索到的文档是否相关 |
| `rewrite_question` | `rewrite_question_node.py` | 智能重写问题（关键词提取/简化策略，最多3次迭代） |
| `generate_response` | `generate_response_node.py` | 根据并行检索结果生成最终响应 |
| `tool_node` | LangGraph 内置 | 执行工具调用（tavily_search/save_conversation_memory） |

#### AgentState 状态

```python
class AgentState(MessagesState):
    parallel_results: List[Dict]    # 并行检索结果（memory + documents）
    loop_step: int                  # 循环计数器（防止无限重写，最大3次）
    routing_decision: Optional[str] # 路由决策
    classifications: List[Dict]     # 分类结果（用于并行路由）
    question: str                   # 当前问题
```

## 项目架构

- **后端**: FastAPI + LangGraph
- **前端**: Vue3 + TypeScript + Pinia + Element Plus
- **LLM**: 阿里云 DashScope (Qwen 模型)
- **向量库**: PostgreSQL+pgvector
- **记忆**: PostgreSQL (LangGraph PostgresStore)
- **会话**: Redis (Checkpointing)
- **检索**: 混合检索（向量 + 全文搜索 + RRF融合）
- **包管理**: pip + conda

## 核心特性

- 🤖 **智能对话**: 基于 LangGraph 的多轮对话工作流
- 📚 **混合检索**: 向量检索 + PostgreSQL 全文搜索 + RRF 融合
- 🔍 **网络搜索**: Tavily API 实时网络搜索
- 💾 **长期记忆**: 用户偏好和历史记录自动保存
- 💾 **异步向量化**: 文件上传后后台向量化，带实时进度追踪
- 📄 **智能切分**: 根据文件类型自适应切分策略
- 🔍 **增量更新**: 基于内容哈希的增量向量化，避免重复处理
- 💬 **多会话**: 支持多个对话会话管理
- 🎨 **现代化UI**: Vue3 + Element Plus 响应式设计

## 技术亮点

### LangGraph 智能体架构

- **状态管理**: 基于 `MessagesState` 的状态持久化，支持多轮对话上下文
- **条件路由**: LLM 智能判断查询类型，动态选择执行路径（记忆检索/RAG/直接回答）
- **自我改进**: 文档相关性评分 + 问题重写机制，最多 3 次迭代优化检索结果
- **重复检测**: 查询历史记录 + 相似度计算，防止陷入重写循环
- **流式输出**: WebSocket 实时推送 Agent 执行步骤，提供完整的执行过程可视化

### 混合检索架构

```mermaid
graph LR
    Query[用户查询] --> Vector[向量检索<br/>PostgreSQL+pgvector]
    Query --> Fulltext[全文搜索<br/>PostgreSQL tsvector]
    Vector --> RRF[RRF 融合<br/>倒数排名融合]
    Fulltext --> RRF
    RRF --> Result[最终结果]
```

- **向量检索**: 基于 pgvector 的语义相似度搜索，使用 DashScope text-embedding-v4 模型（1024 维）
- **全文搜索**: PostgreSQL `ts_rank` 和 `plainto_tsquery` 进行关键词匹配
- **RRF 融合**: Reciprocal Rank Fusion 算法合并结果
  ```
  RRF 公式: score = 1.0 / (rank_k + i + 1)
  其中 rank_k = 60（超参数），i 是排名位置
  ```
- **检索编排**: `RetrievalOrchestrator` 统一管理向量检索、全文搜索和结果融合

### 记忆系统

**双层记忆架构：**

1. **短期记忆**: Redis Checkpointing
   - 保存对话状态和 Agent 执行历史
   - 支持会话恢复（通过 thread_id）
   - LangGraph 原生支持

2. **长期记忆**: PostgreSQL Store (LangGraph PostgresStore)
   - 保存用户偏好、历史对话、重要约定
   - 支持向量化检索（基于 embedding 索引）
   - 通过 `memory_retrieval_node` 节点访问

**记忆保存策略：**
- LLM 在 `generate_response` 节点自动判断是否值得保存
- 只保存有价值的对话内容（避免无关信息污染）
- 使用 `save_conversation_memory` 工具进行存储

### WebSocket 实时通信

**连接管理：**
- `ConnectionManager` 管理活跃连接
- 每个用户独立的 graph 实例缓存
- 支持心跳保持（ping/pong）

**消息类型：**

| 类型 | 用途 |
|------|------|
| `connected` | 连接成功确认 |
| `user_message` | 用户发送消息 |
| `agent_step` | Agent 执行步骤通知（流式） |
| `agent_complete` | Agent 执行完成（含最终答案） |
| `error` | 错误消息 |
| `ping/pong` | 心跳保持连接 |

**消息流：**
```
WebSocket 连接
     ↓
接收消息: {"type": "user_message", "content": "..."}
     ↓
handle_user_message()
     ↓
graph.stream() 获取执行流
     ↓
流式发送 AgentStepMessage（每个节点执行）
     ↓
发送 AgentCompleteMessage（最终答案）
```

### 文件处理

- **支持格式**: PDF, DOCX, TXT, MD, CSV
- **智能切分**: 根据文件类型自动选择分隔符和块大小
- **元数据丰富**: 包含文件ID、用户ID、块索引、内容哈希
- **摘要生成**: 自动生成文档摘要用于快速预览

### 存储设计

- **文件内容**: PostgreSQL BLOB 存储
- **向量数据**: pgvector
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

2. 编辑 `.env` 文件，填入必要配置
```env
# 阿里云 API 配置
DASHSCOPE_API_KEY=your_dashscope_api_key

# Tavily 网络搜索（可选）
TAVILY_API_KEY=your_tavily_api_key

# 数据库连接
REDIS_URL=redis://localhost:6379/0
POSTGRESQL_URL=postgresql://user:pass@localhost:5432/buddy-ai

# 向量数据库配置（PostgreSQL+pgvector）
PGVECTOR_COLLECTION_NAME=buddy_ai_docs

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
│   │   ├── api/v1/              # API 路由
│   │   │   ├── chat.py          # WebSocket 聊天
│   │   │   ├── files.py         # 文件上传与管理
│   │   │   ├── sessions.py      # 会话管理
│   │   │   └── memory.py        # 记忆管理
│   │   ├── agent/               # LangGraph Agent 核心模块
│   │   │   ├── graph.py         # Agent 工作流图（并行节点定义、边定义）
│   │   │   ├── state.py         # Agent 状态定义（AgentState, GradeDocuments）
│   │   │   ├── parallel_routing_node.py # 并行路由节点（判断需要检索记忆和/或文档）
│   │   │   ├── memory_retrieval_node.py # 记忆检索节点
│   │   │   ├── document_retrieval_node.py # 文档检索节点（混合检索）
│   │   │   ├── grade_documents.py # 文档评分节点
│   │   │   ├── rewrite_question_node.py # 问题重写节点（智能重写策略）
│   │   │   ├── generate_response_node.py # 响应生成节点
│   │   │   └── workflow_diagram.py # 工作流程图生成
│   │   ├── tools/               # 工具定义
│   │   │   ├── system_tool.py   # 系统工具（clear_conversation, update_user_name, retrieve_context）
│   │   │   ├── user_tool.py     # 用户工具（save_conversation_memory）
│   │   │   ├── web_search_tool.py # Tavily 网络搜索
│   │   │   └── __init__.py
│   │   ├── services/            # 业务服务层
│   │   │   ├── fulltext_search_service.py  # PostgreSQL 全文搜索（ts_rank）
│   │   │   ├── retrieval_orchestrator.py   # 混合检索编排（向量+全文+RRF）
│   │   │   ├── vectorization_service.py    # 异步向量化服务
│   │   │   ├── user_file_service.py        # 用户文件管理
│   │   │   └── pgvector_singleton.py       # pgvector 单例
│   │   ├── retriever/           # 检索模块
│   │   │   ├── pgvector_store.py # PostgreSQL 向量存储（pgvector）
│   │   │   ├── get_retriever.py # 检索器配置
│   │   │   ├── vectorize_files.py # 文件向量化
│   │   │   └── embeddings_model.py # DashScope 嵌入模型（text-embedding-v4）
│   │   ├── memory/              # 记忆管理
│   │   │   ├── memory_service.py    # 记忆服务（PostgreSQL Store）
│   │   │   └── memory_schema.py     # 记忆数据模型
│   │   ├── llm/                 # LLM 工厂
│   │   │   └── llm_factory.py   # Qwen 模型工厂（DashScope OpenAI API）
│   │   ├── prompt/              # 提示词
│   │   │   └── prompt.py        # 系统提示词模板
│   │   ├── utils/               # 工具函数
│   │   │   ├── datetime_utils.py   # 日期时间工具
│   │   │   └── document_processing.py # 文档处理工具
│   │   └── models/              # Pydantic 模型
│   │       ├── chat.py          # 聊天消息模型
│   │       ├── session.py       # 会话模型
│   │       ├── file.py          # 文件模型
│   │       └── user_file.py     # 用户文件模型
│   ├── requirements.txt         # Python 依赖
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

启动后端后访问 http://localhost:8000/docs 查看 Swagger API 文档（仅在 DEBUG 模式下可用）。

### WebSocket 聊天

**端点**: `ws://localhost:8000/api/v1/chat/ws/{user_id}?thread_id=可选的会话ID`

**发送消息**:
```json
{
  "type": "user_message",
  "content": "你好",
  "thread_id": "可选的会话ID（与URL参数二选一）"
}
```

**心跳保持**:
```json
{"type": "ping"}
```

**响应消息类型**:

| 类型 | 说明 |
|------|------|
| `connected` | 连接成功 |
| `pong` | 心跳响应 |
| `agent_step` | Agent 执行步骤（流式） |
| `agent_complete` | Agent 执行完成，包含最终答案 |
| `error` | 错误消息 |

**agent_step 格式**:
```json
{
  "type": "agent_step",
  "node": "agent_step",
  "message_type": "AIMessage",
  "content": "...",
  "tool_calls": [
    {
      "name": "tavily_search",
      "args": {"query": "..."}
    }
  ]
}
```

**agent_complete 格式**:
```json
{
  "type": "agent_complete",
  "final_answer": "这是最终答案...",
  "thread_id": "会话ID"
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

#### Agent 层 ([app/agent/](backend/app/agent/))

| 文件 | 功能 | 说明 |
|------|------|------|
| `graph.py` | Agent 工作流图 | 定义并行节点、边和条件路由，构建 LangGraph StateGraph |
| `state.py` | Agent 状态定义 | `AgentState` 继承 `MessagesState`，包含并行结果、循环控制等 |
| `parallel_routing_node.py` | 并行路由节点 | LLM 判断需要并行检索哪些来源（记忆/文档） |
| `memory_retrieval_node.py` | 记忆检索节点 | 使用 PostgreSQL Store 检索用户长期记忆 |
| `document_retrieval_node.py` | 文档检索节点 | 执行混合检索 |
| `grade_documents.py` | 文档评分节点 | LLM 评估检索文档相关性 |
| `rewrite_question_node.py` | 问题重写节点 | 智能重写问题（关键词提取/简化策略） |
| `generate_response_node.py` | 响应生成节点 | 根据并行检索结果生成最终响应 |

#### 工具层 ([app/tools/](backend/app/tools/))

| 工具 | 功能 | 说明 |
|------|------|------|
| `system_tool.py` | 系统工具 | 清空对话、更新用户名、检索上下文、retriever_tool |
| `user_tool.py` | 用户工具 | 天气查询、记忆检索/保存、对话记忆保存 |
| `web_search_tool.py` | 网络搜索 | Tavily API 实时搜索（最多 3 个结果） |

#### 服务层 ([app/services/](backend/app/services/))

| 服务 | 功能 | 关键方法 |
|------|------|----------|
| `fulltext_search_service.py` | PostgreSQL 全文搜索 | `search(query, user_id, k)` 使用 ts_rank 排序 |
| `retrieval_orchestrator.py` | 混合检索编排 | `retrieve()` 整合向量+全文+RRF 融合 |
| `vectorization_service.py` | 异步向量化服务 | `vectorize_file()` 带进度追踪 |
| `user_file_service.py` | 用户文件管理 | `save_file()`, `delete_file()` |
| `pgvector_singleton.py` | pgvector 单例 | `get_vector_store()` 获取向量存储实例 |

#### 检索流程

```
1. parallel_routing_node 判断需要并行检索哪些来源
         ↓
   ┌────┴────┐
   ↓         ↓
记忆检索    文档检索
   │         │
   └────┬────┘
        ↓
2. 生成响应节点整合并行结果
         ↓
3. grade_documents 评估文档相关性（如检索了文档）
         ↓
4. 相关 → generate_response
   不相关 → rewrite_question → document_retrieval（循环，最多3次）
```

#### 向量化流程

1. 文件上传到 PostgreSQL BLOB
2. 创建向量化任务记录
3. 异步处理：文档加载 → 智能切分 → 向量化 → 摘要生成
4. 实时进度更新
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

### PostgreSQL+pgvector

```env
POSTGRESQL_URL=postgresql://user:pass@localhost:5432/buddy-ai
PGVECTOR_COLLECTION_NAME=buddy_kb
```

**初始化**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```


## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License