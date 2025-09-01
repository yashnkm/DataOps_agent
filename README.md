# 🔍 RAG-Powered Database Query System

An intelligent document and database query system using **Gradio**, **FAISS**, **Google Gemini**, and **PostgreSQL** for natural language interaction with both documents and structured data.

## 🏗️ Architecture

- **Frontend/Backend**: Gradio (unified application)
- **AI/LLM**: Google Gemini 2.5 Flash
- **Vector Store**: FAISS with local embeddings
- **Database**: PostgreSQL with natural language SQL generation
- **Document Processing**: Multi-format support (PDF, Word, Excel, CSV, Text)
- **Memory**: Session-based conversation tracking

## 📁 Project Structure

```
├── src/
│   ├── apps/                    # Application entry points
│   │   ├── main_app_full.py    # Complete app with memory & database
│   │   ├── rag_only_app.py     # RAG-only version
│   │   ├── simple_app.py       # Basic testing app
│   │   └── app_minimal.py      # Minimal implementation
│   └── components/             # Core system components
│       ├── document_processing/ # File upload & text extraction
│       ├── vector_store/       # FAISS vector operations  
│       ├── rag_engine/         # RAG pipeline & hybrid search
│       ├── database/           # PostgreSQL integration
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

### 1. Setup Project
```bash
# Run automated setup
python scripts/setup_project.py

# Or manual setup:
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r config/requirements.txt
```

### 2. Configure Environment
```bash
# Copy and edit configuration
cp config/.env.template config/.env

# Required: Add your Google API key
GOOGLE_API_KEY_SOL_4=your_api_key_here

# Optional: Database settings for PostgreSQL features
DB_HOST=localhost
DB_NAME=financial_services_db
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. Run Application
```bash
# Full application (recommended)
python scripts/run_app.py --app full

# Or run directly:
cd src/apps && python main_app_full.py

# Other versions:
python scripts/run_app.py --app simple   # Basic version
python scripts/run_app.py --app rag      # RAG-only
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

### Hybrid Queries
- **Document + Database**: Query both sources simultaneously
- **Cross-Reference**: Combine structured and unstructured data
- **Intelligent Routing**: Auto-detect query requirements

## 💬 Example Use Cases

### Document Analysis
- "Summarize the key points from uploaded financial reports"
- "What are the risk factors mentioned in the documents?"
- "Compare Q1 and Q2 performance from the reports"

### Database Queries  
- "Show me customers with credit scores above 750"
- "What loans have payments due this week?"
- "Analyze portfolio performance by risk category"

### Hybrid Analysis
- "Compare database sales figures with projections in uploaded documents"
- "Cross-reference customer risk assessments with compliance reports"
- "Validate database portfolio values against external market reports"

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

## 📋 Available Applications

- **main_app_full.py**: Complete system with memory, database, and RAG
- **rag_only_app.py**: Document RAG with enhanced UI
- **simple_app.py**: Basic document Q&A for testing
- **app_minimal.py**: Minimal implementation

Choose the appropriate application based on your needs and available infrastructure.