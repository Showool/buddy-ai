from fastapi import HTTPException


class NotFoundError(HTTPException):
    """资源不存在异常 (404)"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(status_code=404, detail=f"{resource} 不存在: {identifier}")


class DatabaseError(HTTPException):
    """数据库操作异常 (500)"""
    def __init__(self, operation: str, detail: str):
        super().__init__(status_code=500, detail=f"数据库{operation}失败: {detail}")
