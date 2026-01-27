import os
from dotenv import load_dotenv, find_dotenv
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredMarkdownLoader
from langchain_community.embeddings import DashScopeEmbeddings
import importlib

# 动态导入文档加载器
try:
    from langchain_community.document_loaders import Docx2txtLoader
    docx_loader_available = True
    print("docx2txt加载器可用")
except ImportError:
    docx_loader_available = False
    print("警告: 未安装docx2txt，无法加载.docx文件")

try:
    from langchain_community.document_loaders import TextLoader
    text_loader_available = True
    print("TextLoader可用")
except ImportError:
    text_loader_available = False
    print("警告: 无法导入TextLoader，无法加载.txt文件")

try:
    from langchain_community.document_loaders import CSVLoader
    csv_loader_available = True
    print("CSVLoader可用")
except ImportError:
    csv_loader_available = False
    print("警告: 无法导入CSVLoader，无法加载.csv文件")

# 获取folder_path下所有文件路径，储存在file_paths里
file_paths = []
folder_path = 'knowledge_db/data'
for root, dirs, files in os.walk(folder_path):
    for file in files:
        # 确保文件名使用UTF-8编码
        file_path = os.path.join(root, file)
        file_paths.append(file_path)

print("找到的文件:", file_paths[:3])


# 遍历文件路径并把实例化的loader存放在loaders里
loaders = []

for file_path in file_paths:
    file_type = file_path.split('.')[-1].lower()
    if file_type == 'pdf':
        loaders.append(PyMuPDFLoader(file_path))
    elif file_type == 'md':
        loaders.append(UnstructuredMarkdownLoader(file_path))
    elif file_type == 'docx' and docx_loader_available:
        loaders.append(Docx2txtLoader(file_path))
    elif file_type == 'txt' and text_loader_available:
        loaders.append(TextLoader(file_path, encoding='utf-8'))
    elif file_type == 'csv' and csv_loader_available:
        loaders.append(CSVLoader(file_path))
    else:
        print(f"跳过不支持的文件类型: {file_path}")

# 加载文件并存储到text
texts = []

for loader in loaders:
    try:
        loaded_texts = loader.load()
        texts.extend(loaded_texts)
        print(f"成功加载文件: {getattr(loader, 'file_path', 'Unknown')}")
    except Exception as e:
        print(f"加载文件时出错: {getattr(loader, 'file_path', 'Unknown')}, 错误: {str(e)}")

from langchain_text_splitters import RecursiveCharacterTextSplitter

# 切分文档
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500, chunk_overlap=50)

print(f"原始文档数：{len(texts)}")

split_docs = text_splitter.split_documents(texts)

print(f"切分后的文档数：{len(split_docs)}")


# 定义 Embeddings
load_dotenv(find_dotenv())  # 加载环境变量
embeddings_model = DashScopeEmbeddings(
    model="text-embedding-v4",
)

# 定义持久化路径
persist_directory = '/vector_db/chroma'

from langchain_community.vectorstores import Chroma

vectordb = Chroma.from_documents(
    documents=split_docs,
    embedding=embeddings_model,
    persist_directory=persist_directory  # 允许我们将persist_directory目录保存到磁盘上
)
vectordb.persist()

question = '阿里云百炼Ace Ultra是什么'

sim_docs = vectordb.similarity_search(question, k=3)
print(f"similarity_search检索到的内容数：{len(sim_docs)}")
for i, sim_doc in enumerate(sim_docs):
    print(f"similarity_search检索到的第{i}个内容: \n{sim_doc.page_content[:200]}", end="\n--------------\n")


mmr_docs = vectordb.max_marginal_relevance_search(question, k=3)
print(f"max_marginal_relevance_search检索到的内容数：{len(sim_docs)}")
for i, sim_doc in enumerate(mmr_docs):
    print(f"MMR 检索到的第{i}个内容: \n{sim_doc.page_content[:200]}", end="\n--------------\n")

print("向量数据库创建完成！")