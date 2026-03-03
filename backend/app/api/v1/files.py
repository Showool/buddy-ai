"""
文件上传 API - PostgreSQL 存储版本，支持用户级文件管理
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Form

from app.config import settings
from app.models.file import (
    FileUploadResponse, VectorizeResponse, VectorizeRequest,
    FileInfo, FileListResponse, DeleteFileResponse
)
from app.services.user_file_service import user_file_service
from app.services.vectorization_service import vectorization_service

logger = logging.getLogger(__name__)

router = APIRouter()


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_file(filename: str, file_size: Optional[int] = None):
    """验证文件"""
    # 检查大小
    max_size = settings.MAX_FILE_SIZE
    if file_size is not None and file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制 ({max_size / 1024 / 1024}MB)"
        )

    # 检查类型
    ext = get_file_extension(filename)
    if ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"不支持的文件类型。支持的类型: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )


def get_vector_collection_metadata(user_id: str = None):
    """
    获取向量数据库中的文档元数据
    支持PGVector和Chroma
    新架构：每个文件一个 collection
    """
    try:
        from app.config import settings

        if settings.VECTOR_DB_TYPE == "postgresql":
            # PGVector 需要通过数据库直接查询元数据
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
            cursor = conn.cursor()

            try:
                if user_id:
                    # 查询特定用户的 collection 元数据
                    cursor.execute("""
                        SELECT c.name as collection_name, c.cmetadata
                        FROM langchain_pg_collection c
                        WHERE c.cmetadata @> %s::jsonb
                        ORDER BY c.created_at DESC
                    """, (f'{{"user_id": "{user_id}"}}',))
                else:
                    # 查询所有 collection
                    cursor.execute("""
                        SELECT c.name as collection_name, c.cmetadata
                        FROM langchain_pg_collection
                        ORDER BY c.created_at DESC
                    """)

                rows = cursor.fetchall()
                metadatas = []
                for row in rows:
                    # 获取该 collection 的文档数量
                    collection_name = row['collection_name']
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM langchain_pg_embedding e
                        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                        WHERE c.name = %s
                    """, (collection_name,))
                    count_result = cursor.fetchone()

                    metadata = row['cmetadata'] or {}
                    metadata['collection_name'] = collection_name
                    metadata['chunk_count'] = count_result['count'] if count_result else 0
                    metadatas.append(metadata)

                return metadatas
            finally:
                cursor.close()
                conn.close()
        else:
            # Chroma - 需要遍历所有用户文件的 collection
            from app.services.user_file_service import user_file_service

            if not user_id:
                return []

            # 获取用户的所有文件
            user_files = user_file_service.list_user_files(user_id)
            metadatas = []

            from langchain_chroma import Chroma

            for user_file in user_files:
                try:
                    vector_store = Chroma(
                        persist_directory=settings.CHROMA_PERSIST_DIR,
                        embedding_function=None,
                        collection_name=user_file.original_filename
                    )

                    all_docs = vector_store.get(include=["metadatas"])
                    if all_docs and all_docs.get("metadatas"):
                        chunk_count = len(all_docs["metadatas"])
                        metadatas.append({
                            "file_id": user_file.id,
                            "filename": user_file.original_filename,
                            "collection_name": user_file.original_filename,
                            "chunk_count": chunk_count,
                            "user_id": user_id
                        })
                except Exception as e:
                    logger.warning(f"获取 {user_file.original_filename} 的元数据失败: {e}")

            return metadatas
    except Exception as e:
        logger.error(f"获取向量数据库元数据失败: {e}")
        return []


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    user_id: str = Form(..., description="用户ID"),
    file: UploadFile = File(..., description="上传的文件"),
    is_public: bool = Form(False, description="是否公开")
):
    """
    上传文件到 PostgreSQL 并自动向量化

    如果用户已上传同名文件，则自动删除旧文件和向量数据
    向量化在后台异步执行，立即返回任务信息
    """
    logger.info(f"收到文件上传请求: user_id={user_id}, filename={file.filename}, is_public={is_public}")

    # 验证文件
    validate_file(file.filename or "", getattr(file.file, 'size', None))

    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)

    try:
        # 获取文件类型
        file_ext = get_file_extension(file.filename or "")

        # 保存到 PostgreSQL（同名文件会自动覆盖）
        saved_file_id = user_file_service.save_file(
            user_id=user_id,
            original_filename=file.filename or "",
            file_content=file_content,
            file_type=file_ext
        )

        # 创建向量化任务
        task_id = await vectorization_service.create_task(saved_file_id, user_id)

        # 异步启动向量化（不等待）
        asyncio.create_task(
            vectorization_service.vectorize_file(
                saved_file_id,
                user_id,
                file.filename or "",
                is_public
            )
        )

        logger.info(f"文件上传成功: {file.filename} (用户: {user_id}, ID: {saved_file_id}, 任务ID: {task_id})")

        return FileUploadResponse(
            id=saved_file_id,
            filename=file.filename or "",
            size=file_size,
            status="vectorizing",
            vectorized=False,
            task_id=str(task_id)
        )

    except Exception as e:
        logger.error(f"文件保存失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}"
        )


