"""
向量化服务 - asyncio 异步处理

使用统一 Collection 设计，支持增量更新和进度跟踪
"""
import logging
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass

from langchain_postgres import PGVector
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

from app.config import settings
from app.retriever.embeddings_model import get_embeddings_model
from app.services.user_file_service import user_file_service
from app.utils.document_processing import (
    process_document, compute_content_hash
)

logger = logging.getLogger(__name__)


@dataclass
class VectorizationResult:
    """向量化结果"""
    success: bool
    chunk_count: int
    summary: Optional[str] = None
    vectorized: bool = False
    error_message: Optional[str] = None


class VectorizationService:
    """异步向量化服务 - 使用统一 Collection"""

    def __init__(self):
        self.collection_name = settings.PGVECTOR_COLLECTION_NAME  # 从配置获取
        self.llm = ChatOpenAI(
            model="qwen-plus",
            openai_api_key=settings.DASHSCOPE_API_KEY,
            openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.3
        )

    async def vectorize_file(
        self,
        file_id: str,
        user_id: str,
        filename: str,
        is_public: bool = False
    ) -> VectorizationResult:
        """
        异步向量化文件

        使用 asyncio 实现异步处理，不阻塞主线程
        """
        try:
            user_file = user_file_service.get_file_by_id(file_id)
            if not user_file:
                return VectorizationResult(
                    success=False,
                    chunk_count=0,
                    error_message="文件不存在"
                )

            file_content = user_file_service.get_file_content(file_id)
            if not file_content:
                return VectorizationResult(
                    success=False,
                    chunk_count=0,
                    error_message="文件内容不存在"
                )

            # 检查是否需要向量化
            current_hash = compute_content_hash(file_content)
            if user_file.content_hash and current_hash == user_file.content_hash:
                logger.info(f"文件内容未变化，跳过向量化: {filename}")
                return VectorizationResult(
                    success=True,
                    chunk_count=user_file.chunk_count or 0,
                    summary=user_file.document_summary,
                    vectorized=False
                )

            temp_file_path = user_file_service.get_temp_file_path(file_id, user_file.file_type)

            try:
                # 处理文档
                result = await asyncio.to_thread(
                    process_document,
                    temp_file_path,
                    user_file.file_type,
                    file_content,
                    file_id,
                    user_id,
                    filename
                )

                chunks = result['documents']
                content_hash = result['content_hash']

                # 更新状态为处理中
                await self._update_task_status(file_id, "processing", 0, len(chunks), 0)

                # 生成摘要
                summary = await self._generate_summary(chunks)
                await self._update_task_status(file_id, "processing", 20, len(chunks), 0)

                # 删除旧向量数据
                await self._delete_old_vectors(file_id)

                # 向量化
                await self._vectorize_chunks(
                    chunks,
                    file_id,
                    user_id,
                    filename,
                    is_public,
                    batch_size=10
                )

                # 保存摘要
                await self._save_summary(summary, file_id, user_id, filename, is_public)

                # 更新文件记录
                await self._update_file_record(
                    file_id,
                    content_hash,
                    summary,
                    len(chunks)
                )

                # 标记完成
                await self._update_task_status(file_id, "completed", 100, len(chunks), len(chunks))

                logger.info(f"成功向量化 {filename}: {len(chunks)} 个片段")

                return VectorizationResult(
                    success=True,
                    chunk_count=len(chunks),
                    summary=summary,
                    vectorized=True
                )

            finally:
                user_file_service.cleanup_temp_file(temp_file_path)

        except Exception as e:
            logger.error(f"向量化失败: {e}")
            await self._update_task_status(file_id, "failed", 0, 0, 0, str(e))
            return VectorizationResult(
                success=False,
                chunk_count=0,
                error_message=str(e)
            )

    async def _generate_summary(self, chunks: list) -> str:
        """生成文档摘要"""
        # 使用前3个 chunks 生成摘要
        preview_text = "\n\n".join([c.page_content for c in chunks[:3]])[:5000]

        try:
            response = await self.llm.ainvoke(
                f"请为以下文档生成一个简洁的摘要（不超过200字）：\n\n{preview_text}"
            )
            return response.content
        except Exception as e:
            logger.warning(f"生成摘要失败: {e}")
            return preview_text[:200]

    async def _vectorize_chunks(
        self,
        chunks: list,
        file_id: str,
        user_id: str,
        filename: str,
        is_public: bool,
        batch_size: int = 10
    ):
        """分批向量化片段"""
        vector_store = PGVector(
            embeddings=get_embeddings_model(),
            collection_name=self.collection_name,
            connection=settings.POSTGRESQL_URL,
            use_jsonb=True,
        )

        total = len(chunks)
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]

            # 为每个chunk添加 doc_type 元数据
            for doc in batch:
                doc.metadata["doc_type"] = "chunk"

            await asyncio.to_thread(vector_store.add_documents, batch)

            processed = min(i + batch_size, total)
            progress = 20 + int((processed / total) * 70)  # 20-90%
            await self._update_task_status(file_id, "processing", progress, total, processed)

            logger.debug(f"向量化进度: {progress}% ({processed}/{total})")

    async def _save_summary(
        self,
        summary: str,
        file_id: str,
        user_id: str,
        filename: str,
        is_public: bool
    ):
        """保存摘要向量"""
        summary_doc = Document(
            page_content=summary,
            metadata={
                "doc_type": "summary",
                "file_id": file_id,
                "filename": filename,
                "user_id": user_id,
                "is_public": is_public,
                "source": filename
            }
        )

        vector_store = PGVector(
            embeddings=get_embeddings_model(),
            collection_name=self.collection_name,
            connection=settings.POSTGRESQL_URL,
            use_jsonb=True,
        )

        await asyncio.to_thread(vector_store.add_documents, [summary_doc])

    async def _delete_old_vectors(self, file_id: str):
        """删除旧向量数据"""
        # 通过 metadata 过滤查找该文件的向量数据
        vector_store = PGVector(
            embeddings=get_embeddings_model(),
            collection_name=self.collection_name,
            connection=settings.POSTGRESQL_URL,
            use_jsonb=True,
        )

        # 使用相似度搜索获取所有该文件的文档
        # 由于没有 get 方法，我们搜索一个通用的查询然后过滤
        try:
            # 直接查询数据库删除该 file_id 的向量
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
            cursor = conn.cursor()

            # 从 langchain_pg_embedding 表删除
            cursor.execute("""
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'file_id' = %s
                  AND collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = %s)
            """, (file_id, self.collection_name))

            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()

            if deleted_count > 0:
                logger.debug(f"删除 {deleted_count} 个旧向量片段")
        except Exception as e:
            logger.warning(f"删除旧向量数据失败: {e}")

    async def _update_task_status(
        self,
        file_id: str,
        status: str,
        progress: int,
        total_chunks: int,
        processed_chunks: int,
        error_message: str = None
    ):
        """更新任务状态"""
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE vectorization_tasks
                SET status = %s,
                    progress = %s,
                    total_chunks = %s,
                    processed_chunks = %s,
                    error_message = %s,
                    updated_at = NOW()
                WHERE file_id = %s
            """, (status, progress, total_chunks, processed_chunks, error_message, file_id))

            conn.commit()
        finally:
            cursor.close()
            conn.close()

    async def _update_file_record(
        self,
        file_id: str,
        content_hash: str,
        summary: str,
        chunk_count: int
    ):
        """更新文件记录"""
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE user_files
                SET content_hash = %s,
                    document_summary = %s,
                    chunk_count = %s,
                    last_vectorized_at = NOW()
                WHERE id = %s
            """, (content_hash, summary, chunk_count, file_id))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    async def create_task(self, file_id: str, user_id: str):
        """创建向量化任务"""
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO vectorization_tasks (file_id, user_id, status)
                VALUES (%s, %s, 'pending')
                RETURNING id
            """, (file_id, user_id))
            conn.commit()
            return cursor.fetchone()['id']
        finally:
            cursor.close()
            conn.close()

    async def get_task_status(self, file_id: str) -> Optional[Dict]:
        """获取任务状态"""
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM vectorization_tasks
                WHERE file_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (file_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            cursor.close()
            conn.close()


# 全局实例
vectorization_service = VectorizationService()