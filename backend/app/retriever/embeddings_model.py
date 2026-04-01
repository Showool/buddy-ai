import dotenv
from langchain_community.embeddings import DashScopeEmbeddings
from ..config import settings


def get_embeddings_model():
    dotenv.load_dotenv()  # read local .env file
    return DashScopeEmbeddings(
        model=settings.EMBEDDING_MODEL,
    )
