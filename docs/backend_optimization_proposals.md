# Buddy-AI 后端项目优化方案

## 概述

本文档基于Python开发模式和最佳实践，分析buddy-ai后端项目中存在的问题，并提供相应的修复方案。

> **注意**：配置安全（硬编码）问题已忽略，因为这是为了方便测试。异常处理使用已有的 `apps/exceptions.py`。

---

##问题1：类型注解不完整

### 问题描述

多个函数缺少类型注解或类型注解不完整：

```python
# apps/agent/nodes/planner.py
def work_step(state: PlanStepSchema) -> dict:  # 返回类型不明确
    description = state.description
    response = get_llm().invoke(description)
    return {"step_results": [response.content]}
```

```python
# apps/agent/condition.py
def route_condition(state: GraphState) -> str:  # 返回类型不够具体
    route_decision = state["route_decision"]
    # ...
```

```python
# apps/agent/rag/milvus_vector.py
def hybrid_search(self, query: str, user_id: str, ...) -> List[dict]:  # 返回类型不明确
    # ...
    return [hit["entity"] for hits in result for hit in hits]
```

### 修复方案

**方案1：使用TypedDict定义明确的返回类型**

```python
# apps/agent/nodes/planner.py
from typing import TypedDict

class WorkStepOutput(TypedDict):
    step_results: list[str]

def work_step(state: PlanStepSchema) -> WorkStepOutput:
    """根据计划步骤生成结果"""
    description = state.description
    response = get_llm().invoke(description)
    return {"step_results": [response.content]}
```

```python
# apps/agent/nodes/planner.py
class SynthesisStepOutput(TypedDict):
    final_answer: str

def synthesis_step_results(state: GraphState) -> SynthesisStepOutput:
    """合并步骤结果"""
    return {
        "final_answer": "".join(state.get("step_results", []))
    }
```

**方案2：使用Literal限定返回值**

```python
# apps/agent/condition.py
from typing import Literal

def route_condition(state: GraphState) -> Literal[
    "query_transform",
    "query_transform_HyDE",
    "planner"
]:
    """路由条件"""
    route_decision = state["route_decision"]
    if route_decision == "knowledge_base_search":
        return "query_transform_HyDE"
    elif route_decision == "plan_and_execute":
        return "planner"
    return "query_transform"
```

```python
# apps/agent/condition.py
def generate_response_router(state: GraphState) -> Literal[
    "tool_node",
    "evaluate_node",
    "save_memories"
]:
    """generate_response 统一出边"""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"

    reflection = state.get("reflection")
    reflection_count = state.get("reflection_count", 0)
    if reflection_count < 3 and (reflection is None or not reflection.passed):
        if state.get("draft_answer"):
            return "evaluate_node"

    return "save_memories"
```

**方案3：定义向量搜索结果类型**

```python
# apps/agent/rag/milvus_vector.py
from typing import TypedDict

class SearchResult(TypedDict):
    id: int
    document_text: str

class MilvusVector:
    # ... 现有代码 ...

    def vector_search(
        self,
        query: str,
        user_id: str,
        knowledge_id: int = 1,
        top_k: int = 3
    ) -> list[SearchResult]:
        """向量搜索"""
        query_embeddings = self.openai_ef.encode_queries([query])
        result = self.client.search(
            collection_name=self.collection_name,
            anns_field="text_dense",
            data=query_embeddings,
            filter=f'user_id == "{user_id}" and knowledge_id == {knowledge_id}',
            limit=top_k,
            output_fields=['id', 'document_text'],
        )
        return [hit["entity"] for hits in result for hit in hits]

    def hybrid_search(
        self,
        query: str,
        user_id: str,
        knowledge_id: int = 1,
        top_k: int = 3
    ) -> list[SearchResult]:
        """混合搜索"""
        # ... 实现细节 ...
        return [hit["entity"] for hits in result for hit in hits]

    def text_match(
        self,
        query: str,
        keyword: str,
        user_id: str,
        knowledge_id: int = 1,
        limit: int = 3
    ) -> list[SearchResult]:
        """文本匹配"""
        # ... 实现细节 ...
        return [hit["entity"] for hits in result for hit in hits]
```

**方案4：为节点函数添加明确的返回类型**

```python
# apps/agent/nodes/router.py
from typing import TypedDict

class RouterOutput(TypedDict):
    route_decision: str
    route_reason: str
    original_input: str
    enhanced_input: str | None
    rag_docs: list[dict]
    plan: object | None  # PlanSchema
    reflection_count: int
    reflection: object | None  # ReflectionState
    draft_answer: str | None
    final_answer: str | None

def router(state: GraphState) -> RouterOutput:
    """Route agent to appropriate node."""
    # ... 现有逻辑 ...
    return {
        "route_decision": route_result.route_decision,
        "route_reason": route_result.route_reason,
        "original_input": query,
        "enhanced_input": None,
        "rag_docs": [],
        "plan": None,
        "reflection_count": 0,
        "reflection": None,
        "draft_answer": None,
        "final_answer": None,
    }
```

---

## 问题2：数据库连接池配置不够灵活

### 问题描述

在 `apps/database/async_engine.py` 中，连接池配置写死在代码中：

```python
async_engine = create_async_engine(
    settings.MYSQL_URL,
    echo=True,  # 总是输出SQL日志
    pool_size=10,
    max_overflow=20
)
```

问题：
1. `echo=True` 在生产环境会输出大量SQL日志
2. 连接池参数无法根据环境调整
3. 缺少连接超时和回收配置
4. 缺少连接健康检查

### 修复方案

**方案1：将连接池配置放到 Settings 中**

```python
# apps/config.py
class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # ... 其他配置 ...

    # ========== 数据库连接池配置 ==========
    MYSQL_ECHO: bool = False  # 默认关闭SQL日志
    MYSQL_POOL_SIZE: int = 10
    MYSQL_MAX_OVERFLOW: int = 20
    MYSQL_POOL_TIMEOUT: int = 30  # 获取连接超时时间（秒）
    MYSQL_POOL_RECYCLE: int = 3600  # 连接回收时间（秒）
    MYSQL_POOL_PRE_PING: bool = True  # 连接前检查有效性
    MYSQL_POOL_RECYCLE_IDLE: int = 600  # 空闲连接回收时间（秒）
```

