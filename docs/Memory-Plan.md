# LangGraph 流程优化实施计划（并行架构版）

## Context

**优化目标**：将记忆检索前置到流程开始，优化RAG决策逻辑，统一答案生成节点，利用LangGraph并行执行机制提升性能和用户体验。

**当前问题**：
- 记忆检索依赖LLM工具调用，无法保证优先使用
- RAG决策只有LLM判断，记忆和RAG检索串行执行
- 存在两个答案生成节点（generate_answer 和 generate_response），逻辑重复
- 记忆数据结构简单，无法分类和标签化管理
- 记忆和RAG检索无法并行执行

**预期收益**：
- 性能提升：需要双重检索时并行执行节省~100ms
- 体验优化：记忆始终作为上下文可用
- 架构简化：减少节点数量，统一逻辑
- 并行执行：记忆和知识库检索可同时进行

## 新架构概览

```
START
    ↓
routing_node (新增智能路由节点)
    ├─ 需要记忆检索? → memory_retrieval_node
    ├─ 需要RAG检索? → retrieval_node
    ├─ 直接回答? → generate_response
    └─ 需要记忆 AND RAG? → 并行执行 (fan-out)
        ├→ memory_retrieval_node
        └→ retrieval_node
            ↓
        fan-in → grade_documents → generate_response
```

**关键优势**：
1. **并行检索性能**：记忆和RAG可并行执行，节省~200ms
2. **灵活路由**：LLM智能判断需要哪些检索
3. **LangGraph原生支持**：无需复杂配置，使用send()函数实现并行

## 修改范围

### 文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `backend/app/agent/state.py` | 修改 | 添加 `user_memories` 字段，添加 `retrieval_needed` 字段 |
| `backend/app/agent/routing_node.py` | 新建 | 智能路由节点（并行决策，替代 retrieval_decision） |
| `backend/app/agent/memory_node.py` | 新建 | 记忆检索节点（使用 runtime.store） |
| `backend/app/agent/node.py` | 修改 | 删除 generate_answer，修改 generate_response |
| `backend/app/agent/graph.py` | 修改 | 更新流程：添加路由节点、并行边、删除 retrieval_decision 和 generate_answer |
| `backend/app/memory/` | 新建目录 | 记忆服务层 |
| `backend/app/memory/memory_schema.py` | 新建 | 记忆数据模型和分类定义 |
| `backend/app/memory/memory_service.py` | 新建 | 记忆服务（检索、保存） |
| `backend/app/memory/memory_factory.py` | 新建 | PostgresStore 连接池管理（单例） |
| `backend/app/prompt/prompt.py` | 修改 | 添加记忆分类/标签生成提示词、路由提示词 |
| `backend/app/tools/user_tool.py` | 修改 | 使用 MemoryService 保存/检索记忆 |
| `backend/app/agent/retrieval_node.py` | 删除 | retrieval_decision 相关逻辑移至 routing_node |

## 详细实施步骤

### 步骤1：添加记忆数据模型

**文件**: `backend/app/memory/memory_schema.py` (新建)

```python
from enum import Enum
from typing import List
from pydantic import BaseModel, Field

class MemoryCategory(str, Enum):
    """记忆主分类"""
    PROFILE = "profile"
    PREFERENCE = "preference"
    SCHEDULE = "schedule"
    FACT = "fact"
    RELATIONSHIP = "relationship"
    OTHER = "other"

class MemoryData(BaseModel):
    """记忆数据模型（不存储原始问题）"""
    data: str = Field(description="记忆内容摘要")
    category: MemoryCategory = Field(description="主分类")
    tags: List[str] = Field(default_factory=list, description="自由标签")
    timestamp: str = Field(description="创建时间")

class RetrievalDecision(BaseModel):
    """检索决策结果"""
    need_memory: bool = Field(description="是否需要检索记忆")
    need_rag: bool = Field(description="是否需要检索知识库")
    reason: str = Field(description="决策原因")
```

### 步骤2：添加记忆工厂（连接池管理 + 向量索引）

**文件**: `backend/app/memory/memory_factory.py` (新建)

