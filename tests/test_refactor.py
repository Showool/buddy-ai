"""
测试后端重构方案的修改是否正确
"""
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError


# ========== 问题 1: MemoryManager 延迟初始化 ==========

class TestMemoryManagerSingleton:
    """测试 MemoryManager 的 init/get 单例模式"""

    def test_get_memory_client_before_init_raises(self):
        """未初始化时调用 get_memory_client 应抛出 RuntimeError"""
        import apps.agent.memory.mem0 as mem0_module
        original = mem0_module._memory_client
        try:
            mem0_module._memory_client = None
            with pytest.raises(RuntimeError, match="MemoryClient 未初始化"):
                mem0_module.get_memory_client()
        finally:
            mem0_module._memory_client = original

    @patch("apps.agent.memory.mem0.MemoryManager")
    def test_init_memory_sets_singleton(self, mock_manager_cls):
        """init_memory 应设置模块级 _memory_client"""
        import apps.agent.memory.mem0 as mem0_module
        original = mem0_module._memory_client
        try:
            mem0_module._memory_client = None
            mock_client = MagicMock()
            mock_manager_cls.return_value.memory_client = mock_client

            mem0_module.init_memory()

            assert mem0_module._memory_client is mock_client
            assert mem0_module.get_memory_client() is mock_client
        finally:
            mem0_module._memory_client = original

    @patch("apps.agent.memory.mem0.MemoryManager")
    def test_get_memory_client_after_init(self, mock_manager_cls):
        """init 后 get_memory_client 应返回同一实例"""
        import apps.agent.memory.mem0 as mem0_module
        original = mem0_module._memory_client
        try:
            mem0_module._memory_client = None
            mock_client = MagicMock()
            mock_manager_cls.return_value.memory_client = mock_client

            mem0_module.init_memory()
            client1 = mem0_module.get_memory_client()
            client2 = mem0_module.get_memory_client()
            assert client1 is client2
        finally:
            mem0_module._memory_client = original


# ========== 问题 2: 自定义异常 ==========

class TestCustomExceptions:
    """测试自定义异常类"""

    def test_not_found_error(self):
        from apps.exceptions import NotFoundError
        err = NotFoundError("文件", "id=42")
        assert err.status_code == 404
        assert "文件" in err.detail
        assert "id=42" in err.detail

    def test_database_error(self):
        from apps.exceptions import DatabaseError
        err = DatabaseError("查询", "connection refused")
        assert err.status_code == 500
        assert "数据库查询失败" in err.detail
        assert "connection refused" in err.detail


# ========== 问题 3: 类型注解 ==========

class TestTypeAnnotations:
    """测试 read_root 返回类型"""

    def test_read_root_returns_dict(self):
        """read_root 应返回 dict[str, str]"""
        # 直接导入会触发 settings 加载，这里只验证函数签名
        import inspect
        from main import read_root
        sig = inspect.signature(read_root)
        assert sig.return_annotation == dict[str, str]

    def test_read_root_value(self):
        from main import read_root
        result = read_root()
        assert isinstance(result, dict)
        assert "Hello" in result


# ========== 问题 4: 输入验证 ==========

class TestChatParamsValidation:
    """测试 ChatParams 的输入验证"""

    def test_valid_params(self):
        from apps.models.request_params import ChatParams
        params = ChatParams(user_id="user_1", thread_id="thread_1", user_input="hello")
        assert params.user_id == "user_1"
        assert params.thread_id == "thread_1"
        assert params.user_input == "hello"

    def test_empty_user_id_rejected(self):
        from apps.models.request_params import ChatParams
        with pytest.raises(ValidationError):
            ChatParams(user_id="", thread_id="t1", user_input="hello")

    def test_blank_user_id_rejected(self):
        from apps.models.request_params import ChatParams
        with pytest.raises(ValidationError):
            ChatParams(user_id="   ", thread_id="t1", user_input="hello")

    def test_empty_thread_id_rejected(self):
        from apps.models.request_params import ChatParams
        with pytest.raises(ValidationError):
            ChatParams(user_id="u1", thread_id="", user_input="hello")

    def test_blank_thread_id_rejected(self):
        from apps.models.request_params import ChatParams
        with pytest.raises(ValidationError):
            ChatParams(user_id="u1", thread_id="   ", user_input="hello")

    def test_empty_user_input_rejected(self):
        from apps.models.request_params import ChatParams
        with pytest.raises(ValidationError):
            ChatParams(user_id="u1", thread_id="t1", user_input="")

    def test_blank_user_input_rejected(self):
        from apps.models.request_params import ChatParams
        with pytest.raises(ValidationError):
            ChatParams(user_id="u1", thread_id="t1", user_input="   ")

    def test_user_id_too_long_rejected(self):
        from apps.models.request_params import ChatParams
        with pytest.raises(ValidationError):
            ChatParams(user_id="a" * 65, thread_id="t1", user_input="hello")

    def test_user_input_too_long_rejected(self):
        from apps.models.request_params import ChatParams
        with pytest.raises(ValidationError):
            ChatParams(user_id="u1", thread_id="t1", user_input="a" * 10001)

    def test_strips_whitespace(self):
        from apps.models.request_params import ChatParams
        params = ChatParams(user_id="  u1  ", thread_id="  t1  ", user_input="  hello  ")
        assert params.user_id == "u1"
        assert params.thread_id == "t1"
        assert params.user_input == "hello"


class TestDeleteFileParamsUnchanged:
    """确保 DeleteFileParams 没有被意外修改"""

    def test_valid_delete_params(self):
        from apps.models.request_params import DeleteFileParams
        params = DeleteFileParams(user_id="u1", knowledge_id=1, file_id=42)
        assert params.file_id == 42
