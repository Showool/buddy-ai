# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Buddy-AI is a Chinese-language intelligent Q&A system built with LangChain and LangGraph. It implements a RAG (Retrieval Augmented Generation) architecture with dual retrieval strategy combining local vector database (Chroma) and Tavily web search.

## Common Commands

### Development
- Install dependencies: `pip install -r requirements.txt`
- Run the Streamlit application: `streamlit run streamlit_app.py`

### Configuration
- Copy `.env.example` to `.env` and configure API keys:
  - `DASHSCOPE_API_KEY` - Aliyun DashScope API key (for Qwen LLM and embeddings)
  - `TAVILY_API_KEY` - Tavily search API key
  - `REDIS_URL` - Redis connection string for checkpointing
  - `POSTGRESQL_URL` - PostgreSQL connection string for memory storage

## Architecture

### Agent Framework (LangGraph)

The core agent workflow is defined in [agent/graph.py](agent/graph.py) using LangGraph's StateGraph:

**State Definition** ([agent/state.py](agent/state.py)):
- `AgentState` extends LangGraph's `MessagesState` with a `loop_step` counter
- `GradeDocuments` is a Pydantic model for binary relevance scoring

**Node Flow**:
1. `generate_query_or_respond` ([agent/node.py:13](agent/node.py#L13)) - Decides whether to use retrieval tools or respond directly
2. `tool_node` - Executes tools via LangGraph's ToolNode
3. `grade_documents` ([agent/node.py:71](agent/node.py#L71)) - Evaluates retrieved document relevance, routes to `generate_answer` or `rewrite_question`
4. `rewrite_question` ([agent/node.py:34](agent/node.py#L34)) - Rewrites question if documents aren't relevant (max 3 iterations)
5. `generate_answer` ([agent/node.py:61](agent/node.py#L61)) - Generates final answer using retrieved context

### Tools System ([tools/__init__.py](tools/__init__.py))

The agent uses multiple specialized tools:
- **System Tools**: `clear_conversation`, `update_user_name`, `retrieve_context`, `retriever_tool`
- **User Tools**: `get_weather_for_location`, `retrieve_memory`, `save_memory`
- **Search Tools**: `tavily_search` for web search integration

### Retrieval Strategy

Dual retrieval is implemented in [qa_chain/get_qa_history_chain.py](qa_chain/get_qa_history_chain.py):
- Vector retrieval from Chroma database ([retriever/get_retriever.py](retriever/get_retriever.py))
- Web search via Tavily API (max 3 results)
- Results are combined with knowledge base having priority

### Key Components

- **LLM Factory** ([llm/llm_factory.py](llm/llm_factory.py)): Uses Qwen models via DashScope OpenAI-compatible API
- **Embeddings** ([embedding/](embedding/)): DashScope text embeddings for vectorization
- **Prompts** ([prompt/prompt.py](prompt/prompt.py)): System prompts for various agent operations
- **Streamlit App** ([streamlit_app.py](streamlit_app.py)): Main UI for file upload and chat interface

### Document Processing

Supported formats: PDF, DOCX, TXT, MD, CSV (max 5MB per file)
- Files uploaded to `data_base/knowledge_db/data/`
- Vectorized via [retriever/vectorize_files.py](retriever/vectorize_files.py)
- Stored persistently in Chroma vector DB at path specified by `CHROMA_PERSIST_DIR`

### Memory and State Management

- **Checkpointing**: Redis for conversation state persistence
- **Memory Storage**: PostgreSQL for user-specific memories
- **Session State**: Streamlit session state for conversation history

## Important Notes

- The system is designed for Chinese-language Q&A
- Maximum 3 tool calls per query as defined in [prompt/prompt.py:10](prompt/prompt.py#L10)
- When modifying the agent workflow, maintain the conditional edges structure in [agent/graph.py](agent/graph.py)
- Tool configuration can be adjusted in [tools/__init__.py](tools/__init__.py) by commenting/uncommenting tools