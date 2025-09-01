import os
import sys
import gradio as gr
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple
import google.generativeai as genai

# Add components to path
sys.path.append('components')

from components.document_processing.document_processor import DocumentProcessor
from components.vector_store.faiss_store import FAISSVectorStore
from components.rag_engine.rag_processor import RAGProcessor

# Load environment variables
load_dotenv()

# Configure Google AI
if os.getenv('GOOGLE_API_KEY_SOL_4'):
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))

# Global components (lazy loading)
vector_store = None
rag_processor = None
doc_processor = None
processed_files = set()  # Track processed files to avoid duplicates

def initialize_components():
    """Initialize components when first needed"""
    global vector_store, rag_processor, doc_processor
    
    if vector_store is None:
        print("🔄 Initializing FAISS vector store...")
        vector_store = FAISSVectorStore()
    
    if doc_processor is None:
        print("🔄 Initializing document processor...")
        doc_processor = DocumentProcessor()
    
    if rag_processor is None:
        print("🔄 Initializing RAG processor...")
        rag_processor = RAGProcessor(vector_store)
    
    return vector_store, rag_processor, doc_processor

def upload_documents(files: List[Any]) -> Tuple[str, str]:
    """Handle document uploads in Documents tab"""
    global processed_files
    
    if not files:
        return "No files selected", get_document_list()
    
    # Check file limits
    MAX_FILES = 50
    MAX_SIZE_MB = 100
    
    if len(files) > MAX_FILES:
        return f"❌ Too many files! Maximum {MAX_FILES} files allowed.", get_document_list()
    
    try:
        vs, rag, doc_proc = initialize_components()
        
        # Filter out already processed files
        new_files = []
        skipped_files = []
        
        for file in files:
            filename = os.path.basename(file)
            file_size_mb = os.path.getsize(file) / (1024 * 1024)
            
            if file_size_mb > MAX_SIZE_MB:
                skipped_files.append(f"{filename} (too large: {file_size_mb:.1f}MB)")
                continue
                
            if filename not in processed_files:
                new_files.append(file)
            else:
                skipped_files.append(f"{filename} (already processed)")
        
        if not new_files:
            message = "ℹ️ No new files to process"
            if skipped_files:
                message += f"\n\nSkipped files:\n" + "\n".join([f"- {f}" for f in skipped_files])
            return message, get_document_list()
        
        # Process new files
        processing_results = doc_proc.process_uploaded_files(new_files)
        
        if processing_results['processed_files'] == 0:
            return f"❌ No files processed successfully\nErrors: {'; '.join(processing_results['errors'])}", get_document_list()
        
        # Store in FAISS
        all_chunks = []
        for doc in processing_results['documents']:
            all_chunks.extend(doc['chunks'])
            processed_files.add(doc['filename'])  # Track processed files
        
        storage_results = vs.add_documents_from_chunks(all_chunks)
        
        response = f"✅ Successfully processed {processing_results['processed_files']} new files\n"
        response += f"📄 Created {processing_results['total_chunks']} text chunks\n"
        response += f"💾 Stored {storage_results['stored_count']} chunks in FAISS\n"
        response += f"📊 Total documents in store: {storage_results['total_documents']}\n"
        
        if skipped_files:
            response += f"\n⏭️ Skipped files:\n" + "\n".join([f"- {f}" for f in skipped_files])
        
        return response, get_document_list()
        
    except Exception as e:
        return f"❌ Error processing documents: {str(e)}", get_document_list()

def get_document_list() -> str:
    """Get list of currently processed documents"""
    global processed_files
    
    if not processed_files:
        return "📭 No documents uploaded yet"
    
    try:
        vs, _, _ = initialize_components()
        store_info = vs.get_store_info()
        
        doc_list = f"📚 **Processed Documents ({len(processed_files)} files)**\n\n"
        for i, filename in enumerate(sorted(processed_files), 1):
            doc_list += f"{i}. {filename}\n"
        
        doc_list += f"\n📊 **Vector Store Stats:**\n"
        doc_list += f"- Total chunks: {store_info['total_documents']}\n"
        doc_list += f"- Embedding model: {store_info['embedding_model']}\n"
        
        return doc_list
        
    except Exception as e:
        return f"❌ Error getting document list: {str(e)}"

def remove_document(filename: str) -> Tuple[str, str]:
    """Remove a document from processed files (Note: FAISS doesn't support individual removal)"""
    global processed_files
    
    if filename in processed_files:
        processed_files.remove(filename)
        return f"✅ Removed {filename} from tracking (Note: Vector store requires rebuild for complete removal)", get_document_list()
    else:
        return f"❌ File {filename} not found in processed files", get_document_list()