**方案2：修改 async_engine.py 使用配置**

```python
# apps/database/async_engine.py
async_engine = create_async_engine(
    settings.MYSQL_URL,
    echo=settings.MYSQL_ECHO,
    pool_size=settings.MYSQL_POOL_SIZE,
    max_overflow=settings.MYSQL_MAX_OVERFLOW,
    pool_timeout=settings.MYSQL_POOL_TIMEOUT,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    pool_pre_ping=settings.MYSQL_POOL_PRE_PING,
    pool_recycle_idle=settings.MYSQL_POOL_RECYCLE_IDLE,
)
```

**方案3：在 .env 中配置环境特定值**

```bash
# 开发环境 (.env.development)
MYSQL_ECHO=true
MYSQL_POOL_SIZE=5
MYSQL_MAX_OVERFLOW=10

# 生产环境 (.env.production)
MYSQL_ECHO=false
MYSQL_POOL_SIZE=20
MYSQL_MAX_OVERFLOW=40
MYSQL_POOL_TIMEOUT=60
```

**方案4：添加连接池监控**

**创建 `apps/database/pool_monitor.py`：**

```python
import logging
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

def setup_pool_monitoring(engine: AsyncEngine) -> None:
    """设置连接池监控"""

    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        logger.debug("数据库连接已建立")

    @event.listens_for(engine.sync_engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        pool_size = connection_record.pool.size()
        checked_out = connection_record.pool.checkedout()
        logger.debug(
            "从连接池获取连接: 池大小=%d, 已检出=%d",
            pool_size,
            checked_out
        )

    @event.listens_for(engine.sync_engine, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        logger.debug("连接已归还到连接池")
```

**在 `async_engine.py` 中启用监控：**

```python
from apps.database.pool_monitor import setup_pool_monitoring

# 创建引擎后
setup_pool_monitoring(async_engine)
```

---

## 问题3：内存管理 - 大文件存储

### 问题描述

在 `apps/database/models.py` 中，文件内容直接存储在数据库的 `LargeBinary` 字段：

```python
file_content: Mapped[bytes | None] = mapped_column(
    LargeBinary(length=2**32 - 1),
    comment="文件内容"
)
```

问题：
1. 数据库不适合存储大文件（>1MB）
2. 容易导致内存溢出
3. 影响数据库性能
4. 缺少文件大小限制和验证
5. 在 `apps/api/knowledgebase.py` 的 `download_file` 函数中，将整个文件内容加载到内存

### 修复方案

**方案1：使用文件系统存储（推荐）**

1. 修改模型，移除 file_content 字段：

```python
# apps/database/models.py
class KnowledgeBaseFile(Base):
    __tablename__ = "knowledge_base_file"

    knowledge_id: Mapped[int] = mapped_column(BigInteger, comment="所属知识库ID")
    file_name: Mapped[str] = mapped_column(String(255), comment="文件名")
    file_type: Mapped[str] = mapped_column(String(32), comment="文件类型")
    file_size: Mapped[int] = mapped_column(BigInteger, comment="文件大小(字节)")
    file_path: Mapped[str] = mapped_column(String(500), comment="文件存储路径")
    file_md5: Mapped[str | None] = mapped_column(String(32), comment="文件MD5校验值")
    # 移除 file_content 字段
```

2. 创建文件存储服务：

```python
# apps/services/file_storage.py
import hashlib
import os
from pathlib import Path
from typing import BinaryIO
from fastapi import UploadFile, HTTPException
from apps.config import settings

class FileStorageService:
    """文件存储服务"""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self):
        # 从配置获取存储目录
        storage_dir = getattr(settings, "STORAGE_DIR", "storage")
        self.base_dir = Path(storage_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(
        self,
        user_id: str,
        knowledge_id: int,
        file_md5: str,
        file_ext: str
    ) -> Path:
        """构建文件存储路径"""
        # 路径结构: storage/{user_id}/{knowledge_id}/{file_md5}{ext}
        relative_path = f"{user_id}/{knowledge_id}/{file_md5}{file_ext}"
        return self.base_dir / relative_path

    async def save_file(
        self,
        file: UploadFile,
        user_id: str,
        knowledge_id: int
    ) -> tuple[str, str, int]:
        """
        保存文件到磁盘

        Returns:
            (relative_path, file_md5, file_size)
        """
        # 读取文件内容
        content = await file.read()

        # 检查文件大小
        if len(content) > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制 ({self.MAX_FILE_SIZE} 字节)"
            )

        # 计算MD5
        file_md5 = hashlib.md5(content).hexdigest()
        file_size = len(content)

        # 获取文件扩展名
        ext = Path(file.filename).suffix

        # 构建存储路径
        file_path = self._get_file_path(user_id, knowledge_id, file_md5, ext)

        # 保存文件
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

        return str(file_path.relative_to(self.base_dir)), file_md5, file_size

    def delete_file(self, relative_path: str) -> None:
        """删除文件"""
        file_path = self.base_dir / relative_path
        if file_path.exists():
            file_path.unlink()
            logger.info(f"文件已删除: {relative_path}")

    def get_file_reader(self, relative_path: str) -> BinaryIO:
        """获取文件读取器"""
        file_path = self.base_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {relative_path}")
        return open(file_path, "rb")

    def file_exists(self, relative_path: str) -> bool:
        """检查文件是否存在"""
        file_path = self.base_dir / relative_path
        return file_path.exists()

# 创建全局实例
file_storage = FileStorageService()
```

3. 在 Settings 中添加存储目录配置：

```python
# apps/config.py
class Settings(BaseSettings):
    # ... 其他配置 ...

    # ========== 文件存储配置 ==========
    STORAGE_DIR: str = "storage"  # 文件存储目录
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 最大文件大小 10MB
```

