"""
RAG Metrics Module for Evaluation and Monitoring

Provides comprehensive metrics for:
- Retrieval quality (Recall@K, Precision@K, NDCG, MRR)
- Answer quality (relevance, faithfulness, coverage)
- System performance (latency, token usage, cache hits)
- Logging and tracing
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from collections import defaultdict

logging.basicConfig(level=logging.INFO)


@dataclass
class RetrievalMetrics:
    """Retrieval quality metrics"""
    recall_at_k: float = 0.0
    precision_at_k: float = 0.0
    ndcg_at_k: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    num_retrieved: int = 0
    num_relevant: int = 0


@dataclass
class AnswerMetrics:
    """Answer quality metrics"""
    relevance_score: float = 0.0  # How relevant is the answer to query
    faithfulness_score: float = 0.0  # Is answer grounded in context
    context_precision: float = 0.0  # How much context is used
    context_recall: float = 0.0  # Is all needed context retrieved


@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    query_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    generation_latency_ms: float = 0.0
    total_tokens_used: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class QueryLog:
    """Log entry for a single query"""
    query_id: str
    query: str
    timestamp: str
    num_results: int
    answer: str
    confidence: float
    retrieval_metrics: RetrievalMetrics
    answer_metrics: AnswerMetrics
    performance_metrics: PerformanceMetrics
    sources: List[Dict] = field(default_factory=list)


class RAGMetricsCalculator:
    """
    Calculate various metrics for RAG system evaluation
    """
    
    @staticmethod
    def recall_at_k(
        relevant_doc_ids: List[str],
        retrieved_doc_ids: List[str],
        k: int
    ) -> float:
        """
        Calculate Recall@K
        
        Recall@K = (Number of relevant items in top-K) / (Total number of relevant items)
        
        Args:
            relevant_doc_ids: List of known relevant document IDs
            retrieved_doc_ids: List of retrieved document IDs (ranked)
            k: Number of top results to consider
            
        Returns:
            Recall@K score (0.0 to 1.0)
        """
        if not relevant_doc_ids:
            return 0.0
        
        top_k = set(retrieved_doc_ids[:k])
        relevant_set = set(relevant_doc_ids)
        
        relevant_in_top_k = len(top_k & relevant_set)
        
        return relevant_in_top_k / len(relevant_set)
    
    @staticmethod
    def precision_at_k(
        relevant_doc_ids: List[str],
        retrieved_doc_ids: List[str],
        k: int
    ) -> float:
        """
        Calculate Precision@K
        
        Precision@K = (Number of relevant items in top-K) / K
        
        Args:
            relevant_doc_ids: List of known relevant document IDs
            retrieved_doc_ids: List of retrieved document IDs (ranked)
            k: Number of top results to consider
            
        Returns:
            Precision@K score (0.0 to 1.0)
        """
        if k == 0:
            return 0.0
        
        top_k = retrieved_doc_ids[:k]
        relevant_set = set(relevant_doc_ids)
        
        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant_set)
        
        return relevant_in_top_k / k
    
    @staticmethod
    def ndcg_at_k(
        relevant_doc_ids: List[str],
        retrieved_doc_ids: List[str],
        k: int,
        relevance_scores: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG@K)
        
        NDCG measures ranking quality considering position of relevant items
        
        Args:
            relevant_doc_ids: List of relevant document IDs
            retrieved_doc_ids: List of retrieved document IDs (ranked)
            k: Number of top results to consider
            relevance_scores: Optional dict mapping doc_id to relevance score (0-1)
                            If None, binary relevance is used (1 or 0)
            
        Returns:
            NDCG@K score (0.0 to 1.0)
        """
        if not relevant_doc_ids or k == 0:
            return 0.0
        
        # Binary relevance if scores not provided
        if relevance_scores is None:
            relevance_scores = {doc_id: 1.0 for doc_id in relevant_doc_ids}
        
        # DCG: Discounted Cumulative Gain
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_doc_ids[:k], 1):
            relevance = relevance_scores.get(doc_id, 0.0)
            # DCG formula: rel_i / log2(i + 1)
            dcg += relevance / np.log2(i + 1)
        
        # IDCG: Ideal DCG (if all relevant docs were at top)
        ideal_relevance = sorted(
            [relevance_scores.get(doc_id, 0.0) for doc_id in relevant_doc_ids],
            reverse=True
        )[:k]
        
        idcg = 0.0
        for i, relevance in enumerate(ideal_relevance, 1):
            idcg += relevance / np.log2(i + 1)
        
        # NDCG = DCG / IDCG
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def mean_reciprocal_rank(
        relevant_doc_ids: List[str],
        retrieved_doc_ids: List[str]
    ) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR)
        
        MRR = 1 / rank_of_first_relevant_item
        
        Args:
            relevant_doc_ids: List of relevant document IDs
            retrieved_doc_ids: List of retrieved document IDs (ranked)
            
        Returns:
            MRR score (0.0 to 1.0)
        """
        relevant_set = set(relevant_doc_ids)
        
        for rank, doc_id in enumerate(retrieved_doc_ids, 1):
            if doc_id in relevant_set:
                return 1.0 / rank
        
        return 0.0
    
    @staticmethod
    def answer_relevance(query: str, answer: str) -> float:
        """
        Calculate answer relevance to query (simplified version)
        
        In production, this would use a trained model or LLM evaluation
        
        Args:
            query: User query
            answer: Generated answer
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        # Simple keyword overlap (placeholder)
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        
        if not query_words:
            return 0.0
        
        # Jaccard similarity
        intersection = len(query_words & answer_words)
        union = len(query_words | answer_words)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def faithfulness_score(answer: str, context: str) -> float:
        """
        Calculate faithfulness (is answer grounded in context)
        
        In production, use NLI models or LLM-based evaluation
        
        Args:
            answer: Generated answer
            context: Source context
            
        Returns:
            Faithfulness score (0.0 to 1.0)
        """
        # Simple approach: check if answer statements appear in context
        answer_sentences = [s.strip() for s in answer.split('.') if s.strip()]
        
        if not answer_sentences:
            return 1.0
        
        context_lower = context.lower()
        grounded_count = 0
        
        for sentence in answer_sentences:
            # Check if key words from sentence appear in context
            words = set(sentence.lower().split())
            # Remove very common words
            words = {w for w in words if len(w) > 3}
            
            if words:
                # Calculate overlap
                context_words = set(context_lower.split())
                overlap = len(words & context_words) / len(words)
                
                if overlap > 0.5:  # At least 50% of words found
                    grounded_count += 1
        
        return grounded_count / len(answer_sentences)
    
    @staticmethod
    def context_precision(context: str, answer: str) -> float:
        """
        Calculate context precision (how much of context is used in answer)
        
        Args:
            context: Retrieved context
            answer: Generated answer
            
        Returns:
            Context precision score (0.0 to 1.0)
        """
        # Split into sentences
        context_sentences = [s.strip() for s in context.split('.') if s.strip()]
        answer_lower = answer.lower()
        
        if not context_sentences:
            return 0.0
        
        used_count = 0
        for sentence in context_sentences:
            # Check if sentence information appears in answer
            words = set(sentence.lower().split())
            words = {w for w in words if len(w) > 3}
            
            if words:
                # Check overlap with answer
                answer_words = set(answer_lower.split())
                overlap = len(words & answer_words) / len(words)
                
                if overlap > 0.3:  # At least 30% used
                    used_count += 1
        
        return used_count / len(context_sentences)


