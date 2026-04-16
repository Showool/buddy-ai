from datetime import datetime
from sqlalchemy import BigInteger, func, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.mysql import TINYINT


class Base(DeclarativeBase):
    """所有模型的公共基类"""
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    creator_id: Mapped[str] = mapped_column(String(64), comment="创建者ID")
    create_time: Mapped[datetime] = mapped_column(server_default=func.now(), comment="创建时间")
    update_id: Mapped[str] = mapped_column(String(64), comment="更新者ID")
    update_time: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), comment="更新时间")


class User(Base):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(64), unique=True, comment="用户名")
    password: Mapped[str] = mapped_column(String(128), comment="密码")
    nickname: Mapped[str | None] = mapped_column(String(64), comment="昵称")
    email: Mapped[str | None] = mapped_column(String(128), comment="邮箱")
    avatar: Mapped[str | None] = mapped_column(String(255), comment="头像地址")
    status: Mapped[int] = mapped_column(TINYINT(1), default=1, comment="状态: 1-启用 0-禁用")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    name: Mapped[str] = mapped_column(String(128), comment="知识库名称")
    description: Mapped[str] = mapped_column(String(255), comment="知识库描述")


class KnowledgeBaseFile(Base):
    __tablename__ = "knowledge_base_file"

    knowledge_id: Mapped[int] = mapped_column(BigInteger, comment="所属知识库ID")
    file_name: Mapped[str] = mapped_column(String(255), comment="文件名")
    file_type: Mapped[str] = mapped_column(String(32), comment="文件类型")
    file_size: Mapped[int] = mapped_column(BigInteger, comment="文件大小(字节)")
    file_path: Mapped[str | None] = mapped_column(String(255), comment="文件存储路径")
    file_md5: Mapped[str | None] = mapped_column(String(255), comment="文件MD5校验值")
    file_content: Mapped[bytes | None] = mapped_column(LargeBinary(length=2**32 - 1), comment="文件内容")
