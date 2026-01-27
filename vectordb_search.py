import os

from embedding.get_embeddings_model import get_embeddings_model


from langchain_chroma import Chroma

vectordb = Chroma(
    embedding_function=get_embeddings_model(),
    persist_directory=os.getenv("CHROMA_PERSIST_DIR")
)

question = '介绍下阿里云百炼X1'

sim_docs = vectordb.similarity_search(question, k=3)
print(f"similarity_search检索到的内容数：{len(sim_docs)}")
for i, sim_doc in enumerate(sim_docs):
    print(f"similarity_search检索到的第{i}个内容: \n{sim_doc.page_content[:200]}", end="\n--------------\n")

