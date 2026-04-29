# Buddy-AI 智能问答知识助手

基于 LangGraph 的中文智能问答系统，支持混合检索（Dense 向量 + Sparse BM25 + RRF 融合 + 文本匹配）、Plan-and-Execute 任务规划、Reflection 自我改进、网络搜索和双层记忆（短期 Redis + 长期 Mem0）功能。

## LangGraph 工作流程

![LangGraph 工作流程图](docs/langgraph_workflow.png)

#### 节点说明

| 节点 | 文件 | 功能 |
|------|------|------|
| `retrieve_memories` | `nodes/memory.py` | 从 Mem0 检索用户长期记忆（相似度阈值 0.7，最多 3 条） |
| `router` | `nodes/router.py` | LLM 结构化输出（`json_mode`）判断查询类型，路由到 knowledge_base_search / plan_and_execute / answer_directly |
| `query_transform` | `nodes/query_transformer.py` | 直接回答路径的查询改写：指代消解 → Step-Back Prompting → 查询扩展，LLM 结构化输出 |
| `query_transform_HyDE` | `nodes/retriever.py` | 知识库检索路径的查询转换：指代消解 + HyDE（假设性文档嵌入），生成假设性文档片段 |
| `hybrid_search` | `nodes/retriever.py` | Milvus Dense 向量 + Sparse BM25 混合检索（RRF 融合），HyDE 增强时额外向量检索并合并 |
| `text_match` | `nodes/retriever.py` | jieba 分词提取关键词 + Milvus TEXT_MATCH 文本匹配 + 向量相似性联合检索 |
| `generate_response` | `nodes/generate_response.py` | ReAct 模式响应生成，支持工具调用，含 Chain-of-Thought 推理和消息摘要压缩 |
| `planner` | `nodes/planner.py` | 复杂任务拆解为 2-5 个可独立执行的步骤（LLM 结构化输出） |
| `work_step` | `nodes/planner.py` | 通过 Send() API 并行执行计划中的各步骤 |
| `synthesis_step_results` | `nodes/planner.py` | 汇总所有步骤执行结果为最终答案 |
| `evaluate_node` | `nodes/evaluator.py` | Reflection 评估答案质量（相关性 / 事实准确性 / 完整性 / 逻辑一致性），不通过则带反馈重新生成（最多 3 次） |
| `tool_node` | LangGraph ToolNode | 执行工具调用（Tavily Search Top 5 / Wikipedia） |
| `save_memories` | `nodes/memory.py` | 语义去重（阈值 0.95）后存储本轮对话到 Mem0 长期记忆 |

#### 条件路由

| 路由函数 | 位置 | 逻辑 |
|----------|------|------|
| `route_condition` | `condition.py` | router → knowledge_base_search 走 `query_transform_HyDE` / plan_and_execute 走 `planner` / answer_directly 走 `query_transform` |
| `generate_response_router` | `condition.py` | generate_response → `tool_node`（有工具调用）/ `evaluate_node`（需评估且 < 3 次）/ `save_memories`（完成） |
| `assign_workers` | `condition.py` | planner → 通过 Send() API 并行分发 `work_step` |

#### GraphState 状态

```python
class GraphState(MessagesState):
    memory_context: str | None           # Mem0 记忆上下文
    route_decision: str                  # 路由决策 (answer_directly / knowledge_base_search / plan_and_execute)
    route_reason: str | None             # 路由决策理由
    original_input: str                  # 用户原始输入
    enhanced_input: str | None           # 增强后的查询（Query Transform / HyDE 结果）
    rag_docs: list[dict]                 # 检索到的文档（merge_rag_docs 自动按 ID 去重合并）
    plan: PlanSchema | None              # 任务执行计划（含步骤编号和描述）
    step_results: list[str] | None       # 各步骤执行结果（operator.add 累加）
    reflection_count: int                # 反思次数（最多 3 次）
    reflection: ReflectionState | None   # 反思评估结果（passed + feedback）
    draft_answer: str | None             # 草稿答案
    final_answer: str | None             # 最终答案
```

## 项目架构

