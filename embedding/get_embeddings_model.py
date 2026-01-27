import dotenv
from langchain_community.embeddings import DashScopeEmbeddings


def get_embeddings_model():
    dotenv.load_dotenv()  # read local .env file
    return DashScopeEmbeddings(
        model="text-embedding-v4",
    )