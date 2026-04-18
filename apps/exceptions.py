from fastapi import HTTPException


class NotFoundError(HTTPException):
    """资源不存在异常 (404)"""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(status_code=404, detail=f"{resource} 不存在: {identifier}")


class DatabaseError(HTTPException):
    """数据库操作异常 (500)"""

    def __init__(self, operation: str, detail: str) -> None:
        super().__init__(status_code=500, detail=f"数据库{operation}失败: {detail}")


class LLMError(HTTPException):
    """LLM 调用失败 (502)"""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=502, detail=f"LLM 调用失败: {detail}")


class VectorStoreError(HTTPException):
    """向量库操作失败 (502)"""

    def __init__(self, operation: str, detail: str) -> None:
        super().__init__(status_code=502, detail=f"向量库{operation}失败: {detail}")


class FileProcessingError(HTTPException):
    """文件处理失败 (400)"""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=400, detail=f"文件处理失败: {detail}")
