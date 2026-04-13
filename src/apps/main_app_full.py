import os
import sys
import gradio as gr
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
import sqlite3

# ============ MONKEY-PATCH FIX FOR GRADIO_CLIENT BUG ============
# Fix for TypeError: argument of type 'bool' is not iterable
# This bug occurs in gradio_client 1.0+ when processing JSON schemas
def _patch_gradio_client():
    try:
        import gradio_client.utils as client_utils

        original_json_schema_to_python_type = client_utils._json_schema_to_python_type

        def patched_json_schema_to_python_type(schema, defs=None):
            # Handle case where schema is a boolean (True/False) instead of dict
            if isinstance(schema, bool):
                return "Any"
            if not isinstance(schema, dict):
                return "Any"
            return original_json_schema_to_python_type(schema, defs)

        client_utils._json_schema_to_python_type = patched_json_schema_to_python_type
        print("✅ Applied Gradio client patch for Python 3.9 compatibility")
    except Exception as e:
        print(f"⚠️ Could not patch gradio_client: {e}")

_patch_gradio_client()
# ============ END MONKEY-PATCH ============

# Add src to path for components
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from components.document_processing.document_processor import DocumentProcessor
from components.vector_store.faiss_store import FAISSVectorStore
from components.rag_engine.rag_processor import RAGProcessor
from components.memory.session_manager import SessionManager
from components.database.db_query_interface import DatabaseQueryInterface
from components.dashboard.contract_dashboard import ContractDashboard
from components.analysis.analysis_tab import AnalysisTab

# Load environment variables
load_dotenv()

# Configure Google AI
if os.getenv('GOOGLE_API_KEY_SOL_4'):
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))

# Global components (lazy loading)
vector_store = None
rag_processor = None
doc_processor = None
session_manager = None
db_interface = None

# Session state
current_session_id = None

def initialize_components():
    """Initialize components when first needed"""
    global vector_store, rag_processor, doc_processor, session_manager, db_interface

    if session_manager is None:
        print("🔄 Initializing session manager...")
        session_manager = SessionManager()

    if vector_store is None:
        print("🔄 Initializing vector store...")
        vector_store = FAISSVectorStore()

    if doc_processor is None:
        print("🔄 Initializing document processor...")
        doc_processor = DocumentProcessor()

    if rag_processor is None:
        print("🔄 Initializing RAG processor...")
        rag_processor = RAGProcessor(vector_store)

    if db_interface is None:
        print("🔄 Initializing database interface...")
        db_interface = DatabaseQueryInterface(session_manager)

    return vector_store, rag_processor, doc_processor, session_manager, db_interface

def get_current_session():
    """Get or create current session"""
    global current_session_id
    
    vs, rag, doc_proc, sess_mgr, db_int = initialize_components()

    if current_session_id is None:
        current_session_id = sess_mgr.create_session({
            'user_agent': 'gradio_app',
            'created_by': 'user'
        })
        print(f"🆕 Created new session: {current_session_id[:8]}...")
    
    return current_session_id

def upload_documents_with_memory(files: List[Any]) -> Tuple[str, str, str]:
    """Handle document uploads with session tracking"""
    if not files:
        return "No files selected", get_document_list(), get_session_info()
    
    # Check file limits
    MAX_FILES = 50
    MAX_SIZE_MB = 100
    
    if len(files) > MAX_FILES:
        return f"❌ Too many files! Maximum {MAX_FILES} files allowed.", get_document_list(), get_session_info()
    
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        session_id = get_current_session()
        
        # Get already processed files for this session
        session_docs = sess_mgr.get_session_documents(session_id)
        processed_filenames = {doc['filename'] for doc in session_docs}
        
        # Filter out already processed files
        new_files = []
        skipped_files = []
        
        for file in files:
            filename = os.path.basename(file)
            file_size_mb = os.path.getsize(file) / (1024 * 1024)
            
            if file_size_mb > MAX_SIZE_MB:
                skipped_files.append(f"{filename} (too large: {file_size_mb:.1f}MB)")
                continue
                
            if filename not in processed_filenames:
                new_files.append(file)
            else:
                skipped_files.append(f"{filename} (already in session)")
        
        if not new_files:
            message = "ℹ️ No new files to process"
            if skipped_files:
                message += f"\n\nSkipped files:\n" + "\n".join([f"- {f}" for f in skipped_files])
            return message, get_document_list(), get_session_info()
        
        # Process new files
        processing_results = doc_proc.process_uploaded_files(new_files)
        
        if processing_results['processed_files'] == 0:
            return f"❌ No files processed successfully\nErrors: {'; '.join(processing_results['errors'])}", get_document_list(), get_session_info()
        
        # Store in vector database
        all_chunks = []
        for doc in processing_results['documents']:
            all_chunks.extend(doc['chunks'])
            
            # Track document in session
            sess_mgr.add_document_to_session(
                session_id, 
                doc['filename'], 
                file,  # file path
                len(doc['chunks']),
                {'word_count': len(doc['content'].split())}
            )
        
        storage_results = vs.add_documents_from_chunks(all_chunks)
        
        response = f"✅ Successfully processed {processing_results['processed_files']} new files\n"
        response += f"📄 Created {processing_results['total_chunks']} text chunks\n"
        response += f"💾 Stored {storage_results['stored_count']} chunks in vector store\n"
        response += f"📊 Total documents in store: {storage_results['total_documents']}\n"
        
        if skipped_files:
            response += f"\n⏭️ Skipped files:\n" + "\n".join([f"- {f}" for f in skipped_files])
        
        return response, get_document_list(), get_session_info()
        
    except Exception as e:
        return f"❌ Error processing documents: {str(e)}", get_document_list(), get_session_info()

