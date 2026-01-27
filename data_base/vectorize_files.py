import os
from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredMarkdownLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv, find_dotenv


def vectorize_uploaded_files(file_paths):
    """
    将上传的文件向量化并保存到向量数据库
    """
    # 动态导入文档加载器
    try:
        from langchain_community.document_loaders import Docx2txtLoader
        docx_loader_available = True
    except ImportError:
        docx_loader_available = False

    try:
        from langchain_community.document_loaders import TextLoader
        text_loader_available = True
    except ImportError:
        text_loader_available = False

    try:
        from langchain_community.document_loaders import CSVLoader
        csv_loader_available = True
    except ImportError:
        csv_loader_available = False

    # 加载文件
    texts = [] 
    for file_path in file_paths:
        file_type = file_path.split('.')[-1].lower()
        if file_type == 'pdf':
            loader = PyMuPDFLoader(file_path)
        elif file_type == 'md':
            loader = UnstructuredMarkdownLoader(file_path)
        elif file_type == 'docx' and docx_loader_available:
            loader = Docx2txtLoader(file_path)
        elif file_type == 'txt' and text_loader_available:
            loader = TextLoader(file_path, encoding='utf-8')
        elif file_type == 'csv' and csv_loader_available:
            loader = CSVLoader(file_path)
        else:
            print(f"不支持的文件类型: {file_path}")
            continue
        
        loaded_texts = loader.load()
        texts.extend(loaded_texts)
    
    if not texts:
        print("没有成功加载任何文档")
        return False
    
    # 切分文档
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50)
    split_docs = text_splitter.split_documents(texts)
    
    # 加载环境变量
    load_dotenv(find_dotenv())
    
    # 创建嵌入模型
    embeddings_model = DashScopeEmbeddings(
        model="text-embedding-v4",
    )
    
    # 定义持久化路径
    persist_directory = '/vector_db/chroma'
    
    # 创建或更新向量数据库
    vectordb = Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings_model,
        persist_directory=persist_directory
    )
    vectordb.persist()
    
    print(f"成功向量化 {len(split_docs)} 个文档片段")
    return True