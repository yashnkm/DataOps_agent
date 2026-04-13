# Fee Billing Excellence (FBE) Analytic System

## Project Overview
Gradio web app for natural-language analysis over uploaded contracts and a PostgreSQL financial database. Three core surfaces:
- **Documents**: upload + chunk + embed contract PDFs
- **Dashboard**: real-time contract compliance and discrepancy detection
- **Smart Chat**: RAG over uploaded documents
- **Analysis** (LangGraph agent): cross-source reasoning over Postgres (via MCP) and uploaded documents

## Architecture
- **Frontend/Backend**: Gradio (single application, `src/apps/main_app_full.py`)
- **LLM**: Google Gemini, default `gemini-3.1-flash-lite-preview` (configurable via `GEMINI_MODEL`)
- **Agent framework**: LangChain 1.x `create_agent()` + LangGraph (with `MemorySaver` checkpointer)
- **Tools used by the agent**:
  - Postgres MCP server (`@modelcontextprotocol/server-postgres`, launched via npx subprocess)
  - Local `search_documents` tool wrapping the existing RAG pipeline
- **Vector Store**: FAISS via `langchain_community.vectorstores.FAISS`, local sentence-transformers embeddings
- **Database**: PostgreSQL (psycopg2 + SQLAlchemy)
- **Document Processing**: PDF / Word / Excel / TXT via pypdf, python-docx, openpyxl, etc.
- **Memory**: SQLite session manager (`data/storage/sessions.db`) + LangGraph in-memory checkpointer

## Component Map (`src/components/`)
- `document_processing/` — extract + chunk uploaded files
- `vector_store/` — FAISS wrapper + local embedding fallback
- `rag_engine/` — hybrid FAISS + BM25 search, Gemini synthesis
- `database/` — PostgreSQL connection, schema introspection, NL→SQL
- `mcp/` — Postgres MCP client (subprocess via stdio + langchain-mcp-adapters)
- `agent/` — LangGraph agent built with `langchain.agents.create_agent()`
- `analysis/` — Analysis tab Gradio UI
- `dashboard/` — financial contract analytics dashboard
- `memory/` — SQLite session + per-document tracking

## Commands
**IMPORTANT: Only user runs commands for starting applications and installing dependencies**
- Install: `pip install -r config/requirements.txt --upgrade`
- Start app: `python scripts/run_app.py`
- Tests: `pytest` (when present)

## Development notes
- Skills installed at `.agents/skills/`: `langchain-fundamentals`, `langgraph-fundamentals`, `langchain-rag`
- Per the `langchain-fundamentals` skill: agents MUST be built with `langchain.agents.create_agent()`. Do not use legacy `AgentExecutor` or raw `create_react_agent` patterns.
- LangGraph state is implicit (managed by `create_agent`); custom `StateGraph` only needed for non-standard control flow.
- MCP server runs as a subprocess of the Gradio process; it stays alive for the lifetime of the app.

## Development Log
All development activities are tracked in `data/logs/logs.txt`.
