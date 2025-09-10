#!/usr/bin/env python3
"""
Test script for the embedding fallback system
Tests all fallback levels to ensure robustness
"""

import os
import sys
import traceback

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_local_embeddings():
    """Test the local embedding fallback system"""
    print("🧪 Testing Local Embedding Fallback System")
    print("=" * 50)
    
    try:
        from components.vector_store.local_embeddings import RobustLocalEmbeddings
        
        # Initialize local embedder
        print("\n1️⃣ Testing RobustLocalEmbeddings initialization...")
        embedder = RobustLocalEmbeddings()
        print(f"✅ Initialized with method: {embedder.active_method}")
        
        # Test document embedding
        print("\n2️⃣ Testing document embedding...")
        test_docs = [
            "This is a test document about artificial intelligence and machine learning.",
            "Another document discussing natural language processing and text analysis.",
            "A third document covering database queries and SQL operations."
        ]
        
        embeddings = embedder.embed_documents(test_docs)
        print(f"✅ Created embeddings for {len(embeddings)} documents")
        print(f"   Embedding dimension: {len(embeddings[0]) if embeddings else 0}")
        
        # Test query embedding
        print("\n3️⃣ Testing query embedding...")
        query = "What is machine learning?"
        query_embedding = embedder.embed_query(query)
        print(f"✅ Created query embedding with dimension: {len(query_embedding)}")
        
        # Test embedding info
        print("\n4️⃣ Testing embedding info...")
        info = embedder.get_embedding_info()
        print(f"✅ Method: {info['method']}")
        print(f"   Description: {info['description']}")
        print(f"   Dimension: {info['dimension']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Local embeddings test failed: {e}")
        traceback.print_exc()
        return False

def test_faiss_store_fallback():
    """Test the FAISS store with fallback system"""
    print("\n🧪 Testing FAISS Store with Fallback")
    print("=" * 50)
    
    try:
        from components.vector_store.faiss_store import FAISSVectorStore
        
        # Initialize FAISS store (should use fallback if other methods fail)
        print("\n1️⃣ Testing FAISS store initialization with fallback...")
        
        # Temporarily disable other embedding methods to force fallback
        original_google_key = os.environ.get('GOOGLE_API_KEY_SOL_4')
        if original_google_key:
            os.environ.pop('GOOGLE_API_KEY_SOL_4', None)
        
        store = FAISSVectorStore(persist_directory="./test_faiss_fallback")
        print(f"✅ FAISS store initialized")
        
        # Check store info
        info = store.get_store_info()
        print(f"   Embedding source: {info.get('embedding_source', 'unknown')}")
        print(f"   Embedding model: {info.get('embedding_model', 'unknown')}")
        
        # Test adding documents
        print("\n2️⃣ Testing document addition...")
        test_chunks = [
            {
                'text': "This is a test document about machine learning and AI technologies.",
                'source_file': "test1.txt",
                'chunk_index': 0,
                'word_count': 12
            },
            {
                'text': "Another test document discussing database operations and SQL queries.",
                'source_file': "test2.txt", 
                'chunk_index': 0,
                'word_count': 10
            }
        ]
        
        result = store.add_documents_from_chunks(test_chunks)
        print(f"✅ Added {result['stored_count']} documents")
        print(f"   Total documents in store: {result['total_documents']}")
        
        # Test search
        print("\n3️⃣ Testing document search...")
        results = store.search_similar_documents("machine learning", k=2)
        print(f"✅ Found {len(results)} search results")
        
        for i, result in enumerate(results):
            print(f"   Result {i+1}: Score={result['similarity_score']:.3f}, Source={result['source_file']}")
        
        # Restore Google API key if it existed
        if original_google_key:
            os.environ['GOOGLE_API_KEY_SOL_4'] = original_google_key
        
        # Clean up test directory
        store.clear_store()
        
        return True
        
    except Exception as e:
        print(f"❌ FAISS fallback test failed: {e}")
        traceback.print_exc()
        return False

def test_extreme_fallback():
    """Test the most basic fallback when everything else fails"""
    print("\n🧪 Testing Extreme Fallback Scenario")
    print("=" * 50)
    
    try:
        from components.vector_store.local_embeddings import SimpleWordEmbeddingFallback
        
        # Test simple word embedder
        print("\n1️⃣ Testing SimpleWordEmbeddingFallback...")
        embedder = SimpleWordEmbeddingFallback()
        
        test_texts = ["hello world", "machine learning", "database query"]
        embeddings = embedder.embed_documents(test_texts)
        
        print(f"✅ Created {len(embeddings)} embeddings")
        print(f"   Embedding dimension: {len(embeddings[0])}")
        
        # Test query
        query_emb = embedder.embed_query("test query")
        print(f"✅ Query embedding dimension: {len(query_emb)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Extreme fallback test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all fallback tests"""
    print("🚀 Starting Embedding Fallback System Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Local embeddings
    results.append(test_local_embeddings())
    
    # Test 2: FAISS store fallback
    results.append(test_faiss_store_fallback())
    
    # Test 3: Extreme fallback
    results.append(test_extreme_fallback())
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All fallback tests passed! The system is robust.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit(main())