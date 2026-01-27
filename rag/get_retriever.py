from langchain_chroma import Chroma

from embedding.get_embeddings_model import get_embeddings_model


def get_retriever():
    # 获取 Embeddings
    embeddings_model = get_embeddings_model()
    # 向量数据库持久化路径
    persist_directory = 'data_base/vector_db/chroma'
    # 加载数据库
    vectordb = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings_model
    )
    return vectordb.as_retriever()
