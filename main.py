from collections.abc import AsyncIterable
import logging
import traceback
import uuid

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from langchain_core.messages import AIMessageChunk
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI()

class ChatParams(BaseModel):
    """
    用户输入参数
    """

    user_id: str
    thread_id: str
    user_input: str


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/agent/chat", response_class=EventSourceResponse)
async def agent_chat(chatParams: ChatParams) -> AsyncIterable[dict]:
    try:
        from apps.agent.graph import get_graph

        compiled_graph = get_graph()
        config = {"configurable": {"thread_id": chatParams.thread_id, "user_id": chatParams.user_id}}

        for chunk in compiled_graph.stream(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": chatParams.user_input,
                    }
                ]
            },
            config,
            stream_mode="messages",
        ):
            # stream_mode="messages" 返回 (message, metadata) 元组
            if isinstance(chunk, tuple):
                message, metadata = chunk
                # 只推送 AI 生成的增量 token（AIMessageChunk 且有内容）
                if isinstance(message, AIMessageChunk) and message.content:
                    yield {"event": "workflow_node", "content": message.content, "node": metadata.get("langgraph_node", "")}

        # graph 执行完毕后，从 state 中取 final_answer 返回
        final_state = compiled_graph.get_state(config)
        final_answer = final_state.values.get("final_answer", "")
        if final_answer:
            yield {"event": "final_answer", "content": final_answer}
    except Exception as e:
        logger.error(f"❌ Agent响应失败: {e}")
        traceback.print_exc()
        yield {"error": f"❌ Agent响应失败: {e}"}
