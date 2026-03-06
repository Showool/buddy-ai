"""记忆服务 - 检索与保存"""
import uuid
from datetime import datetime
from typing import List, Optional

from langgraph.store.postgres import PostgresStore

from ..retriever.embeddings_model import get_embeddings_model

from .memory_schema import MemoryCategory, ConversationAnalysis
from ..llm.llm_factory import get_llm
from ..prompt.prompt import CONVERSATION_ANALYSIS_PROMPT
from ..config import settings

class MemoryService:
    """记忆服务 - 使用 PostgresStore 向量搜索和分类过滤"""

    def __init__(self):
        self.llm = get_llm()

    def retrieve_memory(
        self,
        user_id: str,
        query: str,
        category: Optional[MemoryCategory] = None,
        limit: int = 3
    ) -> List[dict]:
        """使用向量搜索和分类过滤检索记忆"""
        namespace = ("memories", user_id)

        filter_dict = None
        if category:
            filter_dict = {"category": category.value}


        embeddings = get_embeddings_model()
        with PostgresStore.from_conn_string(settings.POSTGRESQL_URL, index={"embed": embeddings, "dims": settings.EMBEDDING_DIMENSIONS}) as store:
            namespace = ("memories", user_id)

            # Search for memories using the query
            items = store.search(namespace, query=query,filter=filter_dict,limit=limit)

            return [
                {
                    "key": item.key,
                    "data": item.value.get("data"),
                    "category": item.value.get("category"),
                    "tags": item.value.get("tags", []),
                    "timestamp": item.value.get("timestamp")
                }
                for item in items
            ]

    def save_memory(
        self,
        user_id: str,
        question: str,
        answer: str
    ) -> str:
        """保存记忆"""
        analysis = self._analyze_conversation(question, answer)

        if not analysis.should_save:
            return "对话内容无需保存到长期记忆。"

        memory_data = {
            "data": analysis.summary,
            "category": analysis.category.value,
            "tags": analysis.tags,
            "timestamp": datetime.now().isoformat()
        }

         # 连接到存储并保存记忆
        embeddings = get_embeddings_model()
        with PostgresStore.from_conn_string(settings.POSTGRESQL_URL, index={"embed": embeddings, "dims": settings.EMBEDDING_DIMENSIONS}) as store:
            namespace = ("memories", user_id)
            store.put(namespace, str(uuid.uuid4()), memory_data)

        return f"已保存记忆: {analysis.summary}"

    def _analyze_conversation(self, question: str, answer: str) -> ConversationAnalysis:
        """分析对话提取值得记忆的信息"""
        prompt = CONVERSATION_ANALYSIS_PROMPT.format(
            question=question,
            answer=answer
        )
        response = self.llm.with_structured_output(ConversationAnalysis).invoke([
            {"role": "user", "content": prompt}
        ])
        return response


memory_service = MemoryService()