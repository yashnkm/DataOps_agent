#!/usr/bin/env python3
"""
Fix vector store issues and load contract documents
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from components.document_processing.document_processor import DocumentProcessor
from components.vector_store.faiss_store import FAISSVectorStore


def check_vector_store_directory():
    """Check if vector store directory exists"""
    base_dir = Path(__file__).parent.parent
    vector_dir = base_dir / "data" / "storage" / "faiss_db"
    
    print(f"🔍 Checking vector store directory: {vector_dir}")
    
    if not vector_dir.exists():
        print("📁 Creating vector store directory...")
        vector_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {vector_dir}")
    else:
        print(f"✅ Directory exists: {vector_dir}")
        # List contents
        files = list(vector_dir.glob("*"))
        if files:
            print(f"📄 Found {len(files)} files:")
            for file in files:
                print(f"   - {file.name}")
        else:
            print("📄 Directory is empty")
    
    return vector_dir


def test_vector_store_creation():
    """Test creating a new vector store"""
    print("\n🧪 Testing vector store creation...")
    
    try:
        # Force a specific directory for testing
        test_dir = Path(__file__).parent.parent / "data" / "storage" / "faiss_test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🔄 Creating FAISS vector store in {test_dir}")
        vector_store = FAISSVectorStore(persist_directory=str(test_dir))
        
        # Check store info
        try:
            info = vector_store.get_store_info()
            print(f"✅ Vector store created successfully")
            print(f"   Documents: {info.get('total_documents', 0)}")
            print(f"   Embedding: {info.get('embedding_source', 'unknown')}")
        except Exception as e:
            print(f"⚠️  Error getting store info: {e}")
        
        return vector_store
        
    except Exception as e:
        print(f"❌ Vector store creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_contract_documents(vector_store):
    """Load contract documents into vector store"""
    print("\n📄 Loading contract documents...")
    
    try:
        doc_processor = DocumentProcessor()
        contracts_dir = Path(__file__).parent.parent / "data" / "contracts"
        
        if not contracts_dir.exists():
            print(f"❌ Contracts directory not found: {contracts_dir}")
            return False
        
        contract_files = list(contracts_dir.glob("*.txt"))
        print(f"📑 Found {len(contract_files)} contract files")
        
        if not contract_files:
            print("❌ No contract files found")
            return False
        
        # Process each contract file
        all_chunks = []
        for contract_file in contract_files:
            print(f"🔄 Processing {contract_file.name}...")
            
            try:
                # Read file content
                with open(contract_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Create chunks using document processor
                chunks = doc_processor._chunk_text(
                    content, 
                    str(contract_file), 
                    chunk_size=500, 
                    overlap=50
                )
                
                all_chunks.extend(chunks)
                print(f"   ✅ Created {len(chunks)} chunks")
                
            except Exception as e:
                print(f"   ❌ Error processing {contract_file.name}: {e}")
        
        if not all_chunks:
            print("❌ No chunks created from contract files")
            return False
        
        # Store in vector database
        print(f"💾 Storing {len(all_chunks)} chunks in vector store...")
        storage_result = vector_store.add_documents_from_chunks(all_chunks)
        
        if storage_result.get('stored_count', 0) > 0:
            print(f"✅ Successfully stored {storage_result['stored_count']} chunks")
            print(f"📊 Total documents: {storage_result.get('total_documents', 0)}")
            return True
        else:
            print(f"❌ Failed to store documents")
            print(f"   Errors: {storage_result.get('errors', [])}")
            return False
            
    except Exception as e:
        print(f"❌ Error loading documents: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_document_search(vector_store):
    """Test searching documents in vector store"""
    print("\n🔍 Testing document search...")
    
    try:
        test_queries = [
            "DBS Bank fees",
            "VISA participation agreement",
            "transaction processing fees"
        ]
        
        for query in test_queries:
            print(f"🔎 Searching for: '{query}'")
            results = vector_store.search_similar_documents(query, k=2)
            
            if results:
                print(f"   ✅ Found {len(results)} results")
                for i, result in enumerate(results):
                    print(f"   {i+1}. Score: {result.get('similarity_score', 0):.3f}")
                    print(f"      Source: {result.get('source_file', 'unknown')}")
            else:
                print(f"   ❌ No results found")
        
        return True
        
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False


def cleanup_and_move_to_main():
    """Move test vector store to main location"""
    print("\n🔄 Setting up main vector store...")
    
    try:
        test_dir = Path(__file__).parent.parent / "data" / "storage" / "faiss_test"
        main_dir = Path(__file__).parent.parent / "data" / "storage" / "faiss_db"
        
        if test_dir.exists():
            # Remove old main directory
            if main_dir.exists():
                import shutil
                shutil.rmtree(main_dir)
            
            # Move test to main
            test_dir.rename(main_dir)
            print(f"✅ Moved vector store to main location: {main_dir}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error setting up main vector store: {e}")
        return False


def main():
    """Main function to fix vector store issues"""
    print("🔧 Vector Store Diagnostic & Fix Tool")
    print("=" * 50)
    
    results = []
    
    # Step 1: Check directories
    print("1️⃣ Checking directories...")
    vector_dir = check_vector_store_directory()
    results.append(("Directory Check", True))
    
    # Step 2: Test vector store creation
    print("\n2️⃣ Testing vector store creation...")
    vector_store = test_vector_store_creation()
    results.append(("Vector Store Creation", vector_store is not None))
    
    if not vector_store:
        print("❌ Cannot continue without working vector store")
        return 1
    
    # Step 3: Load documents
    print("\n3️⃣ Loading contract documents...")
    docs_loaded = load_contract_documents(vector_store)
    results.append(("Document Loading", docs_loaded))
    
    if not docs_loaded:
        print("⚠️  Documents not loaded, but vector store works")
    
    # Step 4: Test search
    print("\n4️⃣ Testing document search...")
    search_works = test_document_search(vector_store)
    results.append(("Document Search", search_works))
    
    # Step 5: Move to main location
    print("\n5️⃣ Setting up main vector store...")
    main_setup = cleanup_and_move_to_main()
    results.append(("Main Setup", main_setup))
    
    # Summary
    print(f"\n📋 Summary")
    print("=" * 20)
    
    for step, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {step}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nResult: {passed}/{total} steps completed")
    
    if passed >= 3:  # Vector store creation + at least 2 other steps
        print("\n🎉 Vector store should now work!")
        print("   Try running your main application again.")
        return 0
    else:
        print("\n⚠️  Some issues remain. Check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())