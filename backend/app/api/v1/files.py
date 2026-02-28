"""
文件上传 API - 增强版
"""

import logging
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query

from app.config import settings
from app.models.file import (
    FileUploadResponse, VectorizeResponse, VectorizeRequest,
    FileInfo, FileListResponse, DeleteFileResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_file(filename: str, size: int):
    """验证文件"""
    # 检查大小
    if size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE / 1024 / 1024}MB)"
        )

    # 检查类型
    ext = get_file_extension(filename)
    if ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"不支持的文件类型。支持的类型: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )


def get_vector_collection():
    """获取向量数据库集合（Chroma 或 PGVector）"""
    try:
        from app.config import settings

        if settings.VECTOR_DB_TYPE == "postgresql":
            from app.retriever.pgvector_store import get_pgvector_store
            return get_pgvector_store()
        else:
            from langchain_chroma import Chroma
            from app.retriever.embeddings_model import get_embeddings_model

            return Chroma(
                persist_directory=settings.CHROMA_PERSIST_DIR,
                embedding_function=get_embeddings_model(),
                collection_name=settings.CHROMA_COLLECTION_NAME
            )
    except Exception as e:
        logger.error(f"获取向量数据库集合失败: {e}")
        return None


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文件"""
    # 验证文件
    validate_file(file.filename or "", file.size)

    # 生成唯一ID
    file_id = str(uuid.uuid4())

    # 保存文件
    file_ext = get_file_extension(file.filename or "")
    save_filename = f"{file_id}.{file_ext}"
    save_path = Path(settings.UPLOAD_DIR) / save_filename

    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info(f"文件上传成功: {file.filename} (ID: {file_id})")

        return FileUploadResponse(
            id=file_id,
            filename=file.filename or "",
            size=file.size,
            status="uploaded",
            vectorized=False
        )
    except Exception as e:
        # 保存失败，删除文件
        if save_path.exists():
            save_path.unlink()
        logger.error(f"文件保存失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}"
        )


@router.post("/files/vectorize", response_model=VectorizeResponse)
async def vectorize_files(request: VectorizeRequest):
    """向量化文件"""
    from app.retriever.vectorize_files import vectorize_uploaded_files

    # 获取文件路径
    file_paths = []
    for file_id in request.file_ids:
        # 查找文件
        upload_dir = Path(settings.UPLOAD_DIR)
        for file_path in upload_dir.glob(f"{file_id}.*"):
            file_paths.append(str(file_path))
            break

    if not file_paths:
        return VectorizeResponse(
            status="failed",
            chunk_count=0,
            message="没有找到文件"
        )

    try:
        # 调用向量化函数
        result = vectorize_uploaded_files(file_paths)

        if result.get("success"):
            chunk_count = result.get("chunk_count", 0)
            file_metadata = result.get("file_metadata", {})
            logger.info(f"文件向量化成功，共 {chunk_count} 个chunk，涉及 {len(file_metadata)} 个文件")
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
    user_id: Optional[str] = Query(None, description="用户ID，用于权限验证")
):
    """
    列出已上传的文件

    从向量数据库和上传目录中获取文件信息
    """
    files = []
    upload_dir = Path(settings.UPLOAD_DIR)

    # 首先从上传目录获取文件
    uploaded_files = {}
    if upload_dir.exists():
        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                file_id = file_path.stem
                file_ext = file_path.suffix.lstrip('.')
                uploaded_files[file_id] = {
                    "file_id": file_id,
                    "filename": file_path.name,
                    "file_type": file_ext,
                    "file_size": file_path.stat().st_size,
                    "upload_time": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                    "vectorized": False,
                    "chunk_count": 0
                }

    # 从ChromaDB获取已向量化文件的信息
    vector_collection = get_vector_collection()
    if vector_collection:
        try:
            # 获取所有文档的元数据
            all_docs = vector_collection.get(include=["metadatas"])
            if all_docs and all_docs.get("metadatas"):
                # 收集已向量化文件的信息
                vectorized_files = {}
                for metadata in all_docs["metadatas"]:
                    file_id = metadata.get("file_id")
                    if file_id and file_id not in vectorized_files:
                        # 统计该文件的chunk数量
                        chunk_count = sum(
                            1 for m in all_docs["metadatas"]
                            if m.get("file_id") == file_id
                        )
                        vectorized_files[file_id] = {
                            "file_id": file_id,
                            "filename": metadata.get("filename", f"{file_id}.unknown"),
                            "file_type": metadata.get("file_type", "unknown"),
                            "file_size": metadata.get("file_size", 0),
                            "upload_time": metadata.get("upload_time", ""),
                            "vectorized": True,
                            "chunk_count": chunk_count
                        }

                # 合并文件信息（已向量化文件的优先）
                for file_id, info in vectorized_files.items():
                    uploaded_files[file_id] = info

        except Exception as e:
            logger.error(f"从ChromaDB获取文件信息失败: {e}")

    # 转换为FileInfo对象并按上传时间排序
    for file_info in uploaded_files.values():
        try:
            files.append(FileInfo(**file_info))
        except Exception as e:
            logger.warning(f"文件信息格式错误: {e}, 跳过文件 {file_info.get('file_id')}")

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
    user_id: Optional[str] = Query(None, description="用户ID，用于权限验证")
):
    """
    删除文件

    同时删除上传目录中的文件和向量数据库中的相关数据
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    deleted_from_disk = False
    deleted_from_db = False

    # 1. 从上传目录删除文件
    for file_path in upload_dir.glob(f"{file_id}.*"):
        try:
            file_path.unlink()
            deleted_from_disk = True
            logger.info(f"从磁盘删除文件: {file_path}")
        except Exception as e:
            logger.error(f"从磁盘删除文件失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件删除失败: {str(e)}"
            )

    # 2. 从向量数据库删除相关向量数据
    vector_collection = get_vector_collection()
    if vector_collection:
        try:
            # 获取所有文档
            all_docs = vector_collection.get(include=["metadatas"])
            if all_docs and all_docs.get("metadatas"):
                # 找到该文件的所有文档ID
                doc_ids_to_delete = []
                for idx, metadata in enumerate(all_docs["metadatas"]):
                    if metadata.get("file_id") == file_id:
                        if all_docs.get("ids") and idx < len(all_docs["ids"]):
                            doc_ids_to_delete.append(all_docs["ids"][idx])

                # 删除这些文档
                if doc_ids_to_delete:
                    vector_collection.delete(ids=doc_ids_to_delete)
                    deleted_from_db = True
                    logger.info(f"从向量数据库删除了 {len(doc_ids_to_delete)} 个文档片段")

        except Exception as e:
            logger.error(f"从向量数据库删除文件失败: {e}")
            # 数据库删除失败不影响整体流程，继续

    # 检查是否有文件被删除
    if not deleted_from_disk and not deleted_from_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    return DeleteFileResponse(
        status="success",
        message="文件已删除",
        file_id=file_id
    )


