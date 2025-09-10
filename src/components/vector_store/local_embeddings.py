import os
import numpy as np
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import re
from collections import Counter
import math


class LocalEmbeddingFallback:
    """
    Ultra-lightweight local embedding fallback using TF-IDF and basic NLP
    No external dependencies beyond scikit-learn (already in requirements)
    """
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "storage", "local_embeddings")
        
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # TF-IDF vectorizer with optimized settings
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            stop_words='english',
            lowercase=True,
            strip_accents='ascii',
            token_pattern=r'\b\w+\b'
        )
        
        self.is_fitted = False
        self.vocabulary_cache = os.path.join(cache_dir, 'tfidf_vocab.pkl')
        
        # Load cached vocabulary if exists
        self._load_cached_vectorizer()
    
    def _preprocess_text(self, text: str) -> str:
        """Basic text preprocessing"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s.,!?-]', ' ', text)
        return text
    
    def _load_cached_vectorizer(self):
        """Load cached TF-IDF vectorizer if available"""
        if os.path.exists(self.vocabulary_cache):
            try:
                with open(self.vocabulary_cache, 'rb') as f:
                    vocab_data = pickle.load(f)
                    self.vectorizer.vocabulary_ = vocab_data['vocabulary']
                    self.vectorizer.idf_ = vocab_data['idf']
                    self.is_fitted = True
                print("✅ Loaded cached TF-IDF vocabulary")
            except Exception as e:
                print(f"⚠️  Could not load cached vocabulary: {e}")
    
    def _save_vectorizer_cache(self):
        """Save TF-IDF vectorizer vocabulary for reuse"""
        try:
            vocab_data = {
                'vocabulary': self.vectorizer.vocabulary_,
                'idf': self.vectorizer.idf_
            }
            with open(self.vocabulary_cache, 'wb') as f:
                pickle.dump(vocab_data, f)
            print("✅ Cached TF-IDF vocabulary for reuse")
        except Exception as e:
            print(f"⚠️  Could not cache vocabulary: {e}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Convert texts to embeddings using TF-IDF"""
        try:
            if not texts:
                return []
            
            # Preprocess texts
            processed_texts = [self._preprocess_text(text) for text in texts]
            
            # Fit vectorizer if not already fitted
            if not self.is_fitted:
                print("🔄 Fitting TF-IDF vectorizer on document corpus...")
                self.vectorizer.fit(processed_texts)
                self.is_fitted = True
                self._save_vectorizer_cache()
            
            # Transform texts to TF-IDF vectors
            tfidf_matrix = self.vectorizer.transform(processed_texts)
            
            # Convert sparse matrix to dense lists
            embeddings = []
            for i in range(tfidf_matrix.shape[0]):
                vector = tfidf_matrix[i].toarray()[0]
                # Normalize vector
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
                embeddings.append(vector.tolist())
            
            return embeddings
            
        except Exception as e:
            print(f"❌ Error creating TF-IDF embeddings: {e}")
            # Return zero vectors as absolute fallback
            return [[0.0] * 100 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Convert single query text to embedding"""
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else [0.0] * 100
    
    def compute_similarity(self, query_embedding: List[float], doc_embeddings: List[List[float]]) -> List[float]:
        """Compute cosine similarity between query and documents"""
        try:
            query_vec = np.array(query_embedding).reshape(1, -1)
            doc_matrix = np.array(doc_embeddings)
            
            # Compute cosine similarity
            similarities = cosine_similarity(query_vec, doc_matrix)[0]
            return similarities.tolist()
            
        except Exception as e:
            print(f"❌ Error computing similarities: {e}")
            # Return low similarities for all documents
            return [0.1] * len(doc_embeddings)


class SimpleWordEmbeddingFallback:
    """
    Even simpler word-based embedding fallback if TF-IDF fails
    Uses basic word frequency and Jaccard similarity
    """
    
    def __init__(self):
        self.dimension = 50  # Simple fixed dimension
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text"""
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if len(w) > 2]  # Filter short words
    
    def _text_to_vector(self, text: str) -> List[float]:
        """Convert text to simple word frequency vector"""
        words = self._extract_words(text)
        word_counts = Counter(words)
        
        # Create a simple hash-based vector
        vector = [0.0] * self.dimension
        for word in words:
            # Simple hash to vector position
            hash_pos = hash(word) % self.dimension
            vector[hash_pos] += 1.0
        
        # Normalize
        total = sum(vector)
        if total > 0:
            vector = [v / total for v in vector]
        
        return vector
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Convert texts to simple embeddings"""
        return [self._text_to_vector(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Convert query to simple embedding"""
        return self._text_to_vector(text)


class RobustLocalEmbeddings:
    """
    Multi-level fallback embedding system
    1. TF-IDF with scikit-learn
    2. Simple word frequency vectors
    3. Basic text similarity
    """
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir
        self.primary_embedder = None
        self.fallback_embedder = None
        self.active_method = "none"
        
        # Try to initialize primary embedder (TF-IDF)
        self._initialize_primary()
    
    def _initialize_primary(self):
        """Initialize TF-IDF embedder"""
        try:
            self.primary_embedder = LocalEmbeddingFallback(self.cache_dir)
            self.active_method = "tfidf"
            print("✅ Initialized TF-IDF local embeddings")
        except Exception as e:
            print(f"⚠️  TF-IDF initialization failed: {e}")
            self._initialize_fallback()
    
    def _initialize_fallback(self):
        """Initialize simple word embedder"""
        try:
            self.fallback_embedder = SimpleWordEmbeddingFallback()
            self.active_method = "word_freq"
            print("✅ Initialized simple word frequency embeddings")
        except Exception as e:
            print(f"❌ All embedding methods failed: {e}")
            self.active_method = "basic_similarity"
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents with fallback logic"""
        if self.active_method == "tfidf" and self.primary_embedder:
            try:
                return self.primary_embedder.embed_documents(texts)
            except Exception as e:
                print(f"TF-IDF failed, falling back: {e}")
                self._initialize_fallback()
        
        if self.active_method == "word_freq" and self.fallback_embedder:
            try:
                return self.fallback_embedder.embed_documents(texts)
            except Exception as e:
                print(f"Word frequency failed: {e}")
                self.active_method = "basic_similarity"
        
        # Ultimate fallback - return simple vectors
        print("⚠️  Using basic similarity fallback")
        return [[float(hash(text) % 100) / 100] * 10 for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query with fallback logic"""
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else [0.5] * 10
    
    def get_embedding_info(self) -> Dict[str, Any]:
        """Get info about active embedding method"""
        return {
            'method': self.active_method,
            'dimension': len(self.embed_query("test")),
            'description': {
                'tfidf': 'TF-IDF with scikit-learn (most accurate)',
                'word_freq': 'Word frequency vectors (basic)',
                'basic_similarity': 'Hash-based vectors (minimal)'
            }.get(self.active_method, 'Unknown method')
        }