@router.post("/files/vectorize", response_model=VectorizeResponse)
async def vectorize_files(request: VectorizeRequest):
    """向量化文件"""
    from app.retriever.vectorize_files import vectorize_uploaded_files

    try:
        # 调用向量化函数，传入 user_id
        result = vectorize_uploaded_files(request.file_ids, request.user_id)

        if result.get("success"):
            chunk_count = result.get("chunk_count", 0)
            file_metadata = result.get("file_metadata", {})
            logger.info(f"用户 {request.user_id} 的文件向量化成功，共 {chunk_count} 个chunk，涉及 {len(file_metadata)} 个文件")
            return VectorizeResponse(
                status="success",
                chunk_count=chunk_count,
                message=f"向量化成功，处理了 {len(file_metadata)} 个文件"
            )
        else:
            return VectorizeResponse(
                status="failed",
                chunk_count=0,
                message="向量化失败"
            )
    except Exception as e:
        logger.error(f"向量化失败: {e}")
        return VectorizeResponse(
            status="failed",
            chunk_count=0,
            message=f"向量化失败: {str(e)}"
        )


@router.get("/files", response_model=FileListResponse)
async def list_files(
    user_id: str = Query(..., description="用户ID，用于过滤文件")
):
    """
    列出已上传的文件

    只返回该用户的文件
    从向量数据库和用户文件表中获取文件信息
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor

    files = []

    # 获取文件和向量化任务状态
    user_files = user_file_service.list_user_files(user_id)

    # 获取所有向量化任务状态
    task_status_map = {}
    conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT file_id, status, progress
            FROM vectorization_tasks
            WHERE user_id = %s
        """, (user_id,))
        for row in cursor.fetchall():
            task_status_map[row['file_id']] = {
                'status': row['status'],
                'progress': row['progress']
            }
    finally:
        cursor.close()
        conn.close()

    for user_file in user_files:
        # 确定文件状态
        file_status = "uploaded"
        if user_file.id in task_status_map:
            task = task_status_map[user_file.id]
            if task['status'] == 'pending':
                file_status = 'vectorizing'
            elif task['status'] == 'processing':
                file_status = 'vectorizing'
            elif task['status'] == 'completed':
                file_status = 'vectorized'
            elif task['status'] == 'failed':
                file_status = 'failed'
        elif user_file.chunk_count > 0:
            file_status = 'vectorized'

        files.append(FileInfo(
            id=user_file.id,
            filename=user_file.original_filename,
            upload_time=user_file.upload_time,
            file_size=user_file.file_size,
            file_type=user_file.file_type,
            chunk_count=user_file.chunk_count or 0,
            vectorized=file_status == 'vectorized',
            status=file_status
        ))

    # 从向量数据库获取已向量化文件的 chunk_count（备用）
    vector_metas = get_vector_collection_metadata(user_id)
    if vector_metas:
        file_info_map = {f.filename: f for f in files}

        for metadata in vector_metas:
            filename = metadata.get("collection_name") or metadata.get("filename")
            if filename and filename in file_info_map:
                file_info = file_info_map[filename]
                file_info.chunk_count = metadata.get("chunk_count", 0)
                file_info.vectorized = True
                file_info.status = 'vectorized'

    # 按上传时间倒序排序
    files.sort(key=lambda x: x.upload_time, reverse=True)

    logger.info(f"获取文件列表成功，共 {len(files)} 个文件")

    return FileListResponse(
        files=files,
        total=len(files)
    )


