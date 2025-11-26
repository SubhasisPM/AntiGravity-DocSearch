"""
Advanced Retrieval Module for RAG Pipeline

Features:
- Hybrid search (dense vector + sparse BM25)
- MMR (Maximal Marginal Relevance) for diversity
- Semantic re-ranking
- Metadata filtering
- Result deduplication
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from rank_bm25 import BM25Okapi

logging.basicConfig(level=logging.INFO)


@dataclass
class RetrievalConfig:
    """Configuration for retrieval strategies"""
    vector_weight: float = 0.7
    bm25_weight: float = 0.3
    mmr_lambda: float = 0.5  # Balance between relevance and diversity
    top_k: int = 20
    rerank_top_k: int = 10
    enable_mmr: bool = True
    enable_rerank: bool = False


class AdvancedRetriever:
    """
    Advanced retrieval system with hybrid search and diversity optimization
    
    Combines:
    1. Dense vector search (ChromaDB)
    2. Sparse BM25 search  
    3. MMR for result diversity
    4. Semantic re-ranking
    5. Metadata filtering
    """
    
    def __init__(self, vector_db, config: Optional[RetrievalConfig] = None):
        """
        Initialize advanced retriever
        
        Args:
            vector_db: VectorMemory instance
            config: Retrieval configuration
        """
        self.vector_db = vector_db
        self.config = config or RetrievalConfig()
        self.bm25_index = None
        self.bm25_corpus = []
        self.corpus_metadata = []
        
        logging.info("Advanced Retriever initialized")
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Index documents for BM25 sparse retrieval
        
        Args:
            documents: List of documents with 'content' and 'metadata'
        """
        self.bm25_corpus = []
        self.corpus_metadata = []
        
        for doc in documents:
            # Tokenize for BM25
            tokens = self._tokenize(doc.get('content', ''))
            self.bm25_corpus.append(tokens)
            self.corpus_metadata.append(doc.get('metadata', {}))
        
        # Build BM25 index
        if self.bm25_corpus:
            self.bm25_index = BM25Okapi(self.bm25_corpus)
            logging.info(f"BM25 index built with {len(self.bm25_corpus)} documents")
    
    def hybrid_search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense and sparse retrieval
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"doc_id": "doc_1"})
            
        Returns:
            List of ranked documents with scores
        """
        top_k = top_k or self.config.top_k
        
        # Dense retrieval (vector search)
        dense_results = self._dense_search(query, top_k * 2)
        
        # Sparse retrieval (BM25)
        sparse_results = self._sparse_search(query, top_k * 2)
        
        # Combine and normalize scores
        combined_results = self._combine_results(
            dense_results, 
            sparse_results,
            self.config.vector_weight,
            self.config.bm25_weight
        )
        
        # Apply metadata filters if provided
        if filters:
            combined_results = self._apply_filters(combined_results, filters)
        
        # Apply MMR for diversity
        if self.config.enable_mmr:
            combined_results = self.mmr_rerank(
                query,
                combined_results,
                lambda_param=self.config.mmr_lambda,
                top_k=top_k
            )
        else:
            combined_results = combined_results[:top_k]
        
        logging.info(f"Hybrid search returned {len(combined_results)} results")
        return combined_results
    
    def mmr_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        lambda_param: float = 0.5,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Maximal Marginal Relevance (MMR) re-ranking
        
        Balances relevance and diversity by penalizing similar documents
        
        Args:
            query: Search query
            documents: Retrieved documents
            lambda_param: Trade-off between relevance (1.0) and diversity (0.0)
            top_k: Number of results to return
            
        Returns:
            Re-ranked documents with diversity
        """
        if not documents or len(documents) <= 1:
            return documents[:top_k]
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Get document embeddings
        doc_embeddings = [self._get_embedding(doc['content']) for doc in documents]
        
        # MMR algorithm
        selected_indices = []
        remaining_indices = list(range(len(documents)))
        
        # First selection: most relevant document
        relevance_scores = [
            self._cosine_similarity(query_embedding, doc_emb) 
            for doc_emb in doc_embeddings
        ]
        first_idx = np.argmax(relevance_scores)
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)
        
        # Iteratively select documents
        while len(selected_indices) < top_k and remaining_indices:
            mmr_scores = []
            
            for idx in remaining_indices:
                # Relevance to query
                relevance = relevance_scores[idx]
                
                # Maximum similarity to already selected documents
                max_similarity = max(
                    self._cosine_similarity(doc_embeddings[idx], doc_embeddings[sel_idx])
                    for sel_idx in selected_indices
                )
                
                # MMR score: balance relevance and diversity
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                mmr_scores.append((idx, mmr_score))
            
            # Select document with highest MMR score
            best_idx, _ = max(mmr_scores, key=lambda x: x[1])
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
        
        # Return documents in MMR order
        mmr_results = [documents[idx] for idx in selected_indices]
        logging.info(f"MMR re-ranking: {len(documents)} -> {len(mmr_results)} results")
        return mmr_results
    
    def semantic_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic re-ranking using cross-encoder (placeholder for future enhancement)
        
        Args:
            query: Search query
            documents: Retrieved documents
            top_k: Number of results to return
            
        Returns:
            Re-ranked documents
        """
        top_k = top_k or self.config.rerank_top_k
        
        # TODO: Implement cross-encoder re-ranking
        # For now, return top-k by existing scores
        
        logging.info(f"Semantic re-ranking (placeholder): {len(documents)} -> {top_k} results")
        return documents[:top_k]
    
    def filtered_search(
        self,
        query: str,
        filters: Dict[str, Any],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search with metadata filtering
        
        Args:
            query: Search query
            filters: Metadata filters (e.g., {"doc_id": "doc_1", "has_table": True})
            top_k: Number of results to return
            
        Returns:
            Filtered search results
        """
        return self.hybrid_search(query, top_k=top_k, filters=filters)
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _dense_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Dense vector search using ChromaDB"""
        try:
            results = self.vector_db.search(query, n_results=top_k)
            
            # Normalize to common format
            normalized = []
            for result in results:
                normalized.append({
                    'id': result.get('id'),
                    'content': result.get('content', ''),
                    'metadata': result.get('metadata', {}),
                    'score': 1.0 - result.get('distance', 0.0),  # Convert distance to similarity
                    'source': 'dense'
                })
            
            return normalized
        except Exception as e:
            logging.error(f"Dense search error: {e}")
            return []
    
    def _sparse_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Sparse BM25 search"""
        if not self.bm25_index:
            logging.warning("BM25 index not built, skipping sparse search")
            return []
        
        try:
            # Tokenize query
            query_tokens = self._tokenize(query)
            
            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top-k indices
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            # Format results
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include non-zero scores
                    results.append({
                        'id': f'bm25_{idx}',
                        'content': ' '.join(self.bm25_corpus[idx]),
                        'metadata': self.corpus_metadata[idx] if idx < len(self.corpus_metadata) else {},
                        'score': float(scores[idx]),
                        'source': 'sparse'
                    })
            
            return results
        except Exception as e:
            logging.error(f"Sparse search error: {e}")
            return []
    
    def _combine_results(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict],
        dense_weight: float,
        sparse_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Combine dense and sparse results with weighted scores
        
        Uses Reciprocal Rank Fusion (RRF) for robust combination
        """
        # Build unified result dictionary
        combined = {}
        
        # Add dense results
        for rank, result in enumerate(dense_results, 1):
            doc_id = result['id']
            rrf_score = dense_weight / (60 + rank)  # RRF with k=60
            
            if doc_id not in combined:
                combined[doc_id] = result.copy()
                combined[doc_id]['combined_score'] = rrf_score
            else:
                combined[doc_id]['combined_score'] += rrf_score
        
        # Add sparse results
        for rank, result in enumerate(sparse_results, 1):
            doc_id = result['id']
            rrf_score = sparse_weight / (60 + rank)
            
            if doc_id not in combined:
                combined[doc_id] = result.copy()
                combined[doc_id]['combined_score'] = rrf_score
            else:
                combined[doc_id]['combined_score'] += rrf_score
        
        # Sort by combined score
        results = sorted(combined.values(), key=lambda x: x['combined_score'], reverse=True)
        
        return results
    
    def _apply_filters(
        self,
        results: List[Dict],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply metadata filters to results"""
        filtered = []
        
        for result in results:
            metadata = result.get('metadata', {})
            match = True
            
            for key, value in filters.items():
                if metadata.get(key) != value:
                    match = False
                    break
            
            if match:
                filtered.append(result)
        
        return filtered
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25"""
        return text.lower().split()
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text (uses vector DB's embedding function)"""
        try:
            # Use the vector DB's embedding function
            if hasattr(self.vector_db, 'embedding_fn'):
                embedding = self.vector_db.embedding_fn([text])[0]
                return np.array(embedding)
            else:
                # Fallback: use random embedding (for testing)
                return np.random.randn(384)
        except Exception as e:
            logging.error(f"Embedding error: {e}")
            return np.random.randn(384)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logging.error(f"Cosine similarity error: {e}")
            return 0.0


