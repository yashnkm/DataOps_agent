import os
import gradio as gr
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def simple_chat(message, history):
    """Simple test function"""
    try:
        if not message.strip():
            return history
        
        response = f"Echo: {message}"
        history.append((message, response))
        return history
        
    except Exception as e:
        error_response = f"Error: {str(e)}"
        history.append((message, error_response))
        return history

def test_imports():
    """Test if all imports work"""
    try:
        import chromadb
        import google.generativeai as genai
        import sentence_transformers
        return "✅ All imports successful"
    except Exception as e:
        return f"❌ Import error: {str(e)}"

# Simple Gradio interface for testing
with gr.Blocks(title="Test RAG System") as app:
    gr.Markdown("# Test Interface")
    
    with gr.Tab("Chat Test"):
        chatbot = gr.Chatbot(label="Test Chat", height=400)
        msg = gr.Textbox(label="Message", placeholder="Type a test message...")
        
        msg.submit(fn=simple_chat, inputs=[msg, chatbot], outputs=chatbot)
    
    with gr.Tab("Import Test"):
        test_btn = gr.Button("Test Imports")
        result_text = gr.Textbox(label="Import Test Results")
        
        test_btn.click(fn=test_imports, outputs=result_text)

if __name__ == "__main__":
    print("🧪 Starting test app...")
    app.launch(server_port=7861, share=False)