- **后端**: FastAPI + LangGraph（`main.py` 入口 + `apps/` 模块）
- **前端**: Vue 3 + Vite + TypeScript + Pinia + Element Plus（`frontend/`）
- **LLM**: OpenAI / 阿里云 DashScope (Qwen) / 智谱 AI，通过 LLM Factory 统一切换
- **向量库**: Milvus 2.5+（混合检索：Dense + Sparse BM25 + RRF 融合 + TEXT_MATCH 文本匹配）
- **Embedding**: OpenAI text-embedding-3-large（1024 维），备选 Qwen3-Embedding 本地模型（last-token 池化）
- **长期记忆**: Mem0 + Milvus 向量存储（语义去重）
- **短期记忆**: Redis Checkpointing（LangGraph 原生 `AsyncRedisSaver`，全异步）
- **数据库**: MySQL（知识库文件元数据 + 用户管理，SQLAlchemy AsyncSession）
- **消息压缩**: LLM 摘要压缩，保留最近 5 条消息，旧消息生成摘要
- **包管理**: uv（`pyproject.toml`）

## 核心特性

- 🤖 **智能路由**: LLM 结构化输出（`with_structured_output` + `json_mode`）自动分类查询，三路动态路由
- 📚 **混合检索**: Milvus Dense 向量 + Sparse BM25 + RRF 融合 + TEXT_MATCH 文本匹配，`hybrid_search` 和 `text_match` 并行执行
- 🔄 **查询增强**: 直接回答路径使用指代消解 + Step-Back Prompting + 查询扩展；知识库检索路径使用指代消解 + HyDE（假设性文档嵌入）
- 🔍 **网络搜索**: Tavily Search（Top 5 结果）+ Wikipedia 实时搜索（ReAct 工具调用）
- 💾 **双层记忆**: 短期 Redis Checkpoint + 长期 Mem0 向量记忆（语义去重，阈值 0.95）
- 📋 **任务规划**: Plan-and-Execute 模式，LLM 结构化拆解 2-5 个子任务，Send() API 并行执行
- 🔁 **自我改进**: Reflection 机制四维评估（相关性 / 事实准确性 / 完整性 / 逻辑一致性），最多 3 次迭代优化
- 💬 **流式输出**: SSE 实时推送 Agent 增量 token（FastAPI `EventSourceResponse` + `astream` 全异步 + 前端 fetch ReadableStream + 空闲超时保护）
- 📝 **消息压缩**: 超过 5 条消息自动 LLM 摘要压缩，安全切割避免拆分 `AIMessage(tool_calls)` 和 `ToolMessage` 对
- 📄 **知识库管理**: 支持 txt / docx / md 文件上传、下载、删除，MD5 去重检测，智能分割入库
- 🎨 **现代化 UI**: ChatGPT 风格界面，Element Plus 暗黑主题切换，Markdown 渲染 + DOMPurify XSS 防护

## 技术亮点

### LangGraph 智能体架构

- **三路路由**: LLM `with_structured_output`（`json_mode`）→ 直接回答 / 知识库检索 / 任务规划执行
- **双查询增强策略**: `query_transform` 节点（指代消解 + Step-Back + 查询扩展）和 `query_transform_HyDE` 节点（指代消解 + HyDE）分别服务不同路由路径
- **ReAct 模式**: `generate_response` 节点通过 `bind_tools` 支持工具调用（Tavily Search、Wikipedia），内置 Chain-of-Thought 五步推理
- **Reflection**: `evaluate_node` 四维评估（相关性 / 事实准确性 / 完整性 / 逻辑一致性），不通过则带 feedback 重新生成，最多 3 次
- **Plan-and-Execute**: 复杂任务 LLM 结构化拆解为 2-5 个子任务，`Send()` API 并行执行步骤并汇总
- **状态持久化**: `AsyncRedisSaver` 全异步支持多轮对话上下文恢复（通过 `thread_id`），配合 `astream` / `aget_state` 避免阻塞事件循环
- **消息摘要**: `RemoveMessage` + `SystemMessage` 实现对话历史压缩，`_find_safe_split_index` 安全切割保护工具调用链

### 混合检索架构

