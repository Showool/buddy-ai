import os

from langchain_chroma import Chroma

from .embeddings_model import get_embeddings_model


def get_retriever():
    # 获取 Embeddings
    embeddings_model = get_embeddings_model()
    # 加载数据库
    vectordb = Chroma(
        persist_directory=os.getenv("CHROMA_PERSIST_DIR"),
        embedding_function=embeddings_model
    )
    return vectordb.as_retriever()
