# RAG 系统优化实施方案 v2

## Context

当前 Buddy-AI 项目已实现基础的 RAG 功能，根据 `docs/RAG-Plan.md` 的优化方案进行增强。

### 当前状态

| 组件 | 当前实现 | 优化需求 |
|------|---------|---------|
| 数据库 | 基础 user_files 表 | 添加全文搜索索引、触发器、vectorization_tasks 表 |
| 向量存储 | PGVector，每文件独立 collection | 统一 collection + metadata 过滤 |
| 检索 | 纯向量检索 | 混合检索（向量+全文）+ RRF 融合 + Rerank |
| 向量化 | 同步处理 | 异步处理 + 进度跟踪 |
| Agent | 基础 LangGraph | 集成检索节点 + 循环检测 |
| 前端 | FileUpload 对话框 | 侧边栏知识库管理 + 移除输入框上传按钮 |

### 目标

1. 优化检索质量（混合检索 + RRF + Rerank）
2. 改进用户体验（异步向量化 + 侧边栏管理）
3. 增强系统可维护性（统一 collection + 服务分层）
4. 防止死循环（智能循环检测）

---

## 实施方案

### 阶段 1: 数据库优化

**文件**: `backend/init_db.py`

#### 变更内容

```sql
-- 1. 扩展 user_files 表
ALTER TABLE user_files ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
ALTER TABLE user_files ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
ALTER TABLE user_files ADD COLUMN IF NOT EXISTS document_summary TEXT;
ALTER TABLE user_files ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0;
ALTER TABLE user_files ADD COLUMN IF NOT EXISTS last_vectorized_at TIMESTAMP WITH TIME ZONE;

-- 2. 全文搜索支持
ALTER TABLE langchain_pg_embedding ADD COLUMN IF NOT EXISTS search_vector tsvector;
CREATE INDEX IF NOT EXISTS idx_embedding_search ON langchain_pg_embedding USING GIN(search_vector);

-- 3. 自动更新 search_vector 的触发器
CREATE OR REPLACE FUNCTION update_chunk_search_vector() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('simple', coalesce(NEW.document, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_chunk_search ON langchain_pg_embedding;
CREATE TRIGGER trigger_update_chunk_search
    BEFORE INSERT OR UPDATE ON langchain_pg_embedding
    FOR EACH ROW
    EXECUTE FUNCTION update_chunk_search_vector();

-- 4. 向量化任务状态表
CREATE TABLE IF NOT EXISTS vectorization_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id VARCHAR(255) NOT NULL REFERENCES user_files(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 0,
    processed_chunks INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
```

---

### 阶段 2: 文档处理工具

**新建文件**: `backend/app/utils/document_processing.py`

```python
"""
文档处理工具 - 智能切分和元数据处理
"""
import hashlib
from pathlib import Path
from typing import List
from dataclasses import dataclass

from langchain_community.document_loaders import (
    PyMuPDFLoader, UnstructuredMarkdownLoader,
    Docx2txtLoader, TextLoader, CSVLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


@dataclass
class ChunkPosition:
    chunk_index: int
    start_char: int
    end_char: int
    page_number: int = None


def compute_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def get_document_loader(file_path: str, file_type: str):
    loaders = {
        'pdf': PyMuPDFLoader,
        'md': UnstructuredMarkdownLoader,
        'docx': Docx2txtLoader,
        'txt': TextLoader,
        'csv': CSVLoader
    }
    loader_class = loaders.get(file_type)
    if loader_class == TextLoader:
        return loader_class(file_path, encoding='utf-8')
    return loader_class(file_path) if loader_class else None


def get_smart_splitter(file_type: str):
    filetype_config = {
        'pdf': {'separators': ['\n\n', '\n', '. ', '。', ' ', ''], 'chunk_size': 800, 'chunk_overlap': 150},
        'md': {'separators': ['\n## ', '\n# ', '\n\n', '\n', ' ', ''], 'chunk_size': 1200, 'chunk_overlap': 200},
        'docx': {'separators': ['\n\n', '\n', '. ', '。', ' ', ''], 'chunk_size': 800, 'chunk_overlap': 150},
        'txt': {'separators': ['\n\n', '\n', '. ', '。', ' ', ''], 'chunk_size': 1000, 'chunk_overlap': 200},
        'csv': {'separators': ['\n', ','], 'chunk_size': 500, 'chunk_overlap': 0}
    }

    config = {
        'chunk_size': 1000,
        'chunk_overlap': 200,
        'length_function': len,
        'add_start_index': True,
        **filetype_config.get(file_type, {})
    }

    return RecursiveCharacterTextSplitter(**config)


def process_document(
    file_path: str,
    file_type: str,
    file_content: bytes,
    file_id: str,
    user_id: str,
    original_filename: str
) -> dict:
    loader = get_document_loader(file_path, file_type)
    if not loader:
        raise ValueError(f"不支持的文件类型: {file_type}")

    docs = loader.load()
    splitter = get_smart_splitter(file_type)
    chunks = splitter.split_documents(docs)
    content_hash = compute_content_hash(file_content)

    for idx, chunk in enumerate(chunks):
        chunk.metadata.update({
            'file_id': file_id,
            'user_id': user_id,
            'filename': original_filename,
            'doc_type': 'chunk',
            'chunk_index': idx,
            'content_hash': content_hash
        })

    summary = _generate_summary(chunks)

    return {
        'documents': chunks,
        'summary': summary,
        'chunk_count': len(chunks),
        'content_hash': content_hash
    }


def _generate_summary(chunks: List) -> str:
    if not chunks:
        return ""
    full_text = "\n\n".join([chunk.page_content for chunk in chunks[:10]])
    if len(full_text) <= 500:
        return full_text
    return full_text[:300] + "..." + full_text[-200:]
```

