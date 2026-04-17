from langchain_openai import ChatOpenAI

from apps.config import settings


def get_llm(model: str = "gpt-5.2") -> ChatOpenAI:
    if settings.LLM_PROVIDER == "openai":
        return get_openai_llm(model)
    else:
        return get_dashscope_llm(model)


def get_openai_llm(model: str = "gpt-5.2") -> ChatOpenAI:
    return ChatOpenAI(temperature=0, model=model)


def get_dashscope_llm(model: str = "qwen-plus") -> ChatOpenAI:
    return ChatOpenAI(
        temperature=0,
        model=model,
        openai_api_key=settings.DASHSCOPE_API_KEY,
        openai_api_base=settings.DASHSCOPE_BASE_URL,
    )