```mermaid
graph LR
    Query[用户查询] --> HyDE[Query Transform HyDE<br/>指代消解 + 假设性文档]
    HyDE --> Dense[Dense 向量检索<br/>Milvus]
    HyDE --> Sparse[Sparse BM25<br/>Milvus 内置]
    HyDE --> TM[文本匹配<br/>jieba 分词 + TEXT_MATCH]
    Dense --> RRF[RRF 融合<br/>RRFRanker 100]
    Sparse --> RRF
    RRF --> Merge[去重合并<br/>merge_rag_docs]
    HyDE -->|HyDE 向量检索| Merge
    TM --> Merge
    Merge --> Result[最终结果]
```

- **向量检索**: Milvus Dense 检索，OpenAI text-embedding-3-large（1024 维），`AUTOINDEX` 自动索引
- **BM25 检索**: Milvus 内置 Sparse BM25 函数（`SPARSE_INVERTED_INDEX` + `DAAT_MAXSCORE`）
- **文本匹配**: jieba 分词 + 停用词过滤提取关键词 → Milvus `TEXT_MATCH`（中文 Analyzer）+ 向量相似性联合检索
- **RRF 融合**: `RRFRanker(100)` 合并 Dense 和 Sparse 两路结果
- **HyDE 增强**: 当走知识库检索路径时，额外用假设性文档进行向量检索（`vector_search`）并合并到 `hybrid_search` 结果
- **去重合并**: `merge_rag_docs` 按文档 ID 自动去重（GraphState 的 `Annotated` reducer）

### 文档处理

- **txt / docx**: `RecursiveCharacterTextSplitter`，中文友好分隔符（`\n\n`、`\n`、`。`、`！`、`？`、`.`、`!`、`?`）
- **Markdown**: `MarkdownHeaderTextSplitter`（按 h1/h2/h3 拆分）+ 二次 `RecursiveCharacterTextSplitter`
- **默认参数**: `chunk_size=500`，`chunk_overlap=0`（上传接口使用 `chunk_size=200`）
- **Embedding**: OpenAI `text-embedding-3-large`（1024 维），备选 `Qwen3-Embedding`（last-token 池化，支持 Flash Attention）

### 记忆系统

**双层记忆架构：**

1. **短期记忆**: Redis Checkpointing
   - LangGraph `AsyncRedisSaver` 全异步支持，保存完整对话状态和执行历史
   - 通过 `thread_id` 恢复会话上下文
   - 在 FastAPI `lifespan` 中通过 `async with` 初始化，应用退出时自动关闭连接

2. **长期记忆**: Mem0 + Milvus
   - `retrieve_memories`: 每次对话开始时检索相关记忆（阈值 0.7，最多 3 条）
   - `save_memories`: 对话结束后存储，语义去重（阈值 0.95）避免重复
   - 自动保存用户偏好、历史对话、重要约定
   - `MemoryManager` 单例模式，在 `lifespan` 中初始化

3. **消息压缩**: LLM 摘要
   - 超过 5 条消息时自动触发（`KEEP_RECENT = 5`）
   - `RemoveMessage` 删除旧消息 + `SystemMessage` 插入摘要
   - `_find_safe_split_index`：安全切割，不拆分 `AIMessage(tool_calls)` 和 `ToolMessage` 对

### SSE 流式通信

**接口**: `POST /agent/chat`（`EventSourceResponse`）

**请求体**:
```json
{
  "user_id": "用户ID（1-64字符）",
  "thread_id": "会话ID（1-64字符）",
  "user_input": "用户消息（1-10000字符）"
}
```

**响应**: SSE 流式事件（`astream` + `stream_mode="messages"`，全异步）

| 事件 | 说明 |
|------|------|
| `workflow_node` | 增量 token（`content` 为文本片段，`node` 为当前节点名） |
| `final_answer` | 最终完整答案（通过 `await aget_state()` 从 `GraphState.final_answer` 获取） |
| `error` | 错误信息 |

**连接管理**:
- 后端使用 `compiled_graph.astream()` + `await compiled_graph.aget_state()` 全异步流式输出，不阻塞事件循环
- 后端捕获 `asyncio.CancelledError` 优雅处理客户端断开（路由切换、连续发送、删除线程等场景）
- 前端禁用 axios 全局 30s 请求超时（`timeout: 0`），改用 120 秒空闲超时（idle timeout）保护：连续无数据时主动断开并提示用户

### 知识库管理

**API 路由前缀**: `/knowledgebase`