---

### 阶段 3: PGVector 连接池优化

**新建文件**: `backend/app/services/pgvector_singleton.py`

```python
"""
PGVector 单例服务 - 连接池优化
"""
import logging
from typing import Optional

import asyncpg
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector as LangchainPGVector

from app.config import settings
from app.retriever.embeddings_model import get_embeddings_model

logger = logging.getLogger(__name__)


class PGVectorSingleton:
    _instance: Optional['PGVectorSingleton'] = None
    _vector_store: Optional[LangchainPGVector] = None
    _pool: Optional[asyncpg.Pool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_vector_store(self) -> LangchainPGVector:
        if self._vector_store is None:
            self._pool = await asyncpg.create_pool(
                settings.POSTGRESQL_URL,
                min_size=2,
                max_size=10
            )

            self._vector_store = PGVector(
                collection_name="buddy_ai_docs",  # 统一 collection
                connection=self._pool,
                embeddings=get_embeddings_model(),
                use_jsonb=True
            )
            logger.info("PGVector 实例创建成功（带连接池）")

        return self._vector_store

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._vector_store = None


pgvector_singleton = PGVectorSingleton()
```

---

### 阶段 4: 全文搜索服务

**新建文件**: `backend/app/services/fulltext_search_service.py`

```python
"""
PostgreSQL 全文搜索服务
"""
import logging
from typing import List
from dataclasses import dataclass

import asyncpg
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FulltextResult:
    documents: List[Document]
    scores: List[float]


class FulltextSearchService:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                settings.POSTGRESQL_URL,
                min_size=2,
                max_size=10
            )
        return self._pool

    async def search(
        self,
        query: str,
        user_id: str,
        k: int = 5
    ) -> FulltextResult:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            sql = """
                SELECT
                    e.document,
                    e.cmetadata,
                    ts_rank(e.search_vector, plainto_tsquery('simple', $1)) as score
                FROM langchain_pg_embedding e
                WHERE e.search_vector IS NOT NULL
                  AND (e.cmetadata->>'user_id') = $2
                ORDER BY score DESC
                LIMIT $3
            """

            rows = await conn.fetch(sql, query, user_id, k)

            documents = []
            scores = []

            for row in rows:
                documents.append(Document(
                    page_content=row['document'],
                    metadata=row['cmetadata']
                ))
                scores.append(float(row['score']))

            return FulltextResult(documents=documents, scores=scores)


fulltext_search_service = FulltextSearchService()
```

---

### 阶段 5: Qwen Rerank 服务

**新建文件**: `backend/app/services/qwen_rerank_service.py`

```python
"""
Qwen Rerank 服务
"""
import logging
from typing import List, Optional
from dataclasses import dataclass

from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    documents: List[Document]
    scores: List[float]


class QwenRerankService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None
    ) -> RerankResult:
        if not documents:
            return RerankResult(documents=[], scores=[])

        try:
            from dashscope import TextReRank

            texts = [doc.page_content for doc in documents]
            rerank_result = TextReRank.call(
                api_key=self.api_key,
                model="gte-rerank",
                query=query,
                documents=texts,
                top_n=top_k or len(documents)
            )

            if rerank_result.status_code == 200:
                results = rerank_result.output['results']
                reranked_docs = [documents[r['index']] for r in results]
                reranked_scores = [r['relevance_score'] for r in results]

                return RerankResult(
                    documents=reranked_docs,
                    scores=reranked_scores
                )
        except Exception as e:
            logger.error(f"Rerank 失败: {e}")

        return RerankResult(
            documents=documents[:top_k] if top_k else documents,
            scores=[1.0] * len(documents)
        )


qwen_rerank_service = QwenRerankService()
```

