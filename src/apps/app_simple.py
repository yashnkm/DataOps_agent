import os
import gradio as gr
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Simple initialization without heavy components
def simple_rag_chat(message, history, files):
    """Simplified chat function for debugging"""
    try:
        # Handle file uploads
        if files:
            file_response = f"Received {len(files)} files: {[os.path.basename(f) for f in files]}"
            history.append((f"Uploaded {len(files)} files", file_response))
        
        if not message.strip():
            return "", history
        
        # Simple response without AI processing
        response = f"Received query: '{message}'\nMode detection would happen here.\nAPI Key configured: {bool(os.getenv('GOOGLE_API_KEY_SOL_4'))}"
        
        history.append((message, response))
        return "", history
        
    except Exception as e:
        error_response = f"Error: {str(e)}"
        history.append((message or "Error", error_response))
        return "", history

def get_simple_status():
    """Simple status check"""
    return f"""**System Status**
    
🔑 **API Key:** {'✅ Configured' if os.getenv('GOOGLE_API_KEY_SOL_4') else '❌ Not configured'}
🗂️ **Files:** Ready for upload
💬 **Chat:** Ready
"""

# Simplified Gradio interface
with gr.Blocks(title="RAG System - Debug Version", theme=gr.themes.Soft()) as app:
    
    gr.Markdown("# 🔧 RAG System - Debug Version")
    
    with gr.Tab("💬 Chat"):
        chatbot = gr.Chatbot(label="Debug Chat", height=400)
        
        with gr.Row():
            msg = gr.Textbox(label="Message", placeholder="Test message...", scale=4)
            submit_btn = gr.Button("Send", scale=1)
        
        file_upload = gr.File(
            label="Upload Files",
            file_count="multiple",
            file_types=[".pdf", ".docx", ".txt"]
        )
        
        clear_btn = gr.Button("Clear Chat")
        
        # Event handlers
        submit_btn.click(
            fn=simple_rag_chat,
            inputs=[msg, chatbot, file_upload],
            outputs=[msg, chatbot]
        )
        
        msg.submit(
            fn=simple_rag_chat,
            inputs=[msg, chatbot, file_upload],
            outputs=[msg, chatbot]
        )
        
        clear_btn.click(lambda: [], outputs=chatbot)
    
    with gr.Tab("📊 Status"):
        status_display = gr.Markdown()
        refresh_btn = gr.Button("Refresh")
        
        refresh_btn.click(fn=get_simple_status, outputs=status_display)
        app.load(fn=get_simple_status, outputs=status_display)

if __name__ == "__main__":
    print("🔧 Starting debug app on port 7862...")
    app.launch(server_port=7862, share=False)