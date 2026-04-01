import logging
import traceback
from typing import Dict, Any

from langchain_community.document_loaders import (
    PyMuPDFLoader,
    UnstructuredMarkdownLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector

from .embeddings_model import get_embeddings_model
from app.config import settings
from app.utils.datetime_utils import datetime_to_iso

logger = logging.getLogger(__name__)


def vectorize_uploaded_file(
    file_id: str, filename: str, user_id: str
) -> Dict[str, Any]:
    """
    向量化单个上传的文件

    Args:
        file_id: 文件ID
        filename: 文件名
        user_id: 用户ID

    Returns:
        dict: 包含success和chunk_count的字典
    """
    from app.services.user_file_service import user_file_service

    try:
        # 从数据库获取文件信息
        user_file = user_file_service.get_file_by_id(file_id)
        if not user_file:
            return {"success": False, "chunk_count": 0, "message": "文件不存在"}

        # 创建临时文件用于加载
        temp_file_path = user_file_service.get_temp_file_path(
            file_id, user_file.file_type
        )

        # 加载文件内容
        file_type = user_file.file_type

        if file_type == "pdf":
            loader = PyMuPDFLoader(temp_file_path)
        elif file_type == "md":
            loader = UnstructuredMarkdownLoader(temp_file_path)
        elif file_type == "docx":
            loader = Docx2txtLoader(temp_file_path)
        elif file_type == "txt":
            loader = TextLoader(temp_file_path, encoding="utf-8")
        elif file_type == "csv":
            loader = CSVLoader(temp_file_path)
        else:
            return {
                "success": False,
                "chunk_count": 0,
                "message": f"不支持的文件类型: {file_type}",
            }

        loaded_texts = loader.load()

        # 切分文档
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = text_splitter.split_documents(loaded_texts)

        # 为每个文档添加元数据
        for doc in split_docs:
            doc.metadata.update(
                {
                    "file_id": file_id,
                    "filename": user_file.original_filename,
                    "file_type": user_file.file_type,
                    "file_size": user_file.file_size,
                    "upload_time": (
                        datetime_to_iso(user_file.upload_time)
                        if user_file.upload_time
                        else None
                    ),
                    "source": user_file.original_filename,
                    "user_id": user_id,
                    "doc_type": "chunk",  # 添加 doc_type 用于过滤
                }
            )

        # 删除旧的向量数据（使用统一collection，通过file_id和user_id过滤）
        delete_file_vectors_by_metadata(file_id, user_id)

        # 添加到 PostgreSQL 向量数据库（使用统一collection）
        vectordb = PGVector(
            embeddings=get_embeddings_model(),
            collection_name=settings.PGVECTOR_COLLECTION_NAME,
            connection=settings.POSTGRESQL_URL,
            use_jsonb=True,
        )
        vectordb.add_documents(split_docs)
        logger.info(f"成功向量化 {len(split_docs)} 个文档片段 (PostgreSQL)")

        # 清理临时文件
        user_file_service.cleanup_temp_file(temp_file_path)

        return {"success": True, "chunk_count": len(split_docs)}

    except Exception as e:
        logger.error(f"向量化失败: {e}")
        logger.debug(traceback.format_exc())
        return {"success": False, "chunk_count": 0, "message": str(e)}


def delete_file_vectors_by_metadata(file_id: str, user_id: str) -> bool:
    """
    通过元数据删除指定文件的向量数据（使用统一collection）

    Args:
        file_id: 文件ID
        user_id: 用户ID

    Returns:
        bool: 是否删除成功
    """
    try:
        from psycopg2.extras import RealDictCursor
        import psycopg2

        # 删除 embedding 数据（通过 metadata 过滤）
        conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM langchain_pg_embedding
            WHERE collection_id = (
                SELECT uuid FROM langchain_pg_collection
                WHERE name = %s
            )
            AND cmetadata->>'file_id' = %s
            AND cmetadata->>'user_id' = %s
        """,
            (settings.PGVECTOR_COLLECTION_NAME, file_id, user_id),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"删除文件 {file_id} 的向量数据: {deleted_count} 条记录")
        return deleted_count > 0
    except Exception as e:
        logger.error(f"删除向量数据失败: {e}")
        return False


def delete_file_vectors(filename: str, user_id: str) -> bool:
    """
    删除指定文件的向量数据（废弃：使用 delete_file_vectors_by_metadata 替代）

    此方法保留用于向后兼容，但推荐使用 delete_file_vectors_by_metadata
    """
    try:
        from psycopg2.extras import RealDictCursor
        import psycopg2

        # 删除 collection
        conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        # 先删除 embedding 数据
        cursor.execute(
            """
            DELETE FROM langchain_pg_embedding
            WHERE collection_id = (
                SELECT uuid FROM langchain_pg_collection
                WHERE name = %s AND cmetadata @> %s::jsonb
            )
        """,
            (filename, f'{{"user_id": "{user_id}"}}'),
        )

        # 删除 collection
        cursor.execute(
            "DELETE FROM langchain_pg_collection WHERE name = %s AND cmetadata @> %s::jsonb",
            (filename, f'{{"user_id": "{user_id}"}}'),
        )

        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"删除文件 {filename} 的向量数据")
        return True
    except Exception as e:
        logger.error(f"删除向量数据失败: {e}")
        return False


def delete_user_vector_data(user_id: str) -> bool:
    """
    删除指定用户的所有向量数据

    Args:
        user_id: 用户ID

    Returns:
        bool: 是否删除成功
    """
    try:
        from app.retriever.pgvector_store import get_pgvector_store

        vector_store = get_pgvector_store()

        # 获取所有文档
        all_docs = vector_store.get(include=["metadatas", "ids"])
        if all_docs and all_docs.get("metadatas") and all_docs.get("ids"):
            # 找到该用户的所有文档ID
            doc_ids_to_delete = []
            for idx, metadata in enumerate(all_docs["metadatas"]):
                if metadata.get("user_id") == user_id:
                    doc_ids_to_delete.append(all_docs["ids"][idx])

            # 删除这些文档
            if doc_ids_to_delete:
                vector_store.delete(ids=doc_ids_to_delete)
                logger.info(
                    f"从向量数据库删除了用户 {user_id} 的 {len(doc_ids_to_delete)} 个文档片段"
                )
                return True

        return True

    except Exception as e:
        logger.error(f"删除用户向量数据失败: {e}")
        logger.debug(traceback.format_exc())
        return False
