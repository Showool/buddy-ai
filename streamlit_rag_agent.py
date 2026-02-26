import json
import traceback
import uuid
from pathlib import Path

import dotenv
import streamlit as st

# 加载环境变量
dotenv.load_dotenv()

from agent.graph import get_graph
from retriever.vectorize_files import vectorize_uploaded_files


def get_message_type(message) -> str:
    """获取 LangChain 消息类型名称"""
    # 检查 type 属性优先（LangGraph 标准）
    msg_type = getattr(message, 'type', None)
    if msg_type:
        type_map = {
            'human': 'HumanMessage',
            'ai': 'AIMessage',
            'tool': 'ToolMessage'
        }
        return type_map.get(msg_type, f'{msg_type.capitalize()}Message')

    # 备用：检查 role 属性
    role = getattr(message, 'role', None)
    if role:
        role_map = {
            'user': 'HumanMessage',
            'assistant': 'AIMessage',
            'tool': 'ToolMessage'
        }
        return role_map.get(role, f'{role.capitalize()}Message')

    return 'UnknownMessage'


# 页面配置
st.set_page_config(
    page_title="RAG Agent 调试器",
    page_icon="🤖",
    layout="wide"
)


def main():
    st.markdown('### 🤖 RAG Agent 调试器')

    # 使用侧边栏添加知识库管理功能
    with st.sidebar:
        st.header("⚙️ 配置")

        # 用户ID输入
        user_id = st.text_input("用户ID", value="1", help="用于记忆管理，不同用户ID的记忆是隔离的")

        st.header("📚 知识库管理")

        # 创建知识库目录
        knowledge_db_path = Path("data_base/knowledge_db/data")
        knowledge_db_path.mkdir(parents=True, exist_ok=True)

        # 文件上传
        uploaded_file = st.file_uploader(
            "上传知识库文件",
            type=['pdf', 'docx', 'txt', 'md', 'csv'],
            accept_multiple_files=False,
            help="支持 PDF, DOCX, TXT, MD, CSV 格式，单个文件不超过 5MB"
        )

        if uploaded_file is not None:
            # 检查文件大小
            if uploaded_file.size > 5 * 1024 * 1024:  # 5MB
                st.error("文件大小超过 5MB 限制")
            else:
                # 保存上传的文件
                file_path = knowledge_db_path / uploaded_file.name

                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())

                st.success(f"文件已保存: {uploaded_file.name}")

                # 向量化按钮
                if st.button("🔬 向量化"):
                    try:
                        with st.spinner("正在向量化文件..."):
                            success = vectorize_uploaded_files([str(file_path)])
                            if success:
                                st.success("向量化完成！")
                            else:
                                st.error("向量化失败")
                    except Exception as e:
                        st.error(f"向量化过程中发生错误: {str(e)}")
                        print(traceback.format_exc())

        st.header("🗑️ 操作")

        # 清除对话按钮
        if st.button("清除对话"):
            st.session_state.messages = []
            st.session_state.debug_info = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.success("对话已清除")

    # 初始化 session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "debug_info" not in st.session_state:
        st.session_state.debug_info = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    # 初始化 graph
    if "graph" not in st.session_state:
        with st.spinner("正在初始化智能体..."):
            st.session_state.graph = get_graph()

    # 创建两列布局：左侧聊天，右侧调试信息
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("💬 对话")

        # 聊天容器
        messages = st.container(height=600)

        # 显示对话历史
        for message in st.session_state.messages:
            with messages.chat_message(message["role"]):
                st.write(message["content"])

        # 聊天输入
        if prompt := st.chat_input("输入您的问题..."):
            # 将用户消息添加到对话历史
            st.session_state.messages.append({"role": "user", "content": prompt})

            with messages.chat_message("user"):
                st.write(prompt)

            # 清空调试信息
            st.session_state.debug_info = []

            # 配置
            config = {
                "configurable": {
                    "thread_id": st.session_state.thread_id,
                    "user_id": user_id
                }
            }

            # 使用 graph.stream() 获取执行流
            ai_answer = ""
            assistant_messages = []

            with st.spinner("智能体正在思考..."):
                for chunk in st.session_state.graph.stream(
                        {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt,
                                }
                            ]
                        },
                        config,
                        stream_mode="values",
                ):
                    if "messages" in chunk:
                        last_message = chunk["messages"][-1]
                        # 收集所有的assistant消息
                        message_type = get_message_type(last_message)
                        if message_type == "AIMessage":
                            assistant_messages.append({
                                "content": last_message.content,
                                "tool_calls": getattr(last_message, 'tool_calls', None)
                            })

                        # 添加详细的调试信息
                        st.session_state.debug_info.append({
                            "type": "message",
                            "message_type": get_message_type(last_message),
                            "role": getattr(last_message, 'role', 'unknown'),
                            "content": str(last_message),
                            "tool_calls": getattr(last_message, 'tool_calls', None)
                        })
                    elif "__interrupt__" in chunk:
                        action = chunk["__interrupt__"][0]
                        debug_text = "INTERRUPTED:\n" + json.dumps(action.value, indent=2, ensure_ascii=False)
                        st.session_state.debug_info.append({
                            "type": "interrupt",
                            "content": debug_text
                        })

            # 使用最后一条没有 tool_calls 的 AI 消息作为最终回答
            final_answer = ""
            for msg in reversed(assistant_messages):
                # 仅选择没有 tool_calls 的消息作为最终回答
                if not msg.get('tool_calls'):
                    if msg.get('content') and msg['content'].strip():
                        final_answer = msg['content']
                        break

            # 显示 AI 回答
            if final_answer:
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                with messages.chat_message("assistant"):
                    st.markdown(final_answer)  # 使用markdown格式化显示

            # 触发右侧调试信息更新
            st.rerun()

    with col2:
        st.subheader("🔍 调试信息")

        # 显示调试信息
        if st.session_state.debug_info:
            with st.container(height=600):
                for i, debug in enumerate(st.session_state.debug_info):
                    if debug["type"] == "message":
                        # 根据消息类型显示不同的图标和标题
                        message_type = debug.get("message_type", "UnknownMessage")

                        type_icon = {
                            "HumanMessage": "👤",
                            "AIMessage": "🤖",
                            "ToolMessage": "🔧"
                        }.get(message_type, "📝")

                        # 构建标题，包含工具调用信息
                        title = f"{type_icon} {message_type}"

                        # 对于有 tool_calls 的 AIMessage，添加工具调用前缀
                        if message_type == "AIMessage" and debug.get("tool_calls"):
                            tool_names = [call.get("name", "unknown") for call in debug["tool_calls"]]
                            tool_str = ", ".join(tool_names[:2])  # 最多显示 2 个工具名称
                            if len(tool_names) > 2:
                                tool_str += f" 等{len(tool_names)}个"
                            title = f"{type_icon} AIMessage (工具调用: {tool_str})"

                        # 对于 ToolMessage，尝试获取工具名称
                        if message_type == "ToolMessage":
                            # ToolMessage 通常有 name 属性或 content 包含工具名
                            tool_name = getattr(debug, 'name', None)
                            if tool_name:
                                title = f"{type_icon} ToolMessage ({tool_name})"

                        title += f" {i+1}"

                        # 判断是否为最终 AI 回复（没有 tool_calls 且有内容）
                        is_final = bool(message_type == "AIMessage" and
                                       not debug.get("tool_calls") and
                                       debug.get("content", "").strip())

                        with st.expander(title, expanded=is_final):
                            # 显示工具调用信息
                            if debug.get("tool_calls"):
                                st.write("**工具调用:**")
                                for call in debug["tool_calls"]:
                                    st.code(json.dumps({
                                        "name": call.get("name"),
                                        "args": call.get("args", {})
                                    }, indent=2, ensure_ascii=False), language="json")
                            # 显示消息内容
                            if debug.get("content"):
                                st.write("**内容:**")
                                st.text(debug["content"])
                    elif debug["type"] == "interrupt":
                        with st.expander(f"⏸️ 中断 {i+1}", expanded=True):
                            st.text(debug["content"])
        else:
            st.info("暂无调试信息，开始对话后显示")

        # 显示会话信息
        st.divider()
        st.text("会话信息:")
        st.text(f"用户ID: {user_id}")
        st.text(f"线程ID: {st.session_state.thread_id}")
        st.text(f"消息数: {len(st.session_state.messages)}")


if __name__ == "__main__":
    main()