| 接口 | 方法 | 说明 |
|------|------|------|
| `/upload_file` | POST | 上传文件（multipart/form-data），支持 txt/docx/md，MD5 去重检测 |
| `/get_files` | GET | 获取知识库文件列表 |
| `/delete_file` | POST | 删除文件（同时删除 Milvus 向量数据） |
| `/download_file` | GET | 下载文件（支持中文文件名） |

**上传流程**: 文件上传 → MD5 校验去重 → 文本提取 → 文档分割 → Embedding → Milvus 入库

**数据存储**: MySQL 存储文件元数据和原始内容（`LargeBinary`），Milvus 存储向量数据

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- Redis（会话状态持久化）
- MySQL（知识库文件元数据存储）
- Milvus 2.5+（向量存储 + BM25 + 文本匹配）
- API Key（OpenAI / DashScope，至少一个）
- Tavily API Key（可选，网络搜索）

### 安装

1. 克隆项目
```bash
git clone https://github.com/your-repo/buddy-ai.git
cd buddy-ai
```

2. 安装后端依赖
```bash
uv sync
```

3. 安装前端依赖
```bash
cd frontend
npm install
```

### 配置

编辑项目根目录 `.env` 文件：

```env
# ========== LLM 配置 ==========
LLM_PROVIDER=openai              # openai / dashscope
LLM_MODEL=gpt-5.2

# ========== API Keys ==========
OPENAI_API_KEY=your_openai_key
DASHSCOPE_API_KEY=your_dashscope_key          # 阿里云 DashScope（可选）
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ZHIPUAI_API_KEY=your_zhipuai_key              # 智谱 AI（可选）
ZHIPUAI_URL=https://open.bigmodel.cn/api/paas/v4/
TAVILY_API_KEY=your_tavily_key                # 网络搜索（可选）

# ========== 数据库配置 ==========
REDIS_URL=redis://localhost:6379/0
MYSQL_URL=mysql+aiomysql://root:password@localhost:3306/buddy_ai?charset=utf8

# ========== Milvus 向量库配置 ==========
MILVUS_URL=http://localhost:19530
MILVUS_TOKEN=
MILVUS_DB_NAME=buddy_ai
MILVUS_MEM0_COLLECTION_NAME=mem0

# ========== Embedding 配置 ==========
EMBEDDING_PROVIDER=openai         # openai / huggingface
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=1024

# ========== 日志配置 ==========
LOG_LEVEL=INFO

# ========== LangSmith（可选，调试追踪）==========
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=buddy-ai
```

### 运行

1. 启动后端
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

2. 启动前端
```bash
cd frontend
npm run dev
```

### 访问

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 项目结构