---

### 阶段 6: 检索编排服务（核心）

**新建文件**: `backend/app/services/retrieval_orchestrator.py`

```python
"""
检索编排服务 - 整合向量检索、全文搜索、重排序
"""
import logging
import asyncio
from typing import List, Optional
from dataclasses import dataclass

from langchain_core.documents import Document

from app.retriever.embeddings_model import get_embeddings_model
from app.services.fulltext_search_service import fulltext_search_service
from app.services.qwen_rerank_service import qwen_rerank_service
from app.services.pgvector_singleton import pgvector_singleton

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    documents: List[Document]
    scores: List[float]
    sources: List[str]
    strategy: str = "hybrid"
    metadata: dict = None


class RetrievalOrchestrator:
    def __init__(self):
        self.reranker = qwen_rerank_service
        self.fulltext = fulltext_search_service

    async def retrieve(
        self,
        query: str,
        user_id: str,
        k: int = 4,
        use_fulltext: bool = True,
        use_rerank: bool = True,
        rerank_threshold: int = 3
    ) -> RetrievalResult:
        import time
        start_time = time.time()

        # 并行执行向量检索和全文搜索
        vector_result = self._retrieve_vector(query, user_id, k * 2)
        fulltext_result = self._retrieve_fulltext(query, user_id, k * 2)

        vector_r, fulltext_r = await asyncio.gather(
            vector_result,
            fulltext_result
        )

        # RRF 融合
        fused = self._rrf_fusion(
            vector_r.documents,
            vector_r.scores,
            fulltext_r.documents,
            fulltext_r.scores,
            k=k * 2
        )

        # Rerank（带触发阈值）
        if use_rerank and fused.documents and len(fused.documents) > rerank_threshold:
            reranked = await self.reranker.rerank(query, fused.documents, top_k=k)
            retrieval_time_ms = (time.time() - start_time) * 1000
            return RetrievalResult(
                documents=reranked.documents,
                scores=reranked.scores,
                sources=["rrf_reranked"] * len(reranked.documents),
                metadata={"rerank_triggered": True, "retrieval_time_ms": retrieval_time_ms}
            )
        else:
            retrieval_time_ms = (time.time() - start_time) * 1000
            return RetrievalResult(
                documents=fused.documents[:k],
                scores=fused.scores[:k],
                sources=["rrf_fused"] * len(fused.documents[:k]),
                metadata={"rerank_triggered": False, "retrieval_time_ms": retrieval_time_ms}
            )

    async def _retrieve_vector(
        self,
        query: str,
        user_id: str,
        k: int
    ) -> RetrievalResult:
        vector_store = await pgvector_singleton.get_vector_store()
        docs = await vector_store.asimilarity_search_with_score(
            query=query,
            k=k,
            filter={"user_id": user_id, "doc_type": "chunk"}
        )

        documents = [doc for doc, _ in docs]
        scores = [score for _, score in docs]

        return RetrievalResult(
            documents=documents,
            scores=scores,
            sources=["vector"] * len(documents)
        )

    async def _retrieve_fulltext(
        self,
        query: str,
        user_id: str,
        k: int
    ) -> RetrievalResult:
        result = await fulltext_search_service.search(query, user_id, k)
        return RetrievalResult(
            documents=result.documents,
            scores=result.scores,
            sources=["fulltext"] * len(result.documents)
        )

    def _rrf_fusion(
        self,
        docs1: List[Document],
        scores1: List[float],
        docs2: List[Document],
        scores2: List[float],
        k: int,
        rank_k: int = 60
    ) -> RetrievalResult:
        doc_scores = {}

        for i, doc in enumerate(docs1):
            doc_id = id(doc)
            rrf_score = 1.0 / (rank_k + i + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

        for i, doc in enumerate(docs2):
            doc_id = id(doc)
            rrf_score = 1.0 / (rank_k + i + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

        sorted_docs = sorted(
            [(doc, score) for doc, score in doc_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )

        all_docs = docs1 + docs2
        doc_map = {id(doc): doc for doc in all_docs}

        final_docs = []
        final_scores = []

        for doc_id, score in sorted_docs[:k]:
            if doc_id in doc_map:
                final_docs.append(doc_map[doc_id])
                final_scores.append(score)

        return RetrievalResult(
            documents=final_docs,
            scores=final_scores,
            sources=["rrf_fused"] * len(final_docs)
        )


retrieval_orchestrator = RetrievalOrchestrator()
```

