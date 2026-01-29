import os
import pickle
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from langchain.schema import Document


class FAISSVectorStore:
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "storage", "faiss_db")
        self.persist_directory = persist_directory
        self.vector_store = None
        self.embeddings = None
        self.embedding_type = None

        # Initialize embeddings
        self._initialize_embeddings()

        # Load existing vector store if available
        self._load_existing_store()

    def _initialize_embeddings(self):
        """Initialize embedding model - tries sentence-transformers first, falls back to TF-IDF"""

        # Try sentence-transformers first (best accuracy)
        try:
            from sentence_transformers import SentenceTransformer
            from langchain.embeddings.base import Embeddings

            print("🔄 Initializing sentence-transformers (semantic embeddings)...")

            # Use a lightweight but accurate model
            self.st_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Create LangChain-compatible wrapper
            class SentenceTransformerEmbeddings(Embeddings):
                def __init__(self, model):
                    self.model = model

                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    embeddings = self.model.encode(texts, show_progress_bar=False)
                    return embeddings.tolist()

                def embed_query(self, text: str) -> List[float]:
                    embedding = self.model.encode([text], show_progress_bar=False)[0]
                    return embedding.tolist()

            self.embeddings = SentenceTransformerEmbeddings(self.st_model)
            self.embedding_type = "sentence-transformers"

            # Test
            test_result = self.embeddings.embed_query("test")
            print(f"✅ Sentence-transformers initialized (dim={len(test_result)})")
            print("   Model: all-MiniLM-L6-v2 (semantic search enabled)")
            return

        except Exception as e:
            print(f"⚠️ Sentence-transformers failed: {e}")
            print("   Falling back to TF-IDF...")

        # Fallback to TF-IDF
        try:
            from .local_embeddings import RobustLocalEmbeddings

            print("🔄 Initializing TF-IDF embeddings (fallback)...")
            cache_dir = os.path.join(self.persist_directory, "local_embeddings")
            self.local_embedder = RobustLocalEmbeddings(cache_dir)
            self.embeddings = self._create_local_embedding_function()
            self.embedding_type = "tfidf"

            test_result = self.embeddings.embed_query("test")
            if len(test_result) > 0:
                print(f"✅ TF-IDF embeddings initialized (dim={len(test_result)})")
                return

        except Exception as e:
            print(f"❌ All embeddings failed: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to initialize embeddings: {e}")
    
    
    
    
    def _create_local_embedding_function(self):
        """Create local embedding function compatible with FAISS"""
        from langchain.embeddings.base import Embeddings
        
        class LocalEmbeddingWrapper(Embeddings):
            def __init__(self, local_embedder):
                self.local_embedder = local_embedder
            
            def embed_documents(self, texts):
                return self.local_embedder.embed_documents(texts)
            
            def embed_query(self, text):
                return self.local_embedder.embed_query(text)
        
        return LocalEmbeddingWrapper(self.local_embedder)
    
    def _load_existing_store(self):
        """Load existing FAISS store if available"""
        faiss_path = os.path.join(self.persist_directory, "faiss_index")
        
        if os.path.exists(faiss_path + ".faiss"):
            try:
                print("🔄 Loading existing FAISS index...")
                self.vector_store = FAISS.load_local(
                    self.persist_directory, 
                    self.embeddings,
                    index_name="faiss_index",
                    allow_dangerous_deserialization=True
                )
                print(f"✅ Loaded existing vector store with {self.vector_store.index.ntotal} documents")
            except Exception as e:
                print(f"Error loading existing store: {e}")
                self.vector_store = None
    
    def add_documents_from_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add document chunks to FAISS vector store"""
        try:
            if not chunks:
                return {'stored_count': 0, 'errors': ['No chunks provided']}
            
            # Convert chunks to LangChain Document objects
            documents = []
            for chunk in chunks:
                doc = Document(
                    page_content=chunk['text'],
                    metadata={
                        'source_file': chunk['source_file'],
                        'chunk_index': chunk['chunk_index'],
                        'word_count': chunk['word_count']
                    }
                )
                documents.append(doc)
            
            # Create or update vector store
            if self.vector_store is None:
                print("🔄 Creating new FAISS vector store...")
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
            else:
                print("🔄 Adding documents to existing FAISS store...")
                new_store = FAISS.from_documents(documents, self.embeddings)
                self.vector_store.merge_from(new_store)
            
            # Save to disk
            os.makedirs(self.persist_directory, exist_ok=True)
            self.vector_store.save_local(self.persist_directory, index_name="faiss_index")
            
            return {
                'stored_count': len(chunks),
                'total_documents': self.vector_store.index.ntotal,
                'errors': []
            }
            
        except Exception as e:
            return {
                'stored_count': 0,
                'errors': [f"Error storing documents: {str(e)}"]
            }
    
    def search_similar_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using FAISS"""
        try:
            if self.vector_store is None:
                print("❌ Vector store is None - no documents loaded")
                return []
            
            print(f"🔍 Searching for: '{query}' in {self.vector_store.index.ntotal} documents")
            
            # Perform similarity search
            print(f"Attempting similarity search with query: '{query}', k={k}")
            docs_with_scores = self.vector_store.similarity_search_with_score(query, k=k)
            
            print(f"📊 Found {len(docs_with_scores)} results")
            
            results = []
            for i, (doc, score) in enumerate(docs_with_scores):
                similarity_score = float(1 / (1 + score))
                print(f"Result {i+1}: Score={similarity_score:.3f}, Source={doc.metadata.get('source_file', 'unknown')}")
                
                results.append({
                    'text': doc.page_content,
                    'metadata': doc.metadata,
                    'similarity_score': similarity_score,
                    'source_file': doc.metadata.get('source_file', 'unknown')
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching documents: {e}")
            print(f"Error type: {type(e).__name__}")
            print(f"Vector store status: {self.vector_store is not None}")
            print(f"Embeddings status: {self.embeddings is not None}")
            if self.vector_store:
                print(f"Vector store type: {type(self.vector_store)}")
                print(f"Vector store index total: {getattr(self.vector_store, 'index', {}).ntotal if hasattr(getattr(self.vector_store, 'index', {}), 'ntotal') else 'unknown'}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_store_info(self) -> Dict[str, Any]:
        """Get information about the vector store"""
        # Determine embedding model info
        if self.embedding_type == "sentence-transformers":
            embedding_info = "sentence-transformers (all-MiniLM-L6-v2) - Semantic Search"
        elif self.embedding_type == "tfidf":
            embedding_info = "TF-IDF (keyword matching)"
        else:
            embedding_info = "Unknown"

        return {
            'total_documents': self.vector_store.index.ntotal if self.vector_store else 0,
            'embedding_model': embedding_info,
            'persist_directory': self.persist_directory
        }
    
    def clear_store(self) -> bool:
        """Clear the vector store"""
        try:
            self.vector_store = None
            # Remove files
            import shutil
            if os.path.exists(self.persist_directory):
                shutil.rmtree(self.persist_directory)
            return True
        except Exception as e:
            print(f"Error clearing store: {e}")
            return False