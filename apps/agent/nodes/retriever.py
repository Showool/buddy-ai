import jieba
from langchain.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState, QueryTransformSchema
from apps.agent.rag import milvusVector

STOP_WORDS = {"的", "是", "在", "了", "什么", "如何", "怎么", "吗", "呢", "有", "和", "与", "对", "把", "被", "从", "到", "为", "这", "那", "就", "也", "都", "而", "及", "着", "或", "一个", "没有", "不是", "可以", "我", "你", "他", "她", "它", "们", "请", "能", "会", "要", "让", "给", "用", "很", "最", "更", "还", "但", "却", "只", "已", "已经"}


def extract_keywords(text: str) -> str:
    """基于 jieba 分词 + 停用词过滤提取关键词"""
    words = [w for w in jieba.cut(text) if len(w) > 1 and w not in STOP_WORDS]
    return " ".join(words)

# 退步提示（Step-Back Prompting）
# 当面对一个细节繁多或过于具体的问题时，模型直接作答（即便是使用思维链）也容易出错。退步提示通过引导模型“退后一步”来解决这个问题。
# 假设性文档嵌入 (HyDE)
# 其核心是解决一个普遍存在于检索任务中的难题：用户的查询（Query）通常简短、关键词有限，而数据库中存储的文档则内容详实、上下文丰富，两者在语义向量空间中可能存在“鸿沟”，导致直接用查询向量进行搜索效果不佳。
QUERY_TRANSFORM_PROMPT = """
  你需要根据用户输入的问题，按照以下策略进行转换，并返回指定格式的JSON数据：
  1. 转换策略选择规则：
    - 若用户输入的问题细节繁多或过于具体，采用「退步提示（Step_Back_Prompting）」：将问题“退后一步”，生成一个更概括性的新问题，字数控制在100字以内。
    - 若用户输入的问题简短、关键词有限，采用「假设性文档嵌入 (HyDE)」：生成一个能完美回答该查询的精简答案，字数控制在100字以内。
  2. 输出格式要求：必须返回JSON数据，包含两个字段：
    - "type"：值为"Step_Back_Prompting"或"HyDE"，对应所选转换策略；
    - "result"：值为转换后的内容（新问题或精简答案）。
  示例输出：
  {
      "type":"Step_Back_Prompting",
      "result":"概括性的新问题内容"
  }
"""

def query_transform(state: GraphState) -> dict:
  """ 查询转换 """
  prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=QUERY_TRANSFORM_PROMPT),
    HumanMessagePromptTemplate.from_template("{input}")
  ])
  llm_with_schema = get_llm().with_structured_output(QueryTransformSchema, method="json_mode")
  chain = prompt | llm_with_schema
  response: QueryTransformSchema = chain.invoke({"input": state["original_input"]})
  return {
    "enhanced_input": response.result,
    "query_transform_type": response.type
  }


def hybrid_search(state: GraphState, config: RunnableConfig) -> dict:
  """ 混合搜索 """
  original_input = state["original_input"]
  user_id = config["configurable"].get("user_id")
  data = milvusVector.hybrid_search(original_input, user_id)
  if state["query_transform_type"] == "HyDE":
    hyde_data = milvusVector.vector_search(state["enhanced_input"], user_id)
    data.extend(hyde_data)
  return {
    "rag_docs": data
  }

def text_match(state: GraphState, config: RunnableConfig) -> dict:
  """ 文本匹配 """
  original_input = state["original_input"]
  user_id = config["configurable"].get("user_id")
  keyword = extract_keywords(original_input)
  if not keyword:
    return {"rag_docs": []}
  data = milvusVector.text_match(original_input, keyword, user_id)
  return {
    "rag_docs": data
  }