import logging
from collections.abc import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.config import settings
from apps.database.models import Base
from apps.exceptions import DatabaseError

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
  settings.MYSQL_URL, 
  echo=True, #可选：输出SQL日志
  pool_size=10, # 设置连接池中保持的持久连接数
  max_overflow=20 # 设置连接池允许创建的额外连接数
)

async_session = async_sessionmaker(
    bind=async_engine,          # 绑定的引擎（第一个位置参数）
    class_=AsyncSession,        # 会话类，默认就是 AsyncSession，一般不用显式指定
    expire_on_commit=False,     # commit 后是否过期已加载的属性 会话对象不过期，不重新查询数据库
    autoflush=True,             # 查询前是否自动 flush 待写入的变更
    autocommit=False,           # 是否自动提交（几乎不用改，保持 False）
)



async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error("数据库操作失败: %s", e, exc_info=True)
            raise DatabaseError("操作", str(e)) from e
        except Exception as e:
            await session.rollback()
            logger.error("未知错误: %s", e, exc_info=True)
            raise


async def create_tables():
  async with async_engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
