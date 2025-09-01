# RAG-Powered Database Query System

## Installation & Setup

### 1. Environment Setup
```bash
# Copy environment template
cp .env.template .env

# Edit .env with your credentials
nano .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Setup
Ensure PostgreSQL is running and create your database:
```sql
CREATE DATABASE rag_system;
```

### 4. Run Application
```bash
python app.py
```

## Project Structure
```
├── app.py                 # Main Gradio application
├── document_processor.py  # Document upload and text extraction
├── vector_store.py        # ChromaDB and embedding operations
├── database_manager.py    # PostgreSQL connection and SQL generation
├── rag_engine.py         # RAG pipeline with reranking
├── requirements.txt       # Python dependencies
├── .env.template         # Environment variables template
├── CLAUDE.md             # Development documentation
├── logs/
│   └── logs.txt          # Development activity log
└── chroma_db/            # ChromaDB storage (auto-created)
```

## Required Environment Variables
- `GOOGLE_API_KEY`: Google AI API key for Gemini and embeddings
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL connection details

## Features
- Multi-format document processing (PDF, Word, Excel, CSV, text)
- Semantic search with ChromaDB
- Hybrid search (semantic + keyword)
- CrossEncoder reranking
- Natural language to SQL conversion
- Interactive Gradio chat interface