---

### 阶段 7: LangGraph 集成

#### 7.1 扩展 AgentState

**文件**: `backend/app/agent/state.py`

```python
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.documents import Document
from langgraph.graph import MessagesState


class RetrievalMetadata(BaseModel):
    """检索元数据"""
    query: str
    rewritten_query: Optional[str] = None
    vector_count: int = 0
    fulltext_count: int = 0
    reranked_count: int = 0
    retrieval_time_ms: float = 0
    sources: List[str] = Field(default_factory=list)


class AgentState(MessagesState):
    """增强的 Agent 状态"""
    loop_step: int = 0
    query_history: List[str] = Field(default_factory=list)
    retrieved_documents: List[Document] = Field(default_factory=list)
    retrieval_metadata: Optional[RetrievalMetadata] = None
    should_retrieve: bool = False


class GradeDocuments(BaseModel):
    """文档相关性评分"""
    binary_score: str = Field(
        description="相关性评分：'yes' 表示相关，'no' 表示无关"
    )
```

#### 7.2 新增检索节点

**新建文件**: `backend/app/agent/retrieval_node.py`

```python
"""
检索节点 - LangGraph 节点级检索集成
"""
import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from .state import AgentState
from ..services.retrieval_orchestrator import retrieval_orchestrator

logger = logging.getLogger(__name__)


async def retrieval_node(
    state: AgentState,
    config: RunnableConfig,
    *,
    store: BaseStore
) -> dict:
    """检索节点 - 执行混合检索"""
    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_documents": [], "retrieval_metadata": None}

    query = messages[-1].content
    user_id = config["configurable"].get("user_id")

    logger.info(f"检索节点: query={query[:50]}..., user_id={user_id}")

    try:
        result = await retrieval_orchestrator.retrieve(
            query=query,
            user_id=user_id,
            k=4
        )

        return {
            "retrieved_documents": result.documents,
            "retrieval_metadata": {
                "query": query,
                "strategy": result.strategy
            }
        }

    except Exception as e:
        logger.error(f"检索失败: {e}")
        return {"retrieved_documents": [], "retrieval_metadata": None}


async def retrieval_decision_node(
    state: AgentState,
    config: RunnableConfig,
    *,
    store: BaseStore
) -> dict:
    """检索决策节点 - 简单判断是否需要检索"""
    messages = state.get("messages", [])
    if not messages:
        return {"should_retrieve": False}

    query = messages[-1].content

    # 简单规则：包含"文档"、"文件"、"上传"等关键词时检索
    should_retrieve = any(
        keyword in query for keyword in ["文档", "文件", "上传", "资料", "知识库"]
    )

    logger.info(f"检索决策: should_retrieve={should_retrieve}")

    return {"should_retrieve": should_retrieve}


def retrieval_condition(state: AgentState) -> Literal["retrieval_node", "generate_query_or_respond"]:
    """检索条件函数"""
    return "retrieval_node" if state.get("should_retrieve") else "generate_query_or_respond"
```

#### 7.3 更新 Graph

**文件**: `backend/app/agent/graph.py`