@router.get("/files/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: str,
    user_id: Optional[str] = Query(None, description="用户ID，用于权限验证")
):
    """
    获取单个文件信息

    从向量数据库中获取文件的详细信息
    """
    upload_dir = Path(settings.UPLOAD_DIR)

    # 首先从上传目录获取基本信息
    file_info = None
    for file_path in upload_dir.glob(f"{file_id}.*"):
        if file_path.is_file():
            file_info = {
                "file_id": file_id,
                "filename": file_path.name,
                "file_type": file_path.suffix.lstrip('.'),
                "file_size": file_path.stat().st_size,
                "upload_time": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                "vectorized": False,
                "chunk_count": 0
            }
            break

    # 从向量数据库获取更详细的信息
    vector_collection = get_vector_collection()
    if vector_collection:
        try:
            all_docs = vector_collection.get(include=["metadatas"])
            if all_docs and all_docs.get("metadatas"):
                for metadata in all_docs["metadatas"]:
                    if metadata.get("file_id") == file_id:
                        # 统计chunk数量
                        chunk_count = sum(
                            1 for m in all_docs["metadatas"]
                            if m.get("file_id") == file_id
                        )
                        file_info = {
                            "file_id": file_id,
                            "filename": metadata.get("filename", f"{file_id}.unknown"),
                            "file_type": metadata.get("file_type", "unknown"),
                            "file_size": metadata.get("file_size", 0),
                            "upload_time": metadata.get("upload_time", ""),
                            "vectorized": True,
                            "chunk_count": chunk_count
                        }
                        break
        except Exception as e:
            logger.error(f"从向量数据库获取文件信息失败: {e}")

    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    return FileInfo(**file_info)