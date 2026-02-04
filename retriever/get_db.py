from langchain_community.utilities import SQLDatabase


def get_sqlite_db():
    return SQLDatabase.from_uri("sqlite:///C:/Windows/System32/buddy_ai_database.db")
