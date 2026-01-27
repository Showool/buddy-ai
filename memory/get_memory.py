from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore


def get_memory():
    return InMemorySaver()


def get_store():
    return InMemoryStore()
