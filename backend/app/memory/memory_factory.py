import os

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.redis import RedisSaver
from redis.asyncio import Redis


def get_memory():
    return InMemorySaver()


def get_store():
    return InMemoryStore()
