from collections.abc import AsyncIterable
import logging
import traceback

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse
from langchain_core.messages import AIMessageChunk

from apps.models.request_params import ChatParams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_class=EventSourceResponse)
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
            if isinstance(chunk, tuple):
                message, metadata = chunk
                if isinstance(message, AIMessageChunk) and message.content:
                    yield {"event": "workflow_node", "content": message.content, "node": metadata.get("langgraph_node", "")}

        final_state = compiled_graph.get_state(config)
        final_answer = final_state.values.get("final_answer", "")
        if final_answer:
            yield {"event": "final_answer", "content": final_answer}
    except Exception as e:
        logger.error(f"❌ Agent响应失败: {e}")
        traceback.print_exc()
        yield {"error": f"❌ Agent响应失败: {e}"}
