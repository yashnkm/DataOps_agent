import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi
import numpy as np


class RAGProcessor:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        
        # Initialize reranking model (lazy loading)
        self.reranker = None
        
        # Configure Gemini
        if os.getenv('GOOGLE_API_KEY_SOL_4'):
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))
        
        # BM25 index for hybrid search
        self.bm25_index = None
        self.bm25_documents = []
    
    def build_bm25_index(self, documents: List[str]) -> bool:
        """Build BM25 index from document texts"""
        try:
            if not documents:
                return False
            
            # Tokenize documents for BM25
            tokenized_docs = [doc.lower().split() for doc in documents]
            self.bm25_documents = documents
            self.bm25_index = BM25Okapi(tokenized_docs)
            return True
            
        except Exception as e:
            print(f"Error building BM25 index: {e}")
            return False
    
    def hybrid_search(self, query: str, semantic_weight: float = 0.7, k: int = 10) -> List[Dict[str, Any]]:
        """Perform hybrid search combining semantic and keyword search"""
        
        # 1. Semantic search using FAISS
        semantic_results = self.vector_store.search_similar_documents(query, k=k)
        
        # 2. Build BM25 index if needed
        if not self.bm25_index and semantic_results:
            documents = [result['text'] for result in semantic_results]
            self.build_bm25_index(documents)
        
        # 3. BM25 search
        bm25_results = []
        if self.bm25_index and self.bm25_documents:
            query_tokens = query.lower().split()
            bm25_scores = self.bm25_index.get_scores(query_tokens)
            
            for i, score in enumerate(bm25_scores):
                if score > 0:
                    bm25_results.append({
                        'text': self.bm25_documents[i],
                        'bm25_score': float(score),
                        'index': i
                    })
        
        # 4. Combine results
        combined_results = self._combine_search_results(semantic_results, bm25_results, semantic_weight)
        return combined_results[:k]
    
    def _combine_search_results(self, semantic_results: List[Dict], bm25_results: List[Dict], 
                               semantic_weight: float) -> List[Dict[str, Any]]:
        """Combine semantic and BM25 search results"""
        
        text_scores = {}
        
        # Add semantic scores
        for result in semantic_results:
            text = result['text']
            text_scores[text] = {
                'semantic_score': result['similarity_score'],
                'bm25_score': 0.0,
                'metadata': result.get('metadata', {}),
                'source_file': result.get('source_file', '')
            }
        
        # Add BM25 scores
        for result in bm25_results:
            text = result['text']
            if text in text_scores:
                text_scores[text]['bm25_score'] = result['bm25_score']
        
        # Calculate combined scores
        combined_results = []
        for text, scores in text_scores.items():
            semantic_norm = scores['semantic_score']
            bm25_norm = min(scores['bm25_score'] / 10.0, 1.0)
            
            combined_score = (semantic_weight * semantic_norm) + ((1 - semantic_weight) * bm25_norm)
            
            combined_results.append({
                'text': text,
                'combined_score': combined_score,
                'semantic_score': semantic_norm,
                'bm25_score': bm25_norm,
                'metadata': scores['metadata'],
                'source_file': scores['source_file']
            })
        
        return sorted(combined_results, key=lambda x: x['combined_score'], reverse=True)
    
    def rerank_results(self, query: str, search_results: List[Dict[str, Any]], 
                      top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank search results using CrossEncoder"""
        
        if not search_results or len(search_results) <= 1:
            return search_results
        
        try:
            # Lazy load reranker
            if self.reranker is None:
                print("🔄 Loading reranking model...")
                self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            # Prepare query-document pairs
            query_doc_pairs = [(query, result['text']) for result in search_results]
            
            # Get reranking scores
            rerank_scores = self.reranker.predict(query_doc_pairs)
            
            # Add scores to results
            for i, result in enumerate(search_results):
                result['rerank_score'] = float(rerank_scores[i])
            
            # Sort and return top_k
            reranked = sorted(search_results, key=lambda x: x['rerank_score'], reverse=True)
            return reranked[:top_k]
            
        except Exception as e:
            print(f"Error during reranking: {e}")
            return search_results[:top_k]
    
    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Generate response using Gemini with retrieved context"""
        
        if not context_chunks:
            return "I couldn't find relevant information to answer your question."
        
        # Build context
        context_text = ""
        sources = set()
        
        for chunk in context_chunks:
            context_text += f"Source: {chunk['source_file']}\n{chunk['text']}\n\n"
            sources.add(chunk['source_file'])
        
        # Generate response
        try:
            if os.getenv('GOOGLE_API_KEY_SOL_4'):
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""Answer the user's question based on the provided document context.
Use only the information from the context. If the answer isn't in the context, say so clearly.
Always cite the source files.

Context:
{context_text}

User Question: {query}

Please provide a comprehensive answer based on the context above."""

                response = model.generate_content(prompt)
                source_list = "\n\n**Sources:** " + ", ".join(sources)
                return response.text + source_list
            
            else:
                return f"Context found from: {', '.join(sources)}\n\nPlease configure GOOGLE_API_KEY_SOL_4 to generate AI responses."
                
        except Exception as e:
            return f"Error generating response: {str(e)}\n\nContext available from: {', '.join(sources)}"
    
    def process_query(self, query: str, use_reranking: bool = True, 
                     search_results: int = 10, final_results: int = 5) -> Dict[str, Any]:
        """Complete RAG pipeline: search, rerank, generate response"""
        
        # 1. Perform hybrid search
        search_results_data = self.hybrid_search(query, k=search_results)
        
        if not search_results_data:
            return {
                'query': query,
                'response': "No relevant documents found. Please upload documents first.",
                'context_used': [],
                'search_results_count': 0
            }
        
        # 2. Rerank results (optional)
        if use_reranking:
            final_context = self.rerank_results(query, search_results_data, top_k=final_results)
        else:
            final_context = search_results_data[:final_results]
        
        # 3. Generate response
        response = self.generate_response(query, final_context)
        
        return {
            'query': query,
            'response': response,
            'context_used': final_context,
            'search_results_count': len(search_results_data),
            'final_context_count': len(final_context)
        }