# ============================================================================
# Convenience Functions
# ============================================================================

def create_retriever(vector_db, config: Optional[RetrievalConfig] = None) -> AdvancedRetriever:
    """
    Create advanced retriever instance
    
    Args:
        vector_db: VectorMemory instance
        config: Optional retrieval configuration
        
    Returns:
        AdvancedRetriever instance
    """
    return AdvancedRetriever(vector_db, config)


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Advanced Retrieval Module - Testing")
    print("=" * 80)
    
    # Mock vector DB for testing
    class MockVectorDB:
        def search(self, query, n_results=5):
            return [
                {
                    'id': 'doc1',
                    'content': 'Machine learning is a subset of artificial intelligence.',
                    'metadata': {'doc_id': 'doc1', 'page': 1},
                    'distance': 0.2
                },
                {
                    'id': 'doc2',
                    'content': 'Deep learning uses neural networks with multiple layers.',
                    'metadata': {'doc_id': 'doc2', 'page': 5},
                    'distance': 0.3
                },
                {
                    'id': 'doc3',
                    'content': 'Natural language processing enables computers to understand text.',
                    'metadata': {'doc_id': 'doc3', 'page': 10},
                    'distance': 0.4
                }
            ]
    
    # Create retriever
    vector_db = MockVectorDB()
    config = RetrievalConfig(
        vector_weight=0.7,
        bm25_weight=0.3,
        mmr_lambda=0.5,
        enable_mmr=True
    )
    
    retriever = create_retriever(vector_db, config)
    
    # Test hybrid search
    query = "What is machine learning?"
    results = retriever.hybrid_search(query, top_k=5)
    
    print(f"\nQuery: {query}")
    print(f"\nResults: {len(results)}")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result.get('combined_score', result.get('score', 0)):.4f}")
        print(f"   Content: {result['content'][:100]}...")
        print(f"   Source: {result.get('source', 'unknown')}")
    
    print("\n" + "=" * 80)
    print("Test completed successfully")
    print("=" * 80)
