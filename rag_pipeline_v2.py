"""
Enhanced RAG Pipeline v2.0
Integrates advanced retrieval, multi-granularity chunking, and comprehensive metrics
"""

import logging
import time
import uuid
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)


@dataclass
class RAGResponse:
    """RAG system response"""
    answer: str
    sources: List[Dict]
    confidence: Dict[str, float]  # Multi-faceted confidence
    query: str
    context_used: str
    query_id: str
    latency_ms: float


class EnhancedRAGPipeline:
    """
    Enhanced RAG Pipeline with:
    - Advanced hybrid retrieval (dense + sparse + MMR)
    - Multi-granularity document processing
    - Comprehensive metrics and monitoring
    - Streaming response support
    """
    
    def __init__(
        self,
        vector_db,
        llm_provider: str = "mock",
        llm_api_key: Optional[str] = None,
        use_advanced_retrieval: bool = True,
        use_query_expansion: bool = True,
        use_relevance_filter: bool = True,
        use_synthesis: bool = True,
        use_metrics: bool = True
    ):
        """
        Initialize enhanced RAG pipeline
        
        Args:
            vector_db: VectorMemory instance
            llm_provider: "openai", "gemini", "ollama", or "mock"
            llm_api_key: API key for cloud LLMs
            use_advanced_retrieval: Enable advanced retrieval with MMR
            use_query_expansion: Enable Antigravity-Expand
            use_relevance_filter: Enable Antigravity-Filter
            use_synthesis: Enable Antigravity-Synthesize
            use_metrics: Enable metrics tracking
        """
        self.vector_db = vector_db
        
        # Initialize LLM
        from rag_llm import create_llm
        self.llm = create_llm(provider=llm_provider, api_key=llm_api_key)
        
        # Initialize advanced retriever
        self.advanced_retriever = None
        if use_advanced_retrieval:
            try:
                from advanced_retrieval import create_retriever, RetrievalConfig
                config = RetrievalConfig(
                    vector_weight=0.7,
                    bm25_weight=0.3,
                    mmr_lambda=0.5,
                    enable_mmr=True
                )
                self.advanced_retriever = create_retriever(vector_db, config)
                logging.info("✓ Advanced Retrieval enabled (Hybrid + MMR)")
            except ImportError as e:
                logging.warning(f"Advanced Retrieval not available: {e}")
        
        # Load optional components
        self.query_expander = None
        self.relevance_filter = None
        self.synthesizer = None
        self.metrics_tracker = None
        
        if use_query_expansion:
            try:
                from query_expander import query_expander
                self.query_expander = query_expander
                logging.info("✓ Query Expansion enabled")
            except ImportError:
                logging.warning("Query Expansion not available")
        
        if use_relevance_filter:
            try:
                from relevance_filter import relevance_filter
                self.relevance_filter = relevance_filter
                logging.info("✓ Relevance Filtering enabled")
            except ImportError:
                logging.warning("Relevance Filtering not available")
        
        if use_synthesis:
            try:
                from document_synthesizer import document_synthesizer
                self.synthesizer = document_synthesizer
                logging.info("✓ Document Synthesis enabled")
            except ImportError:
                logging.warning("Document Synthesis not available")
        
        if use_metrics:
            try:
                from rag_metrics import get_tracer, RAGMetricsCalculator
                self.metrics_tracker = get_tracer()
                self.metrics_calc = RAGMetricsCalculator()
                logging.info("✓ Metrics Tracking enabled")
            except ImportError:
                logging.warning("Metrics not available")
        
        logging.info(f"Enhanced RAG Pipeline initialized with {llm_provider} LLM")
    
    def query(
        self,
        user_query: str,
        n_results: int = 5,
        max_context_tokens: int = 3000,
        system_prompt: Optional[str] = None,
        enable_streaming: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> RAGResponse:
        """
        Complete RAG query with metrics tracking
        
        Args:
            user_query: User's question
            n_results: Number of documents to retrieve
            max_context_tokens: Maximum context size for LLM
            system_prompt: Optional custom system prompt
            enable_streaming: Enable streaming response
            stream_callback: Callback for streaming tokens
            
        Returns:
            RAGResponse with answer, sources, and metrics
        """
        query_id = str(uuid.uuid4())
        start_time = time.time()
        
        logging.info(f"RAG Query [{query_id}]: {user_query}")
        
        # Step 1: Query Expansion
        queries = self._expand_query(user_query, n_results)
        
        # Step 2: Advanced Retrieval
        retrieval_start = time.time()
        all_results = self._retrieve_documents(queries, n_results * 2)
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        # Step 3: Relevance Filtering
        relevant_results = self._filter_relevance(user_query, all_results)
        
        if not relevant_results:
            return self._empty_response(query_id, user_query, start_time)
        
        # Step 4: Context Preparation
        context = self._prepare_context(user_query, relevant_results, max_context_tokens)
        
        # Step 5: LLM Generation
        generation_start = time.time()
        if enable_streaming and stream_callback:
            answer = self._generate_answer_stream(user_query, context, system_prompt, stream_callback)
        else:
            answer = self._generate_answer(user_query, context, system_prompt)
        generation_time = (time.time() - generation_start) * 1000
        
        # Step 6: Calculate multi-faceted confidence
        confidence = self._calculate_confidence(user_query, answer, context, relevant_results)
        
        # Calculate total latency
        total_time = (time.time() - start_time) * 1000
        
        # Create response
        response = RAGResponse(
            answer=answer,
            sources=relevant_results[:5],
            confidence=confidence,
            query=user_query,
            context_used=context,
            query_id=query_id,
            latency_ms=total_time
        )
        
        # Log metrics if enabled
        if self.metrics_tracker:
            self._log_metrics(
                query_id, user_query, response, 
                retrieval_time, generation_time, total_time
            )
        
        return response
    
    def _expand_query(self, query: str, n_results: int) -> List[str]:
        """Step 1: Expand query into multiple variations"""
        if not self.query_expander:
            return [query]
        
        try:
            expanded = self.query_expander.expand_query(query)
            queries = expanded.get('queries', [query])
            logging.info(f"Expanded into {len(queries)} queries")
            return queries
        except Exception as e:
            logging.error(f"Query expansion error: {e}")
            return [query]
    
    def _retrieve_documents(self, queries: List[str], top_k: int) -> List[Dict]:
        """Step 2: Advanced retrieval with hybrid search and MMR"""
        if self.advanced_retriever:
            # Use advanced retrieval (hybrid + MMR)
            try:
                all_results = []
                for query in queries:
                    results = self.advanced_retriever.hybrid_search(query, top_k=top_k)
                    all_results.extend(results)
                
                # Deduplicate results
                seen_ids = set()
                unique_results = []
                for result in all_results:
                    result_id = result.get('id')
                    if result_id not in seen_ids:
                        seen_ids.add(result_id)
                        unique_results.append(result)
                
                logging.info(f"Advanced retrieval: {len(unique_results)} unique documents")
                return unique_results
            except Exception as e:
                logging.error(f"Advanced retrieval error: {e}, falling back to basic search")
        
        # Fallback to basic vector search
        all_results = []
        seen_ids = set()
        
        for query in queries:
            results = self.vector_db.search(query, n_results=top_k)
            for result in results:
                if result['id'] not in seen_ids:
                    seen_ids.add(result['id'])
                    all_results.append(result)
        
        logging.info(f"Basic retrieval: {len(all_results)} documents")
        return all_results
    
    def _filter_relevance(self, query: str, results: List[Dict]) -> List[Dict]:
        """Step 3: Filter for relevance"""
        if not self.relevance_filter:
            return results
        
        try:
            relevant = []
            for result in results:
                decision = self.relevance_filter.filter_relevance(
                    user_query=query,
                    document_excerpt=result.get('content', '')
                )
                if decision == "YES":
                    relevant.append(result)
            
            logging.info(f"Filtered to {len(relevant)} relevant documents")
            return relevant
        except Exception as e:
            logging.error(f"Relevance filtering error: {e}")
            return results
    
    def _prepare_context(
        self,
        query: str,
        results: List[Dict],
        max_tokens: int
    ) -> str:
        """Step 4: Prepare context for LLM"""
        if self.synthesizer:
            try:
                contexts = [
                    {
                        'text': r.get('content', ''),
                        'doc_name': r.get('metadata', {}).get('name', 'Unknown'),
                        'page': r.get('metadata', {}).get('page', 'N/A')
                    }
                    for r in results
                ]
                
                summary = self.synthesizer.synthesize(query, contexts)
                context = summary
            except Exception as e:
                logging.error(f"Synthesis error: {e}")
                context = self._fallback_context(results)
        else:
            context = self._fallback_context(results)
        
        # Truncate if needed
        context = self.llm.truncate_context(context, max_tokens)
        
        return context
    
    def _fallback_context(self, results: List[Dict]) -> str:
        """Fallback context preparation"""
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            doc_name = result.get('metadata', {}).get('name', 'Unknown')
            content = result.get('content', '')[:500]
            context_parts.append(f"[Source {i}: {doc_name}]\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _generate_answer(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Step 5: Generate answer using LLM"""
        try:
            answer = self.llm.generate_answer(
                query=query,
                context=context,
                system_prompt=system_prompt
            )
            return answer
        except Exception as e:
            logging.error(f"Answer generation error: {e}")
            return f"Error generating answer: {str(e)}"
    
    def _generate_answer_stream(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str],
        callback: Callable[[str], None]
    ) -> str:
        """Generate answer with streaming"""
        # TODO: Implement streaming when LLM supports it
        # For now, return full answer
        answer = self._generate_answer(query, context, system_prompt)
        callback(answer)
        return answer
    
    def _calculate_confidence(
        self,
        query: str,
        answer: str,
        context: str,
        results: List[Dict]
    ) -> Dict[str, float]:
        """Multi-faceted confidence scoring"""
        confidence = {}
        
        # Retrieval confidence (based on similarity scores)
        if results:
            avg_score = sum(r.get('score', r.get('combined_score', 0.5)) for r in results) / len(results)
            confidence['retrieval'] = min(avg_score, 1.0)
        else:
            confidence['retrieval'] = 0.0
        
        # Answer quality confidence
        if self.metrics_calc:
            try:
                relevance = self.metrics_calc.answer_relevance(query, answer)
                faithfulness = self.metrics_calc.faithfulness_score(answer, context)
                
                confidence['relevance'] = relevance
                confidence['faithfulness'] = faithfulness
            except:
                confidence['relevance'] = 0.5
                confidence['faithfulness'] = 0.5
        
        # Overall confidence (weighted average)
        confidence['overall'] = (
            confidence.get('retrieval', 0.0) * 0.4 +
            confidence.get('relevance', 0.0) * 0.3 +
            confidence.get('faithfulness', 0.0) * 0.3
        )
        
        return confidence
    
    def _empty_response(self, query_id: str, query: str, start_time: float) -> RAGResponse:
        """Create empty response when no results found"""
        return RAGResponse(
            answer="I couldn't find relevant information to answer your question. Please try rephrasing or ask something else.",
            sources=[],
            confidence={'overall': 0.0, 'retrieval': 0.0},
            query=query,
            context_used="",
            query_id=query_id,
            latency_ms=(time.time() - start_time) * 1000
        )
    
    def _log_metrics(
        self,
        query_id: str,
        query: str,
        response: RAGResponse,
        retrieval_time: float,
        generation_time: float,
        total_time: float
    ) -> None:
        """Log metrics for query"""
        try:
            from rag_metrics import PerformanceMetrics, AnswerMetrics
            
            perf_metrics = PerformanceMetrics(
                query_latency_ms=total_time,
                retrieval_latency_ms=retrieval_time,
                generation_latency_ms=generation_time,
                total_tokens_used=0  # TODO: track token usage
            )
            
            answer_metrics = AnswerMetrics(
                relevance_score=response.confidence.get('relevance', 0.0),
                faithfulness_score=response.confidence.get('faithfulness', 0.0)
            )
            
            self.metrics_tracker.log_query(
                query_id=query_id,
                query=query,
                answer=response.answer,
                confidence=response.confidence.get('overall', 0.0),
                sources=response.sources,
                performance_metrics=perf_metrics,
                answer_metrics=answer_metrics
            )
        except Exception as e:
            logging.error(f"Metrics logging error: {e}")


# ============================================================================
# Convenience Functions
# ============================================================================

def create_rag_pipeline(
    vector_db,
    llm_provider: str = "mock",
    **kwargs
) -> EnhancedRAGPipeline:
    """
    Create enhanced RAG pipeline instance
    
    Args:
        vector_db: VectorMemory instance
        llm_provider: "openai", "gemini", "ollama", or "mock"
        **kwargs: Additional configuration
        
    Returns:
        EnhancedRAGPipeline instance
    """
    return EnhancedRAGPipeline(vector_db=vector_db, llm_provider=llm_provider, **kwargs)


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Enhanced RAG Pipeline v2.0 - Testing")
    print("=" * 80)
    
    # Mock vector DB
    class MockVectorDB:
        def search(self, query, n_results=5):
            return [
                {
                    'id': 'doc1',
                    'content': 'Machine learning is a method of data analysis that automates analytical model building.',
                    'metadata': {'name': 'ML Basics', 'page': '1'},
                    'distance': 0.2
                },
                {
                    'id': 'doc2',
                    'content': 'Deep learning is a subset of machine learning based on artificial neural networks.',
                    'metadata': {'name': 'DL Guide', 'page': '5'},
                    'distance': 0.3
                }
            ]
    
    # Create pipeline
    vector_db = MockVectorDB()
    rag = create_rag_pipeline(
        vector_db=vector_db,
        llm_provider="mock",
        use_advanced_retrieval=False,  # Disable for basic testing
        use_query_expansion=False,
        use_relevance_filter=False,
        use_synthesis=False,
        use_metrics=True
    )
    
    # Test query
    query = "What is machine learning?"
    response = rag.query(query)
    
    print(f"\nQuery: {query}")
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nConfidence: {response.confidence['overall']:.2%}")
    print(f"  - Retrieval: {response.confidence.get('retrieval', 0):.2%}")
    print(f"  - Relevance: {response.confidence.get('relevance', 0):.2%}")
    print(f"  - Faithfulness: {response.confidence.get('faithfulness', 0):.2%}")
    print(f"\nSources: {len(response.sources)}")
    print(f"Latency: {response.latency_ms:.0f}ms")
    
    # Export metrics
    if rag.metrics_tracker:
        metrics = rag.metrics_tracker.export_metrics()
        print(f"\nSystem Metrics:")
        print(f"  Total queries: {metrics['total_queries']}")
        print(f"  Avg latency: {metrics['average_latency']}")
    
    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)