4. 修改 upload_file 端点：

```python
# apps/api/knowledgebase.py
from apps.services.file_storage import file_storage
from docx import Document
import io

ALLOWED_FILE_TYPE = {"txt", "docx", "md"}

@router.post("/upload_file")
async def upload_file(
    file: UploadFile = Depends(validate_file),
    user_id: str = Form(...),
    knowledge_id: int = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """上传单个文件，仅支持 txt、docx、md 格式"""
    ext = Path(file.filename or "").suffix.lstrip(".").lower()

    # 读取文件内容（用于MD5计算和向量生成）
    raw = await file.read()

    # 检查文件大小
    if len(raw) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE} 字节)"
        )

    file_md5 = hashlib.md5(raw).hexdigest()

    # 查询是否已存在同名文件
    result = await session.execute(
        select(KnowledgeBaseFile).where(
            KnowledgeBaseFile.creator_id == user_id,
            KnowledgeBaseFile.knowledge_id == knowledge_id,
            KnowledgeBaseFile.file_name == file.filename,
        )
    )
    existing = result.scalar_one_or_none()
    file_id = None

    if existing:
        if existing.file_md5 == file_md5:
            return {"filename": file.filename, "message": "文件未变更，跳过上传"}

        # md5 不一致，更新文件
        existing.file_size = len(raw)
        existing.file_type = ext

        # 保存新文件
        file_path, _, file_size = await file_storage.save_file(
            file, user_id, knowledge_id
        )
        existing.file_path = file_path
        existing.file_md5 = file_md5
        existing.update_id = user_id

        await session.commit()
        file_id = existing.id

        # 删除旧文件和向量数据
        if existing.file_path:
            file_storage.delete_file(existing.file_path)
        milvusVector.delete_documents(file_id, user_id, knowledge_id)
    else:
        # 保存新文件
        file_path, _, file_size = await file_storage.save_file(
            file, user_id, knowledge_id
        )

        knowledgeBaseFile = KnowledgeBaseFile(
            knowledge_id=knowledge_id,
            file_name=file.filename,
            file_size=file_size,
            file_type=ext,
            file_path=file_path,
            file_md5=file_md5,
            creator_id=user_id,
            update_id=user_id,
        )
        session.add(knowledgeBaseFile)
        await session.commit()
        await session.refresh(knowledgeBaseFile)
        file_id = knowledgeBaseFile.id

    # 处理文本内容（用于向量生成）
    if ext in ("txt", "md"):
        content = raw.decode("utf-8")
    else:
        doc = Document(io.BytesIO(raw))
        content = "\n".join(p.text for p in doc.paragraphs)

    # 切分文档，保存向量数据
    document_list = split_document(content, ext, 200)
    milvusVector.save_documents(document_list, user_id, knowledge_id, file_id)

    return {"filename": file.filename, "content": document_list}
```

5. 修改 download_file 端点，使用流式传输：

```python
# apps/api/knowledgebase.py
from fastapi.responses import StreamingResponse

@router.get("/download_file")
async def download_file(
    file_id: int = Query(..., description="文件ID"),
    session: AsyncSession = Depends(get_session),
):
    """通过文件ID下载文件（流式传输，避免内存溢出）"""
    result = await session.execute(
        select(KnowledgeBaseFile).where(KnowledgeBaseFile.id == file_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    content_type = CONTENT_TYPE_MAP.get(file.file_type, "application/octet-stream")
    encoded_filename = quote(file.file_name)

    def iter_file():
        """迭代器函数，逐块读取文件"""
        chunk_size = 64 * 1024  # 64KB chunks
        with file_storage.get_file_reader(file.file_path) as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        iter_file(),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
```

**方案2：如果必须存储在数据库，添加大小限制和流式读取**

```python
# apps/database/models.py
class KnowledgeBaseFile(Base):
    __tablename__ = "knowledge_base_file"

    # ... 其他字段 ...

    file_content: Mapped[bytes | None] = mapped_column(
        LargeBinary(length=5 * 1024 * 1024),  # 限制5MB
        comment="文件内容(最大5MB)"
    )
```

在上传时验证大小：

```python
MAX_DB_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/upload_file")
async def upload_file(...):
    raw = await file.read()

    # 检查文件大小
    if len(raw) > MAX_DB_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过数据库限制 ({MAX_DB_FILE_SIZE} 字节)"
        )

    # 继续处理...
```

---

## 问题5：日志记录不够完善

### 问题描述

1. 数据库日志写死为开启：`echo=True`（已在问题2中解决）
2. 缺少结构化日志
3. 某些关键操作没有日志记录
4. 日志级别使用不当（如某些info应该用debug）
5. 缺少请求追踪ID

### 修复方案

**方案1：创建结构化日志器**

```python
# apps/utils/logging_config.py
import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from apps.config import settings

class JSONFormatter(logging.Formatter):
    """JSON格式化器，用于结构化日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra") and record.extra:
            log_entry["extra"] = record.extra

        return json.dumps(log_entry, ensure_ascii=False)

class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(
        self,
        level: int,
        message: str,
        extra: dict[str, Any] | None = None,
        exc_info: Any = None
    ) -> None:
        """记录结构化日志"""
        if extra:
            extra_obj = type("Extra", (), {"extra": extra})()
            self.logger.log(level, message, extra={"obj": extra_obj}, exc_info=exc_info)
        else:
            self.logger.log(level, message, exc_info=exc_info)

    def debug(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self._log(logging.DEBUG, message, extra)

    def info(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self._log(logging.INFO, message, extra)

    def warning(self, message: str, extra: dict[str, Any] | None = None) -> None:
        self._log(logging.WARNING, message, extra)

    def error(
        self,
        message: str,
        extra: dict[str, Any] | None = None,
        exc_info: Any = None
    ) -> None:
        self._log(logging.ERROR, message, extra, exc_info)

def setup_logging() -> None:
    """配置应用日志"""
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    # 根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # 使用JSON格式化器（生产环境）或简单格式化器（开发环境）
    if settings.LOG_LEVEL == "DEBUG":
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        formatter = JSONFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器（可选）
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 设置第三方库日志级别
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
```

