import os

from langchain_community.tools import TavilySearchResults
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBranch, RunnablePassthrough, RunnableLambda

from llm.get_llm import get_llm
from rag.get_retriever import get_retriever


def get_qa_history_chain():
    retriever = get_retriever()
    # 创建 LLM 实例
    llm = get_llm("qwen-plus")
    condense_question_system_template = (
        "请根据聊天记录总结用户最近的问题，"
        "如果没有多余的聊天记录则返回用户的问题。"
    )
    condense_question_prompt = ChatPromptTemplate([
        ("system", condense_question_system_template),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ])

    # 创建文档检索分支
    retrieve_docs = RunnableBranch(
        (lambda x: not x.get("chat_history", False), (lambda x: x["input"]) | retriever,),
        condense_question_prompt | llm | StrOutputParser() | retriever,
    )
    
    # 创建搜索工具
    os.environ['TAVILY_API_KEY'] = os.getenv("TAVILY_API_KEY")
    search = TavilySearchResults(max_results=3)
    
    # 定义创建组合检索的函数
    def create_combined_retrieval(inputs):
        input_query = inputs["input"]
        
        # 执行向量检索
        retrieved_docs_result = retrieve_docs.invoke(inputs)
        
        # 如果 retrieve_docs 返回的是文档列表
        if isinstance(retrieved_docs_result, list):
            docs_context = "\n\n".join([doc.page_content for doc in retrieved_docs_result])
        else:
            # 否则直接转换为字符串
            docs_context = str(retrieved_docs_result)
        
        # 执行网络搜索
        search_query = input_query  # 可以根据需要调整搜索查询
        search_results = search.invoke({"query": search_query})
        
        # 处理搜索结果
        if isinstance(search_results, list):
            search_context = "\n\n".join([result.get('content', result.get('answer', str(result))) for result in search_results])
        else:
            search_context = str(search_results)
        
        return {
            "context_vector_db": docs_context,
            "context_web_search": search_context,
            "combined_context": f"来自知识库的信息:\n{docs_context}\n\n来自网络搜索的信息:\n{search_context}"
        }
    
    # 定义处理输入的函数
    def process_inputs_with_context(inputs):
        # 获取合并的上下文数据
        context_data = create_combined_retrieval(inputs)
        # 将上下文数据添加到输入中
        result = inputs.copy()
        result.update(context_data)
        return result
    
    # 将处理函数封装为 Runnable
    processing_runnable = RunnableLambda(process_inputs_with_context)
        
    # 为新上下文结构创建提示词模板
    system_prompt_formatted = (
        "你是一个问答任务的助手。 "
        "请结合来自知识库和网络搜索的信息回答问题。 "
        "来自知识库的信息: {context_vector_db} "
        "来自网络搜索的信息: {context_web_search} "
        "如果你不知道答案就说不知道。 "
        "请使用简洁的话语回答用户。"
    )
        
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_formatted),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ])
        
    qa_chain = (
        processing_runnable
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    
    qa_history_chain = RunnablePassthrough().assign(answer=qa_chain)
    
    return qa_history_chain


