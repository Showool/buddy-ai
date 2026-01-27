# Buddy-AI

一个基于 Streamlit 构建的智能问答系统，结合了 RAG (Retrieval Augmented Generation) 技术和向量数据库，支持用户上传知识库文档并进行智能问答。

## 🌟 特性

- **智能问答**: 基于大语言模型的智能对话系统
- **知识库上传**: 支持 PDF, DOCX, TXT, MD, CSV 格式的文档上传
- **向量化存储**: 使用 Chroma 向量数据库存储和检索知识
- **双路检索**: 结合本地向量数据库和 Tavily 网络搜索
- **对话历史**: 保持对话上下文，提供连贯交互体验
- **响应式界面**: 使用 Streamlit 构建的现代化用户界面

## 🏗️ 项目架构

```
buddy-ai/
├── agent/              # 智能体框架
│   ├── agent_context.py
│   ├── create_agent.py
│   └── response_format.py
├── data_base/          # 数据库管理
│   ├── knowledge_db/   # 知识库文件
│   ├── create_vector_db.py
│   └── vectorize_files.py
├── embedding/          # 嵌入模型
│   └── get_embeddings_model.py
├── llm/               # 大语言模型管理
├── memory/            # 对话记忆管理
├── prompt/            # 提示词管理
│   └── prompt.py
├── qa_chain/          # 问答链
│   ├── get_qa_history_chain.py
│   └── get_response.py
├── rag/               # RAG 组件
│   ├── get_retriever.py
│   └── get_vector_store.py
├── tools/             # 工具函数
│   ├── __init__.py
│   ├── system_tool.py
│   └── user_tool.py
├── streamlit_app.py   # 主应用入口
└── .env              # 环境变量配置
```

## 🚀 快速开始

### 环境准备

1. 克隆项目
```bash
git clone <repository-url>
cd buddy-ai
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件，填入 API 密钥
nano .env
```

### 运行应用

```bash
# 启动 Streamlit 应用
streamlit run streamlit_app.py
```

## 🔧 配置说明

项目使用 `.env` 文件管理配置，主要包含：

- `DASHSCOPE_API_KEY`: 通义千问 API 密钥
- `TAVILY_API_KEY`: Tavily 搜索 API 密钥

## 📁 文件上传与向量化

1. 在侧边栏点击"上传知识库文件"
2. 选择支持格式的文档（单个文件不超过 5MB）
3. 点击"向量化"按钮将文档内容添加到向量数据库
4. 向 AI 提问，系统将结合知识库内容回答

## 🛠️ 技术栈

- **前端**: Streamlit
- **向量数据库**: Chroma
- **嵌入模型**: DashScope 文本嵌入
- **语言模型**: 通义千问系列
- **文档处理**: LangChain Document Loaders
- **搜索服务**: Tavily Search API
- **智能体**: LangGraph

## 📚 支持的文档格式

- PDF (.pdf)
- Word 文档 (.docx)
- 纯文本 (.txt)
- Markdown (.md)
- CSV 表格 (.csv)

## 💡 使用场景

- **企业知识库**: 存储和查询企业内部文档
- **学术研究**: 管理和检索学术论文
- **个人助手**: 创建个性化知识问答系统
- **客户服务**: 自动回答常见问题

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 📄 许可证

MIT License