```python
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore
from .node import generate_query_or_respond, rewrite_question, generate_answer, grade_documents, _calculate_query_similarity
from .state import AgentState, GradeDocuments
from .retrieval_node import retrieval_node, retrieval_decision_node, retrieval_condition
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from ..config import settings
from ..llm.llm_factory import get_llm
from ..prompt.prompt import GRADE_PROMPT


def grade_documents_with_loop_check(state: AgentState) -> Literal["generate_answer", "rewrite_question"]:
    """文档评分（带循环检查）"""
    MAX_RETRIES = 3
    loop_step = state.get("loop_step", 0)

    if loop_step >= MAX_RETRIES:
        return "generate_answer"

    # 检查重复查询
    query_history = state.get("query_history", [])
    question = state["messages"][0].content
    current_query_normalized = question.lower().strip()

    for prev_query in query_history[-3:]:
        if _calculate_query_similarity(current_query_normalized, prev_query.lower().strip()) > 0.9:
            return "generate_answer"

    retrieved_docs = state.get("retrieved_documents", [])

    if retrieved_docs:
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        prompt = GRADE_PROMPT.format(question=question, context=context)

        response = (
            get_llm()
            .with_structured_output(GradeDocuments)
            .invoke([{"role": "user", "content": prompt}])
        )

        return "generate_answer" if response.binary_score == "yes" else "rewrite_question"

    return "rewrite_question"


def get_graph():
    with (RedisSaver.from_conn_string(settings.REDIS_URL) as checkpointer,
          PostgresStore.from_conn_string(settings.POSTGRESQL_URL) as store):

        workflow = StateGraph(AgentState)

        # 节点定义
        workflow.add_node("retrieval_decision", retrieval_decision_node)
        workflow.add_node("retrieval_node", retrieval_node)
        workflow.add_node("generate_query_or_respond", generate_query_or_respond)
        workflow.add_node("tool_node", ToolNode(get_tools()))
        workflow.add_node("grade_documents", grade_documents)
        workflow.add_node("rewrite_question", rewrite_question)
        workflow.add_node("generate_answer", generate_answer)

        # 边定义
        workflow.add_edge(START, "retrieval_decision")
        workflow.add_conditional_edges(
            "retrieval_decision",
            retrieval_condition,
            {
                "retrieval_node": "retrieval_node",
                "generate_query_or_respond": "generate_query_or_respond"
            }
        )
        workflow.add_edge("retrieval_node", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            grade_documents_with_loop_check
        )
        workflow.add_conditional_edges(
            "generate_query_or_respond",
            tools_condition
        )
        workflow.add_edge("tool_node", "grade_documents")
        workflow.add_edge("rewrite_question", "retrieval_node")
        workflow.add_edge("generate_answer", END)

        return workflow.compile(checkpointer=checkpointer, store=store)
```

#### 7.4 更新重写问题节点

**文件**: `backend/app/agent/node.py` (修改 `rewrite_question` 函数)

```python
def rewrite_question(state: AgentState):
    """重写问题（防止死循环）"""
    messages = state["messages"]
    question = messages[0].content
    loop_step = state.get("loop_step", 0)
    query_history = state.get("query_history", [])

    MAX_RETRIES = 3
    if loop_step >= MAX_RETRIES:
        logger.warning(f"超过最大重试次数 ({MAX_RETRIES})，停止重写")
        return {"messages": [HumanMessage(content=question)], "loop_step": loop_step + 1}

    # 检测重复查询
    current_query_normalized = question.lower().strip()
    for prev_query in query_history[-3:]:
        if _calculate_query_similarity(current_query_normalized, prev_query.lower().strip()) > 0.9:
            logger.warning("检测到重复查询，停止重写")
            return {"messages": [HumanMessage(content=question)], "loop_step": loop_step + 1}

    # 策略判断
    last_message = messages[-1]
    strategy = "优化检索"

    if hasattr(last_message, "tool_call_id") or last_message.type == "tool":
        content = last_message.content
        if "没有找到" in content or len(content) < 50:
            strategy = "联网搜索"
        elif loop_step >= 1:
            strategy = "简化表达"

    # 生成重写问题
    prompt = REWRITE_PROMPT.format(question=question, strategy=strategy)
    response = get_llm().invoke([{"role": "user", "content": prompt}])

    rewritten_query = response.content.strip()

    # 验证重写结果
    similarity = _calculate_query_similarity(current_query_normalized, rewritten_query.lower().strip())
    if similarity > 0.85:
        rewritten_query = question

    logger.info(f"重写问题: '{question}' -> '{rewritten_query}', 次数: {loop_step}")

    return {
        "messages": [HumanMessage(content=rewritten_query)],
        "loop_step": loop_step + 1,
        "query_history": query_history + [question]
    }


def _calculate_query_similarity(q1: str, q2: str) -> float:
    """简单计算查询相似度"""
    if q1 == q2:
        return 1.0

    words1 = set(q1.split())
    words2 = set(q2.split())

    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0
```

#### 7.5 更新答案生成节点

**文件**: `backend/app/agent/node.py` (修改 `generate_answer` 函数)

```python
def generate_answer(state: AgentState):
    """生成答案 - 使用检索到的上下文"""
    question = state["messages"][0].content

    # 从状态中获取检索结果
    retrieved_docs = state.get("retrieved_documents", [])
    metadata = state.get("retrieval_metadata")

    if retrieved_docs:
        context = "\n\n".join([
            f"[来源: {doc.metadata.get('filename', 'unknown')}] {doc.page_content}"
            for doc in retrieved_docs
        ])
        logger.info(f"生成答案: 使用 {len(retrieved_docs)} 个检索文档")
    else:
        context = state["messages"][-1].content

    prompt = GENERATE_PROMPT.format(question=question, context=context)
    response = get_llm().invoke([{"role": "user", "content": prompt}])
    return {"messages": [response]}
```