```python
"""记忆工厂 - 单例 PostgresStore 配合向量索引"""
from typing import Optional

from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore

from ..config import settings
from ..retriever.embeddings_model import get_embeddings_model


class MemoryFactory:
    """PostgresStore 单例工厂 - 使用阿里 DashScope 嵌入模型"""

    _instance: Optional[PostgresStore] = None
    _embeddings_model = None

    @classmethod
    def _get_embeddings(cls):
        """延迟加载嵌入模型（阿里 DashScope）"""
        if cls._embeddings_model is None:
            cls._embeddings_model = get_embeddings_model()
        return cls._embeddings_model

    @classmethod
    def _embed_function(cls, texts: list[str]) -> list[list[float]]:
        """PostgresStore 向量索引的嵌入函数"""
        embeddings = cls._get_embeddings()
        return embeddings.embed_documents(texts)

    @classmethod
    def get_store(cls) -> PostgresStore:
        """获取带向量索引的 PostgresStore 单例"""
        if cls._instance is None:
            cls._instance = PostgresStore.from_conn_string(
                settings.POSTGRESQL_URL,
                index={
                    "embed": cls._embed_function,
                    "dims": settings.EMBEDDING_DIMENSIONS  # 1024 (DashScope text-embedding-v4)
                }
            )
            cls._instance.setup()  # 首次使用时初始化表
        return cls._instance


def get_memory_store() -> PostgresStore:
    """获取记忆存储实例"""
    return MemoryFactory.get_store()


def get_memory():
    """获取 Redis 检查点"""
    return RedisSaver.from_conn_string(settings.REDIS_URL)


def get_store():
    """获取 PostgresStore 实例 - get_memory_store 的别名"""
    return get_memory_store()
```

### 步骤3：添加记忆服务（分类过滤 + 向量搜索）

**文件**: `backend/app/memory/memory_service.py` (新建)

```python
"""记忆服务 - 检索与保存（向量搜索 + 分类过滤）"""
import uuid
from datetime import datetime
from typing import List, Optional
from langgraph.types import BaseStore

from .memory_schema import MemoryCategory, ConversationAnalysis
from ..llm.llm_factory import get_llm
from ..prompt.prompt import CONVERSATION_ANALYSIS_PROMPT


class ConversationAnalysis(BaseModel):
    """对话分析结果"""
    category: MemoryCategory
    tags: List[str]
    summary: str
    should_save: bool


class MemoryService:
    """记忆服务 - 使用 PostgresStore 向量搜索和分类过滤

    基于 LangChain 最佳实践：
    - PostgresStore 作为单例初始化（使用连接池）
    - 使用向量搜索（启用 pgvector）
    - 支持分类过滤
    - 通过 runtime.store 访问（推荐方式）
    """

    def __init__(self):
        self.llm = get_llm()

    def retrieve_memory(
        self,
        store: BaseStore,
        user_id: str,
        query: str,
        category: Optional[MemoryCategory] = None,
        limit: int = 3
    ) -> List[dict]:
        """检索记忆 - 使用 PostgresStore 向量搜索 + 分类过滤

        Args:
            store: PostgresStore 实例（通过 runtime.store 传入）
            user_id: 用户ID
            query: 查询文本（语义搜索）
            category: 可选分类过滤
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        namespace = ("memories", user_id)

        # 构建过滤字典（如果指定了分类）
        filter_dict = None
        if category:
            filter_dict = {"category": category.value}

        # 使用 PostgresStore 向量搜索
        items = store.search(
            namespace,
            query=query,  # 语义搜索
            filter=filter_dict,  # 分类过滤
            limit=limit
        )

        return [
            {
                "key": item.key,
                "data": item.value.get("data"),
                "category": item.value.get("category"),
                "tags": item.value.get("tags", []),
                "timestamp": item.value.get("timestamp")
            }
            for item in items
        ]

    def save_memory(
        self,
        store: BaseStore,
        user_id: str,
        question: str,
        answer: str
    ) -> str:
        """保存记忆"""
        # LLM 分析是否需要保存
        analysis = self._analyze_conversation(question, answer)

        if not analysis.should_save:
            return "对话内容无需保存到长期记忆。"

        # 保存到 PostgresStore（包含向量嵌入）
        namespace = ("memories", user_id)
        store.put(namespace, str(uuid.uuid4()), {
            "data": analysis.summary,
            "category": analysis.category.value,
            "tags": analysis.tags,
            "timestamp": datetime.now().isoformat()
        })

        return f"已保存记忆: {analysis.summary}"

    def _analyze_conversation(self, question: str, answer: str) -> ConversationAnalysis:
        """分析对话，提取需要记住的信息"""
        prompt = CONVERSATION_ANALYSIS_PROMPT.format(
            question=question,
            answer=answer
        )

        response = self.llm.with_structured_output(ConversationAnalysis).invoke([
            {"role": "user", "content": prompt}
        ])
        return response


# 全局单例
memory_service = MemoryService()
```