在 `main.py` 中使用：

```python
from apps.utils.logging_config import setup_logging, StructuredLogger

setup_logging()
logger = StructuredLogger(__name__)
```

**方案2：添加请求追踪中间件**

```python
# main.py
import uuid
import time
from fastapi import Request

@app.middleware("http")
async def request_tracing(request: Request, call_next):
    """请求跟踪中间件"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()

    logger.info(
        "请求开始",
    )

    response = await call_next(request)
    elapsed = time.perf_counter() - start_time

    logger.info(
        "请求完成",
    )

    return response
```

**方案3：为关键操作添加结构化日志**

```python
# apps/api/knowledgebase.py
from apps.utils.logging_config import StructuredLogger

logger = StructuredLogger(__name__)

@router.post("/upload_file")
async def upload_file(...):
    ext = Path(file.filename or "").suffix.lstrip(".").lower()

    logger.info(
        "开始文件上传",
        extra={
            "user_id": user_id,
            "knowledge_id": knowledge_id,
            "file_name": file.filename,
            "file_type": ext,
        }
    )

    try:
        raw = await file.read()
        file_md5 = hashlib.md5(raw).hexdigest()

        # 查询是否已存在同名文件
        result = await session.execute(
            select(KnowledgeBaseFile).where(
                KnowledgeBaseFile.creator_id == user_id,
                KnowledgeBaseFile.knowledge_id == knowledge_id,
                KnowledgeBaseFile.file_name == file.filename,
            )
        )
        existing = result.scalar_one_or_none()

        if existing and existing.file_md5 == file_md5:
            logger.info(
                "文件未变更，跳过上传",
                extra={
                    "user_id": user_id,
                    "file_name": file.filename,
                    "file_id": existing.id,
                }
            )
            return {"filename": file.filename, "message": "文件未变更，跳过上传"}

        # 处理文件...
        file_id = knowledgeBaseFile.id

        logger.info(
            "文件上传成功",
            extra={
                "file_id": file_id,
                "file_path": file_path,
                "file_size": file_size,
                "is_new": existing is None,
                "doc_count": len(document_list),
            }
        )

        return {"filename": file.filename, "content": document_list}

    except Exception as e:
        logger.error(
            "文件上传失败",
            extra={
                "user_id": user_id,
                "file_name": file.filename,
                "error_type": type(e).__name__,
            },
            exc_info=e
        )
        raise
```

**方案4：为数据库操作添加日志**

```python
# apps/database/async_engine.py
import logging

logger = StructuredLogger(__name__)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(
                "数据库操作失败",
                extra={
                    "operation": "unknown",
                    "error_type": type(e).__name__,
                },
                exc_info=e
            )
            raise DatabaseError("操作", str(e)) from e
```

---

## 问题6：缺少请求验证和限流

### 问题描述

1. API端点缺少速率限制
2. 没有请求体大小限制
3. 输入验证不够严格
4. 没有防止暴力攻击的机制
5. 缺少请求ID验证

### 修复方案

**方案1：使用 slowapi 添加速率限制**

```bash
# 安装依赖
pip install slowapi
```

```python
# main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, status, JSONResponse

# 创建限流器
limiter = Limiter(key_func=get_remote_address)

# 添加到FastAPI应用
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 自定义限流异常处理器
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded
):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "请求过于频繁，请稍后再试",
            "retry_after": str(exc.retry_after) if exc.retry_after else None
        }
    )
```

在路由上应用：

```python
# apps/api/knowledgebase.py
from slowapi import Limiter

limiter: Limiter = ...  # 从main导入

@router.post(
    "/upload_file",
    dependencies=[Depends(limiter.limit("5/minute"))]  # 每分钟5次
)
async def upload_file(...):
    pass
```

**方案2：基于用户的速率限制**

```python
def get_user_id(request: Request) -> str:
    """从请求中获取用户ID用于限流"""
    # 优先从请求体中获取，其次从头部，最后使用IP
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        user_id = get_remote_address(request)
    return user_id

# 创建基于用户的限流器
user_limiter = Limiter(key_func=get_user_id)

@router.post(
    "/upload_file",
    dependencies=[Depends(user_limiter.limit("10/minute"))]  # 每用户每分钟10次
)
async def upload_file(...):
    pass
```

**方案3：请求体大小限制**

```python
# main.py
from fastapi import Request, JSONResponse

MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """限制请求体大小"""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        logger.warning(
            "请求体过大",
            extra={
                "content_length": int(content_length),
                "max_size": MAX_REQUEST_SIZE,
                "client": request.client.host if request.client else None,
            }
        )
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": f"请求体过大，最大允许 {MAX_REQUEST_SIZE} 字节"}
        )

    response = await call_next(request)
    return response
```

**方案4：增强输入验证**

```python
# apps/models/request_params.py
from pydantic import BaseModel, Field, field_validator
import re

class ChatParams(BaseModel):
    """用户对话输入参数"""

    user_id: str = Field(..., min_length=1, max_length=64, description="用户ID")
    thread_id: str = Field(..., min_length=1, max_length=64, description="会话ID")
    user_input: str = Field(..., min_length=1, max_length=10000, description="用户输入")

    @field_validator("user_id", "thread_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("不能为空或仅包含空白字符")
        # 只允许字母、数字、下划线、连字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("ID只能包含字母、数字、下划线和连字符")
        return v.strip()

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("用户输入不能为空或仅包含空白字符")
        stripped = v.strip()
        # 检查是否包含过多重复字符（防止恶意输入）
        if len(set(stripped)) < len(stripped) * 0.1:
            raise ValueError("输入包含过多重复字符")
        # 检查是否包含可疑的SQL注入模式
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC)\b)",
            r"(--|#|/\*|\*/)",
            r"(\bor\b|\band\b)\s*\d+\s*=\s*\d+"
        ]
        for pattern in sql_patterns:
            if re.search(pattern, stripped, re.IGNORECASE):
                raise ValueError("输入包含非法字符")
        return stripped

class DeleteFileParams(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64, description="用户ID")
    knowledge_id: int = Field(..., gt=0, description="知识库ID")
    file_id: int = Field(..., gt=0, description="文件ID")
```

