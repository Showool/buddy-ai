"""
用户文件服务 - 处理文件的 PostgreSQL 存储和检索

使用统一的数据库连接池 (db_pool.py)
"""

import logging
import uuid
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.models.user_file import UserFile
from app.services.db_pool import get_conn, return_conn  # 使用统一连接池
from app.utils.datetime_utils import get_beijing_now

logger = logging.getLogger(__name__)


class UserFileService:
    """用户文件服务"""

    def save_file(
        self, user_id: str, original_filename: str, file_content: bytes, file_type: str
    ) -> str:
        """
        保存用户文件到 PostgreSQL

        如果用户已上传同名文件，则删除旧文件和向量数据

        Args:
            user_id: 用户ID
            original_filename: 原始文件名
            file_content: 文件内容
            file_type: 文件类型

        Returns:
            str: 文件ID
        """
        conn = get_conn()
        cursor = conn.cursor()

        try:
            # 检查用户是否已上传同名文件
            cursor.execute(
                "SELECT id FROM user_files WHERE user_id = %s AND original_filename = %s",
                (user_id, original_filename),
            )
            existing_file = cursor.fetchone()

            old_file_id = None
            if existing_file:
                old_file_id = existing_file["id"]
                logger.info(f"发现同名文件，删除旧文件和向量数据: {original_filename}")

                # 【关键】先删除向量数据：使用统一collection，通过元数据过滤
                try:
                    cursor.execute(
                        """
                        DELETE FROM langchain_pg_embedding
                        WHERE collection_id = (
                            SELECT uuid FROM langchain_pg_collection
                            WHERE name = %s
                        )
                        AND cmetadata->>'user_id' = %s
                        AND cmetadata->>'filename' = %s
                    """,
                        (
                            settings.PGVECTOR_COLLECTION_NAME,
                            user_id,
                            original_filename,
                        ),
                    )

                    deleted_count = cursor.rowcount
                    logger.info(
                        f"已删除向量数据: 用户={user_id}, 文件={original_filename}, 记录数={deleted_count}"
                    )
                except Exception as e:
                    logger.warning(f"删除向量数据失败（可能尚不存在）: {e}")

                # 再删除旧文件记录
                cursor.execute("DELETE FROM user_files WHERE id = %s", (old_file_id,))

            # 生成新的文件ID
            file_id = str(uuid.uuid4())

            # 保存新文件
            cursor.execute(
                """
                INSERT INTO user_files (id, user_id, original_filename, file_content, file_type, file_size, upload_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    file_id,
                    user_id,
                    original_filename,
                    file_content,
                    file_type,
                    len(file_content),
                    get_beijing_now(),
                ),
            )

            conn.commit()
            logger.info(f"文件保存成功: {file_id}")
            return file_id

        except Exception as e:
            conn.rollback()
            logger.error(f"保存文件失败: {e}")
            raise
        finally:
            cursor.close()
            return_conn(conn)

    def get_file_by_id(self, file_id: str) -> Optional[UserFile]:
        """通过文件ID获取文件信息"""
        conn = get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, user_id, original_filename, file_type, file_size, upload_time,
                       is_public, content_hash, document_summary, chunk_count, last_vectorized_at, vectorization_status
                FROM user_files WHERE id = %s
                """,
                (file_id,),
            )
            row = cursor.fetchone()

            if row:
                return UserFile(
                    id=row["id"],
                    user_id=row["user_id"],
                    original_filename=row["original_filename"],
                    file_type=row["file_type"],
                    file_size=row["file_size"],
                    upload_time=row["upload_time"],
                    is_public=row.get("is_public", False),
                    content_hash=row.get("content_hash"),
                    document_summary=row.get("document_summary"),
                    chunk_count=row.get("chunk_count", 0),
                    last_vectorized_at=row.get("last_vectorized_at"),
                    vectorization_status=row.get("vectorization_status", "pending"),
                )
            return None

        except Exception as e:
            logger.error(f"获取文件失败: {e}")
            raise
        finally:
            cursor.close()
            return_conn(conn)

    def get_file_content(self, file_id: str) -> Optional[bytes]:
        """获取文件内容"""
        conn = get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT file_content FROM user_files WHERE id = %s",
                (file_id,),
            )
            row = cursor.fetchone()

            if row:
                return row["file_content"]
            return None

        except Exception as e:
            logger.error(f"获取文件内容失败: {e}")
            raise
        finally:
            cursor.close()
            return_conn(conn)

    def get_file_by_user_and_filename(
        self, user_id: str, original_filename: str
    ) -> Optional[UserFile]:
        """通过用户ID和文件名获取文件"""
        conn = get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, user_id, original_filename, file_type, file_size, upload_time,
                       is_public, content_hash, document_summary, chunk_count, last_vectorized_at, vectorization_status
                FROM user_files
                WHERE user_id = %s AND original_filename = %s
                """,
                (user_id, original_filename),
            )
            row = cursor.fetchone()

            if row:
                return UserFile(
                    id=row["id"],
                    user_id=row["user_id"],
                    original_filename=row["original_filename"],
                    file_type=row["file_type"],
                    file_size=row["file_size"],
                    upload_time=row["upload_time"],
                    is_public=row.get("is_public", False),
                    content_hash=row.get("content_hash"),
                    document_summary=row.get("document_summary"),
                    chunk_count=row.get("chunk_count", 0),
                    last_vectorized_at=row.get("last_vectorized_at"),
                    vectorization_status=row.get("vectorization_status", "pending"),
                )
            return None

        except Exception as e:
            logger.error(f"获取用户文件失败: {e}")
            raise
        finally:
            cursor.close()
            return_conn(conn)

    def list_user_files(self, user_id: str) -> List[UserFile]:
        """列出用户的所有文件"""
        conn = get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, user_id, original_filename, file_type, file_size, upload_time,
                       is_public, content_hash, document_summary, chunk_count, last_vectorized_at, vectorization_status
                FROM user_files
                WHERE user_id = %s
                ORDER BY upload_time DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()

            return [
                UserFile(
                    id=row["id"],
                    user_id=row["user_id"],
                    original_filename=row["original_filename"],
                    file_type=row["file_type"],
                    file_size=row["file_size"],
                    upload_time=row["upload_time"],
                    is_public=row.get("is_public", False),
                    content_hash=row.get("content_hash"),
                    document_summary=row.get("document_summary"),
                    chunk_count=row.get("chunk_count", 0),
                    last_vectorized_at=row.get("last_vectorized_at"),
                    vectorization_status=row.get("vectorization_status", "pending"),
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"列出用户文件失败: {e}")
            raise
        finally:
            cursor.close()
            return_conn(conn)

    def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        conn = get_conn()
        cursor = conn.cursor()

        try:
            self._delete_vector_data(file_id, conn, cursor)

            cursor.execute(
                "DELETE FROM user_files WHERE id = %s",
                (file_id,),
            )

            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"文件已删除: {file_id}")

            return deleted

        except Exception as e:
            conn.rollback()
            logger.error(f"删除文件失败: {e}")
            raise
        finally:
            cursor.close()
            return_conn(conn)

    def delete_user_files(self, user_id: str) -> int:
        """删除用户的所有文件"""
        conn = get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id FROM user_files WHERE user_id = %s",
                (user_id,),
            )
            rows = cursor.fetchall()

            for row in rows:
                self._delete_vector_data(row["id"], conn, cursor)

            cursor.execute(
                "DELETE FROM user_files WHERE user_id = %s",
                (user_id,),
            )

            conn.commit()

            deleted_count = cursor.rowcount
            logger.info(f"已删除用户 {user_id} 的 {deleted_count} 个文件")

            return deleted_count

        except Exception as e:
            conn.rollback()
            logger.error(f"删除用户文件失败: {e}")
            raise
        finally:
            cursor.close()
            return_conn(conn)

    def _delete_vector_data(self, file_id: str, conn=None, cursor=None):
        """删除文件相关的向量数据"""
        own_connection = False
        if conn is None or cursor is None:
            conn = get_conn()
            cursor = conn.cursor()
            own_connection = True

        try:
            from app.retriever.pgvector_store import get_pgvector_store

            vector_store = get_pgvector_store()

            all_docs = vector_store.get(include=["metadatas", "ids"])
            if all_docs and all_docs.get("metadatas") and all_docs.get("ids"):
                doc_ids_to_delete = []
                for idx, metadata in enumerate(all_docs["metadatas"]):
                    if metadata.get("file_id") == file_id:
                        doc_ids_to_delete.append(all_docs["ids"][idx])

                if doc_ids_to_delete:
                    vector_store.delete(ids=doc_ids_to_delete)
                    logger.info(
                        f"从向量数据库删除了 {len(doc_ids_to_delete)} 个文档片段"
                    )

        except Exception as e:
            logger.error(f"删除向量数据失败: {e}")
        finally:
            if own_connection:
                cursor.close()
                return_conn(conn)

    def get_temp_file_path(self, file_id: str, file_type: str) -> str:
        """将文件内容写入临时文件并返回文件路径"""
        file_content = self.get_file_content(file_id)
        if not file_content:
            raise ValueError(f"文件内容不存在: {file_id}")

        temp_dir = Path(settings.UPLOAD_DIR) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        temp_file_path = temp_dir / f"{file_id}.{file_type}"

        with open(temp_file_path, "wb") as f:
            f.write(file_content)

        return str(temp_file_path)

    def cleanup_temp_file(self, file_path: str):
        """清理临时文件"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.debug(f"临时文件已删除: {file_path}")
        except Exception as e:
            logger.warning(f"删除临时文件失败: {e}")

    def list_public_files(self) -> List[UserFile]:
        """列出所有公开的文件"""
        conn = get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, user_id, original_filename, file_type, file_size, upload_time
                FROM user_files
                WHERE is_public = TRUE
                ORDER BY upload_time DESC
            """
            )
            rows = cursor.fetchall()

            return [
                UserFile(
                    id=row["id"],
                    user_id=row["user_id"],
                    original_filename=row["original_filename"],
                    file_type=row["file_type"],
                    file_size=row["file_size"],
                    upload_time=row["upload_time"],
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"列出公开文件失败: {e}")
            raise
        finally:
            cursor.close()
            return_conn(conn)


# 全局实例
user_file_service = UserFileService()