class RAGTracer:
    """
    Logging and tracing for RAG system
    """
    
    def __init__(self):
        """Initialize tracer"""
        self.query_logs: List[QueryLog] = []
        self.performance_stats = defaultdict(list)
        self.cache_stats = {'hits': 0, 'misses': 0}
        
        logging.info("RAG Tracer initialized")
    
    def log_query(
        self,
        query_id: str,
        query: str,
        answer: str,
        confidence: float,
        sources: List[Dict],
        retrieval_metrics: Optional[RetrievalMetrics] = None,
        answer_metrics: Optional[AnswerMetrics] = None,
        performance_metrics: Optional[PerformanceMetrics] = None
    ) -> None:
        """
        Log a complete query transaction
        
        Args:
            query_id: Unique query identifier
            query: User query
            answer: Generated answer
            confidence: Confidence score
            sources: Retrieved sources
            retrieval_metrics: Retrieval metrics
            answer_metrics: Answer quality metrics
            performance_metrics: Performance metrics
        """
        log_entry = QueryLog(
            query_id=query_id,
            query=query,
            timestamp=datetime.now().isoformat(),
            num_results=len(sources),
            answer=answer,
            confidence=confidence,
            retrieval_metrics=retrieval_metrics or RetrievalMetrics(),
            answer_metrics=answer_metrics or AnswerMetrics(),
            performance_metrics=performance_metrics or PerformanceMetrics(),
            sources=sources
        )
        
        self.query_logs.append(log_entry)
        
        # Update performance stats
        if performance_metrics:
            self.performance_stats['query_latency'].append(performance_metrics.query_latency_ms)
            self.performance_stats['retrieval_latency'].append(performance_metrics.retrieval_latency_ms)
            self.performance_stats['generation_latency'].append(performance_metrics.generation_latency_ms)
            self.performance_stats['tokens_used'].append(performance_metrics.total_tokens_used)
    
    def log_cache_hit(self) -> None:
        """Log a cache hit"""
        self.cache_stats['hits'] += 1
    
    def log_cache_miss(self) -> None:
        """Log a cache miss"""
        self.cache_stats['misses'] += 1
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_stats['hits'] + self.cache_stats['misses']
        return self.cache_stats['hits'] / total if total > 0 else 0.0
    
    def get_average_latency(self) -> Dict[str, float]:
        """Get average latencies"""
        return {
            'query': np.mean(self.performance_stats['query_latency']) if self.performance_stats['query_latency'] else 0.0,
            'retrieval': np.mean(self.performance_stats['retrieval_latency']) if self.performance_stats['retrieval_latency'] else 0.0,
            'generation': np.mean(self.performance_stats['generation_latency']) if self.performance_stats['generation_latency'] else 0.0
        }
    
    def get_token_usage_stats(self) -> Dict[str, Any]:
        """Get token usage statistics"""
        tokens = self.performance_stats['tokens_used']
        if not tokens:
            return {'total': 0, 'average': 0, 'max': 0}
        
        return {
            'total': sum(tokens),
            'average': np.mean(tokens),
            'max': max(tokens)
        }
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics
        
        Returns:
            Dictionary with all metrics
        """
        return {
            'total_queries': len(self.query_logs),
            'cache_hit_rate': self.get_cache_hit_rate(),
            'average_latency': self.get_average_latency(),
            'token_usage': self.get_token_usage_stats(),
            'average_confidence': np.mean([log.confidence for log in self.query_logs]) if self.query_logs else 0.0,
            'average_num_sources': np.mean([log.num_results for log in self.query_logs]) if self.query_logs else 0.0
        }
    
    def get_recent_queries(self, n: int = 10) -> List[QueryLog]:
        """Get N most recent queries"""
        return self.query_logs[-n:]


# Global tracer instance
_tracer = None

def get_tracer() -> RAGTracer:
    """Get or create global tracer instance"""
    global _tracer
    if _tracer is None:
        _tracer = RAGTracer()
    return _tracer


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("RAG Metrics Module - Testing")
    print("=" * 80)
    
    calc = RAGMetricsCalculator()
    
    # Test retrieval metrics
    relevant_docs = ['doc1', 'doc3', 'doc5']
    retrieved_docs = ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']
    
    print("\nRetrieval Metrics Test:")
    print(f"Relevant docs: {relevant_docs}")
    print(f"Retrieved docs: {retrieved_docs}")
    
    recall = calc.recall_at_k(relevant_docs, retrieved_docs, k=5)
    precision = calc.precision_at_k(relevant_docs, retrieved_docs, k=5)
    ndcg = calc.ndcg_at_k(relevant_docs, retrieved_docs, k=5)
    mrr = calc.mean_reciprocal_rank(relevant_docs, retrieved_docs)
    
    print(f"\nRecall@5: {recall:.3f}")
    print(f"Precision@5: {precision:.3f}")
    print(f"NDCG@5: {ndcg:.3f}")
    print(f"MRR: {mrr:.3f}")
    
    # Test answer metrics
    query = "What is machine learning?"
    answer = "Machine learning is a type of artificial intelligence that enables systems to learn from data."
    context = "Machine learning is a subset of artificial intelligence (AI) that provides systems the ability to automatically learn and improve from experience without being explicitly programmed. Machine learning focuses on the development of computer programs that can access data and use it to learn for themselves."
    
    print("\n\nAnswer Metrics Test:")
    print(f"Query: {query}")
    print(f"Answer: {answer}")
    
    relevance = calc.answer_relevance(query, answer)
    faithfulness = calc.faithfulness_score(answer, context)
    precision = calc.context_precision(context, answer)
    
    print(f"\nRelevance: {relevance:.3f}")
    print(f"Faithfulness: {faithfulness:.3f}")
    print(f"Context Precision: {precision:.3f}")
    
    # Test tracer
    print("\n\nTracer Test:")
    tracer = get_tracer()
    
    # Log some queries
    for i in range(5):
        tracer.log_query(
            query_id=f"q{i}",
            query=f"Test query {i}",
            answer=f"Test answer {i}",
            confidence=0.7 + i * 0.05,
            sources=[],
            performance_metrics=PerformanceMetrics(
                query_latency_ms=100 + i * 10,
                retrieval_latency_ms=50 + i * 5,
                generation_latency_ms=50 + i * 5,
                total_tokens_used=100 + i * 20
            )
        )
        
        # Simulate cache hits/misses
        if i % 2 == 0:
            tracer.log_cache_hit()
        else:
            tracer.log_cache_miss()
    
    metrics = tracer.export_metrics()
    print(f"\nTotal queries: {metrics['total_queries']}")
    print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")
    print(f"Average latency: {metrics['average_latency']}")
    print(f"Token usage: {metrics['token_usage']}")
    
    print("\n" + "=" * 80)
    print("Test completed successfully")
    print("=" * 80)
