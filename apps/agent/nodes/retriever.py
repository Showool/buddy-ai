from langchain_core.runnables import RunnableConfig
from apps.agent.state import GraphState
from apps.agent.rag import milvusVector

def query_transform(state: GraphState) -> dict:
  return {
    "enhanced_input": [state["original_input"]]
  }


def hybrid_search(state: GraphState, config: RunnableConfig) -> dict:
  """ 混合搜索 """
  original_input = state["original_input"]
  user_id = config["configurable"].get("user_id")
  data = milvusVector.hybrid_search(original_input, user_id)
  return {
    "rag_docs": data
  }

def text_match(state: GraphState, config: RunnableConfig) -> dict:
  """ 文本匹配 """
  original_input = state["original_input"]
  user_id = config["configurable"].get("user_id")
  # 获取关键词
  keyword = ""
  data = milvusVector.text_match(original_input, keyword, user_id)
  return {
    "rag_docs": data
  }