from pydantic import BaseModel, Field, field_validator


class ChatParams(BaseModel):
    """用户对话输入参数"""

    user_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$", description="用户ID")
    thread_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$", description="会话ID")
    user_input: str = Field(..., min_length=1, max_length=10000, description="用户输入")

    @field_validator("user_id", "thread_id")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("不能为空或仅包含空白字符")
        return v.strip()

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("用户输入不能为空或仅包含空白字符")
        return v.strip()

class DeleteFileParams(BaseModel):
    user_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$", description="用户ID")
    knowledge_id: int = Field(..., description="知识库ID")
    file_id: int = Field(..., description="文件ID")