---

### 阶段 8: 前端侧边栏知识库组件

**新建文件**: `frontend/src/components/KnowledgeBaseSidebar.vue`

```vue
<template>
  <div class="kb-sidebar" :class="{ 'collapsed': isCollapsed }">
    <div class="kb-header">
      <div class="kb-title" v-if="!isCollapsed">知识库</div>
      <button class="toggle-btn" @click="toggleCollapse">
        {{ isCollapsed ? '▶' : '◀' }}
      </button>
    </div>

    <div class="kb-content" v-show="!isCollapsed">
      <!-- 上传区域 -->
      <div class="upload-section">
        <button class="upload-btn" @click="triggerUpload" :disabled="uploading">
          {{ uploading ? '上传中...' : '+ 上传文件' }}
        </button>
        <input
          ref="fileInput"
          type="file"
          @change="handleFileUpload"
          accept=".pdf,.docx,.txt,.md,.csv"
          style="display: none"
        />
      </div>

      <!-- 文件列表 -->
      <div class="file-list">
        <div class="file-list-header">
          <span>我的文档 ({{ files.length }})</span>
          <button class="refresh-btn" @click="loadFiles">↻</button>
        </div>

        <div class="file-list-content">
          <div
            v-for="file in files"
            :key="file.id"
            class="file-item"
          >
            <div class="file-icon">{{ getFileIcon(file.file_type) }}</div>
            <div class="file-info">
              <div class="file-name">{{ file.filename }}</div>
              <div class="file-meta">
                <span>{{ formatFileSize(file.file_size) }}</span>
                <span class="file-date">{{ formatDate(file.upload_time) }}</span>
              </div>
            </div>
            <button class="delete-btn" @click="deleteFile(file.id)">×</button>
          </div>

          <div v-if="files.length === 0" class="empty-state">
            暂无文档，点击上传
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { filesApi } from '@/api/files'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const isCollapsed = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement>()
const files = ref<any[]>([])

const loadFiles = async () => {
  try {
    const result = await filesApi.list(userStore.userId)
    files.value = result.files || []
  } catch (error) {
    console.error('加载文件列表失败:', error)
  }
}

const triggerUpload = () => {
  fileInput.value?.click()
}

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  uploading.value = true

  try {
    await filesApi.upload(file, userStore.userId)
    await loadFiles()
  } catch (error) {
    console.error('文件上传失败:', error)
  } finally {
    uploading.value = false
    target.value = ''
  }
}

const deleteFile = async (fileId: string) => {
  if (!confirm('确定要删除这个文件吗？')) return

  try {
    await filesApi.delete(fileId, userStore.userId)
    await loadFiles()
  } catch (error) {
    console.error('删除文件失败:', error)
  }
}

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const getFileIcon = (fileType: string) => {
  const icons: Record<string, string> = {
    pdf: '📄', docx: '📝', txt: '📃', md: '📑', csv: '📊'
  }
  return icons[fileType] || '📁'
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days} 天前`
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.kb-sidebar {
  width: 300px;
  background: #f5f7fa;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
}

.kb-sidebar.collapsed {
  width: 40px;
}

.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}

.kb-title {
  font-weight: 600;
  font-size: 16px;
  color: #1f2937;
}

.toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  font-size: 14px;
  color: #6b7280;
}

.toggle-btn:hover {
  color: #3b82f6;
}

.kb-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.upload-section {
  margin-bottom: 20px;
}

.upload-btn {
  width: 100%;
  padding: 10px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.upload-btn:hover:not(:disabled) {
  background: #2563eb;
}

.upload-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.file-list {
  display: flex;
  flex-direction: column;
}

.file-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.refresh-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #6b7280;
  font-size: 14px;
  padding: 4px;
}