```
buddy-ai/
├── main.py                          # FastAPI 入口（lifespan 初始化 DB/Graph/Memory，AsyncRedisSaver 全异步）
├── apps/
│   ├── config.py                    # Pydantic Settings 配置管理（.env 加载，支持 OpenAI/DashScope/智谱）
│   ├── exceptions.py                # 自定义异常（NotFoundError 404 / DatabaseError 500）
│   ├── models/
│   │   └── request_params.py        # 请求参数模型（ChatParams / DeleteFileParams，含字段校验）
│   ├── database/
│   │   ├── async_engine.py          # SQLAlchemy AsyncSession（MySQL 连接池，自动 commit/rollback）
│   │   └── models.py               # ORM 模型（User / KnowledgeBase / KnowledgeBaseFile）
│   ├── api/
│   │   ├── agent_chat.py            # SSE 对话接口（/agent/chat，astream 全异步 + CancelledError 优雅断开）
│   │   └── knowledgebase.py         # 知识库 CRUD（上传/列表/删除/下载，MD5 去重）
│   └── agent/
│       ├── graph.py                 # StateGraph 工作流（13 个节点、条件路由、AsyncRedisSaver 单例）
│       ├── state.py                 # GraphState + Schema 定义（Route/QueryTransform/Plan/Reflection）
│       ├── condition.py             # 条件路由函数（route_condition / generate_response_router / assign_workers）
│       ├── workflow_diagram.py      # LangGraph 流程图 PNG 生成工具
│       ├── nodes/
│       │   ├── router.py            # 智能路由（LLM json_mode 结构化输出 → 三路分类）
│       │   ├── query_transformer.py # 查询改写（指代消解 / Step-Back Prompting / 查询扩展）
│       │   ├── retriever.py         # 检索节点（query_transform_HyDE / hybrid_search / text_match）
│       │   ├── generate_response.py # ReAct 响应生成（bind_tools + CoT 推理 + 消息摘要压缩）
│       │   ├── planner.py           # Plan-and-Execute（plan_step / work_step / synthesis）
│       │   ├── evaluator.py         # Reflection 四维评估（LLM json_mode 结构化输出）
│       │   ├── memory.py            # 记忆检索（retrieve_memories）与存储（save_memories）
│       │   └── message_summarizer.py # 消息摘要节点（已弃用，功能移至 utils）
│       ├── llm/
│       │   └── llm_factory.py       # LLM 工厂（OpenAI / DashScope，统一 ChatOpenAI 接口）
│       ├── memory/
│       │   └── mem0.py              # Mem0 长期记忆单例（Milvus 向量存储，lifespan 初始化）
│       ├── rag/
│       │   ├── milvus_vector.py     # Milvus 客户端（Collection 初始化 / Dense+BM25 混合检索 / 文本匹配 / 文档 CRUD）
│       │   ├── document_split.py    # 文档分割（txt/docx → Recursive / md → Header + Recursive）
│       │   └── qwen3_embedding.py   # Qwen3-Embedding 本地模型（last-token 池化，备选方案）
│       ├── tools/
│       │   └── tools.py             # 工具定义（Tavily Search max_results=5 / Wikipedia）
│       ├── prompt/
│       │   └── prompt.py            # 系统提示词模板（预留）
│       └── utils/
│           ├── message_summarizer.py # 消息摘要压缩（RemoveMessage + SystemMessage，安全切割）
│           └── id_util.py           # Snowflake ID 生成器
├── frontend/                        # Vue 3 前端
│   ├── index.html
│   ├── package.json                 # 依赖：vue3 / pinia / element-plus / markdown-it / dompurify / nanoid / axios
│   ├── vite.config.ts               # Vite 配置（/agent + /knowledgebase 代理到后端）
│   ├── .env.development             # 开发环境（VITE_API_BASE_URL=http://localhost:8000）
│   ├── .env.production              # 生产环境配置
│   └── src/
│       ├── main.ts                  # 入口（Vue Router + Pinia + Element Plus 暗黑主题 CSS）
│       ├── App.vue                  # 根组件（Sidebar + RouterView 布局，初始化主题和用户状态）
│       ├── config/env.ts            # 环境变量校验与导出
│       ├── router/index.ts          # 路由（/ 欢迎页、/chat/:threadId 对话页、404 重定向）
│       ├── stores/
│       │   ├── chat.ts              # ChatStore（线程 CRUD / 消息追加 / 流式状态 / localStorage 持久化）
│       │   └── user.ts              # UserStore（userId / 主题切换 / kbRefreshCount / localStorage 持久化）
│       ├── services/
│       │   ├── request.ts           # axios 实例（开发环境 proxy / 生产环境 baseURL / 响应拦截器 / 30s 超时）
│       │   ├── sse.ts               # SSE 客户端（axios + ReadableStream，POST 请求，标准 SSE 解析，120s 空闲超时保护）
│       │   └── api.ts               # 知识库 API（文件上传/列表/删除/下载，扩展名校验）
│       ├── views/
│       │   ├── WelcomePage.vue      # 欢迎页（居中标题 + 输入框，发送后自动创建线程跳转）
│       │   └── ChatPage.vue         # 对话页（ChatWindow + ChatInput + SSE 集成 + pendingSend 自动发送）
│       ├── components/
│       │   ├── Sidebar.vue          # 侧边栏（项目名 + 设置 + 新建对话 + 对话列表 + 知识库文件管理）
│       │   ├── SidebarSettings.vue  # 设置区域（User ID 输入 + 主题切换）
│       │   ├── ThemeSwitcher.vue    # 主题切换（el-switch 🌙/☀️）
│       │   ├── ChatWindow.vue       # 聊天窗口（消息气泡 + markdown-it 渲染 + DOMPurify XSS 防护 + 自动滚动 + 打字指示器）
│       │   └── ChatInput.vue        # 消息输入（textarea 自适应 + 文件上传 + Enter 发送 + Shift+Enter 换行）
│       ├── types/index.ts           # TypeScript 类型定义（Message / Thread / SSEJsonLine / KnowledgeFile）
│       └── assets/styles/main.css   # 全局样式（暗黑主题 / 滚动条 / 布局）
├── docs/                            # 文档
│   └── langgraph_workflow.png       # LangGraph 工作流程图
├── pyproject.toml                   # Python 依赖（uv 管理，Python 3.12+）
└── .env                             # 环境变量配置
```


