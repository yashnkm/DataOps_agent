#!/usr/bin/env python3
"""
Project Setup Script
Sets up the RAG system project with dependencies and configuration
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("📁 Virtual environment already exists")
        return True
    
    try:
        print("🔄 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False

def install_dependencies():
    """Install project dependencies"""
    requirements_path = Path("config/requirements.txt")
    
    if not requirements_path.exists():
        print(f"❌ Requirements file not found: {requirements_path}")
        return False
    
    try:
        print("📦 Installing dependencies...")
        
        # Get pip path for virtual environment
        if os.name == 'nt':  # Windows
            pip_path = "venv/Scripts/pip"
        else:  # Linux/Mac
            pip_path = "venv/bin/pip"
        
        subprocess.run([pip_path, "install", "-r", str(requirements_path)], check=True)
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_configuration():
    """Setup configuration files"""
    config_dir = Path("config")
    env_template = config_dir / ".env.template"
    env_file = config_dir / ".env"
    
    if not env_file.exists() and env_template.exists():
        print("🔧 Creating .env configuration file...")
        shutil.copy(env_template, env_file)
        print("✅ Configuration file created")
        print("⚠️ Please edit config/.env with your API keys and database settings")
        return True
    elif env_file.exists():
        print("📋 Configuration file already exists")
        return True
    else:
        print("❌ No configuration template found")
        return False

def create_data_directories():
    """Create data storage directories"""
    data_dirs = [
        "data/storage/faiss_db",
        "data/storage/chroma_db", 
        "data/uploads",
        "data/exports"
    ]
    
    for dir_path in data_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("📁 Data directories created")
    return True

def check_external_dependencies():
    """Check for external dependencies"""
    dependencies = []
    
    # Check for PostgreSQL (optional)
    try:
        subprocess.run(["psql", "--version"], capture_output=True, check=True)
        dependencies.append("✅ PostgreSQL detected")
    except (subprocess.CalledProcessError, FileNotFoundError):
        dependencies.append("⚠️ PostgreSQL not found (optional for database features)")
    
    # Check for Git
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        dependencies.append("✅ Git detected")
    except (subprocess.CalledProcessError, FileNotFoundError):
        dependencies.append("⚠️ Git not found (recommended for version control)")
    
    print("🔍 External dependencies:")
    for dep in dependencies:
        print(f"  {dep}")
    
    return True

def display_next_steps():
    """Display next steps for user"""
    print("\n🎉 Project setup completed!")
    print("\n📋 Next Steps:")
    print("1. Edit config/.env with your API keys:")
    print("   - GOOGLE_API_KEY_SOL_4=your_google_api_key")
    print("   - DB_* settings for PostgreSQL (optional)")
    print("\n2. Run the application:")
    print("   python scripts/run_app.py --app full")
    print("\n3. Or run specific versions:")
    print("   python scripts/run_app.py --app simple  # Simple version")
    print("   python scripts/run_app.py --app rag     # RAG-only version")
    print("\n4. Setup financial test database (optional):")
    print("   python database/setup/setup_financial_db.py")
    print("\n🌐 Access the app at: http://localhost:7860")

def main():
    """Main setup function"""
    print("🔍 RAG System Project Setup")
    print("=" * 40)
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    steps = [
        ("Checking Python version", check_python_version),
        ("Creating virtual environment", create_virtual_environment),
        ("Installing dependencies", install_dependencies),
        ("Setting up configuration", setup_configuration), 
        ("Creating data directories", create_data_directories),
        ("Checking external dependencies", check_external_dependencies)
    ]
    
    for desc, func in steps:
        print(f"\n🔄 {desc}...")
        if not func():
            print(f"❌ Setup failed at: {desc}")
            return False
    
    display_next_steps()
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)