### 步骤4：修改状态定义

**文件**: `backend/app/agent/state.py`

```python
from typing import List, Dict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

class RetrievalMetadata(BaseModel):
    """检索元数据"""
    query: str
    sources: List[str] = Field(default_factory=list)
    latency_ms: float = 0

class AgentState(MessagesState):
    """增强的 Agent 状态"""
    loop_step: int = 0
    query_history: List[str] = Field(default_factory=list)
    retrieved_documents: List[Document] = Field(default_factory=list)
    retrieval_metadata: Optional[RetrievalMetadata] = None
    user_memories: List[Dict] = Field(default_factory=list)  # 新增：用户记忆
    retrieval_needed: Dict[str, bool] = Field(default_factory=dict)  # 新增：检索需求标志
```

### 步骤5：添加智能路由节点

**文件**: `backend/app/agent/routing_node.py` (新建)

```python
from typing import Literal
from langchain_core.runnables import RunnableConfig
from langgraph.types import send
from .state import AgentState
from ..llm.llm_factory import get_llm
from ..memory.memory_schema import RetrievalDecision

def routing_node(state: AgentState, config: RunnableConfig) -> dict:
    """智能路由节点 - 让LLM判断是否需要检索记忆和/或RAG

    返回路由决策，用于后续并行执行
    """
    query = state["messages"][-1].content

    # 使用LLM智能判断
    prompt = f"""分析以下用户查询，判断是否需要检索记忆和/或知识库（RAG）。

用户查询: {query}

返回JSON格式：
{{
    "need_memory": true/false (是否需要检索用户记忆),
    "need_rag": true/false (是否需要检索知识库),
    "reason": "决策原因"
}}

判断标准：
- need_memory: 查询涉及个人信息、偏好、历史对话、日程等需要记住的信息
- need_rag: 查询涉及产品功能、使用方法、文档说明等知识库信息
- 如果两者都不需要，则直接回答用户问题
"""

    llm = get_llm().with_structured_output(RetrievalDecision)
    decision = llm.invoke([{"role": "user", "content": prompt}])

    return {
        "retrieval_needed": {"memory": decision.need_memory, "rag": decision.need_rag}
    }

def routing_condition(state: AgentState) -> str:
    """路由条件函数 - 决定后续执行路径

    返回值说明：
    - "parallel_both": 需要记忆和RAG检索（并行执行）
    - "memory_only": 只需要记忆检索
    - "rag_only": 只需要RAG检索
    - "direct_answer": 直接回答，无需检索
    """
    needed = state.get("retrieval_needed", {})
    need_memory = needed.get("memory", False)
    need_rag = needed.get("rag", False)

    if need_memory and need_rag:
        return "parallel_both"
    elif need_memory:
        return "memory_only"
    elif need_rag:
        return "rag_only"
    else:
        return "direct_answer"

def create_parallel_branches(state: AgentState, config: RunnableConfig):
    """创建并行分支（用于fan-out）

    LangGraph的send()机制允许并行执行多个节点
    """
    needed = state.get("retrieval_needed", {})
    branches = []

    if needed.get("memory", False):
        branches.append(send("memory_retrieval", state))
    if needed.get("rag", False):
        branches.append(send("retrieval_node", state))

    return branches
```

