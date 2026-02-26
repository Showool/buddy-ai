"""
文件上传 API
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.config import settings
from app.models.file import FileUploadResponse, VectorizeResponse, VectorizeRequest


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
        success = vectorize_uploaded_files(file_paths)

        if success:
            # 计算chunk数量（简化计算）
            chunk_count = 0
            for file_path in file_paths:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    chunk_count += len(content) // 450 + 1

            return VectorizeResponse(
                status="success",
                chunk_count=chunk_count,
                message="向量化成功"
            )
        else:
            return VectorizeResponse(
                status="failed",
                chunk_count=0,
                message="向量化失败"
            )
    except Exception as e:
        return VectorizeResponse(
            status="failed",
            chunk_count=0,
            message=f"向量化失败: {str(e)}"
        )


@router.get("/files")
async def list_files():
    """列出已上传的文件"""
    files = []
    upload_dir = Path(settings.UPLOAD_DIR)

    if upload_dir.exists():
        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                files.append({
                    "id": file_path.stem,
                    "filename": file_path.name,
                    "size": file_path.stat().st_size
                })

    return {"files": files}


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """删除文件"""
    upload_dir = Path(settings.UPLOAD_DIR)

    # 查找文件
    for file_path in upload_dir.glob(f"{file_id}.*"):
        try:
            file_path.unlink()
            return {"status": "success", "message": "文件已删除"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件删除失败: {str(e)}"
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="文件不存在"
    )