import os
import traceback
from pathlib import Path
from typing import Dict, List, Optional

from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredMarkdownLoader, Docx2txtLoader, TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from .embeddings_model import get_embeddings_model
from app.config import settings
from app.utils.datetime_utils import datetime_to_iso


def vectorize_uploaded_file(file_id: str, filename: str, user_id: str) -> Dict[str, any]:
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
        temp_file_path = user_file_service.get_temp_file_path(file_id, user_file.file_type)

        # 加载文件内容
        path = Path(temp_file_path)
        file_type = user_file.file_type

        if file_type == 'pdf':
            loader = PyMuPDFLoader(temp_file_path)
        elif file_type == 'md':
            loader = UnstructuredMarkdownLoader(temp_file_path)
        elif file_type == 'docx':
            loader = Docx2txtLoader(temp_file_path)
        elif file_type == 'txt':
            loader = TextLoader(temp_file_path, encoding='utf-8')
        elif file_type == 'csv':
            loader = CSVLoader(temp_file_path)
        else:
            return {"success": False, "chunk_count": 0, "message": f"不支持的文件类型: {file_type}"}

        loaded_texts = loader.load()

        # 切分文档
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = text_splitter.split_documents(loaded_texts)

        # 为每个文档添加元数据
        for doc in split_docs:
            doc.metadata.update({
                "file_id": file_id,
                "filename": user_file.original_filename,
                "file_type": user_file.file_type,
                "file_size": user_file.file_size,
                "upload_time": datetime_to_iso(user_file.upload_time) if user_file.upload_time else None,
                "source": user_file.original_filename,
                "user_id": user_id
            })

        # 删除旧的向量数据（使用文件名作为 collection name）
        delete_file_vectors(filename, user_id)

        # 添加到向量数据库（使用文件名作为 collection name）
        if settings.VECTOR_DB_TYPE == "postgresql":
            from langchain_postgres import PGVector

            # 使用文件名作为 collection name，在 cmetadata 中存储 file_id 和 user_id
            collection_metadata = {
                "file_id": file_id,
                "user_id": user_id
            }

            vectordb = PGVector(
                embeddings=get_embeddings_model(),
                collection_name=filename,  # 使用文件名
                collection_metadata=collection_metadata,
                connection=settings.POSTGRESQL_URL,
                use_jsonb=True,
            )
            vectordb.add_documents(split_docs)
            print(f"成功向量化 {len(split_docs)} 个文档片段 (PostgreSQL)")
        else:
            # Chroma 逻辑
            vectordb = Chroma.from_documents(
                documents=split_docs,
                embedding=get_embeddings_model(),
                persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"),
                collection_name=filename,
                metadata={"file_id": file_id, "user_id": user_id}
            )
            vectordb.persist()

        # 清理临时文件
        user_file_service.cleanup_temp_file(temp_file_path)

        return {
            "success": True,
            "chunk_count": len(split_docs)
        }

    except Exception as e:
        print(f"向量化失败: {e}")
        print(traceback.format_exc())
        return {
            "success": False,
            "chunk_count": 0,
            "message": str(e)
        }


def delete_file_vectors(filename: str, user_id: str) -> bool:
    """删除指定文件的向量数据"""
    try:
        if settings.VECTOR_DB_TYPE == "postgresql":
            from psycopg2.extras import RealDictCursor
            import psycopg2

            # 删除 collection
            conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
            cursor = conn.cursor()

            # 先删除 embedding 数据
            cursor.execute("""
                DELETE FROM langchain_pg_embedding
                WHERE collection_id = (
                    SELECT uuid FROM langchain_pg_collection
                    WHERE name = %s AND cmetadata @> %s::jsonb
                )
            """, (filename, f'{{"user_id": "{user_id}"}}'))

            # 删除 collection
            cursor.execute(
                "DELETE FROM langchain_pg_collection WHERE name = %s AND cmetadata @> %s::jsonb",
                (filename, f'{{"user_id": "{user_id}"}}')
            )

            conn.commit()
            cursor.close()
            conn.close()
            print(f"删除文件 {filename} 的向量数据")
            return True
        else:
            # Chroma 逻辑
            from langchain_chroma import Chroma

            vector_store = Chroma(
                persist_directory=settings.CHROMA_PERSIST_DIR,
                embedding_function=get_embeddings_model(),
                collection_name=filename
            )
            # 删除整个 collection
            vector_store.delete_collection()
            print(f"删除 Chroma collection: {filename}")
            return True
    except Exception as e:
        print(f"删除向量数据失败: {e}")
        return False


