from langchain_openai import ChatOpenAI
import os
import dotenv


def get_llm(model: str):
    dotenv.load_dotenv()  # read local .env file
    return ChatOpenAI(
        temperature=0.7,
        model=model,
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base=os.getenv("DASHSCOPE_BASE_URL")
    )
