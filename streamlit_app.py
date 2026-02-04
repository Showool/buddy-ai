import traceback

import streamlit as st
from pathlib import Path

from retriever.vectorize_files import vectorize_uploaded_files
from qa_chain.get_qa_history_chain import get_qa_history_chain
from qa_chain.get_response import gen_response


# Streamlit 应用程序界面
def main():
    st.markdown('### 🦜🔗 Buddy-AI')
    
    # 使用侧边栏添加知识库管理功能
    with st.sidebar:
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

    # 用于跟踪对话历史
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # 存储检索问答链
    if "qa_history_chain" not in st.session_state:
        st.session_state.qa_history_chain = get_qa_history_chain()

    messages = st.container(height=800)
    # 显示整个对话历史
    for message in st.session_state.messages:
        with messages.chat_message(message[0]):
            st.write(message[1])
    if prompt := st.chat_input("Say something"):
        # 将用户输入添加到对话历史中
        st.session_state.messages.append(("human", prompt))
        with messages.chat_message("human"):
            st.write(prompt)

        answer = gen_response(
            chain=st.session_state.qa_history_chain,
            input=prompt,
            chat_history=st.session_state.messages
        )
        with messages.chat_message("ai"):
            output = st.write_stream(answer)
        st.session_state.messages.append(("ai", output))


if __name__ == "__main__":
    main()
