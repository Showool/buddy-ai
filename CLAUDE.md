# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Buddy-AI is a Chinese-language intelligent Q&A system built with LangGraph, implementing a RAG (Retrieval Augmented Generation) architecture. The project consists of:

1. **Backend API** - FastAPI with LangGraph agent
2. **Frontend UI** - Vue3 + TypeScript + Pinia

## Common Commands

### Backend Development (FastAPI)

**Package Management (pip + conda)**:
```bash
cd backend

# Make sure conda environment is activated
conda activate buddy-ai

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Install new dependency
pip install package_name

# Check installed packages
pip list
```

**Running the Server**:
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Health Check**: `curl http://localhost:8000/health`

**API Docs**: http://localhost:8000/docs (DEBUG mode only)

### Frontend Development (Vue3)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (runs on http://localhost:3000)
npm run dev

# Build for production
npm run build
```

### Configuration

Create or edit `backend/.env`:
- `DASHSCOPE_API_KEY` - Aliyun DashScope API key (for Qwen LLM and embeddings)
- `TAVILY_API_KEY` - Tavily search API key
- `REDIS_URL` - Redis connection string for checkpointing
- `POSTGRESQL_URL` - PostgreSQL connection string for memory and vector storage
- `VECTOR_DB_TYPE` - `chroma` (default) or `postgresql`

## Architecture

### Backend (FastAPI + LangGraph)

**Entry Point**: [backend/app/main.py](backend/app/main.py)

The backend implements a FastAPI application with WebSocket support for real-time chat.

**Agent Framework (LangGraph)**:

The core agent workflow is defined in [backend/app/agent/graph.py](backend/app/agent/graph.py):

**State Definition** ([backend/app/agent/state.py](backend/app/agent/state.py)):
- `AgentState` extends LangGraph's `MessagesState` with a `loop_step` counter
- `GradeDocuments` is a Pydantic model for binary relevance scoring

**Node Flow**:
1. `generate_query_or_respond` ([backend/app/agent/node.py:13](backend/app/agent/node.py#L13)) - Decides whether to use retrieval tools or respond directly
2. `tool_node` - Executes tools via LangGraph's ToolNode
3. `grade_documents` ([backend/app/agent/node.py:71](backend/app/agent/node.py#L71)) - Evaluates retrieved document relevance, routes to `generate_answer` or `rewrite_question`
4. `rewrite_question` ([backend/app/agent/node.py:34](backend/app/agent/node.py#L34)) - Rewrites question if documents aren't relevant (max 3 iterations)
5. `generate_answer` ([backend/app/agent/node.py:61](backend/app/agent/node.py#L61)) - Generates final answer using retrieved context

**Tools System** ([backend/app/tools/](backend/app/tools/)):
- **System Tools** ([system_tool.py](backend/app/tools/system_tool.py)): `clear_conversation`, `update_user_name`, `retrieve_context`, `retriever_tool`
- **User Tools** ([user_tool.py](backend/app/tools/user_tool.py)): `get_weather_for_location`, `retrieve_memory`, `save_memory`, `save_conversation_memory`
- **Search Tools** ([web_search_tool.py](backend/app/tools/web_search_tool.py)): `tavily_search` for web search integration

**API Routes** ([backend/app/api/v1/](backend/app/api/v1/)):
- `/api/v1/chat/ws/{user_id}` - WebSocket chat endpoint
- `/api/v1/files/` - File upload and vectorization
- `/api/v1/sessions/` - Session management
- `/api/v1/memory/` - Memory CRUD operations

**Configuration** ([backend/app/config.py](backend/app/config.py)):
Uses Pydantic Settings for environment-based configuration with support for development, staging, and production environments.

**Key Components**:
- **LLM Factory** ([backend/app/llm/llm_factory.py](backend/app/llm/llm_factory.py)): Uses Qwen models via DashScope OpenAI-compatible API
- **Embeddings** ([backend/app/retriever/embeddings_model.py](backend/app/retriever/embeddings_model.py)): DashScope text embeddings for vectorization
- **Prompts** ([backend/app/prompt/prompt.py](backend/app/prompt/prompt.py)): System prompts for various agent operations
- **Vector Store** ([backend/app/retriever/vector_store.py](backend/app/retriever/vector_store.py)): Abstraction layer that selects Chroma or PostgreSQL+pgvector based on `VECTOR_DB_TYPE` config
- **PGVector Store** ([backend/app/retriever/pgvector_store.py](backend/app/retriever/pgvector_store.py)): PostgreSQL vector storage implementation
- **Retriever** ([backend/app/retriever/get_retriever.py](backend/app/retriever/get_retriever.py)): Retrieval setup combining vector search and web search
- **Memory** ([backend/app/memory/memory_factory.py](backend/app/memory/memory_factory.py)): PostgreSQL memory store

### Frontend (Vue3 + TypeScript)

**Entry Point**: [frontend/src/main.ts](frontend/src/main.ts)

The frontend is a Vue3 SPA with TypeScript, using Vite as the build tool.

**State Management (Pinia)**:
- [frontend/src/stores/chat.ts](frontend/src/stores/chat.ts) - Chat message and state management
- [frontend/src/stores/session.ts](frontend/src/stores/session.ts) - Session management
- [frontend/src/stores/user.ts](frontend/src/stores/user.ts) - User state

**Communication Layer**:
- **WebSocket**: [frontend/src/composables/useWebSocket.ts](frontend/src/composables/useWebSocket.ts) - Real-time chat connection to backend
- **REST API**: [frontend/src/api/](frontend/src/api/) - File upload, session, and memory operations via Axios

### Vector Database Configuration

**Chroma (default)**:
- Stores vectors in local directory specified by `CHROMA_PERSIST_DIR` config (default: `./chroma_db`)
- No additional database setup required

**PostgreSQL+pgvector**:
- Set `VECTOR_DB_TYPE=postgresql` in `.env`
- Requires pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
- Uses the same PostgreSQL connection as memory storage

### Retrieval Strategy

Dual retrieval is implemented:
- Vector retrieval from configured vector database (Chroma or PostgreSQL) with DashScope embeddings
- Web search via Tavily API (max 3 results)
- Results are combined with knowledge base having priority

### Memory and State Management

- **Checkpointing**: Redis for conversation state persistence
- **Memory Storage**: PostgreSQL for user-specific memories via PostgresStore
- **WebSocket**: Real-time bidirectional communication for chat streaming

## Document Processing

Supported formats: PDF, DOCX, TXT, MD, CSV (max 5MB per file)
- Files uploaded via backend API and vectorized
- Stored persistently in configured vector database

## Important Notes

- Python 3.11+ required
- The system is designed for Chinese-language Q&A
- Maximum 3 tool calls per query
- When modifying the agent workflow, maintain the conditional edges structure in [backend/app/agent/graph.py](backend/app/agent/graph.py)
- Tool configuration can be adjusted by modifying the tools list in agent configuration
- WebSocket connections require user_id and optionally thread_id for session management
- Vector store path uses `settings.CHROMA_PERSIST_DIR` config (see [vector_store.py](backend/app/retriever/vector_store.py))

## Dependencies

**Backend**:
- `pyproject.toml` - Main dependency specification
- `requirements.txt` - Simplified list for direct installation

**Version Constraints**:
- `langgraph-checkpoint==3.0.1` (must be <4.0.0 for compatibility with langgraph-checkpoint-redis)
- `fastapi==0.109.0` with `starlette<0.36.0`