def vectorize_uploaded_files(file_ids: List[str], user_id: Optional[str] = None) -> Dict[str, any]:
    """
    将上传的文件向量化并保存到向量数据库

    Args:
        file_ids: 文件ID列表
        user_id: 用户ID（可选，用于用户级检索）

    Returns:
        dict: 包含success、chunk_count和file_metadata的字典
    """
    from app.services.user_file_service import user_file_service

    # 加载文件
    texts = []
    file_metadata = {}
    temp_file_paths = []

    try:
        for file_id in file_ids:
            try:
                # 从数据库获取文件信息
                user_file = user_file_service.get_file_by_id(file_id)
                if not user_file:
                    print(f"文件不存在: {file_id}")
                    continue

                # 创建临时文件用于加载
                temp_file_path = user_file_service.get_temp_file_path(file_id, user_file.file_type)
                temp_file_paths.append(temp_file_path)

                path = Path(temp_file_path)
                file_type = user_file.file_type

                # 获取加载器
                if file_type == 'pdf':
                    loader = PyMuPDFLoader(temp_file_path)
                elif file_type == 'md':
                    loader = UnstructuredMarkdownLoader(temp_file_path)
                elif file_type == 'docx':
                    loader = Docx2txtLoader(temp_file_path)
                elif file_type == 'txt':
                    loader = TextLoader(temp_file_path, encoding='utf-8')
                elif file_type == 'csv':
                    loader = CSVLoader(temp_file_path)
                else:
                    print(f"不支持的文件类型: {file_type}")
                    continue

                loaded_texts = loader.load()

                # 为每个文档添加文件元数据
                for doc in loaded_texts:
                    doc.metadata.update({
                        "file_id": file_id,
                        "filename": user_file.original_filename,
                        "file_type": user_file.file_type,
                        "file_size": user_file.file_size,
                        "upload_time": datetime_to_iso(user_file.upload_time) if user_file.upload_time else None,  # 转换为 ISO 格式字符串
                        "source": user_file.original_filename,
                        "user_id": user_id  # 添加用户ID用于过滤
                    })

                texts.extend(loaded_texts)

                # 保存文件元数据
                file_metadata[file_id] = {
                    "file_id": file_id,
                    "filename": user_file.original_filename,
                    "file_type": user_file.file_type,
                    "file_size": user_file.file_size,
                    "upload_time": datetime_to_iso(user_file.upload_time) if user_file.upload_time else None,
                    "chunk_count": 0  # 稍后更新
                }

                print(f"成功加载文件: {user_file.original_filename}")

            except Exception as e:
                print(f"加载文件时出错: {file_id}, 错误: {str(e)}")
                print(traceback.format_exc())
                continue

        if not texts:
            print("没有成功加载任何文档")
            return {"success": False, "chunk_count": 0, "file_metadata": {}}

        # 切分文档
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = text_splitter.split_documents(texts)

        # 统计每个文件的chunk数量
        for doc in split_docs:
            file_id = doc.metadata.get("file_id")
            if file_id in file_metadata:
                file_metadata[file_id]["chunk_count"] += 1

        # 创建或更新向量数据库
        try:
            # 根据配置选择向量数据库类型
            if settings.VECTOR_DB_TYPE == "postgresql":
                from app.retriever.pgvector_store import get_pgvector_store

                # 使用 PGVector
                vectordb = get_pgvector_store()
                vectordb.add_documents(split_docs)
                print(f"成功向量化 {len(split_docs)} 个文档片段 (PostgreSQL)")
            else:
                # 使用 Chroma
                vectordb = Chroma.from_documents(
                    documents=split_docs,
                    embedding=get_embeddings_model(),
                    persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"),
                    collection_name=os.getenv("CHROMA_COLLECTION_NAME", "buddy_ai_knowledge")
                )
                vectordb.persist()
                print(f"成功向量化 {len(split_docs)} 个文档片段 (Chroma)")

            return {
                "success": True,
                "chunk_count": len(split_docs),
                "file_metadata": file_metadata
            }
        except Exception as e:
            print(f"创建向量数据库时出错: {str(e)}")
            print(traceback.format_exc())
            return {"success": False, "chunk_count": 0, "file_metadata": {}}

    finally:
        # 清理临时文件
        for temp_file_path in temp_file_paths:
            try:
                user_file_service.cleanup_temp_file(temp_file_path)
            except Exception as e:
                print(f"清理临时文件失败: {e}")


def delete_user_vector_data(user_id: str) -> bool:
    """
    删除指定用户的所有向量数据

    Args:
        user_id: 用户ID

    Returns:
        bool: 是否删除成功
    """
    try:
        if settings.VECTOR_DB_TYPE == "postgresql":
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
                    print(f"从向量数据库删除了用户 {user_id} 的 {len(doc_ids_to_delete)} 个文档片段")
                    return True
        else:
            # Chroma
            from langchain_chroma import Chroma
            from app.retriever.embeddings_model import get_embeddings_model

            vector_store = Chroma(
                persist_directory=settings.CHROMA_PERSIST_DIR,
                embedding_function=get_embeddings_model(),
                collection_name=settings.CHROMA_COLLECTION_NAME
            )

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
                    print(f"从 Chroma 向量数据库删除了用户 {user_id} 的 {len(doc_ids_to_delete)} 个文档片段")
                    return True

        return True

    except Exception as e:
        print(f"删除用户向量数据失败: {e}")
        print(traceback.format_exc())
        return False