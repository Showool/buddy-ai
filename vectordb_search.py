# vectordb = Chroma(
#     embedding_function=get_embeddings_model(),
#     persist_directory=os.getenv("CHROMA_PERSIST_DIR")
# )
#
# question = '介绍下Buddy-AI手机'
#
# sim_docs = vectordb.similarity_search(question, k=3)
# print(f"similarity_search检索到的内容数：{len(sim_docs)}")
# for i, sim_doc in enumerate(sim_docs):
#     print(f"similarity_search检索到的第{i}个内容: \n{sim_doc.page_content[:200]}", end="\n--------------\n")



from llm.llm_factory import get_llm
from retriever.get_db import get_sqlite_db

# 1. 连接本地SQLite文件（替换为你的.db路径）
db = get_sqlite_db()

# 3. 获取表schema
print(db.get_table_info(["user"]))

# 4. 执行查询
result = db.run("SELECT * FROM user LIMIT 5")
print(f'result: {result}')

from langchain_community.agent_toolkits import SQLDatabaseToolkit

toolkit = SQLDatabaseToolkit(db=db, llm=get_llm())

tools = toolkit.get_tools()

for tool in tools:
    print(f"{tool.name}: {tool.description}\n")