.file-list-content {
  flex: 1;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.file-item:hover {
  background: #e5e7eb;
}

.file-icon {
  font-size: 20px;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  color: #9ca3af;
  padding: 4px;
  opacity: 0;
  transition: all 0.2s;
}

.file-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #ef4444;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #9ca3af;
  font-size: 14px;
}
</style>
```

---

### 阶段 9: 更新 ChatInput（移除上传按钮）

**文件**: `frontend/src/components/ChatInput.vue`

移除上传按钮相关代码，简化为：

```vue
<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <!-- 输入框 -->
      <el-input
        v-model="inputMessage"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 8 }"
        placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)"
        :disabled="isStreaming"
        @keydown="handleKeydown"
        class="chat-input"
      />

      <!-- 发送按钮 -->
      <el-button
        type="primary"
        circle
        :icon="isStreaming ? Loading : Promotion"
        :loading="isStreaming"
        :disabled="!inputMessage.trim() || isStreaming"
        class="send-button"
        @click="handleSend"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import type { Message } from '@/types'
import { Loading, Promotion } from '@element-plus/icons-vue'

const chatStore = useChatStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const inputMessage = ref('')
const isStreaming = computed(() => chatStore.isStreaming)
const userId = computed(() => userStore.userId)

const { connect, sendMessage } = useWebSocket(userId.value)
connect()

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

async function handleSend() {
  if (!inputMessage.value.trim() || isStreaming.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  const userMessage: Message = {
    role: 'user',
    content: message,
  }

  chatStore.addMessage(userMessage)

  if (!sessionStore.currentSession?.title && sessionStore.currentSession?.thread_id) {
    sessionStore.updateSessionTitle(
      sessionStore.currentSession.thread_id,
      message.slice(0, 30) + (message.length > 30 ? '...' : '')
    )
  }
  if (sessionStore.currentSession?.thread_id) {
    sessionStore.updateSessionMessageCount(sessionStore.currentSession.thread_id)
  }

  chatStore.isStreaming = true
  sendMessage(message, sessionStore.currentSession?.thread_id)
}
</script>

<style scoped>
.chat-input-container {
  padding: 16px;
  background: var(--el-bg-color-overlay);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--el-border-color);
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 900px;
  margin: 0 auto;
  background: var(--el-bg-color);
  border-radius: 16px;
  border: 1px solid var(--el-border-color);
  padding: 4px;
}

.input-wrapper:deep(.el-textarea__inner) {
  padding-right: 12px;
  padding-left: 8px;
  padding-top: 12px;
  padding-bottom: 12px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  min-height: 60px;
}

.send-button {
  background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
  border-color: transparent;
}

.send-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffaa66 0%, #ff7b7b 100%);
}
</style>
```

---

### 阶段 10: 更新 ChatView 集成侧边栏

**文件**: `frontend/src/views/ChatView.vue`

```vue
<template>
  <div class="chat-container">
    <!-- 侧边栏 - 会话列表 -->
    <Sidebar
      class="sidebar"
      :class="{ 'mobile-open': mobileSidebarOpen }"
      @toggleSidebar="toggleMobileSidebar"
    />

    <!-- 主聊天区域 -->
    <div class="main-chat">
      <!-- 知识库侧边栏 -->
      <KnowledgeBaseSidebar class="kb-sidebar" />

      <!-- 聊天内容区域 -->
      <div class="chat-content">
        <!-- 顶部标题栏 -->
        <div class="chat-header">
          <div class="header-left">
            <el-button
              circle
              :icon="Menu"
              class="menu-toggle"
              @click="toggleMobileSidebar"
            />
            <div class="header-title">
              <h1>Buddy-AI</h1>
              <span class="header-subtitle">智能助手</span>
            </div>
          </div>
        </div>

        <!-- 聊天消息区域 -->
        <div class="messages-container" ref="messagesContainer">
          <div v-if="messages.length === 0" class="empty-state">
            <transition name="fade">
              <div class="empty-icon-wrapper">
                <IconBuddy class="empty-icon" />
              </div>
            </transition>
            <h2>你好！我是 Buddy-AI</h2>
            <p>我可以帮你回答问题、检索知识库、保存记忆等</p>
          </div>

          <div v-else class="messages-list">
            <ChatMessage
              v-for="(msg, index) in messages"
              :key="`${msg.role}-${index}`"
              :message="msg"
            />
            <div v-if="isStreaming" class="streaming-indicator">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <div ref="messagesEndRef" class="messages-end"></div>
          </div>
        </div>

        <!-- 输入区域 -->
        <ChatInput />
      </div>
    </div>

    <!-- 移动端侧边栏遮罩 -->
    <transition name="fade">
      <div
        v-if="mobileSidebarOpen"
        class="sidebar-overlay"
        @click="toggleMobileSidebar"
      ></div>
    </transition>

    <!-- 调试面板 -->
    <DebugPanel
      v-if="showDebug"
      :debug-info="debugInfo"
      class="debug-panel"
      @close="showDebug = false"
      @clear="chatStore.clearDebug()"
    />

    <!-- 文件上传模态框 -->
    <FileUpload
      :visible="showFileUploadModal"
      @close="showFileUploadModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useUserStore } from '@/stores/user'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import Sidebar from '@/components/Sidebar.vue'