def clear_all_documents() -> Tuple[str, str]:
    """Clear all documents"""
    global processed_files
    
    try:
        vs, _, _ = initialize_components()
        success = vs.clear_store()
        processed_files.clear()
        
        if success:
            return "✅ All documents cleared successfully", get_document_list()
        else:
            return "❌ Failed to clear document store", get_document_list()
    except Exception as e:
        return f"❌ Error clearing documents: {str(e)}", get_document_list()

def rag_chat_query(message: str, history: List[Dict]) -> Tuple[str, List[Dict]]:
    """RAG chat function - FILES HANDLED IN DOCUMENTS TAB ONLY"""
    
    try:
        if not message.strip():
            return "", history
        
        # Initialize components
        vs, rag, doc_proc = initialize_components()
        
        # Check if any documents are loaded
        if not processed_files:
            response = "📭 No documents loaded. Please upload documents in the **Documents** tab first."
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response})
            return "", history
        
        # Process query through RAG pipeline (disable reranking for now)
        result = rag.process_query(message, use_reranking=False, final_results=3)
        
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": result['response']})
        
    except Exception as e:
        error_msg = f"❌ Error processing query: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
    
    return "", history

def get_system_status():
    """Get current system status"""
    try:
        vs, rag, doc_proc = initialize_components()
        store_info = vs.get_store_info()
        
        status = f"""**🔍 FAISS RAG System Status**

🔑 **Google AI API:** {'✅ Configured' if os.getenv('GOOGLE_API_KEY_SOL_4') else '❌ Not configured'}

📊 **Vector Store (FAISS):**
- Documents: {store_info['total_documents']} chunks
- Processed Files: {len(processed_files)} files
- Embedding Model: {store_info['embedding_model']}
- Storage: {store_info['persist_directory']}

🤖 **AI Models:**
- Embeddings: ✅ Ready
- Reranker: {'✅ Loaded' if rag.reranker else '⏳ Will load on first use'}
- Response Generator: {'✅ Gemini 1.5 Flash' if os.getenv('GOOGLE_API_KEY_SOL_4') else '❌ API key needed'}

📋 **Limits:**
- Max files per upload: 50
- Max file size: 100MB each
- Supported formats: PDF, Word, Text
"""
        
        return status
        
    except Exception as e:
        return f"❌ Error getting system status: {str(e)}"