## 开发指南

### 后端开发

```bash
# 安装依赖
uv sync

# 启动开发服务器
uvicorn main:app --reload --port 8000

# 添加新依赖
uv add package_name

# 生成 LangGraph 工作流程图
python -m apps.agent.workflow_diagram
```

### 代码质量

项目使用 `ruff`（lint + 格式化）和 `mypy`（类型检查）保证代码质量。

```bash
# 检查代码问题
ruff check .

# 自动修复可修复的问题
ruff check --fix .

# 格式化代码（替代 black + isort）
ruff format .

# 类型检查
mypy apps/
```

日常开发流程：写完代码后执行 `ruff check --fix . && ruff format .` 格式化，提交前执行 `mypy apps/` 检查类型。

ruff 规则配置在 `pyproject.toml` 的 `[tool.ruff]` 中，当前启用的规则集：
- `E` / `F` / `W` — 基础错误和警告
- `I` — import 排序（替代 isort）
- `N` — 命名规范
- `UP` — 自动升级旧语法
- `B` — bugbear（常见 bug 模式）
- `SIM` — 简化代码建议

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 类型检查 + 构建
npm run build
```

**前端技术栈**:
- Vue 3 Composition API + TypeScript
- Pinia 状态管理（localStorage 持久化）
- Element Plus UI 组件库（含暗黑主题 CSS 变量）
- markdown-it Markdown 渲染 + DOMPurify XSS 防护（白名单标签 + 属性过滤 + 危险协议拦截）
- axios HTTP 客户端 + SSE 流式通信（fetch + ReadableStream，标准 SSE 格式解析，120s 空闲超时保护）
- Vue Router 4（欢迎页 + 对话页 + 404 重定向）
- nanoid 生成线程 ID
- Vite 开发服务器代理（`/agent` + `/knowledgebase` → 后端 8000）

### LLM Provider 切换

在 `.env` 中修改 `LLM_PROVIDER`：

| Provider | 配置值 | 所需 Key | 默认模型 |
|----------|--------|----------|----------|
| OpenAI | `openai` | `OPENAI_API_KEY` | `gpt-5.2` |
| 阿里云 DashScope | `dashscope` | `DASHSCOPE_API_KEY` | `qwen-plus` |

LLM Factory 统一使用 `ChatOpenAI` 接口，DashScope 通过兼容模式（`openai_api_base`）接入。

### 主要依赖

**后端（Python）**:
- `fastapi[standard]` - Web 框架
- `langgraph` + `langgraph-checkpoint-redis` - 智能体工作流 + Redis 状态持久化
- `langchain` + `langchain-openai` + `langchain-community` + `langchain-tavily` - LLM 框架 + 工具链
- `pymilvus[model]` - Milvus 向量数据库客户端
- `mem0ai` - 长期记忆管理
- `sqlalchemy[asyncio]` + `aiomysql` - 异步 ORM + MySQL 驱动
- `pydantic-settings` - 配置管理
- `jieba` - 中文分词（关键词提取）
- `python-docx` - DOCX 文件解析
- `torch` + `transformers` - Qwen3-Embedding 本地模型（备选）
- `snowflake-id` - 分布式 ID 生成
- `ruff` - 代码 lint + 格式化（替代 black / isort / flake8）
- `mypy` - 静态类型检查

**前端（Node.js）**:
- `vue` 3.5 + `vue-router` 4 + `pinia` - 核心框架
- `element-plus` - UI 组件库
- `axios` - HTTP 客户端
- `markdown-it` + `dompurify` - Markdown 渲染 + XSS 防护
- `nanoid` - ID 生成

## 许可证

MIT License