@router.delete("/files/{file_id}", response_model=DeleteFileResponse)
async def delete_file(
    file_id: str,
    user_id: str = Query(..., description="用户ID，用于权限验证")
):
    """
    删除文件

    同时删除 PostgreSQL 中的文件记录和向量数据库中的相关数据
    """
    # 验证文件存在和权限
    user_file = user_file_service.get_file_by_id(file_id)
    if not user_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    if user_file.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除此文件"
        )

    # 删除向量数据（统一 Collection 架构 - 按 file_id 过滤）
    if settings.VECTOR_DB_TYPE == "postgresql":
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        try:
            # 从统一 collection 中删除该文件的向量数据
            cursor.execute("""
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'file_id' = %s
                  AND collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = %s)
            """, (file_id, settings.PGVECTOR_COLLECTION_NAME))

            deleted_count = cursor.rowcount
            logger.info(f"删除了 {deleted_count} 个向量片段")
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    # 删除文件记录
    deleted = user_file_service.delete_file(file_id)

    if deleted:
        return DeleteFileResponse(
            status="success",
            message="文件及向量数据已删除",
            file_id=file_id
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件删除失败"
        )


@router.get("/files/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: str,
    user_id: str = Query(..., description="用户ID，用于权限验证")
):
    """
    获取单个文件信息
    """
    user_file = user_file_service.get_file_by_id(file_id)

    if not user_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    # 验证权限
    if user_file.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此文件"
        )

    # 从向量数据库获取是否已向量化
    vectorized = False
    chunk_count = 0

    vector_metas = get_vector_collection_metadata(user_id)
    if vector_metas:
        for metadata in vector_metas:
            filename = metadata.get("collection_name") or metadata.get("filename")
            if filename == user_file.original_filename:
                vectorized = True
                chunk_count = metadata.get("chunk_count", 0)
                break

    return FileInfo(
        id=user_file.id,
        filename=user_file.original_filename,
        upload_time=user_file.upload_time,
        file_size=user_file.file_size,
        file_type=user_file.file_type,
        chunk_count=chunk_count,
        vectorized=vectorized
    )


@router.get("/files/vectorization/progress/{file_id}")
async def get_vectorization_progress(file_id: str):
    """
    获取文件向量化进度

    Args:
        file_id: 文件ID
    """
    task_status = await vectorization_service.get_task_status(file_id)
    if not task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到向量化任务"
        )
    return task_status


@router.get("/files/knowledge-base")
async def get_knowledge_base_files(
    user_id: str = Query(..., description="用户ID"),
    include_public: bool = Query(True, description="是否包含公开文档")
):
    """
    获取知识库文档列表

    返回用户的私有文档和公开文档
    """
    # 私有文档
    private_files = user_file_service.list_user_files(user_id)

    # 公开文档
    public_files = []
    if include_public:
        public_files = user_file_service.list_public_files()

    return {
        "private": [
            {
                "id": f.id,
                "filename": f.original_filename,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "chunk_count": f.chunk_count if hasattr(f, 'chunk_count') else 0,
                "summary": f.document_summary if hasattr(f, 'document_summary') else None,
                "last_vectorized": f.last_vectorized_at if hasattr(f, 'last_vectorized_at') else None,
                "upload_time": f.upload_time,
                "is_public": f.is_public if hasattr(f, 'is_public') else False
            }
            for f in private_files
        ],
        "public": [
            {
                "id": f.id,
                "filename": f.original_filename,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "chunk_count": f.chunk_count if hasattr(f, 'chunk_count') else 0,
                "summary": f.document_summary if hasattr(f, 'document_summary') else None,
                "last_vectorized": f.last_vectorized_at if hasattr(f, 'last_vectorized_at') else None,
                "upload_time": f.upload_time
            }
            for f in public_files
        ]
    }