### 步骤6：添加记忆检索节点（使用 Runtime）

**文件**: `backend/app/agent/memory_node.py` (新建)

```python
from typing import Dict
from langchain_core.runnables import RunnableConfig
from langgraph.types import BaseStore
from langgraph.runtime import Runtime
from .state import AgentState
import logging

logger = logging.getLogger(__name__)

def memory_retrieval_node(
    state: AgentState,
    config: RunnableConfig,
    *,
    store: BaseStore  # LangGraph 自动注入 PostgresStore
) -> dict:
    """记忆检索节点 - 使用 runtime.store

    store 参数由 LangGraph Runtime 自动注入，使用连接池，
    无需每次创建新连接。
    """
    messages = state.get("messages", [])
    if not messages:
        return {"user_memories": []}

    query = messages[-1].content
    user_id = config["configurable"].get("user_id")

    try:
        from ..memory.memory_service import memory_service
        # 使用已注入的 store（连接池）
        memories = memory_service.retrieve_memory(store, user_id, query, limit=3)
        logger.info(f"检索到 {len(memories)} 条记忆")
        return {"user_memories": memories}
    except Exception as e:
        logger.error(f"记忆检索失败: {e}")
        return {"user_memories": []}
```

### 步骤7：修改统一响应节点

**文件**: `backend/app/agent/node.py`

```python
from typing import Literal
from langchain_core.runnables import RunnableConfig
from langgraph.types import BaseStore
from .state import AgentState
from ..llm.llm_factory import get_llm
from ..tools.web_search_tool import tavily_search
from ..tools.user_tool import save_conversation_memory
import logging

logger = logging.getLogger(__name__)

def tools_condition(state: AgentState) -> Literal["tools", END]:
    """判断是否需要调用工具"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

def generate_response(state: AgentState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """统一响应节点 - 始终绑定工具"""
    user_id = config["configurable"]["user_id"]
    question = state["messages"][0].content

    # 获取上下文
    retrieved_docs = state.get("retrieved_documents", [])
    user_memories = state.get("user_memories", [])
    has_context = bool(retrieved_docs or user_memories)

    # 构建上下文信息
    context_parts = []
    if user_memories:
        memory_context = "\n".join([f"- {m['data']} ({m['timestamp'][:10]})" for m in user_memories])
        context_parts.append(f"【用户记忆】\n{memory_context}")
    if retrieved_docs:
        doc_context = "\n\n".join([
            f"[{doc.metadata.get('filename', 'unknown')}] {doc.page_content}"
            for doc in retrieved_docs
        ])
        context_parts.append(f"【知识库】\n{doc_context}")

    # 构建提示词
    if has_context:
        system_msg = f"""你是一个智能助手，用户ID: {user_id}

【已检索到以下上下文信息】
{chr(10).join(context_parts)}

回答规则：
1. 优先使用上述上下文回答用户问题
2. 如果上下文足够，直接回答即可
3. 如果需要补充信息（如实时数据），可以使用工具：
   - tavily_search: 获取实时信息
4. 如果对话中包含重要新信息，调用 save_conversation_memory 保存到记忆

用户问题：{question}
"""
    else:
        system_msg = f"""你是一个智能助手，用户ID: {user_id}

【没有检索到相关的上下文信息】

回答规则：
1. 可以使用以下工具获取信息：
   - tavily_search: 获取实时信息
2. 如果对话中包含重要新信息，调用 save_conversation_memory 保存

用户问题：{question}
"""

    # 始终绑定工具（无论是否有上下文）
    from ..tools.web_search_tool import tavily_search
    response = get_llm().bind_tools([tavily_search, save_conversation_memory]).invoke([
        {"role": "system", "content": system_msg}
    ])

    return {"messages": [response]}

# 保留现有的 rewrite_question 和 grade_documents 节点
# 删除 generate_answer 函数（统一到 generate_response）

def grade_documents_node(state: AgentState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """文档评分节点 - 评估检索文档相关性"""
    from ..prompt.prompt import GRADE_DOCUMENTS_PROMPT

    retrieved_docs = state.get("retrieved_documents", [])
    query = state["messages"][0].content

    if not retrieved_docs:
        return {"retrieved_documents": []}

    llm = get_llm().with_structured_output(GradeDocuments)
    result = llm.invoke(GRADE_DOCUMENTS_PROMPT.format(
        documents="\n\n".join([d.page_content for d in retrieved_docs]),
        question=query
    ))

    if result.score == "yes":
        return {"retrieved_documents": retrieved_docs}
    else:
        return {"retrieved_documents": []}

def rewrite_question_node(state: AgentState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """重写问题节点"""
    from ..prompt.prompt import REWRITE_QUESTION_PROMPT

    loop_step = state.get("loop_step", 0)
    if loop_step >= 3:
        return {"loop_step": loop_step + 1}

    query = state["messages"][0].content
    llm = get_llm()
    rewritten = llm.invoke(REWRITE_QUESTION_PROMPT.format(question=query))

    return {
        "loop_step": loop_step + 1,
        "messages": [rewritten]
    }
```

