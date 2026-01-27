import os

from langchain_chroma import Chroma

from embedding.get_embeddings_model import get_embeddings_model


def get_vector_store():

    return Chroma(
        embedding_function=get_embeddings_model(),
        persist_directory=os.getenv("CHROMA_PERSIST_DIR"),
    )