**方案5：添加IP白名单（可选）**

```python
# apps/config.py
class Settings(BaseSettings):
    # ... 其他配置 ...

    # IP白名单（如果启用，则只允许这些IP访问）
    IP_WHITELIST: list[str] = []
    # IP黑名单
    IP_BLACKLIST: list[str] = []

# main.py
@app.middleware("http")
async def ip_filter(request: Request, call_next):
    """IP过滤中间件"""
    client_ip = request.client.host if request.client else None

    # 检查黑名单
    if client_ip and settings.IP_BLACKLIST:
        if client_ip in settings.IP_BLACKLIST:
            logger.warning(f"IP被黑名单阻止: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "访问被拒绝"}
            )

    # 检查白名单
    if settings.IP_WHITELIST:
        if client_ip not in settings.IP_WHITELIST:
            logger.warning(f"IP不在白名单中: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "访问被拒绝"}
            )

    return await call_next(request)
```

---

## 问题8：缺少资源清理和超时控制

### 问题描述

1. 文件处理没有超时控制
2. LLM调用没有超时设置
3. 长时间运行的操作可能导致资源泄漏
4. 数据库查询可能长时间阻塞
5. 某些资源没有正确关闭

### 修复方案

**方案1：使用 asyncio.timeout 添加超时控制**

```python
# apps/utils/timeout.py
import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

@asynccontextmanager
async def timeout_context(seconds: int, timeout_message: str | None = None) -> AsyncGenerator[None, None]:
    """超时上下文管理器"""
    try:
        async with asyncio.timeout(seconds):
            yield
    except TimeoutError:
        msg = timeout_message or f"操作超时（{seconds}秒）"
        raise TimeoutError(msg) from None

class AsyncTimeout:
    """异步超时装饰器"""

    def __init__(self, seconds: int, timeout_message: str | None = None):
        self.seconds = seconds
        self.timeout_message = timeout_message

    def __call__(self, func: Any) -> Any:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async with timeout_context(self.seconds, self.timeout_message):
                return await func(*args, **kwargs)
        return wrapper
```

**方案2：为文件上传添加超时**

```python
# apps/api/knowledgebase.py
from apps.utils.timeout import timeout_context

@router.post("/upload_file")
async def upload_file(...):
    async with timeout_context(30, "文件上传超时"):
        raw = await file.read()
        # 继续处理...
```

**方案3：为LLM调用添加超时**

```python
# apps/agent/llm/llm_factory.py
from apps.config import settings

def get_openai_llm(
    model: str = "gpt-5.2",
    timeout: int = 60,
    max_retries: int = 3
) -> ChatOpenAI:
    return ChatOpenAI(
        temperature=0,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
        request_timeout=timeout,
    )

# 在配置中添加
# apps/config.py
class Settings(BaseSettings):
    # ... 其他配置 ...

    # LLM配置
    LLM_TIMEOUT: int = 60  # LLM调用超时（秒）
    LLM_MAX_RETRIES: int = 3  # 最大重试次数
```

**方案4：数据库查询超时**

```python
# apps/database/async_engine.py
from apps.utils.timeout import timeout_context

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            async with timeout_context(settings.MYSQL_STATEMENT_TIMEOUT, "数据库提交超时"):
                await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error("数据库操作失败: %s", e, exc_info=True)
            raise DatabaseError("操作", str(e)) from e
        except Exception as e:
            await session.rollback()
            logger.error("未知错误: %s", e, exc_info=True)
            raise
```

**方案5：使用上下文管理器管理资源**

```python
# apps/utils/resource_manager.py
from contextlib import asynccontextmanager, contextmanager
from typing import BinaryIO, AsyncGenerator

@contextmanager
def managed_file(path: str, mode: str = "rb"):
    """自动关闭文件的上下文管理器"""
    f = open(path, mode)
    try:
        yield f
    finally:
        f.close()

@asynccontextmanager
async def managed_lock(lock: asyncio.Lock) -> AsyncGenerator[None, None]:
    """自动释放锁的上下文管理器"""
    await lock.acquire()
    try:
        yield finally:
        lock.release()
```

**方案6：为Agent图执行添加超时**

```python
# apps/api/agent_chat.py
from apps.utils.timeout import AsyncTimeout

@router.post("/chat", response_class=EventSourceResponse)
@AsyncTimeout(300, "Agent响应超时")  # 5分钟超时
async def agent_chat(chatParams: ChatParams) -> AsyncIterable[dict]:
    try:
        from apps.agent.graph import get_graph

        compiled_graph = get_graph()
        config = {
            "configurable": {
                "thread_id": chatParams.thread_id,
                "user_id": chatParams.user_id
            }
        }

        for chunk in compiled_graph.stream(
            {"messages": [{"role": "user", "content": chatParams.user_input}]},
            config,
            stream_mode="messages",
        ):
            # 处理chunk...
            pass

    except TimeoutError as e:
        logger.error(f"Agent响应超时: {e}")
        yield {"error": f"❌ 响应超时: {e}"}
    except Exception as e:
        logger.error(f"❌ Agent响应失败: {e}")
        traceback.print_exc()
        yield {"error": f"❌ Agent响应失败: {e}"}
```

---

## 问题9：单例模式实现不安全

### 问题描述

在多个文件中使用了模块级单例：

```python
# apps/agent/graph.py
_compiled_graph = None

def init_graph(checkpointer):
    global _compiled_graph
    _compiled_graph = build_workflow().compile(checkpointer=checkpointer)
```

```python
# apps/agent/memory/mem0.py
_memory_client = None

def init_memory():
    global _memory_client
    _memory_client = MemoryManager().memory_client
```

问题：
1. 在多线程/异步环境下不安全
2. 初始化状态难以追踪
3. 没有防止重复初始化
4. 测试时难以重置