### 步骤8：更新流程图（支持并行执行）

**文件**: `backend/app/agent/graph.py`

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import send
from .state import AgentState
from .node import (
    generate_response,
    grade_documents_node,
    rewrite_question_node,
    tools_condition
)
from .routing_node import (
    routing_node,
    routing_condition,
    create_parallel_branches
)
from .memory_node import memory_retrieval_node
from .retrieval_node import retrieval_node
from ..tools import ToolNode

def get_graph():
    """构建LangGraph流程（支持并行执行）"""
    workflow = StateGraph(AgentState)

    # 节点定义
    workflow.add_node("routing", routing_node)
    workflow.add_node("memory_retrieval", memory_retrieval_node)
    workflow.add_node("retrieval_node", retrieval_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("rewrite_question", rewrite_question_node)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("tool_node", ToolNode([tavily_search, save_conversation_memory]))

    # 边定义
    workflow.add_edge(START, "routing")

    # 路由决策后的条件边
    workflow.add_conditional_edges(
        "routing",
        routing_condition,
        {
            "parallel_both": "fan_out",  # 并行执行记忆和RAG检索
            "memory_only": "memory_retrieval",
            "rag_only": "retrieval_node",
            "direct_answer": "generate_response"
        }
    )

    # fan-out节点（并行分支入口）
    workflow.add_node("fan_out", create_parallel_branches)
    workflow.add_conditional_edges(
        "fan_out",
        lambda state: state["retrieval_needed"],
        {
            {"memory": True, "rag": True}: ["memory_retrieval", "retrieval_node"],
            {"memory": True, "rag": False}: "memory_retrieval",
            {"memory": False, "rag": True}: "retrieval_node"
        }
    )

    # RAG检索后的文档评分
    workflow.add_edge("retrieval_node", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        lambda state: "generate_response" if state.get("retrieved_documents") else "rewrite_question",
        {
            "generate_response": "generate_response",
            "rewrite_question": "rewrite_question"
        }
    )

    # 重写问题后重新检索
    workflow.add_edge("rewrite_question", "retrieval_node")

    # 记忆检索后直接响应（如果有记忆）
    workflow.add_conditional_edges(
        "memory_retrieval",
        lambda state: "generate_response" if state.get("user_memories") else "generate_response",
        {"generate_response": "generate_response"}
    )

    # 响应节点的工具调用
    workflow.add_conditional_edges(
        "generate_response",
        tools_condition,
        {
            "tools": "tool_node",
            END: END
        }
    )

    # 工具调用后返回响应节点
    workflow.add_edge("tool_node", "generate_response")

    return workflow.compile(checkpointer=MemorySaver())
```

### 步骤9：添加提示词

**文件**: `backend/app/prompt/prompt.py`

```python
# 新增：记忆分类和标签生成提示词
MEMORY_ANALYSIS_PROMPT = """分析以下对话，提取记忆的分类和标签。

用户问题: {question}

请返回JSON格式：
{{
    "category": 从以下分类中选择一个: ["profile", "preference", "schedule", "fact", "relationship", "other"],
    "tags": 提取3-5个具体的自由标签（如"川菜"、"辣味"、"周五会议"等）
}}

分类说明：
- profile: 个人信息（姓名、年龄、职业等）
- preference: 偏好喜好（喜欢、不喜欢、习惯等）
- schedule: 日程约定（会议、计划、约定等）
- fact: 事实记录（历史事件、完成事项等）
- relationship: 人际关系（家人、朋友、同事等）
- other: 其他
"""

# 新增：对话分析提示词
CONVERSATION_ANALYSIS_PROMPT = """分析以下对话内容，提取需要记住的信息。

用户ID: {user_id}
用户问题: {question}
AI回答: {answer}

请返回JSON格式：
{{
    "category": 从以下分类中选择一个: ["profile", "preference", "schedule", "fact", "relationship", "other"],
    "tags": 提取3-5个具体标签,
    "summary": 用一句话总结需要记住的信息,
    "should_save": true/false (是否值得保存)
}}
"""
```

### 步骤10：修改工具文件

**文件**: `backend/app/tools/user_tool.py`

```python
from langchain_core.tools import tool
from langgraph.types import BaseStore

@tool
def retrieve_memory(query: str, user_id: str, *, store: BaseStore) -> str:
    """Retrieve user memories (已弃用，使用 memory_retrieval_node)

    记忆检索已前置到流程开始，此工具保留兼容性但不推荐使用。
    """
    return "记忆检索已通过 memory_retrieval_node 自动完成"

@tool
def save_conversation_memory(question: str, answer: str, user_id: str, *, store: BaseStore) -> str:
    """保存对话到长期记忆 - 使用 MemoryService

    当对话中包含重要新信息时调用，AI会自动判断是否需要保存。
    store 参数由 LangGraph Runtime 自动注入。
    """
    from ..memory.memory_service import memory_service
    return memory_service.save_memory(store, user_id, question, answer)
```

## LangChain 最佳实践说明

### PostgresStore 连接管理

**问题**：每次调用 `PostgresStore.from_conn_string()` 会创建新连接，导致：
- 性能下降（连接建立开销）
- 数据库连接数耗尽风险

**解决方案**（LangChain 官方推荐）：

1. **使用单例模式**：
   ```python
   # memory_factory.py
   class MemoryFactory:
       _instance: PostgresStore = None

       @classmethod
       def get_store(cls) -> PostgresStore:
           if cls._instance is None:
               cls._instance = PostgresStore.from_conn_string(DATABASE_URL)
           return cls._instance
   ```

2. **通过 Runtime 注入**（推荐）：
   ```python
   def my_node(state, config, *, store: BaseStore):
       # store 由 LangGraph Runtime 自动注入
       memories = store.search(namespace, query=query)
   ```

3. **配置连接池**：
   ```bash
   export LANGGRAPH_POSTGRES_POOL_MAX_SIZE=150  # 默认值
   ```

### 记忆检索方式选择

**向量搜索**（本方案采用）：
- `store.search(namespace, query="用户偏好")` 配合 `index={"embed": embed_fn, "dims": dim}`
- 适用于：语义搜索、模糊查询
- 优点：智能语义匹配，支持自然语言查询
- 使用阿里 DashScope `text-embedding-v4` 嵌入模型（1024维）

**分类过滤**：
- `store.search(namespace, query=text, filter={"category": "preference"})`
- 适用于：按记忆类型筛选

**配置说明**：
- 向量索引通过 `PostgresStore.from_conn_string(..., index=...)` 配置
- 首次使用需要调用 `store.setup()` 初始化数据库表
- 嵌入维度：1024 (DashScope text-embedding-v4)

## 新流程图（并行架构）

```
START
    ↓
routing_node (新增，LLM智能路由)
    └─ LLM分析 (~100ms) → need_memory + need_rag

并行执行路径:
├─ parallel_both:
│   ├→ memory_retrieval_node (~5ms)
│   └→ retrieval_node (~200ms)
│       ↓
│   fan-in → grade_documents → generate_response
│
├─ memory_only:
│   └→ memory_retrieval_node (~5ms) → generate_response
│
├─ rag_only:
│   └→ retrieval_node (~200ms) → grade_documents → generate_response
│
└─ direct_answer:
    └→ generate_response (无检索上下文)

generate_response (统一响应，始终绑定工具)
    ├─ 有上下文 → 使用上下文回答
    │   └─ 需要补充信息时调用工具 → tool_node → generate_response
    │
    └─ 无上下文 → 使用工具获取信息
        ├─ 有工具调用 → tool_node → generate_response
        └─ 无工具调用 → END

END
```

## 性能分析

| 场景 | 原始架构 | 新架构（并行） | 提升 |
|------|---------|--------------|------|
| 纯记忆问题 | ~100ms (LLM工具调用) | ~105ms (LLM路由+5ms检索) | 持平 |
| 纯RAG问题 | ~300ms (串行) | ~300ms (LLM路由+200ms检索) | 持平 |
| 记忆+RAG问题 | ~400ms (串行) | ~300ms (并行) | **25%** |
| 直接回答 | ~100ms (LLM路由) | ~100ms (LLM路由) | 持平 |

## 数据结构确认

### 记忆保存格式（PostgresStore文本存储）
```python
{
    "data": "用户不喜欢吃香菜",
    "category": "preference",
    "tags": ["不喜欢", "吃", "香菜"],
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### user_memories 状态格式
```python
[
    {
        "data": "用户不喜欢吃香菜",
        "category": "preference",
        "tags": ["不喜欢", "吃", "香菜"],
        "timestamp": "2024-01-15"
    }
]
```

### retrieval_needed 状态格式
```python
{
    "memory": True,   # 是否需要检索记忆
    "rag": True       # 是否需要检索知识库
}
```

## 配置参数

```python
# config.py 新增
class Settings(BaseSettings):
    MEMORY_RETRIEVAL_LIMIT: int = 3  # 默认返回3条记忆
    POSTGRES_POOL_MAX_SIZE: int = 150  # 连接池最大连接数

# 环境变量（可选）
# export LANGGRAPH_POSTGRES_POOL_MAX_SIZE=150
```

## 验证步骤

### 1. 启动测试
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 2. 测试场景

#### 场景A：纯记忆问题
```
用户: "我记得之前说过我不喜欢吃香菜"
预期:
  - routing 判断为 memory_only
  - memory_retrieval 返回记忆
  - generate_response 直接用记忆回答
  - 性能: ~105ms
```

#### 场景B：明确RAG问题
```
用户: "这个产品的功能是什么？"
预期:
  - routing 判断为 rag_only
  - retrieval_node 检索知识库
  - generate_response 用知识库回答
  - 性能: ~300ms
```

#### 场景C：记忆+RAG问题
```
用户: "我的偏好是什么？这个产品怎么用？"
预期:
  - routing 判断为 parallel_both
  - memory_retrieval 和 retrieval_node 并行执行
  - generate_response 综合回答
  - 性能: ~300ms (而非串行400ms)
```

#### 场景D：实时信息
```
用户: "今天天气怎么样？"
预期:
  - routing 判断为 direct_answer
  - generate_response 绑定工具，调用 tavily_search
  - 性能: ~100ms + 搜索时间
```

### 3. 检查点

- [ ] 记忆检索正常工作
- [ ] LLM路由判断准确
- [ ] 并行执行正确（记忆+RAG同时进行）
- [ ] 工具绑定正确（始终绑定tavily_search和save_conversation_memory）
- [ ] 提示词区分生效
- [ ] 性能符合预期（并行场景25%提升）

## 回滚计划

如果出现问题，可以回滚到：
```bash
git revert <commit-hash>
```

关键回滚点：
1. state.py: 移除 user_memories 和 retrieval_needed 字段
2. graph.py: 恢复原始节点和边
3. node.py: 恢复 generate_answer 函数
4. 删除 memory_node.py, routing_node.py