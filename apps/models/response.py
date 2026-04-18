from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """标准 API 响应"""

    success: bool
    data: T | None = None
    message: str | None = None
