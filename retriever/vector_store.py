from langchain_chroma import Chroma

from retriever.embeddings_model import get_embeddings_model


def get_vector_store():

    return Chroma(
        embedding_function=get_embeddings_model(),
        persist_directory='../data_base/vector_db/chroma',
    )