import DebugPanel from '@/components/DebugPanel.vue'
import FileUpload from '@/components/FileUpload.vue'
import KnowledgeBaseSidebar from '@/components/KnowledgeBaseSidebar.vue'
import IconBuddy from '@/components/icons/IconBuddy.vue'
import {
  Menu
} from '@element-plus/icons-vue'

const chatStore = useChatStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const showDebug = ref(false)
const showFileUploadModal = ref(false)
const mobileSidebarOpen = ref(false)
const messagesContainer = ref<HTMLElement>()
const messagesEndRef = ref<HTMLElement>()

const messages = computed(() => chatStore.messages)
const isStreaming = computed(() => chatStore.isStreaming)
const debugInfo = computed(() => chatStore.debugInfo)

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesEndRef.value) {
      messagesEndRef.value.scrollIntoView({ behavior: 'smooth' })
    }
  })
}

// 监听消息变化，自动滚动
watch(() => messages.value.length, () => {
  scrollToBottom()
})

watch(() => isStreaming.value, (streaming) => {
  if (!streaming) {
    scrollToBottom()
  }
})

function toggleMobileSidebar() {
  mobileSidebarOpen.value = !mobileSidebarOpen.value
}

onMounted(() => {
  // 创建初始会话
  if (!sessionStore.currentSession) {
    sessionStore.createNewThread()
  }
})
</script>

<style scoped>
/* ... 样式 ... */
</style>
```

---

## 关键文件清单

### 新建文件

| 文件路径 | 说明 |
|---------|------|
| `backend/app/utils/document_processing.py` | 文档处理工具 |
| `backend/app/services/pgvector_singleton.py` | PGVector 单例（连接池） |
| `backend/app/services/fulltext_search_service.py` | 全文搜索服务 |
| `backend/app/services/qwen_rerank_service.py` | Qwen Rerank 服务 |
| `backend/app/services/retrieval_orchestrator.py` | 检索编排服务（核心） |
| `backend/app/agent/retrieval_node.py` | 检索节点 |
| `frontend/src/components/KnowledgeBaseSidebar.vue` | 侧边栏知识库组件 |

### 修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| `backend/init_db.py` | 添加数据库迁移 SQL |
| `backend/app/agent/state.py` | 扩展 AgentState |
| `backend/app/agent/node.py` | 更新重写问题、答案生成 |
| `backend/app/agent/graph.py` | 集成检索节点 |
| `frontend/src/components/ChatInput.vue` | 移除上传按钮 |
| `frontend/src/views/ChatView.vue` | 集成侧边栏组件 |

---

## 验证计划

### 后端验证

1. **数据库迁移**
   ```bash
   cd backend
   python init_db.py
   ```

2. **启动服务**
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **测试检索**
   - 上传一个 PDF 文件
   - 发送包含文档关键词的查询
   - 验证检索结果包含相关内容

### 前端验证

1. **启动前端**
   ```bash
   cd frontend
   npm run dev
   ```

2. **测试侧边栏**
   - [ ] 侧边栏展开/折叠
   - [ ] 文件上传功能
   - [ ] 文件列表展示
   - [ ] 删除文件功能

3. **测试聊天**
   - [ ] 输入框无上传按钮
   - [ ] Enter 发送 / Shift+Enter 换行
   - [ ] 检索结果展示

---

## 回滚计划

如需回滚：

1. 数据库回滚
   ```sql
   DROP INDEX IF EXISTS idx_embedding_search;
   DROP TRIGGER IF EXISTS trigger_update_chunk_search ON langchain_pg_embedding;
   DROP FUNCTION IF EXISTS update_chunk_search_vector;
   DROP TABLE IF EXISTS vectorization_tasks;
   ALTER TABLE user_files DROP COLUMN IF EXISTS is_public;
   ALTER TABLE user_files DROP COLUMN IF EXISTS content_hash;
   ALTER TABLE user_files DROP COLUMN IF EXISTS document_summary;
   ALTER TABLE user_files DROP COLUMN IF EXISTS chunk_count;
   ALTER TABLE user_files DROP COLUMN IF EXISTS last_vectorized_at;
   ```

2. 代码回滚：使用 git 恢复
   ```bash
   git checkout HEAD~1
   ```