def rag_chat_with_memory(message: str, history: List[Dict]) -> Tuple[str, List[Dict], str]:
    """RAG chat with conversation memory - uses messages format for Gradio 6.0"""

    try:
        if not message.strip():
            return "", history, get_session_info()

        # Initialize components and session
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        session_id = get_current_session()

        # Check if any documents are loaded in this session
        session_docs = sess_mgr.get_session_documents(session_id)
        if not session_docs:
            response = "📭 No documents loaded in this session. Please upload documents in the **Contract** tab first."
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response})

            # Save to memory
            sess_mgr.add_message(session_id, 'user', message)
            sess_mgr.add_message(session_id, 'assistant', response)

            return "", history, get_session_info()

        # Get conversation context for better responses
        conversation_context = sess_mgr.get_context_for_query(session_id)

        # Enhanced query with context
        enhanced_query = message
        if conversation_context:
            enhanced_query = f"Conversation Context:\n{conversation_context}\n\nCurrent Question: {message}"

        # Process query through RAG pipeline
        result = rag.process_query(enhanced_query, use_reranking=False, final_results=8)

        # Add conversation context to response if relevant
        response = result['response']
        if conversation_context and len(history) > 0:
            response += f"\n\n*Response considers conversation context from {len(sess_mgr.get_conversation_history(session_id))} previous messages*"

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})

        # Save to memory
        sess_mgr.add_message(session_id, 'user', message, {
            'query_mode': 'document',
            'context_length': len(conversation_context) if conversation_context else 0
        })
        sess_mgr.add_message(session_id, 'assistant', response, {
            'search_results_count': result.get('search_results_count', 0),
            'context_chunks_used': result.get('final_context_count', 0)
        })

    except Exception as e:
        error_msg = f"❌ Error processing query: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})

        # Save error to memory (if session manager is available)
        try:
            vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
            session_id = get_current_session()
            sess_mgr.add_message(session_id, 'user', message)
            sess_mgr.add_message(session_id, 'assistant', error_msg, {'error': True})
        except:
            pass  # If session manager fails, just skip memory saving

    return "", history, get_session_info()

def get_document_list() -> str:
    """Get list of documents for current session"""
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        session_id = get_current_session()
        
        session_docs = sess_mgr.get_session_documents(session_id)
        
        if not session_docs:
            return "📭 No documents uploaded in this session"
        
        doc_list = f"📚 **Session Documents ({len(session_docs)} files)**\n\n"
        total_chunks = 0
        
        for i, doc in enumerate(session_docs, 1):
            upload_time = doc['upload_time'][:19]  # Remove milliseconds
            doc_list += f"{i}. **{doc['filename']}**\n"
            doc_list += f"   📅 Uploaded: {upload_time}\n"
            doc_list += f"   📄 Chunks: {doc['chunk_count']}\n\n"
            total_chunks += doc['chunk_count']
        
        doc_list += f"📊 **Total chunks in session:** {total_chunks}\n"
        
        # Add vector store info
        vs_info = vs.get_store_info()
        doc_list += f"🗃️ **Vector store total:** {vs_info['total_documents']} chunks\n"
        
        # Debug info
        if vs.vector_store:
            doc_list += f"✅ **Vector store status:** Active with {vs.vector_store.index.ntotal} documents"
        else:
            doc_list += f"❌ **Vector store status:** Not initialized"
        
        return doc_list
        
    except Exception as e:
        return f"❌ Error getting document list: {str(e)}"

