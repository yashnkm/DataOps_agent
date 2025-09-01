import os
import gradio as gr
from dotenv import load_dotenv
from typing import List, Tuple, Any, Dict
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Google AI
if os.getenv('GOOGLE_API_KEY_SOL_4'):
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))

def extract_text_from_file(file_path: str) -> str:
    """Simple text extraction without heavy libraries"""
    try:
        filename = os.path.basename(file_path).lower()
        
        if filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif filename.endswith('.pdf'):
            import pypdf
            text = []
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text.append(page.extract_text())
            return '\n\n'.join(text)
        
        elif filename.endswith('.docx'):
            from docx import Document
            doc = Document(file_path)
            return '\n\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        
        else:
            return f"File type not supported yet: {filename}"
            
    except Exception as e:
        return f"Error reading file: {str(e)}"

def process_documents(files: List[Any]) -> str:
    """Process uploaded documents"""
    if not files:
        return "No files to process"
    
    results = []
    for file in files:
        try:
            filename = os.path.basename(file)
            content = extract_text_from_file(file)
            word_count = len(content.split())
            
            results.append(f"✅ **{filename}**")
            results.append(f"   📄 {word_count} words extracted")
            results.append(f"   📝 Content preview: {content[:200]}...")
            results.append("")
            
        except Exception as e:
            results.append(f"❌ **{filename}**: {str(e)}")
    
    return "\n".join(results)

def simple_ai_chat(message: str, document_content: str = "") -> str:
    """Simple AI chat using Gemini"""
    try:
        if not os.getenv('GOOGLE_API_KEY_SOL_4'):
            return "❌ Google API key not configured. Please set GOOGLE_API_KEY_SOL_4 in .env file."
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        if document_content:
            prompt = f"""Based on the following document content, answer the user's question:

Document Content:
{document_content}

User Question: {message}

Please provide a helpful answer based on the document content."""
        else:
            prompt = f"Please answer this question: {message}"
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"❌ Error generating response: {str(e)}"

# Global document storage
uploaded_documents = {}

def working_chat(message: str, history: List[Dict], files: List[Any]) -> Tuple[str, List[Dict]]:
    """Working chat with basic document processing"""
    global uploaded_documents
    
    # Handle file uploads
    if files:
        upload_response = process_documents(files)
        
        # Store document content
        for file in files:
            filename = os.path.basename(file)
            content = extract_text_from_file(file)
            uploaded_documents[filename] = content
        
        history.append({"role": "user", "content": f"Uploaded {len(files)} files"})
        history.append({"role": "assistant", "content": upload_response})
    
    if not message.strip():
        return "", history
    
    # Combine all document content for context
    all_content = "\n\n".join(uploaded_documents.values())
    
    # Generate AI response
    response = simple_ai_chat(message, all_content)
    
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    
    return "", history

def get_working_status():
    """Status for working app"""
    return f"""**Working RAG System Status**

🔑 **Google API:** {'✅ Configured' if os.getenv('GOOGLE_API_KEY_SOL_4') else '❌ Not configured'}
📁 **Documents:** {len(uploaded_documents)} files loaded
💬 **Chat:** ✅ Ready
🤖 **AI Model:** {'✅ Gemini 1.5 Flash' if os.getenv('GOOGLE_API_KEY_SOL_4') else '❌ API key needed'}

**Loaded Documents:**
{chr(10).join([f"- {name} ({len(content.split())} words)" for name, content in uploaded_documents.items()]) if uploaded_documents else "None"}
"""

def clear_documents():
    """Clear uploaded documents"""
    global uploaded_documents
    uploaded_documents = {}
    return "✅ Documents cleared"

# Working Gradio interface
with gr.Blocks(title="Working RAG System") as app:
    
    gr.Markdown("# 🚀 Working RAG System")
    gr.Markdown("Functional document Q&A without heavy vector processing")
    
    with gr.Tab("💬 Chat"):
        chatbot = gr.Chatbot(
            label="Working RAG Assistant", 
            height=400,
            type="messages"
        )
        
        with gr.Row():
            msg = gr.Textbox(label="Ask about your documents...", scale=4)
            send_btn = gr.Button("Send", scale=1, variant="primary")
        
        file_upload = gr.File(
            label="Upload Documents",
            file_count="multiple",
            file_types=[".pdf", ".docx", ".txt"]
        )
        
        with gr.Row():
            clear_chat_btn = gr.Button("Clear Chat")
            clear_docs_btn = gr.Button("Clear Documents")
        
        # Events
        send_btn.click(
            fn=working_chat,
            inputs=[msg, chatbot, file_upload],
            outputs=[msg, chatbot]
        )
        
        msg.submit(
            fn=working_chat,
            inputs=[msg, chatbot, file_upload],
            outputs=[msg, chatbot]
        )
        
        clear_chat_btn.click(lambda: [], outputs=chatbot)
        clear_docs_btn.click(fn=clear_documents, outputs=gr.Textbox(visible=False))
    
    with gr.Tab("📊 Status"):
        status_md = gr.Markdown()
        refresh_btn = gr.Button("Refresh Status")
        
        refresh_btn.click(fn=get_working_status, outputs=status_md)
        app.load(fn=get_working_status, outputs=status_md)

if __name__ == "__main__":
    print("🚀 Starting working RAG system...")
    app.launch(server_port=7864, share=False)