### 修复方案

**方案1：使用线程安全的单例基类**

```python
# apps/utils/singleton.py
import threading
from typing import Any, TypeVar

T = TypeVar("T")

class ThreadSafeSingleton:
    """线程安全的单例基类"""

    _instance: Any = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls: type[T]) -> T:
        if not cls._initialized:
            with cls._lock:
                if not cls._initialized:
                    instance = super().__new__(cls)
                    cls._instance = instance
                    cls._initialized = True
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例（主要用于测试）"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
```

**方案2：应用到 graph.py**

```python
# apps/agent/graph.py
from apps.utils.singleton import ThreadSafeSingleton

class CompiledGraph(ThreadSafeSingleton):
    """编译后的图单例"""

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.graph = None
            self.initialized = False

    def init(self, checkpointer) -> None:
        """初始化 graph"""
        if not self.initialized:
            self.graph = build_workflow().compile(checkpointer=checkpointer)
            self.initialized = True

    def get(self):
        """获取 graph 实例"""
        if not self.initialized:
            raise RuntimeError("Graph 未初始化，请先在 lifespan 中调用 init()")
        return self.graph

    def reset(self) -> None:
        """重置 graph（主要用于测试）"""
        self.graph = None
        self.initialized = False

# 创建单例
_compiled_graph = CompiledGraph()

def init_graph(checkpointer):
    """初始化 graph"""
    _compiled_graph.init(checkpointer)

def get_graph():
    """获取已编译的 graph 单例"""
    return _compiled_graph.get()

def reset_graph():
    """重置 graph（主要用于测试）"""
    _compiled_graph.reset()
```

**方案3：应用到 memory/mem0.py**

```python
# apps/agent/memory/mem0.py
from apps.utils.singleton import ThreadSafeSingleton

class MemoryClientSingleton(ThreadSafeSingleton):
    """Memory客户端单例"""

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.client = None
            self.initialized = False

    def init(self) -> None:
        """初始化 memory_client"""
        if not self.initialized:
            manager = MemoryManager()
            self.client = manager.memory_client
            self.initialized = True

    def get(self):
        """获取 memory_client 实例"""
        if not self.initialized:
            raise RuntimeError("MemoryClient 未初始化")
        return self.client

    def reset(self) -> None:
        """重置 memory_client（主要用于测试）"""
        self.client = None
        self.initialized = False

# 创建单例
_memory_client = MemoryClientSingleton()

def init_memory():
    """初始化 memory_client"""
    _memory_client.init()

def get_memory_client():
    """获取已初始化的 memory_client 单例"""
    return _memory_client.get()

def reset_memory():
    """重置 memory_client（主要用于测试）"""
    _memory_client.reset()
```

**方案4：添加测试支持**

在测试文件中：

```python
# tests/conftest.py
import pytest
from apps.agent.graph import reset_graph
from apps.agent.memory.mem0 import reset_memory

@pytest.fixture(autouse=True)
def reset_singletons():
    """每个测试前重置单例"""
    yield
    reset_graph()
    reset_memory()
```

---

## 问题10：缺少健康检查和监控

### 问题描述

1. 只有一个简单的根路径健康检查
2. 无法检查依赖服务状态
3. 没有性能监控
4. 无法追踪应用状态
5. 缺少指标收集

### 修复方案

**方案1：添加健康检查路由**

```python
# apps/api/health.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from datetime import datetime
from typing import Any

from apps.database.async_engine import get_session
from apps.agent.memory.mem0 import get_memory_client
from apps.agent.rag import milvusVector
from apps.agent.graph import get_graph
from apps.exceptions import NotFoundError

health_router = APIRouter(prefix="/health", tags=["health"])

@health_router.get("/")
async def health_check() -> dict[str, Any]:
    """基本健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }

@health_router.get("/detailed")
async def detailed_health_check(
    session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    """详细健康检查 - 检查所有依赖服务"""
    checks = {
        "database": await check_database(session),
        "memory": await check_memory(),
        "vector_store": await check_vector_store(),
        "graph": check_graph(),
    }

    all_healthy = all(check["status"] == "ok" for check in checks.values())
    status_code = 200 if all_healthy else 503

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }

async def check_database(session: AsyncSession) -> dict[str, Any]:
    """检查数据库连接"""
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "ok", "message": "数据库连接正常"}
    except Exception as e:
        return {"status": "error", "message": f"数据库连接失败: {str(e)}"}

async def check_memory() -> dict[str, Any]:
    """检查记忆系统"""
    try:
        memory_client = get_memory_client()
        # 简单的搜索操作测试连接
        _ = memory_client.search("test", user_id="health_check", limit=1)
        return {"status": "ok", "message": "记忆系统正常"}
    except Exception as e:
        return {"status": "error", "message": f"记忆系统失败: {str(e)}"}

async def check_vector_store() -> dict[str, Any]:
    """检查向量存储"""
    try:
        # 测试连接
        _ = milvusVector.client.list_collections()
        return {"status": "ok", "message": "向量存储正常"}
    except Exception as e:
        return {"status": "error", "message": f"向量存储失败: {str(e)}"}

def check_graph() -> dict[str, Any]:
    """检查Agent图"""
    try:
        graph = get_graph()
        return {"status": "ok", "message": "Agent图已初始化"}
    except RuntimeError as e:
        return {"status": "error", "message": f"Agent图未初始化: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Agent图检查失败: {str(e)}"}
```

在 `main.py` 中注册：

```python
from apps.api.health import router as health_router

app.include_router(health_router)
```

**方案2：添加性能监控**

```python
# apps/utils/metrics.py
import time
import threading
from collections import defaultdict, deque
from typing import Callable, Any
from functools import wraps

class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histories: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        self._lock = threading.Lock()

    def increment(self, name: str, value: int = 1) -> None:
        """增加计数器"""
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        """设置仪表值"""
        with self._lock:
            self._gauges[name] = value

    def record_timing(self, name: str, duration: float) -> None:
        """记录耗时"""
        with self._lock:
            self._histories[name].append(duration)

    def get_summary(self) -> dict[str, Any]:
        """获取指标摘要"""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timings": {
                    name: {
                        "count": len(history),
                        "avg": sum(history) / len(history) if history else 0,
                        "min": min(history) if history else 0,
                        "max": max(history) if history else 0,
                    }
                    for name, history in self._histories.items()
                },
            }

# 全局指标收集器
metrics = MetricsCollector()

def monitor_performance(name: str | None = None) -> Callable:
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            metric_name = name or func.__name__
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time

                metrics.increment(f"{metric_name}_calls")
                metrics.record_timing(f"{metric_name}_duration", elapsed)

                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time

                metrics.increment(f"{metric_name}_errors")
                metrics.record_timing(f"{metric_name}_duration", elapsed)

                raise

        return wrapper
    return decorator
```

**方案3：添加指标端点**

```python
# apps/api/health.py
from apps.utils.metrics import metrics

@health_router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """获取应用指标"""
    return metrics.get_summary()
```

**方案4：应用性能监控到关键函数**

```python
# apps/api/knowledgebase.py
from apps.utils.metrics import monitor_performance

@router.post("/upload_file")
@monitor_performance("upload_file")
async def upload_file(...):
    pass

@router.get("/get_files")
@monitor_performance("get_files")
async def get_files(...):
    pass
```

**方案5：添加就绪/存活检查**

```python
# apps/api/health.py
@health_router.get("/live")
async def liveness_probe() -> dict[str, Any]:
    """存活探针 - 检查应用是否在运行"""
    return {"status": "alive"}

@health_router.get("/ready")
async def readiness_probe(
    session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    """就绪探针 - 检查应用是否准备好接收流量"""
    checks = {
        "database": await check_database(session),
        "memory": await check_memory(),
    }

    all_ready = all(check["status"] == "ok" for check in checks.values())

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
    }
```

---

## 问题11：测试覆盖不足

### 问题描述

1. 缺少单元测试
2. 缺少集成测试
3. 没有测试覆盖率报告
4. 关键功能未经测试
5. 测试目录结构不完整

### 修复方案

**方案1：创建测试目录结构**

```
tests/
├── conftest.py              # pytest 配置和 fixtures
├── test_config.py            # 配置测试
├── test_api/                # API 测试
│   ├── __init__.py
│   ├── test_knowledgebase.py
│   └── test_agent_chat.py
├── test_agent/              # Agent 测试
│   ├── __init__.py
│   ├── test_graph.py
│   ├── test_nodes/
│   │   ├── __init__.py
│   │   ├── test_router.py
│   │   ├── test_retriever.py
│   │   ├── test_planner.py
│   │   └── test_evaluator.py
│   └── test_memory/
│       ├── __init__.py
│       └── test_mem0.py
└── test_services/           # 服务测试
    ├── __init__.py
    └── test_file_storage.py
```

**方案2：创建 conftest.py**

```python
# tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from main import app
from apps.database.models import Base
from apps.config import settings

# 测试数据库配置
TEST_DATABASE_URL = settings.MYSQL_URL.replace(
    settings.MYSQL_DATABASE,
    "test_buddy_ai"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_test_database():
    """创建测试数据库表"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 清理
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_test_database) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def client() -> Generator:
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(autouse=True)
async def reset_singletons():
    """每个测试前重置单例"""
    from apps.agent.graph import reset_graph
    from apps.agent.memory.mem0 import reset_memory

    yield
    reset_graph()
    reset_memory()

@pytest.fixture
def mock_llm():
    """Mock LLM"""
    from unittest.mock import Mock, patch

    mock = Mock()
    mock_response = Mock()
    mock_response.content = "模拟的LLM响应"
    mock.invoke.return_value = mock_response
    mock.with_structured_output.return_value.invoke.return_value = Mock(
        route_decision="answer_directly",
        route_reason="测试"
    )

    return mock
```

**方案3：编写API测试**

```python
# tests/test_api/test_knowledgebase.py
import pytest
from fastapi.testclient import TestClient
from io import BytesIO

from tests.conftest import db_session


@pytest.mark.integration
class TestKnowledgeBaseAPI:
    """知识库API测试"""

    def test_upload_txt_file_success(self, client: TestClient):
        """测试上传txt文件成功"""
        response = client.post(
            "/knowledgebase/upload_file",
            files={
                "file": (
                    "test.txt",
                    BytesIO(b"这是测试内容\n第二行内容"),
                    "text/plain"
                )
            },
            data={
                "user_id": "test_user",
                "knowledge_id": 1
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "content" in data
        assert data["filename"] == "test.txt"

    def test_upload_md_file_success(self, client: TestClient):
        """测试上传md文件成功"""
        md_content = b"""# 测试标题

## 子标题

这是markdown内容。
"""
        response = client.post(
            "/knowledgebase/upload_file",
            files={
                "file": (
                    "test.md",
                    BytesIO(md_content),
                    "text/markdown"
                )
            },
            data={
                "user_id": "test_user",
                "knowledge_id": 1
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.md"

    def test_upload_file_invalid_type(self, client: TestClient):
        """测试上传不支持的文件类型"""
        response = client.post(
            "/knowledgebase/upload_file",
            files={
                "file": (
                    "test.pdf",
                    BytesIO(b"test content"),
                    "application/pdf"
                )
            },
            data={
                "user_id": "test_user",
                "knowledge_id": 1
            }
        )

        assert response.status_code == 400
        assert "不支持的文件格式" in response.json()["detail"]

    def test_get_files_empty(self, client: TestClient):
        """测试获取空文件列表"""
        response = client.get(
            "/knowledgebase/get_files",
            params={"user_id": "test_user", "knowledge_id": 999}
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_files_with_data(self, client: TestClient):
        """测试获取有数据的文件列表"""
        # 先上传一个文件
        client.post(
            "/knowledgebase/upload_file",
            files={
                "file": ("test.txt", BytesIO(b"test"), "text/plain")
            },
            data={"user_id": "test_user", "knowledge_id": 1}
        )

        # 获取文件列表
        response = client.get(
            "/knowledgebase/get_files",
            params={"user_id": "test_user", "knowledge_id": 1}
        )

        assert response.status_code == 200
        files = response.json()
        assert len(files) > 0
        assert files[0]["file_name"] == "test.txt"
```

**方案4：编写节点单元测试**

```python
# tests/test_agent/test_nodes/test_router.py
import pytest
from unittest.mock import Mock, patch

from apps.agent.nodes.router import router
from apps.agent.state import GraphState, RouteSchema

@pytest.mark.unit
class TestRouterNode:
    """Router 节点测试"""

    def test_router_with_knowledge_search(self, mock_llm):
        """测试知识库搜索路由"""
        state = GraphState(
            messages=[Mock(content="测试知识查询")]
        )

        with patch('apps.agent.nodes.router.get_llm') as mock_get_llm:
            mock_get_llm.return_value = mock_llm

            result = router(state)

            assert result["route_decision"] == "knowledge_base_search"
            assert "route_reason" in result
            assert result["original_input"] == "测试知识查询"
            assert result["enhanced_input"] is None
            assert result["rag_docs"] == []

    def test_router_with_plan_and_execute(self, mock_llm):
        """测试计划执行路由"""
        state = GraphState(
            messages=[Mock(content="帮我制定一个计划")]
        )

        with patch('apps.agent.nodes.router.get_llm') as mock_getllm:
            mock_llm_instance = Mock()
            mock_schema = Mock()
            mock_schema.route_decision = "plan_and_execute"
            mock_schema.route_reason = "需要多步骤执行"
            mock_llm_instance.with_structured_output.return_value.invoke.return_value = mock_schema
            mock_getllm.return_value = mock_llm_instance

            result = router(state)

            assert result["route_decision"] == "plan_and_execute"

    def test_router_empty_messages(self, mock_llm):
        """测试空消息"""
        state = GraphState(messages=[])

        with patch('apps.agent.nodes.router.get_llm') as mock_get_llm:
            mock_get_llm.return_value = mock_llm

            result = router(state)

            assert result["route_decision"] == "answer_directly"
            assert result["original_input"] == ""
```

**方案5：配置pytest**

在 `pyproject.toml` 中添加：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "--cov=apps",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=80",  # 要求80%覆盖率
    "-v",
    "--tb=short"
]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: 单元测试",
    "integration: 集成测试",
    "slow: 慢速测试",
]
```

**方案6：运行测试**

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api/test_knowledgebase.py

# 运行带标记的测试
pytest -m unit
pytest -m integration

# 生成覆盖率报告
pytest --cov=apps --cov-report=html
pytest --cov=apps --cov-report=term-missing

# 跳过慢速测试
pytest -m "not slow"

# 并行运行测试（需要 pytest-xdist）
pytest -n auto
```

---

## 问题12：文档和类型检查工具配置

### 问题描述

虽然项目有 `pyproject.toml`，但缺少以下工具配置：
1. Black 代码格式化配置
2. isort 导入排序配置
3. mypy 类型检查配置
4. ruff 代码检查配置

### 修复方案

**方案1：在 pyproject.toml 中添加工具配置**

```toml
# pyproject.toml
[project]
name = "buddy-ai"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    # ... 现有依赖 ...
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-xdist>=3.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "bandit>=1.7.0",
    "pre-commit>=3.0.0",
    "slowapi>=0.1.9",
]

# ========== Black 配置 ==========
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | \.pytest_cache
  | \.idea
  | build
  | dist
)/
'''

# ========== isort 配置 ==========
[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

# ========== Ruff 配置 ==========
[tool.ruff]
line-length = 88
target-version = "py310"
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by black)
    "B008",   # do not perform function calls in argument defaults
    "C901",   # too complex
]
exclude = [
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pypackages__",
    "_build",
    "buck-out",
    "build",
    "dist",
    "node_modules",
    "venv",
]

# ========== Mypy 配置 ==========
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
follow_imports = "normal"
ignore_missing_imports = true
strict_optional = true

plugins = []

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

# ========== Pytest 配置 ==========
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "--cov=apps",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
    "-v",
    "--tb=short",
    "--asyncio-mode=auto"
]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: 单元测试",
    "integration: 集成测试",
    "slow: 慢速测试",
]
filterwarnings = [
    "ignore::DeprecationWarning",
]

# ========== Coverage 配置 ==========
[tool.coverage.run]
source = ["apps"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

**方案2：创建 .pre-commit-config.yaml**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0]
```

**方案3：创建 Makefile 或 scripts**

```bash
# Makefile
.PHONY: help install format lint test clean

help:
	@echo "可用命令:"
	@echo "  make install      - 安装依赖"
	@echo "  make format       - 格式化代码"
	@echo "  make lint         - 代码检查"
	@echo "  make test         - 运行测试"
	@echo "  make clean        - 清理"

install:
	pip install -e ".[dev]"

format:
	black apps tests
	isort apps tests

lint:
	ruff check apps tests
	mypy apps

test:
	pytest --cov=apps --cov-report=html

test-unit:
	pytest -m unit --cov=apps

test-integration:
	pytest -m integration --cov=apps

clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
```

---

## 总结

以上是buddy-ai后端项目中发现的主要问题及其修复方案。建议按优先级处理：

### 高优先级（安全和稳定性）
1. **问题3**：内存管理 - 大文件存储（可能导致OOM）
2. **问题6**：缺少请求验证和限流（安全风险）
3. **问题8**：缺少资源清理和超时控制（可能导致资源泄漏）

### 中优先级（可维护性和性能）
4. **问题2**：数据库连接池配置不够灵活
5. **问题5**：日志记录不够完善
6. **问题9**：单例模式实现不安全
7. **问题10**：缺少健康检查和监控

### 低优先级（代码质量）
8. **问题1**：类型注解不完整
9. **问题11**：测试覆盖不足
10. **问题12**：文档和类型检查工具配置

修复这些问题将显著提升项目的安全性、稳定性、性能和可维护性。
