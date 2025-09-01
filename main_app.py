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

def process_documents_and_store(files: List[Any]) -> str:
    """Process documents and store in FAISS"""
    try:
        vs, rag, doc_proc = initialize_components()
        
        # Process files
        processing_results = doc_proc.process_uploaded_files(files)
        
        if processing_results['processed_files'] == 0:
            return f"❌ No files processed successfully\nErrors: {'; '.join(processing_results['errors'])}"
        
        # Store in FAISS
        all_chunks = []
        for doc in processing_results['documents']:
            all_chunks.extend(doc['chunks'])
        
        storage_results = vs.add_documents_from_chunks(all_chunks)
        
        if storage_results['stored_count'] > 0:
            response = f"✅ Successfully processed {processing_results['processed_files']} files\n"
            response += f"📄 Created {processing_results['total_chunks']} text chunks\n"
            response += f"💾 Stored {storage_results['stored_count']} chunks in FAISS\n"
            response += f"📊 Total documents in store: {storage_results['total_documents']}"
        else:
            response = f"❌ Failed to store documents\nErrors: {'; '.join(storage_results['errors'])}"
        
        return response
        
    except Exception as e:
        return f"❌ Error processing documents: {str(e)}"

def rag_chat_query(message: str, history: List[Dict], files: List[Any]) -> Tuple[str, List[Dict]]:
    """Main RAG chat function"""
    
    try:
        # Handle file uploads first
        if files:
            upload_response = process_documents_and_store(files)
            history.append({"role": "user", "content": f"Uploaded {len(files)} files"})
            history.append({"role": "assistant", "content": upload_response})
        
        if not message.strip():
            return "", history
        
        # Initialize components
        vs, rag, doc_proc = initialize_components()
        
        # Process query through RAG pipeline
        result = rag.process_query(message, use_reranking=True, final_results=3)
        
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
- Embedding Model: {store_info['embedding_model']}
- Storage: {store_info['persist_directory']}

🤖 **AI Models:**
- Embeddings: ✅ Ready
- Reranker: {'✅ Loaded' if rag.reranker else '⏳ Will load on first use'}
- Response Generator: {'✅ Gemini 1.5 Flash' if os.getenv('GOOGLE_API_KEY_SOL_4') else '❌ API key needed'}

💬 **Features:**
- Document Upload: ✅ PDF, Word, Text
- Semantic Search: ✅ FAISS-powered
- Hybrid Search: ✅ Semantic + Keyword
- Reranking: ✅ CrossEncoder
"""
        
        return status
        
    except Exception as e:
        return f"❌ Error getting system status: {str(e)}"

def clear_vector_store():
    """Clear all documents from vector store"""
    try:
        vs, _, _ = initialize_components()
        success = vs.clear_store()
        if success:
            return "✅ Vector store cleared successfully"
        else:
            return "❌ Failed to clear vector store"
    except Exception as e:
        return f"❌ Error clearing vector store: {str(e)}"

# Main Gradio Interface
with gr.Blocks(
    title="FAISS RAG System", 
    theme=gr.themes.Soft(),
    css=".gradio-container {max-width: 1200px !important}"
) as app:
    
    # Header
    with gr.Row():
        gr.Markdown("# 🔍 FAISS-Powered RAG System")
    
    with gr.Row():
        gr.Markdown("**Intelligent Document Q&A with Vector Search, Hybrid Indexing & Reranking**")
    
    # Main interface
    with gr.Tab("💬 Document Chat"):
        
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="RAG Assistant", 
                    height=500,
                    type="messages",
                    show_label=True,
                    avatar_images=["👤", "🤖"]
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Ask about your documents...",
                        placeholder="What information do you need from the uploaded documents?",
                        scale=4,
                        lines=2
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary")
            
            with gr.Column(scale=1):
                file_upload = gr.File(
                    label="📁 Upload Documents",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt"],
                    height=200
                )
                
                with gr.Row():
                    clear_chat_btn = gr.Button("Clear Chat", variant="secondary")
                    clear_docs_btn = gr.Button("Clear Documents", variant="secondary")
        
        # Event handlers
        send_btn.click(
            fn=rag_chat_query,
            inputs=[msg, chatbot, file_upload],
            outputs=[msg, chatbot]
        )
        
        msg.submit(
            fn=rag_chat_query,
            inputs=[msg, chatbot, file_upload],
            outputs=[msg, chatbot]
        )
        
        clear_chat_btn.click(lambda: [], outputs=chatbot)
        clear_docs_btn.click(fn=clear_vector_store, outputs=gr.Textbox(visible=False))
    
    with gr.Tab("📊 System Status"):
        status_display = gr.Markdown()
        
        with gr.Row():
            refresh_status_btn = gr.Button("🔄 Refresh Status", variant="primary")
        
        refresh_status_btn.click(fn=get_system_status, outputs=status_display)
        app.load(fn=get_system_status, outputs=status_display)
    
    with gr.Tab("📖 Usage Guide"):
        gr.Markdown("""
        ## 🚀 How to Use the FAISS RAG System
        
        ### 📁 Document Upload
        1. **Upload documents** using the file upload area (supports PDF, Word, Text files)
        2. **Wait for processing** - files are chunked and indexed automatically
        3. **Confirmation** - you'll see processing results in the chat
        
        ### 💬 Asking Questions
        - **Simple queries**: "What are the main points in the document?"
        - **Specific searches**: "Find information about project timelines"
        - **Comparative analysis**: "Compare the recommendations in different sections"
        
        ### 🔍 How It Works
        - **FAISS Vector Search**: Fast semantic similarity matching
        - **Hybrid Search**: Combines semantic + keyword search
        - **Reranking**: CrossEncoder model improves result relevance
        - **AI Response**: Gemini generates answers with source citations
        
        ### ⚙️ Technical Features
        - **Embeddings**: Google API (if configured) or local HuggingFace models
        - **Vector Store**: FAISS for efficient similarity search
        - **Chunking**: Smart text segmentation with overlap
        - **Persistence**: Vector store saved locally for reuse
        
        ### 🔧 Setup Requirements
        1. **Google API Key**: Set `GOOGLE_API_KEY_SOL_4` in `.env` file
        2. **Dependencies**: Run `pip install -r requirements.txt`
        3. **Documents**: Upload your documents to start querying
        """)

if __name__ == "__main__":
    print("🔍 Starting FAISS-powered RAG system...")
    print("📝 Make sure GOOGLE_API_KEY_SOL_4 is configured in .env!")
    print("🌐 Opening browser interface...")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )