from functools import lru_cache

from langchain_openai import ChatOpenAI

from apps.config import settings


def get_llm(model: str | None = None) -> ChatOpenAI:
    """获取 LLM 实例（同参数复用缓存）"""
    resolved_model = model or settings.LLM_MODEL
    if settings.LLM_PROVIDER == "openai":
        return _get_openai_llm(resolved_model)
    else:
        return _get_dashscope_llm(resolved_model)


@lru_cache(maxsize=4)
def _get_openai_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(temperature=0, model=model)


@lru_cache(maxsize=4)
def _get_dashscope_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        temperature=0,
        model=model,
        openai_api_key=settings.DASHSCOPE_API_KEY,
        openai_api_base=settings.DASHSCOPE_BASE_URL,
    )
