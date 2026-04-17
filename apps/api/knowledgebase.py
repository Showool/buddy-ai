import hashlib
import io
import logging
from pathlib import Path
from urllib.parse import quote

import docx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.agent.rag import milvus_vector
from apps.agent.rag.document_split import split_document
from apps.config import settings
from apps.database.async_engine import get_session
from apps.database.models import KnowledgeBaseFile
from apps.exceptions import NotFoundError
from apps.models.request_params import DeleteFileParams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledgebase", tags=["knowledgebase"])

ALLOWED_FILE_TYPE = {"txt", "docx", "md"}
MAX_UPLOAD_SIZE = settings.MAX_UPLOAD_SIZE


async def validate_file(file: UploadFile = File(...)) -> UploadFile:
    """校验上传文件的类型和大小。"""
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in ALLOWED_FILE_TYPE:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，仅支持 {', '.join(ALLOWED_FILE_TYPE)}")
    if file.size is not None and file.size > MAX_UPLOAD_SIZE:
        max_mb = MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"文件大小超过限制，最大允许 {max_mb:.0f}MB")
    return file


@router.post("/upload_file")
async def upload_file(
    file: UploadFile = Depends(validate_file),
    user_id: str = Form(...),
    knowledge_id: int = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """上传单个文件，仅支持 txt、docx、md 格式，返回文件内容。"""
    file_type = Path(file.filename or "").suffix.lstrip(".").lower()
    raw = await file.read()

    # 二次校验文件大小（file.size 可能为 None）
    if len(raw) > MAX_UPLOAD_SIZE:
        max_mb = MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"文件大小超过限制，最大允许 {max_mb:.0f}MB")

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
        existing.file_type = file_type
        existing.file_content = raw
        existing.file_md5 = file_md5
        existing.update_id = user_id
        await session.commit()
        file_id = existing.id
        # 删除向量数据
        milvus_vector.delete_documents(file_id, user_id, knowledge_id)
    else:
        # 新文件，直接保存
        knowledge_base_file = KnowledgeBaseFile(
            knowledge_id=knowledge_id,
            file_name=file.filename,
            file_size=len(raw),
            file_type=file_type,
            file_content=raw,
            file_md5=file_md5,
            creator_id=user_id,
            update_id=user_id,
        )
        session.add(knowledge_base_file)
        await session.commit()
        await session.refresh(knowledge_base_file)  # 确保从数据库刷新自增ID
        file_id = knowledge_base_file.id

    if file_type in ("txt", "md"):
        content = raw.decode("utf-8")
    else:
        doc = docx.Document(io.BytesIO(raw))
        content = "\n".join(p.text for p in doc.paragraphs)
    # 切分文档，保存向量数据
    document_list = split_document(content, file_type, 200)
    milvus_vector.save_documents(document_list, user_id, knowledge_id, file_id)
    return {"filename": file.filename, "content": document_list}


@router.get("/get_files")
async def get_files(
    user_id: str = Query(..., description="用户ID"),
    knowledge_id: int = Query(..., description="知识库ID"),
    session: AsyncSession = Depends(get_session),
):
    """获取知识库文件列表。"""
    result = await session.execute(
        select(
            KnowledgeBaseFile.id,
            KnowledgeBaseFile.knowledge_id,
            KnowledgeBaseFile.file_name,
            KnowledgeBaseFile.file_type,
            KnowledgeBaseFile.file_size,
            KnowledgeBaseFile.file_path,
            KnowledgeBaseFile.file_md5,
            KnowledgeBaseFile.creator_id,
            KnowledgeBaseFile.create_time,
            KnowledgeBaseFile.update_id,
            KnowledgeBaseFile.update_time,
        ).where(
            KnowledgeBaseFile.knowledge_id == knowledge_id,
            KnowledgeBaseFile.creator_id == user_id,
        )
    )
    rows = result.all()
    return [row._asdict() for row in rows]


@router.post("/delete_file")
async def delete_file(params: DeleteFileParams, session: AsyncSession = Depends(get_session)):
    """删除单个文件。"""
    result = await session.execute(
        select(KnowledgeBaseFile).where(
            KnowledgeBaseFile.id == params.file_id,
            KnowledgeBaseFile.knowledge_id == params.knowledge_id,
            KnowledgeBaseFile.creator_id == params.user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("文件", f"id={params.file_id}")
    await session.delete(doc)
    milvus_vector.delete_documents(params.file_id, params.user_id, params.knowledge_id)
    return {"message": "删除成功", "file_id": params.file_id}


# MIME 映射
CONTENT_TYPE_MAP = {
    "txt": "text/plain",
    "md": "text/markdown",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/download_file")
async def download_file(
    file_id: int = Query(..., description="文件ID"),
    session: AsyncSession = Depends(get_session),
):
    """通过文件ID下载文件。"""
    result = await session.execute(select(KnowledgeBaseFile).where(KnowledgeBaseFile.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    content_type = CONTENT_TYPE_MAP.get(file.file_type, "application/octet-stream")
    encoded_filename = quote(file.file_name)
    return StreamingResponse(
        io.BytesIO(file.file_content),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
