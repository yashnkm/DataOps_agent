import os
import gradio as gr
from dotenv import load_dotenv
from typing import List, Tuple, Any, Dict
import tempfile
from pathlib import Path

# Load environment variables
load_dotenv()

def simple_file_processing(files: List[Any]) -> str:
    """Simple file processing without AI models"""
    if not files:
        return "No files uploaded"
    
    results = []
    for file in files:
        try:
            filename = os.path.basename(file)
            file_size = os.path.getsize(file)
            results.append(f"✅ {filename} ({file_size} bytes)")
        except Exception as e:
            results.append(f"❌ Error: {str(e)}")
    
    return "\n".join(results)

def simple_chat(message: str, history: List[Dict], files: List[Any]) -> Tuple[str, List[Dict]]:
    """Simple chat without AI processing"""
    
    # Handle file uploads
    if files:
        upload_response = simple_file_processing(files)
        history.append({"role": "user", "content": f"Uploaded {len(files)} files"})
        history.append({"role": "assistant", "content": upload_response})
    
    if not message.strip():
        return "", history
    
    # Simple response
    response = f"Received: '{message}'\n\nDocument RAG processing would happen here.\nAPI Key: {'✅' if os.getenv('GOOGLE_API_KEY_SOL_4') else '❌'}"
    
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    return "", history

def get_status():
    """Simple status"""
    return f"""**Minimal RAG System**

🔑 **API Key:** {'✅ Configured' if os.getenv('GOOGLE_API_KEY_SOL_4') else '❌ Not configured'}
📁 **File Upload:** ✅ Ready
💬 **Chat:** ✅ Ready
🤖 **AI Models:** ⏸️ Disabled for testing
"""

# Minimal Gradio interface
with gr.Blocks(title="Minimal RAG System") as app:
    
    gr.Markdown("# 🔧 Minimal RAG System")
    gr.Markdown("Testing without heavy AI model loading")
    
    with gr.Tab("💬 Chat"):
        chatbot = gr.Chatbot(
            label="Minimal Chat", 
            height=400,
            type="messages"
        )
        
        with gr.Row():
            msg = gr.Textbox(label="Message", scale=4)
            send_btn = gr.Button("Send", scale=1)
        
        file_upload = gr.File(
            label="Upload Files",
            file_count="multiple"
        )
        
        clear_btn = gr.Button("Clear")
        
        # Events
        send_btn.click(
            fn=simple_chat,
            inputs=[msg, chatbot, file_upload],
            outputs=[msg, chatbot]
        )
        
        msg.submit(
            fn=simple_chat,
            inputs=[msg, chatbot, file_upload],
            outputs=[msg, chatbot]
        )
        
        clear_btn.click(lambda: [], outputs=chatbot)
    
    with gr.Tab("📊 Status"):
        status_md = gr.Markdown()
        refresh_btn = gr.Button("Refresh")
        
        refresh_btn.click(fn=get_status, outputs=status_md)
        app.load(fn=get_status, outputs=status_md)

if __name__ == "__main__":
    print("🔧 Starting minimal RAG system...")
    app.launch(server_port=7863, share=False)