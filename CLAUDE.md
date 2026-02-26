# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Buddy-AI is a Chinese-language intelligent Q&A system built with LangGraph, implementing a RAG (Retrieval Augmented Generation) architecture. The project consists of:

1. **Backend API** - FastAPI with LangGraph agent
2. **Frontend UI** - Vue3 + TypeScript + Pinia
3. **Debug UI** - Streamlit debugging interface

## Common Commands

### Backend Development (FastAPI)
- Install dependencies: `pip install -r requirements.txt`
- Start backend server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Or use startup scripts: `cd backend && start.bat` (Windows) or `./start.sh` (Linux/Mac)
- Health check: `curl http://localhost:8000/health`
- API docs (DEBUG mode): http://localhost:8000/docs

### Frontend Development (Vue3)
- Install dependencies: `cd frontend && npm install`
- Start dev server: `npm run dev` (runs on http://localhost:3000)
- Build for production: `npm run build`
- Lint: `npm run lint`
- Format: `npm run format`

### Streamlit Debug Interface
- Run: `streamlit run streamlit_rag_agent.py`

### Configuration
Copy `.env.example` to `.env` (in root or backend directory) and configure:
- `DASHSCOPE_API_KEY` - Aliyun DashScope API key (for Qwen LLM and embeddings)
- `TAVILY_API_KEY` - Tavily search API key
- `REDIS_URL` - Redis connection string for checkpointing (optional)
- `POSTGRESQL_URL` - PostgreSQL connection string for memory storage (optional)

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
- **Retriever** ([backend/app/retriever/get_retriever.py](backend/app/retriever/get_retriever.py)): Chroma vector database setup
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

**Components** ([frontend/src/components/](frontend/src/components/)):
- `ChatMessage.vue` - Message display with markdown rendering
- `ChatInput.vue` - Input field with file attachment
- `Sidebar.vue` - Session list and navigation
- `DebugPanel.vue` - Debug information display
- `FileUpload.vue` - File upload interface

**Views** ([frontend/src/views/](frontend/src/views/)):
- `ChatView.vue` - Main chat interface

**Router** ([frontend/src/router/index.ts](frontend/src/router/index.ts)): Vue Router configuration for navigation.

### Retrieval Strategy

Dual retrieval is implemented:
- Vector retrieval from Chroma database with DashScope embeddings (text-embedding-v4)
- Web search via Tavily API (max 3 results)
- Results are combined with knowledge base having priority

### Memory and State Management

- **Checkpointing**: Redis for conversation state persistence
- **Memory Storage**: PostgreSQL for user-specific memories via PostgresStore
- **WebSocket**: Real-time bidirectional communication for chat streaming

## Document Processing

Supported formats: PDF, DOCX, TXT, MD, CSV (max 5MB per file)
- Files uploaded via backend API and vectorized
- Stored persistently in Chroma vector DB at path specified by `CHROMA_PERSIST_DIR`

## Important Notes

- The system is designed for Chinese-language Q&A
- Maximum 3 tool calls per query
- When modifying the agent workflow, maintain the conditional edges structure in [backend/app/agent/graph.py](backend/app/agent/graph.py)
- Tool configuration can be adjusted by modifying the tools list in agent configuration
- WebSocket connections require user_id and optionally thread_id for session management
- The Streamlit debug interface ([streamlit_rag_agent.py](streamlit_rag_agent.py)) provides a separate way to test the agent without the full backend/frontend stack

## Project Structure

```
buddy-ai/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── main.py         # FastAPI app entry point
│   │   ├── config.py       # Configuration
│   │   ├── api/v1/         # API routes
│   │   ├── agent/          # LangGraph agent
│   │   ├── tools/          # Agent tools
│   │   ├── retriever/      # Vector DB & retrieval
│   │   ├── llm/            # LLM factory
│   │   ├── memory/         # Memory management
│   │   └── models/         # Pydantic models
│   ├── requirements.txt
│   ├── start.bat           # Windows startup script
│   └── start.sh            # Linux/Mac startup script
├── frontend/               # Vue3 Frontend
│   ├── src/
│   │   ├── main.ts         # Entry point
│   │   ├── App.vue         # Root component
│   │   ├── components/     # Vue components
│   │   ├── views/          # Page views
│   │   ├── stores/         # Pinia stores
│   │   ├── api/            # API clients
│   │   ├── composables/    # Vue composables
│   │   └── router/         # Vue Router
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── streamlit_rag_agent.py  # Debug interface
├── requirements.txt        # Dependencies
└── .env.example           # Environment template
```

## Dependencies

**Important Version Constraints**:
- `langgraph-checkpoint==3.0.1` (must be <4.0.0 for compatibility with langgraph-checkpoint-redis)
- `fastapi==0.109.0` with `starlette<0.36.0`