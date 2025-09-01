#!/usr/bin/env python3
"""
Application Runner Script
Convenient script to run different versions of the RAG application
"""

import os
import sys
import argparse
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def run_app(app_type="full", port=7860, host="0.0.0.0", share=False):
    """Run the specified application"""
    
    app_files = {
        "full": "main_app_full.py",
        "simple": "simple_app.py", 
        "rag": "rag_only_app.py",
        "minimal": "app_minimal.py"
    }
    
    if app_type not in app_files:
        print(f"❌ Unknown app type: {app_type}")
        print(f"Available options: {', '.join(app_files.keys())}")
        return False
    
    app_file = app_files[app_type]
    app_path = project_root / "src" / "apps" / app_file
    
    if not app_path.exists():
        print(f"❌ App file not found: {app_path}")
        return False
    
    print(f"🚀 Starting {app_type} RAG application...")
    print(f"📁 App: {app_file}")
    print(f"🌐 URL: http://{host}:{port}")
    print("🔄 Loading components...")
    
    # Change to project root for relative paths
    os.chdir(project_root)
    
    # Set environment variables for the app
    os.environ["GRADIO_SERVER_NAME"] = host
    os.environ["GRADIO_SERVER_PORT"] = str(port)
    
    # Import and run the app
    try:
        # Add apps directory to path
        apps_path = project_root / "src" / "apps"
        sys.path.insert(0, str(apps_path))
        
        # Import the app module
        module_name = app_file[:-3]  # Remove .py extension
        app_module = __import__(module_name)
        
        print("✅ Application started successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run RAG Application")
    parser.add_argument(
        "--app", 
        choices=["full", "simple", "rag", "minimal"],
        default="full",
        help="Application type to run (default: full)"
    )
    parser.add_argument("--port", type=int, default=7860, help="Port number (default: 7860)")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--share", action="store_true", help="Create public Gradio link")
    
    args = parser.parse_args()
    
    print("🔍 RAG System Application Runner")
    print("=" * 40)
    
    success = run_app(args.app, args.port, args.host, args.share)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()