def get_session_info() -> str:
    """Get current session information"""
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        session_id = get_current_session()
        
        stats = sess_mgr.get_session_stats(session_id)
        
        session_info = f"""**🔐 Current Session**

📋 **Session ID:** `{session_id[:12]}...`
📅 **Created:** {stats['created_at'][:19] if stats['created_at'] else 'Unknown'}
⏰ **Last Activity:** {stats['last_activity'][:19] if stats['last_activity'] else 'Unknown'}
💬 **Messages:** {stats['message_count']}
📄 **Documents:** {stats['document_count']} files
📊 **Chunks:** {stats['total_chunks']} total
"""
        
        return session_info
        
    except Exception as e:
        return f"❌ Error getting session info: {str(e)}"

def new_session() -> Tuple[List[Dict], str, str, str]:
    """Start a new session"""
    global current_session_id

    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        current_session_id = sess_mgr.create_session({
            'restart_reason': 'user_requested',
            'previous_session': current_session_id
        })

        return [], "🆕 New session started!", get_document_list(), get_session_info()

    except Exception as e:
        return [], f"❌ Error starting new session: {str(e)}", get_document_list(), get_session_info()

def clear_all_documents() -> Tuple[str, str, str]:
    """Clear all documents from current session"""
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        session_id = get_current_session()
        
        # Clear from vector store
        vs_success = vs.clear_store()
        
        # Clear from session tracking  
        with sqlite3.connect(sess_mgr.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM session_documents WHERE session_id = ?', (session_id,))
            conn.commit()
        
        if vs_success:
            return "✅ All documents cleared from session and vector store", get_document_list(), get_session_info()
        else:
            return "❌ Failed to clear document store", get_document_list(), get_session_info()
            
    except Exception as e:
        return f"❌ Error clearing documents: {str(e)}", get_document_list(), get_session_info()

def database_natural_query(query: str) -> Tuple[str, str]:
    """Handle natural language database queries"""
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        session_id = get_current_session()
        
        if not query.strip():
            return "Please enter a database query", ""
        
        response, sql_used = db_int.execute_natural_language_query(query, session_id)
        return response, sql_used
        
    except Exception as e:
        return f"❌ Error processing database query: {str(e)}", ""

def database_direct_sql(sql_query: str) -> Tuple[str, str]:
    """Handle direct SQL query execution"""
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        session_id = get_current_session()
        
        if not sql_query.strip():
            return "Please enter a SQL query", ""
        
        response, sql_executed = db_int.execute_direct_sql(sql_query, session_id)
        return response, sql_executed
        
    except Exception as e:
        return f"❌ Error executing SQL: {str(e)}", ""

def get_database_analysis() -> str:
    """Get database structure analysis"""
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        return db_int.format_database_overview_display()
        
    except Exception as e:
        return f"❌ Error analyzing database: {str(e)}"

def get_crud_examples() -> str:
    """Get CRUD operation examples"""
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        return db_int.get_crud_examples()
        
    except Exception as e:
        return f"❌ Error getting CRUD examples: {str(e)}"

def get_database_connection_info() -> str:
    """Get database connection information"""
    try:
        vs, rag, doc_proc, sess_mgr, db_int = initialize_components()
        return db_int.get_connection_info()
        
    except Exception as e:
        return f"❌ Error getting connection info: {str(e)}"

# Main Gradio Interface with Memory
with gr.Blocks(
    title="FBE Analytic System",
    theme=gr.themes.Default(),
    css="""
    .gradio-container {max-width: 1400px !important}
    .message-wrap {border-radius: 12px !important; margin: 8px 0px !important}
    .chat-message {padding: 12px !important}
    .primary {
        background: linear-gradient(45deg, #ff6b35, #ff8c42) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
    }
    .primary:hover {
        background: linear-gradient(45deg, #ff5722, #ff7043) !important;
        transform: translateY(-1px) !important;
    }
    .textbox textarea {
        border: 2px solid #ff8c42 !important;
        border-radius: 8px !important;
    }
    .textbox textarea:focus {
        border-color: #ff6b35 !important;
        box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1) !important;
    }
    .tab-nav button.selected {
        background: linear-gradient(45deg, #ff6b35, #ff8c42) !important;
        color: white !important;
    }
    footer {
        display: none !important;
    }
    """
) as app:
    
    # Header
    gr.Markdown("# Fee Billing Excellence Analytic System")
    gr.Markdown("**Intelligent Contract Processing and Analysis Platform**")
    
    # Document Management Tab
    with gr.Tab("📁 Documents"):
        gr.Markdown("### 📂 Document Management")
        
        with gr.Row():
            with gr.Column(scale=2):
                file_upload = gr.File(
                    label="📁 Upload Documents",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt"],
                    height=200
                )
                
                with gr.Row():
                    upload_btn = gr.Button("🔄 Process Documents", variant="primary", size="lg")
                    clear_all_btn = gr.Button("🗑️ Clear Session Documents", variant="secondary")
                
                upload_status = gr.Textbox(
                    label="📋 Upload Status",
                    lines=6,
                    interactive=False
                )
            
            with gr.Column(scale=2):
                document_list = gr.Textbox(
                    label="📚 Session Documents",
                    lines=8,
                    interactive=False,
                    value="📭 No documents uploaded yet"
                )
                
                session_info = gr.Textbox(
                    label="🔐 Session Information",
                    lines=6,
                    interactive=False
                )
                
                refresh_docs_btn = gr.Button("🔄 Refresh")
        
        # Document events
        upload_btn.click(
            fn=upload_documents_with_memory,
            inputs=[file_upload],
            outputs=[upload_status, document_list, session_info]
        )
        
        clear_all_btn.click(
            fn=clear_all_documents,
            outputs=[upload_status, document_list, session_info]
        )
        
        refresh_docs_btn.click(
            fn=lambda: ("", get_document_list(), get_session_info()),
            outputs=[upload_status, document_list, session_info]
        )
    
    # Dashboard Tab (Financial Analytics Dashboard)
    with gr.Tab("📊 Dashboard"):
        gr.Markdown("# 📊 **Financial Contract Analytics Dashboard**")
        gr.Markdown("*Real-time contract compliance monitoring with AI-powered discrepancy detection*")

        # Initialize dashboard component
        dashboard = ContractDashboard()

        # Create the 3-section dashboard interface
        dashboard.create_full_dashboard_interface()

    # Analysis Tab (LangGraph agent with MCP Postgres + RAG tools)
    with gr.Tab("🔬 Analysis"):
        vs_a, rag_a, _dp_a, sess_a, _db_a = initialize_components()
        analysis_tab = AnalysisTab(rag_processor=rag_a, session_manager=sess_a)
        analysis_tab.render()

    # Chat Interface with Memory
    with gr.Tab("💬 Smart Chat"):
        gr.Markdown("### 💬 Document Chat Assistant")
        gr.Markdown("*Ask questions about your uploaded documents*")

        # Full-width chat interface
        chatbot = gr.Chatbot(
            label="Document Chat Assistant",
            height=700,
            show_label=True
        )

        with gr.Row():
            msg = gr.Textbox(
                label="Ask about your documents...",
                placeholder="What do you want to know? (Press Enter to send)",
                scale=5,
                lines=2,
                autofocus=True
            )
            send_btn = gr.Button("📤 Send", scale=1, variant="primary", size="lg")

        with gr.Row():
            clear_chat_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
            new_session_btn = gr.Button("🆕 New Session", variant="secondary")

        # Chat events - simplified without session display
        send_btn.click(
            fn=lambda msg_input, history: rag_chat_with_memory(msg_input, history)[0:2],  # Only return msg and history
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )

        msg.submit(
            fn=lambda msg_input, history: rag_chat_with_memory(msg_input, history)[0:2],  # Only return msg and history
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )

        clear_chat_btn.click(lambda: [], outputs=[chatbot])
        new_session_btn.click(fn=lambda: ([], ""), outputs=[chatbot, upload_status])
    
    # Load initial data
    app.load(
        fn=lambda: (get_document_list(), get_session_info()),
        outputs=[document_list, session_info]
    )

if __name__ == "__main__":
    print("📋 Starting Fee Billing Excellence Analytic System...")
    print("💾 Document processing and analysis enabled")
    print("🌐 Opening browser interface...")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )