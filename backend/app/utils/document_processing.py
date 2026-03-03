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