# Main Gradio Interface
with gr.Blocks(
    title="FAISS RAG System", 
    theme=gr.themes.Default(),
    css="""
    .gradio-container {max-width: 1400px !important}
    .message-wrap {border-radius: 12px !important; margin: 8px 0px !important}
    .chat-message {padding: 12px !important}
    
    /* Orange theme styling */
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
    
    /* Input styling */
    .textbox textarea {
        border: 2px solid #ff8c42 !important;
        border-radius: 8px !important;
    }
    .textbox textarea:focus {
        border-color: #ff6b35 !important;
        box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1) !important;
    }
    
    /* File upload styling */
    .file-upload {
        border: 2px dashed #ff8c42 !important; 
        border-radius: 12px !important;
        background: rgba(255, 140, 66, 0.05) !important;
    }
    
    /* Tab styling */
    .tab-nav button.selected {
        background: linear-gradient(45deg, #ff6b35, #ff8c42) !important;
        color: white !important;
    }
    
    /* Chat styling */
    .message.user {
        background: rgba(255, 140, 66, 0.1) !important;
        border-left: 4px solid #ff8c42 !important;
    }
    .message.bot {
        background: rgba(255, 107, 53, 0.05) !important;
        border-left: 4px solid #ff6b35 !important;
    }
    """
) as app:
    
    # Header
    gr.Markdown("# 🔍 FAISS-Powered RAG System")
    gr.Markdown("**Intelligent Document Q&A with Vector Search, Hybrid Indexing & Reranking**")
    
    # Documents Management Tab
    with gr.Tab("📁 Documents"):
        gr.Markdown("### 📂 Document Management")
        gr.Markdown("Upload, process, and manage your documents for RAG queries")
        
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
                    clear_all_btn = gr.Button("🗑️ Clear All Documents", variant="secondary")
                
                upload_status = gr.Textbox(
                    label="📋 Upload Status",
                    lines=8,
                    interactive=False
                )
            
            with gr.Column(scale=2):
                document_list = gr.Textbox(
                    label="📚 Current Documents",
                    lines=12,
                    interactive=False,
                    value="📭 No documents uploaded yet"
                )
                
                refresh_list_btn = gr.Button("🔄 Refresh List")
        
        gr.Markdown("""
        **📋 Upload Limits:**
        - Maximum 50 files per upload
        - Maximum 100MB per file
        - Supported: PDF, Word (.docx), Text (.txt)
        - Duplicate files are automatically skipped
        """)
        
        # Document management events
        upload_btn.click(
            fn=upload_documents,
            inputs=[file_upload],
            outputs=[upload_status, document_list]
        )
        
        clear_all_btn.click(
            fn=clear_all_documents,
            outputs=[upload_status, document_list]
        )
        
        refresh_list_btn.click(
            fn=get_document_list,
            outputs=document_list
        )
        
        # Load initial document list
        app.load(fn=get_document_list, outputs=document_list)
    
    # Chat Interface Tab (NO FILE UPLOAD HERE)
    with gr.Tab("💬 Document Chat"):
        gr.Markdown("### 💬 Ask Questions About Your Documents")
        gr.Markdown("*Upload documents in the **Documents** tab first*")
        
        chatbot = gr.Chatbot(
            label="RAG Assistant", 
            height=600,
            type="messages",
            show_label=True,
            avatar_images=["👤", "🤖"],
            bubble_full_width=False
        )
        
        with gr.Row():
            msg = gr.Textbox(
                label="Ask about your documents...",
                placeholder="What information do you need from the uploaded documents? (Press Enter to send)",
                scale=5,
                lines=2,
                autofocus=True
            )
            send_btn = gr.Button("📤 Send", scale=1, variant="primary", size="lg")
        
        with gr.Row():
            clear_chat_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
            
        # Chat events (NO FILE INPUT)
        send_btn.click(
            fn=rag_chat_query,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )
        
        msg.submit(
            fn=rag_chat_query,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )
        
        clear_chat_btn.click(lambda: [], outputs=chatbot)
    
    # System Status Tab
    with gr.Tab("📊 System Status"):
        gr.Markdown("### 📊 System Information & Health")
        
        status_display = gr.Markdown()
        
        with gr.Row():
            refresh_status_btn = gr.Button("🔄 Refresh Status", variant="primary", size="lg")
        
        refresh_status_btn.click(fn=get_system_status, outputs=status_display)
        app.load(fn=get_system_status, outputs=status_display)
    
    # Usage Guide Tab
    with gr.Tab("📖 Usage Guide"):
        gr.Markdown("""
        ## 🚀 How to Use the FAISS RAG System
        
        ### 📁 Step 1: Upload Documents
        1. Go to the **📁 Documents** tab
        2. **Select files** using the upload area (PDF, Word, Text)
        3. **Click "Process Documents"** to add them to the system
        4. **Check the document list** to confirm upload
        
        ### 💬 Step 2: Ask Questions
        1. Go to the **💬 Document Chat** tab
        2. **Type your question** about the uploaded documents
        3. **Get AI-powered answers** with source citations
        
        ### 🔍 Advanced Features
        - **Semantic Search**: Finds conceptually similar content
        - **Hybrid Search**: Combines semantic + keyword matching
        - **Reranking**: CrossEncoder improves result relevance
        - **Source Citations**: See which documents contain the answers
        
        ### 📋 Limits & Guidelines
        - **Maximum files**: 50 files per upload
        - **File size limit**: 100MB per file
        - **Supported formats**: PDF, Word (.docx), Text (.txt)
        - **Duplicate handling**: Same files are automatically skipped
        - **Persistence**: Uploaded documents remain until manually cleared
        
        ### ⚙️ Technical Details
        - **Vector Store**: FAISS for fast similarity search
        - **Embeddings**: Google API (preferred) or local HuggingFace
        - **Text Processing**: Smart chunking with overlap
        - **AI Model**: Gemini 1.5 Flash for response generation
        
        ### 🔧 Troubleshooting
        - **No AI responses**: Configure `GOOGLE_API_KEY_SOL_4` in `.env`
        - **Upload errors**: Check file format and size limits
        - **Poor answers**: Upload more relevant documents
        - **Slow responses**: Large documents may take time to process
        """)

if __name__ == "__main__":
    print("🔍 Starting FAISS-powered RAG system...")
    print("📝 Documents tab for uploads, Chat tab for queries")
    print("🌐 Opening browser interface...")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )