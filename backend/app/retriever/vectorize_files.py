import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredMarkdownLoader, Docx2txtLoader, TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from .embeddings_model import get_embeddings_model


def vectorize_uploaded_files(file_paths: List[str]) -> Dict[str, any]:
    """
    将上传的文件向量化并保存到向量数据库

    Args:
        file_paths: 文件路径列表

    Returns:
        dict: 包含success、chunk_count和file_metadata的字典
    """
    # 加载文件
    texts = []
    file_metadata = {}

    for file_path in file_paths:
        try:
            path = Path(file_path)
            file_id = path.stem  # 获取文件ID（不带扩展名的文件名）
            filename = path.name
            file_type = path.suffix.lstrip('.').lower()
            file_size = path.stat().st_size
            upload_time = datetime.utcnow().isoformat()

            # 获取加载器
            if file_type == 'pdf':
                loader = PyMuPDFLoader(file_path)
            elif file_type == 'md':
                loader = UnstructuredMarkdownLoader(file_path)
            elif file_type == 'docx':
                loader = Docx2txtLoader(file_path)
            elif file_type == 'txt':
                loader = TextLoader(file_path, encoding='utf-8')
            elif file_type == 'csv':
                loader = CSVLoader(file_path)
            else:
                print(f"不支持的文件类型: {file_path}")
                continue

            loaded_texts = loader.load()

            # 为每个文档添加文件元数据
            for doc in loaded_texts:
                doc.metadata.update({
                    "file_id": file_id,
                    "filename": filename,
                    "file_type": file_type,
                    "file_size": file_size,
                    "upload_time": upload_time,
                    "source": filename
                })

            texts.extend(loaded_texts)

            # 保存文件元数据
            file_metadata[file_id] = {
                "file_id": file_id,
                "filename": filename,
                "file_type": file_type,
                "file_size": file_size,
                "upload_time": upload_time,
                "chunk_count": 0  # 稍后更新
            }

            print(f"成功加载文件: {file_path}")
        except Exception as e:
            print(f"加载文件时出错: {file_path}, 错误: {str(e)}")
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
        if os.getenv("VECTOR_DB_TYPE", "chroma") == "postgresql":
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
