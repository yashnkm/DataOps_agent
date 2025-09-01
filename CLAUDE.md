# RAG-Powered Database Query System with Gradio

## Project Overview
Building an intelligent document and database query system using Gradio as the complete frontend and backend framework. The system enables natural language interaction with both document repositories and PostgreSQL databases.

## Architecture
- **Frontend & Backend**: Gradio (single application)
- **AI/LLM**: Google Gemini 2.5 Flash
- **Vector Store**: ChromaDB with embeddings
- **Database**: PostgreSQL
- **Document Processing**: Multiple format support (PDF, Word, Excel, etc.)

## Core Functions to Implement

### 1. Document Processing Functions
- `upload_and_process_documents()` - Handle file uploads and extract text
- `create_embeddings()` - Generate vector embeddings for document chunks
- `store_in_chromadb()` - Store vectors in ChromaDB collection

### 2. Database Functions  
- `connect_to_postgres()` - Database connection management
- `generate_sql_query()` - Convert natural language to SQL using Gemini
- `execute_database_query()` - Run SQL queries safely

### 3. RAG Functions
- `semantic_search()` - Query ChromaDB for relevant document chunks
- `rerank_results()` - Use CrossEncoder for result reranking
- `generate_response()` - Combine context with Gemini for final answer

### 4. Hybrid Query Functions
- `detect_query_mode()` - Determine if query needs docs, DB, or both
- `process_hybrid_query()` - Handle complex queries using multiple data sources
- `extract_and_insert_data()` - Auto-extract document data into database

## Development Approach
Building functions incrementally, testing each component before integration into the Gradio interface.

## Commands
**IMPORTANT: Only user will run commands for starting applications and installing dependencies**
- Testing: `pytest` (when test files exist)
- Linting: `ruff check .` (if ruff is used)
- Type checking: `mypy .` (if mypy is configured)
- Installation: User handles `pip install -r requirements.txt`
- Starting: User runs the Gradio application

## Development Log
All development activities are tracked in `logs/logs.txt`