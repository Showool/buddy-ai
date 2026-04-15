from collections.abc import AsyncIterable
import logging
import traceback
import docx
import io
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.sse import EventSourceResponse
from langchain_core.messages import AIMessageChunk
from pydantic import BaseModel
from pathlib import Path
from apps.agent.rag.document_split import split_document
from apps.agent.rag import milvusVector
from apps.agent.utils.id_util import generate_id
from apps.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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


ALLOWED_EXTENSIONS = {".txt", ".docx", ".md"}


async def validate_file(file: UploadFile = File(...)) -> UploadFile:
    """校验上传文件的扩展名，仅允许 txt、docx、md。"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")
    return file


@app.post("/upload_file")
async def upload_file(file: UploadFile = Depends(validate_file), user_id: str = Form(...), knowledge_id: int = Form(...)):
    """上传单个文件，仅支持 txt、docx、md 格式，返回文件内容。"""
    ext = Path(file.filename or "").suffix.lower()
    raw = await file.read()

    if ext in (".txt", ".md"):
        content = raw.decode("utf-8")
    else:
        doc = docx.Document(io.BytesIO(raw))
        content = "\n".join(p.text for p in doc.paragraphs)

    document_list = split_document(content, ext, 200)
    milvusVector.save_documents(document_list, user_id, knowledge_id, generate_id())
    return {"filename": file.filename, "content": document_list}


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
