"""
初始化 PostgreSQL 数据库 - RAG 系统优化 V2

执行此脚本将更新数据库表结构以支持：
1. 统一 Collection 设计
2. 全文搜索功能（基于 user_files 表）
3. 异步向量化任务跟踪
4. 文档元数据增强
"""

import logging
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        )
    """, (table_name, column_name))
    return cursor.fetchone()[0]


def check_index_exists(cursor, index_name: str) -> bool:
    """检查索引是否存在"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM pg_indexes
            WHERE indexname = %s
        )
    """, (index_name,))
    return cursor.fetchone()[0]


def init_database():
    """初始化数据库表结构"""
    try:
        conn = psycopg2.connect(settings.POSTGRESQL_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        logger.info("开始数据库初始化...")

        # ============================================================
        # 1. 扩展 user_files 表
        # ============================================================
        logger.info("检查 user_files 表结构...")

        # 添加 is_public 列
        if not check_column_exists(cursor, 'user_files', 'is_public'):
            cursor.execute("""
                ALTER TABLE user_files ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
            """)
            logger.info("添加列: user_files.is_public")
        else:
            logger.info("列已存在: user_files.is_public")

        # 添加 content_hash 列
        if not check_column_exists(cursor, 'user_files', 'content_hash'):
            cursor.execute("""
                ALTER TABLE user_files ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
            """)
            logger.info("添加列: user_files.content_hash")
        else:
            logger.info("列已存在: user_files.content_hash")

        # 添加 document_summary 列
        if not check_column_exists(cursor, 'user_files', 'document_summary'):
            cursor.execute("""
                ALTER TABLE user_files ADD COLUMN IF NOT EXISTS document_summary TEXT;
            """)
            logger.info("添加列: user_files.document_summary")
        else:
            logger.info("列已存在: user_files.document_summary")

        # 添加 chunk_count 列
        if not check_column_exists(cursor, 'user_files', 'chunk_count'):
            cursor.execute("""
                ALTER TABLE user_files ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0;
            """)
            logger.info("添加列: user_files.chunk_count")
        else:
            logger.info("列已存在: user_files.chunk_count")

        # 添加 last_vectorized_at 列
        if not check_column_exists(cursor, 'user_files', 'last_vectorized_at'):
            cursor.execute("""
                ALTER TABLE user_files ADD COLUMN IF NOT EXISTS last_vectorized_at TIMESTAMP WITH TIME ZONE;
            """)
            logger.info("添加列: user_files.last_vectorized_at")
        else:
            logger.info("列已存在: user_files.last_vectorized_at")

        conn.commit()

        # ============================================================
        # 2. 全文搜索支持（基于 user_files 表）
        # ============================================================
        logger.info("设置全文搜索...")

        # 添加 search_vector 列到 user_files
        if not check_column_exists(cursor, 'user_files', 'search_vector'):
            cursor.execute("""
                ALTER TABLE user_files ADD COLUMN IF NOT EXISTS search_vector tsvector;
            """)
            logger.info("添加列: user_files.search_vector")
        else:
            logger.info("列已存在: user_files.search_vector")

        # 创建 GIN 索引
        if not check_index_exists(cursor, 'idx_user_files_search'):
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_files_search
                ON user_files USING GIN(search_vector);
            """)
            logger.info("创建索引: idx_user_files_search")
        else:
            logger.info("索引已存在: idx_user_files_search")

        conn.commit()

        # ============================================================
        # 3. 自动更新 search_vector 的触发器
        # ============================================================
        logger.info("创建全文搜索更新触发器...")

        # 删除旧触发器
        cursor.execute("""
            DROP TRIGGER IF EXISTS trigger_update_search_vector ON user_files;
        """)

        # 创建更新函数
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_search_vector()
            RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := to_tsvector('simple', coalesce(NEW.file_content::text, ''));
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # 创建触发器
        cursor.execute("""
            CREATE TRIGGER trigger_update_search_vector
                BEFORE INSERT OR UPDATE ON user_files
                FOR EACH ROW
                EXECUTE FUNCTION update_search_vector();
        """)

        logger.info("触发器已创建: trigger_update_search_vector")
        conn.commit()

        # 一次性更新现有数据
        cursor.execute("""
            UPDATE user_files
            SET search_vector = to_tsvector('simple', coalesce(file_content::text, ''))
            WHERE search_vector IS NULL OR search_vector = ''::tsvector;
        """)

        updated_count = cursor.rowcount
        logger.info(f"更新了 {updated_count} 个文件的 search_vector")
        conn.commit()

        # ============================================================
        # 4. 向量化任务状态表
        # ============================================================
        logger.info("创建 vectorization_tasks 表...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vectorization_tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_id UUID NOT NULL REFERENCES user_files(id) ON DELETE CASCADE,
                user_id VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                total_chunks INTEGER DEFAULT 0,
                processed_chunks INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vec_tasks_user_id
            ON vectorization_tasks(user_id);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vec_tasks_status
            ON vectorization_tasks(status);
        """)

        logger.info("表已创建: vectorization_tasks")
        conn.commit()

        # ============================================================
        # 5. 验证 pgvector 扩展
        # ============================================================
        logger.info("检查 pgvector 扩展...")

        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_extension WHERE extname = 'vector'
            );
        """)

        if not cursor.fetchone()[0]:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("已安装 pgvector 扩展")
        else:
            logger.info("pgvector 扩展已安装")

        conn.commit()

        # ============================================================
        # 6. 验证表结构
        # ============================================================
        logger.info("=" * 50)
        logger.info("数据库初始化完成！")
        logger.info("=" * 50)

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise


if __name__ == "__main__":
    try:
        init_database()
        sys.exit(0)
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)