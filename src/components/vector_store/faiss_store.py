import os
import pickle
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document


class FAISSVectorStore:
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "storage", "faiss_db")
        self.persist_directory = persist_directory
        self.vector_store = None
        self.embeddings = None
        
        # Initialize embeddings
        self._initialize_embeddings()
        
        # Load existing vector store if available
        self._load_existing_store()
    
    def _initialize_embeddings(self):
        """Initialize embedding model with multiple fallback strategies"""
        strategies = [
            self._try_sentence_transformers,
            self._try_huggingface_embeddings,
            self._try_local_embeddings_fallback
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                print(f"🔄 Trying embedding strategy {i}/{len(strategies)}...")
                if strategy():
                    return
            except Exception as e:
                print(f"Strategy {i} failed: {e}")
                continue
        
        raise RuntimeError("All embedding initialization strategies failed")
    
    def _try_sentence_transformers(self):
        """Try sentence-transformers with proper device handling"""
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            
            print("🔄 Initializing sentence-transformers...")
            
            # Force CPU usage
            device = 'cpu'
            model_name = 'all-MiniLM-L6-v2'
            
            # Initialize with explicit device
            self.embedding_model = SentenceTransformer(model_name, device=device)
            
            # Test encoding
            test_result = self.embedding_model.encode(["test"], convert_to_tensor=False)
            if len(test_result) > 0:
                self.embeddings = self._create_embedding_function()
                print("✅ Sentence-transformers initialized successfully")
                return True
            
        except Exception as e:
            print(f"Sentence-transformers failed: {e}")
            return False
    
    def _try_huggingface_embeddings(self):
        """Try HuggingFace embeddings fallback"""
        try:
            print("🔄 Trying HuggingFace embeddings...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name='all-MiniLM-L6-v2',
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'device': 'cpu', 'batch_size': 1}
            )
            # Test encoding
            test_result = self.embeddings.embed_query("test")
            if len(test_result) > 0:
                print("✅ HuggingFace embeddings initialized successfully")
                return True
                
        except Exception as e:
            print(f"HuggingFace embeddings failed: {e}")
            return False
    
    def _try_local_embeddings_fallback(self):
        """Try local embeddings fallback (no external models)"""
        try:
            from .local_embeddings import RobustLocalEmbeddings
            
            print("🔄 Initializing local embeddings fallback...")
            cache_dir = os.path.join(self.persist_directory, "local_embeddings")
            self.local_embedder = RobustLocalEmbeddings(cache_dir)
            self.embeddings = self._create_local_embedding_function()
            
            # Test encoding
            test_result = self.embeddings.embed_query("test")
            if len(test_result) > 0:
                print("✅ Local embeddings fallback initialized successfully")
                return True
                
        except Exception as e:
            print(f"Local embeddings fallback failed: {e}")
            return False
    
    def _create_embedding_function(self):
        """Create embedding function compatible with FAISS"""
        from langchain.embeddings.base import Embeddings
        
        class CustomEmbeddings(Embeddings):
            def __init__(self, model):
                self.model = model
            
            def embed_documents(self, texts):
                return self.model.encode(texts).tolist()
            
            def embed_query(self, text):
                return self.model.encode([text])[0].tolist()
        
        return CustomEmbeddings(self.embedding_model)
    
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
            return []
    
    def get_store_info(self) -> Dict[str, Any]:
        """Get information about the vector store"""
        # Determine embedding model info
        embedding_info = 'Unknown'
        if hasattr(self, 'embedding_model') and self.embedding_model:
            embedding_info = 'Sentence-Transformers'
        elif hasattr(self, 'local_embedder') and self.local_embedder:
            local_info = self.local_embedder.get_embedding_info()
            embedding_info = f"Local ({local_info['method']})"
        elif self.embeddings:
            embedding_info = 'HuggingFace'
        
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