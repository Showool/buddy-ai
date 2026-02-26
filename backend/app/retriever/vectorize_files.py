import os
import traceback
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredMarkdownLoader, Docx2txtLoader, TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

from .embeddings_model import get_embeddings_model


def vectorize_uploaded_files(file_paths):
    """
    将上传的文件向量化并保存到向量数据库
    
    Args:
        file_paths: 文件路径列表
        
    Returns:
        bool: 成功返回True，失败返回False
    """

    # 加载文件
    texts = [] 
    for file_path in file_paths:
        try:
            file_type = file_path.split('.')[-1].lower()
            if file_type == 'pdf':
                loader = PyMuPDFLoader(file_path)
            elif file_type == 'md':
                loader = UnstructuredMarkdownLoader(file_path)
            elif file_type == 'docx':
                loader = Docx2txtLoader(file_path)
            elif file_type == 'txt':
                loader = TextLoader(file_path, encoding='utf-8')
            elif file_type == 'csv':
                loader = CSVLoader(file_path)
            else:
                print(f"不支持的文件类型: {file_path}")
                continue
            
            loaded_texts = loader.load()
            texts.extend(loaded_texts)
            print(f"成功加载文件: {file_path}")
        except Exception as e:
            print(f"加载文件时出错: {file_path}, 错误: {str(e)}")
            print(traceback.format_exc())
            continue
    
    if not texts:
        print("没有成功加载任何文档")
        return False
    
    # 切分文档
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50)
    split_docs = text_splitter.split_documents(texts)
    
    # 创建或更新向量数据库
    try:
        vectordb = Chroma.from_documents(
            documents=split_docs,
            embedding=get_embeddings_model(),
            persist_directory=os.getenv("CHROMA_PERSIST_DIR")
        )
        vectordb.persist()
        print(f"成功向量化 {len(split_docs)} 个文档片段")
        return True
    except Exception as e:
        print(f"创建向量数据库时出错: {str(e)}")
        print(traceback.format_exc())
        return False
