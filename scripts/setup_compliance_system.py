#!/usr/bin/env python3
"""
Complete setup script for Contract Compliance system
Sets up database, loads contracts, and generates test data
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from components.database.db_analyzer import DatabaseAnalyzer
from components.document_processing.document_processor import DocumentProcessor
from components.vector_store.faiss_store import FAISSVectorStore


def setup_database():
    """Setup database tables and initial data"""
    print("🗄️  Setting up database...")
    
    try:
        db_analyzer = DatabaseAnalyzer()
        
        if db_analyzer.connection_status != "connected":
            print("❌ Database connection failed. Check your database configuration.")
            return False
        
        # Load schema
        schema_file = Path(__file__).parent.parent / "database" / "schemas" / "contract_compliance_schema.sql"
        
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        print("📋 Creating database tables...")
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        result = db_analyzer.execute_query(schema_sql)
        if not result['success']:
            print(f"❌ Database setup failed: {result.get('error', 'Unknown error')}")
            return False
        
        print("✅ Database tables created successfully")
        
        # Verify tables were created
        verify_query = """
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('contracts', 'fees', 'transactions', 'discrepancies')
        """
        
        result = db_analyzer.execute_query(verify_query)
        if result['success']:
            tables = [row['table_name'] for row in result['data']]
            print(f"📊 Created tables: {', '.join(tables)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False


def load_contracts_to_rag():
    """Load contract documents into RAG system"""
    print("📄 Loading contract documents into RAG system...")
    
    try:
        # Initialize components
        doc_processor = DocumentProcessor()
        vector_store = FAISSVectorStore()
        
        # Find contract files
        contracts_dir = Path(__file__).parent.parent / "data" / "contracts"
        contract_files = list(contracts_dir.glob("*.txt"))
        
        if not contract_files:
            print(f"⚠️  No contract files found in {contracts_dir}")
            return False
        
        print(f"📑 Found {len(contract_files)} contract files:")
        for file in contract_files:
            print(f"   - {file.name}")
        
        # Process contracts
        all_chunks = []
        for contract_file in contract_files:
            print(f"🔄 Processing {contract_file.name}...")
            
            # Read file content
            with open(contract_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create file-like object for processor
            file_info = {
                'name': contract_file.name,
                'content': content,
                'size': len(content)
            }
            
            # Process document
            chunks = doc_processor._chunk_text(
                content, 
                str(contract_file), 
                chunk_size=500, 
                overlap=50
            )
            
            all_chunks.extend(chunks)
            print(f"   ✅ Created {len(chunks)} chunks from {contract_file.name}")
        
        # Store in vector database
        print(f"💾 Storing {len(all_chunks)} chunks in vector store...")
        storage_result = vector_store.add_documents_from_chunks(all_chunks)
        
        if storage_result['stored_count'] > 0:
            print(f"✅ Successfully stored {storage_result['stored_count']} contract chunks")
            print(f"📊 Total documents in vector store: {storage_result['total_documents']}")
            return True
        else:
            print("❌ Failed to store contract documents")
            return False
        
    except Exception as e:
        print(f"❌ Contract loading error: {e}")
        return False


def generate_test_transactions():
    """Generate initial test transaction data"""
    print("💳 Generating test transaction data...")
    
    try:
        # Import and run transaction generator
        from generate_transaction_data import TransactionGenerator
        
        generator = TransactionGenerator()
        
        # Generate batch of test transactions
        print("🔄 Creating 100 test transactions with discrepancies...")
        transactions = generator.generate_batch_transactions(100)
        
        if transactions:
            summary = generator.get_transaction_summary()
            print(f"✅ Generated {len(transactions)} test transactions")
            print(f"📊 Summary:")
            print(f"   Total transactions: {summary.get('total_transactions', 0)}")
            print(f"   Average amount: ${summary.get('avg_amount', 0):.2f}")
            print(f"   Total fees: ${summary.get('total_fees', 0):.2f}")
            return True
        else:
            print("❌ Failed to generate test transactions")
            return False
            
    except Exception as e:
        print(f"❌ Transaction generation error: {e}")
        return False


def verify_system():
    """Verify the complete system is working"""
    print("🔍 Verifying system setup...")
    
    try:
        db_analyzer = DatabaseAnalyzer()
        
        # Check database tables
        table_counts = {}
        tables = ['contracts', 'fees', 'transactions', 'discrepancies']
        
        for table in tables:
            query = f"SELECT COUNT(*) as count FROM {table}"
            result = db_analyzer.execute_query(query)
            if result['success']:
                table_counts[table] = result['data'][0]['count']
            else:
                table_counts[table] = 0
        
        print("📊 Database verification:")
        for table, count in table_counts.items():
            print(f"   {table}: {count} records")
        
        # Check vector store
        try:
            vector_store = FAISSVectorStore()
            store_info = vector_store.get_store_info()
            print(f"🔍 Vector store: {store_info['total_documents']} documents")
            print(f"   Embedding method: {store_info['embedding_model']}")
        except Exception as e:
            print(f"⚠️  Vector store verification failed: {e}")
        
        # Basic system health check
        required_data = {
            'contracts': table_counts.get('contracts', 0) >= 3,
            'fees': table_counts.get('fees', 0) >= 10,
            'transactions': table_counts.get('transactions', 0) >= 50,
        }
        
        all_good = all(required_data.values())
        
        if all_good:
            print("✅ System verification passed!")
            print("🚀 Contract Compliance system is ready to use")
        else:
            print("⚠️  System verification found issues:")
            for component, status in required_data.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {component}")
        
        return all_good
        
    except Exception as e:
        print(f"❌ System verification error: {e}")
        return False


def main():
    """Main setup function"""
    print("🔧 Contract Compliance System Setup")
    print("=" * 50)
    
    steps = [
        ("Database Setup", setup_database),
        ("Contract Loading", load_contracts_to_rag),
        ("Test Data Generation", generate_test_transactions),
        ("System Verification", verify_system)
    ]
    
    results = []
    
    for step_name, step_function in steps:
        print(f"\n{step_name}:")
        print("-" * (len(step_name) + 1))
        
        try:
            success = step_function()
            results.append((step_name, success))
            
            if success:
                print(f"✅ {step_name} completed successfully")
            else:
                print(f"❌ {step_name} failed")
                
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
            results.append((step_name, False))
    
    # Final summary
    print("\n📋 Setup Summary")
    print("=" * 20)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for step_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {step_name}")
    
    print(f"\nResult: {passed}/{total} steps completed successfully")
    
    if passed == total:
        print("\n🎉 Setup complete! You can now:")
        print("   1. Run the main application: python src/apps/main_app_full.py")
        print("   2. Open the 'Contract Compliance' tab")
        print("   3. Upload contract documents and monitor transactions")
        print("   4. Generate more test data: python scripts/generate_transaction_data.py --batch 50")
    else:
        print("\n⚠️  Setup incomplete. Please check the failed steps above.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())