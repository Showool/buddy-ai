"""
文档分割模块

根据文件类型选择合适的分割策略：
- txt: RecursiveCharacterTextSplitter
- md:  MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter
- docx: RecursiveCharacterTextSplitter
"""

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# 默认分割参数
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 0


def split_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Document]:
    """通用文本分割，适用于 txt / docx。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )
    return splitter.create_documents([text])



def split_markdown(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Document]:
    """Markdown 分割：先按标题拆分保留结构，再对过长片段二次分割。"""
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_docs: List[Document] = md_splitter.split_text(text)

    # 二次分割：对超出 chunk_size 的片段再用 RecursiveCharacterTextSplitter 切分
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return char_splitter.split_documents(md_docs)



def split_document(text: str, file_ext: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Document]:
    """
    根据文件扩展名选择分割策略。

    Args:
        text: 文档文本内容
        file_ext: 文件扩展名，如 ".txt", ".md", ".docx"
        chunk_size: 分块大小
        chunk_overlap: 分块重叠大小

    Returns:
        分割后的文本列表
    """
    ext = file_ext.lower()
    if ext == ".md":
        return split_markdown(text, chunk_size, chunk_overlap)
    return split_text(text, chunk_size, chunk_overlap)
