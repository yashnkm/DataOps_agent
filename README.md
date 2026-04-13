# 🔍 RAG-Powered Database Query System

An intelligent document and database query system using **Gradio**, **FAISS**, **Google Gemini**, and **PostgreSQL** for natural language interaction with both documents and structured data.

## 🏗️ Architecture

- **Frontend/Backend**: Gradio (unified application)
- **AI/LLM**: Google Gemini (default `gemini-3.1-flash-lite-preview`, configurable via `GEMINI_MODEL`)
- **Agent**: LangChain 1.x `create_agent()` + LangGraph (cross-source reasoning)
- **Tools**: Postgres MCP server (`@modelcontextprotocol/server-postgres`) + local RAG tool
- **Vector Store**: FAISS with local sentence-transformers embeddings
- **Database**: PostgreSQL with natural language SQL generation
- **Document Processing**: Multi-format support (PDF, Word, Excel, CSV, Text)
- **Memory**: Session-based conversation tracking + LangGraph MemorySaver checkpointer

## 📁 Project Structure

```
├── src/
│   ├── apps/                    # Application entry point
│   │   └── main_app_full.py    # Complete app with memory & database
│   └── components/             # Core system components
│       ├── document_processing/ # File upload & text extraction
│       ├── vector_store/       # FAISS vector operations
│       ├── rag_engine/         # RAG pipeline & hybrid search
│       ├── database/           # PostgreSQL integration
│       ├── mcp/                # Postgres MCP client wrapper
│       ├── agent/              # LangGraph agent (create_agent)
│       ├── analysis/           # Analysis tab UI
│       ├── dashboard/          # Financial contract dashboard
│       └── memory/             # Session management
├── database/                   # Database setup & schemas
│   ├── schemas/                # SQL schema files
│   ├── setup/                  # Database setup scripts
│   └── FINANCIAL_DB_README.md  # Database documentation
├── config/                     # Configuration files
│   ├── .env.template          # Environment template
│   └── requirements.txt       # Python dependencies
├── scripts/                    # Utility scripts
│   ├── run_app.py             # Application runner
│   └── setup_project.py       # Project setup
├── data/                       # Data storage
│   ├── storage/               # Persistent data (FAISS, sessions)
│   ├── uploads/               # Document uploads
│   ├── exports/               # Query exports
│   └── logs/                  # Application logs
├── tests/                      # Test files
├── docs/                       # Project documentation
└── venv/                       # Virtual environment
```

## 🚀 Quick Start

### 0. Prerequisites
- **Python 3.9+**
- **Node.js ≥ 18** (required by `@modelcontextprotocol/server-postgres`, launched via `npx`)
- **PostgreSQL** (running locally or remote)

### 1. Setup Project
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r config/requirements.txt
```

### 2. Configure Environment
Add to `.env` (or `config/.env`):
```env
# Required: Google AI key
GOOGLE_API_KEY_SOL_4=your_api_key_here

# PostgreSQL — for Dashboard, Smart Chat DB queries, and the MCP server
DB_HOST=localhost
DB_PORT=5432
DB_NAME=financial_services_db
DB_USER=postgres
DB_PASSWORD=your_password

# MCP server connection string (URL form of the above)
POSTGRES_CONNECTION_STRING=postgresql://postgres:your_password@localhost:5432/financial_services_db

# Gemini model for the LangGraph agent (preview model with 500 RPD free tier)
GEMINI_MODEL=gemini-3.1-flash-lite-preview
# Fallback if preview tool-calling is flaky:
# GEMINI_MODEL=gemini-2.5-flash
```

### 3. Run Application
```bash
python scripts/run_app.py

# Or run directly:
cd src/apps && python main_app_full.py
```

### 4. Setup Test Database (Optional)
```bash
# Create financial services test database
python database/setup/setup_financial_db.py
```

## 🔧 Features

### Document Processing
- **Multi-format Support**: PDF, Word, Excel, CSV, Text
- **Smart Chunking**: Overlapping text segments for better retrieval
- **Metadata Tracking**: Source file and chunk information
- **Duplicate Prevention**: Automatic file deduplication

### Vector Search & RAG
- **FAISS Vector Store**: Fast similarity search
- **Hybrid Search**: Semantic + keyword (BM25) matching
- **Reranking**: CrossEncoder for improved relevance
- **Context Generation**: AI-powered responses with source citations

### Database Integration
- **Natural Language to SQL**: Convert queries using Gemini
- **Schema Analysis**: Automatic database structure understanding
- **Safe Execution**: SQL injection protection
- **Relationship Detection**: Foreign key and table relationships

### Session Management
- **Conversation Memory**: Persistent chat history
- **Document Tracking**: Per-session file management
- **Context Aware**: Uses conversation history for better responses
- **Auto Cleanup**: Expired session management

### Cross-Source Analysis (🔬 Analysis tab)
- **LangGraph agent** with `langchain.agents.create_agent()`
- **Postgres MCP tools** — agent dynamically inspects schema and runs SELECT queries
- **RAG tool** — agent searches uploaded contracts on demand
- **Reasoning trace** — collapsible panel shows every tool call and its arguments
- **Per-session memory** via LangGraph `MemorySaver` checkpointer

## 💬 Example Use Cases

### Document Analysis
- "Summarize the key points from uploaded financial reports"
- "What are the risk factors mentioned in the documents?"
- "Compare Q1 and Q2 performance from the reports"

### Database Queries  
- "Show me customers with credit scores above 750"
- "What loans have payments due this week?"
- "Analyze portfolio performance by risk category"

### Cross-Source Analysis (Analysis tab)
- "What tables are in the database and how are they related?"
- "Show me the top 5 contracts by value and summarize their fee schedules from the uploaded PDFs"
- "Are there any transactions that don't match a contract in the database?"
- "Compare the fee schedule in the uploaded contract against actual transactions"

## 🧪 Testing

### Financial Services Test Database
Use the included financial database for comprehensive testing:
- 13 tables with realistic financial relationships
- Customer portfolios, loans, transactions, compliance data
- Complex joins and aggregations
- Time-based queries and calculations

### Test Queries
- Customer analysis and segmentation
- Portfolio performance tracking
- Loan payment status monitoring
- Risk assessment and compliance reporting

## 📖 Documentation

- `docs/context/` - Project context and requirements
- `database/FINANCIAL_DB_README.md` - Database schema documentation
- `data/logs/logs.txt` - Development activity log
- `CLAUDE.md` - Project instructions and function specifications

## 🛠️ Development

### Adding New Features
1. Create components in `src/components/`
2. Update imports in application files
3. Test with simple app before full integration
4. Update documentation

### Directory Conventions
- **src/apps/**: Application entry points
- **src/components/**: Reusable system components  
- **database/**: All database-related files
- **config/**: Configuration and dependencies
- **scripts/**: Utility and setup scripts
- **data/**: Persistent data and logs
- **tests/**: Test files and test data
- **docs/**: Documentation and context

