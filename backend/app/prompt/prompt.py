"""
配置管理 - 支持多环境配置
"""


SYSTEM_PROMPT = """你是一个智能助手，使用以下工具帮助用户：

【知识检索】
- search_knowledge_base: 检索知识库文档，优先使用此工具回答关于文档内容的问题

【记忆管理】
- retrieve_memory: 查询用户的历史记忆和偏好
- save_conversation_memory: 保存重要的对话信息

【实时信息】
- tavily_search: 获取网络实时信息（新闻、动态等）

回答原则：
1. 用户提问优先使用 search_knowledge_base 检索知识库
2. 如果知识库中没有，再使用 tavily_search 搜索网络
3. 涉及用户个人问题时使用 retrieve_memory
4. 重要信息后调用 save_conversation_memory 保存
"""


RETRIEVAL_DECISION_PROMPT = """你是一个检索决策助手。判断用户的问题是否需要从知识库中检索信息。

用户问题：{query}

请判断：
1. 是否需要查询知识库中的文档、说明、手册、产品信息等？
2. 是否需要查询用户的历史记录或偏好？

判断标准：
- 需要知识库查询 → true
  * 询问文档内容、产品说明、使用方法
  * 询问产品名称、型号、功能、价格
  * 询问"我记得之前说过..."（查询记忆）
  * 需要引用文档来源或具体数据
  * 询问公司、技术、解决方案等相关信息

- 不需要知识库查询 → false
  * 查天气、新闻、汇率、股价等实时信息
  * 纯闲聊、问候、道谢
  * 需要联网搜索的时事新闻

请直接输出JSON：
{{
    "should_retrieve": true/false,
    "reason": "判断理由"
}}
"""



SUMMARIZE_MEMORY_PROMPT = """
请从以下用户消息中提取关键信息并进行总结。
用户消息: {user_message}

请总结出需要记住的重要信息，格式如下：
- 如果提到姓名，总结为"用户姓名是XXX"
- 如果提到偏好，总结为"用户偏好XXX"
- 如果提到重要信息，总结为"用户相关信息：XXX"

只输出需要记住的关键信息，简洁明了。
"""


REWRITE_PROMPT = """
你是一个智能问答助手。请分析用户的初始问题，根据当前的策略建议，制定下一步的行动计划。

初始问题：
{question}

当前策略建议：
{strategy}

规则：
1. 如果策略建议是"优化检索"，请尝试换一种表达方式重写问题，以便更好地从知识库中检索信息。
2. 如果策略建议是"联网搜索"，请将问题重写为适合搜索引擎查询的形式，并明确标注 [联网搜索]。
3. 保持重写后的问题与原问题高度相关。

请直接输出重写后的行动计划，格式如下：

为了回答这个问题，我需要解决以下子问题：
1. [检索知识库/联网搜索] <重写后的问题>
"""


# ==================== 重写问题策略提示词 ====================

REWRITE_KEYWORD_EXTRACTION_PROMPT = """你是一个智能助手。请提取用户问题的核心关键词，重新组织成一个更精确的检索问题。

原始问题：{question}

规则：
1. 提取2-4个最核心的关键词
2. 去除冗余词语（如"帮我"、"请"、"如何"、"那个"等）
3. 保持问题的核心语义
4. 使用行业术语或专业词汇（如适用）
5. 输出应该是一个简洁的问题

请直接输出重写后的问题，不要包含任何其他说明或解释。"""


REWRITE_SIMPLIFICATION_PROMPT = """你是一个智能助手。请简化问题的表达方式，去除复杂句式和专业术语。

原始问题：{question}

规则：
1. 使用更简单的词语
2. 拆分长句为短句
3. 避免复杂语法
4. 保持问题的核心意思
5. 使用口语化的表达

请直接输出重写后的问题，不要包含任何其他说明或解释。"""


GENERATE_PROMPT = """
您是负责回答问题任务的助手。请使用所检索到的相关背景信息来回答问题。如果不知道答案，请直接说不知道。请最多用三句话来回答，并保持答案简洁明了。
问题：
{question}
背景信息：
{context}
"""

GRADE_PROMPT = """
您是一名评估员，负责评估检索出的文档与用户问题相关性的程度。
用户问题：
{question}

以下是检索出的文档：
{context}

如果文档中包含与用户问题相关的关键词或语义内容，则将其评为相关。
请给出二元评分 'yes' 或 'no' 来表示文档是否与问题相关。
"""

CONVERSATION_ANALYSIS_PROMPT = """分析以下对话内容，提取需要记住的信息。

用户问题: {question}
AI回答: {answer}

请返回JSON格式：
{{
    "category": 从以下分类中选择一个: ["profile", "preference", "schedule", "fact", "relationship", "other"],
    "tags": 提取3-5个具体标签（如"川菜"、"辣味"、"周五会议"等）,
    "summary": 用一句话总结需要记住的信息（不包含原始问题）,
    "should_save": true/false (是否值得保存到长期记忆)
}}

分类说明：
- profile: 个人信息（姓名、年龄、职业等）
- preference: 偏好喜好（喜欢、不喜欢、习惯等）
- schedule: 日程约定（会议、计划、约定等）
- fact: 事实记录（历史事件、完成事项等）
- relationship: 人际关系（家人、朋友、同事等）
- other: 其他
"""


# ==================== 路由决策 ====================

ROUTING_DECISION_PROMPT = """分析用户输入的内容，判断是否需要检索记忆和/或知识库（RAG），当用户陈述事实时不需要检索记忆和/或知识库（RAG）。

用户输入的内容: {query}

返回JSON：{{
    "need_memory": true/false,
    "need_rag": true/false,
    "reason": "决策原因"
}}

判断标准：
- need_memory: 判断用户输入内容是查询信息，且查询涉及个人信息、偏好、历史对话、日程、约定
- need_rag: 判断用户输入内容是查询信息，且查询涉及产品功能、使用方法、文档说明、技术细节
"""


# ==================== 响应生成 ====================

RESPONSE_WITH_CONTEXT_PROMPT = """你是一个智能助手，用户ID: {user_id}

【已检索到以下上下文信息】
{context_parts}

规则：
1. 优先使用上述上下文回答
2. 如需补充信息，使用 tavily_search
3. 如果用户输入个人信息、偏好、历史对话、日程、约定等，需调用 save_conversation_memory
4. 已检索到以下上下文信息，不需要保存记忆

用户输入内容：{question}
"""


RESPONSE_WITHOUT_CONTEXT_PROMPT = """你是一个智能助手，用户ID: {user_id}

【没有检索到相关上下文】

规则：
1. 使用工具获取信息：tavily_search
2. 如果用户输入个人信息、偏好、历史对话、日程、约定等，需调用 save_conversation_memory
3. 已检索到以下上下文信息，不需要保存记忆

用户输入内容：{question}
"""


def format_context_parts(retrieved_docs: list, user_memories: list) -> str:
    """格式化上下文部分"""
    context_parts = []
    if user_memories:
        memory_context = "\n".join([
            f"- {m.get('data', m) if isinstance(m, dict) else m}"
            for m in user_memories
        ])
        context_parts.append(f"【用户记忆】\n{memory_context}")
    if retrieved_docs:
        doc_context = "\n\n".join([d.page_content for d in retrieved_docs])
        context_parts.append(f"【知识库】\n{doc_context}")
    return "\n\n".join(context_parts)