"""
Complete RAG Pipeline
Integrates all components: Retrieval + Generation
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)


@dataclass
class RAGResponse:
    """RAG system response"""
    answer: str
    sources: List[Dict]
    confidence: float
    query: str
    context_used: str


class CompleteRAGPipeline:
    """
    Complete RAG (Retrieval-Augmented Generation) Pipeline
    
    Combines:
    1. Query Expansion (Antigravity-Expand)
    2. Vector Search (ChromaDB)
    3. Relevance Filtering (Antigravity-Filter)
    4. Context Synthesis (Antigravity-Synthesize)
    5. LLM Generation (RAG-LLM)
    """
    
    def __init__(
        self,
        vector_db,
        llm_provider: str = "mock",
        llm_api_key: Optional[str] = None,
        use_query_expansion: bool = True,
        use_relevance_filter: bool = True,
        use_synthesis: bool = True
    ):
        """
        Initialize complete RAG pipeline
        
        Args:
            vector_db: VectorMemory instance
            llm_provider: "openai", "gemini", "ollama", or "mock"
            llm_api_key: API key for cloud LLMs
            use_query_expansion: Enable Antigravity-Expand
            use_relevance_filter: Enable Antigravity-Filter
            use_synthesis: Enable Antigravity-Synthesize
        """
        self.vector_db = vector_db
        
        # Initialize LLM
        from rag_llm import create_llm
        self.llm = create_llm(provider=llm_provider, api_key=llm_api_key)
        
        # Optional components
        self.use_query_expansion = use_query_expansion
        self.use_relevance_filter = use_relevance_filter
        self.use_synthesis = use_synthesis
        
        # Load optional components
        self.query_expander = None
        self.relevance_filter = None
        self.synthesizer = None
        
        if use_query_expansion:
            try:
                from query_expander import query_expander
                self.query_expander = query_expander
                logging.info("Query Expansion enabled")
            except ImportError:
                logging.warning("Query Expansion not available")
        
        if use_relevance_filter:
            try:
                from relevance_filter import relevance_filter
                self.relevance_filter = relevance_filter
                logging.info("Relevance Filtering enabled")
            except ImportError:
                logging.warning("Relevance Filtering not available")
        
        if use_synthesis:
            try:
                from document_synthesizer import document_synthesizer
                self.synthesizer = document_synthesizer
                logging.info("Document Synthesis enabled")
            except ImportError:
                logging.warning("Document Synthesis not available")
        
        logging.info(f"RAG Pipeline initialized with {llm_provider} LLM")
    
    def query(
        self,
        user_query: str,
        n_results: int = 5,
        max_context_tokens: int = 3000,
        system_prompt: Optional[str] = None
    ) -> RAGResponse:
        """
        Complete RAG query pipeline
        
        Args:
            user_query: User's question
            n_results: Number of documents to retrieve
            max_context_tokens: Maximum context size for LLM
            system_prompt: Optional custom system prompt
            
        Returns:
            RAGResponse with answer and sources
        """
        logging.info(f"RAG Query: {user_query}")
        
        # Step 1: Query Expansion
        queries = self._expand_query(user_query, n_results)
        
        # Step 2: Retrieval
        all_results = self._retrieve_documents(queries)
        
        # Step 3: Relevance Filtering
        relevant_results = self._filter_relevance(user_query, all_results)
        
        if not relevant_results:
            return RAGResponse(
                answer="I couldn't find relevant information to answer your question. Please try rephrasing or ask something else.",
                sources=[],
                confidence=0.0,
                query=user_query,
                context_used=""
            )
        
        # Step 4: Context Preparation
        context = self._prepare_context(user_query, relevant_results, max_context_tokens)
        
        # Step 5: LLM Generation
        answer = self._generate_answer(user_query, context, system_prompt)
        
        # Step 6: Calculate confidence
        confidence = self._calculate_confidence(relevant_results)
        
        return RAGResponse(
            answer=answer,
            sources=relevant_results[:5],  # Top 5 sources
            confidence=confidence,
            query=user_query,
            context_used=context
        )
    
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
    
    def _retrieve_documents(self, queries: List[str]) -> List[Dict]:
        """Step 2: Retrieve documents for all query variations"""
        all_results = []
        seen_ids = set()
        
        for query in queries:
            results = self.vector_db.search(query, n_results=5)
            for result in results:
                # Deduplicate by ID
                if result['id'] not in seen_ids:
                    seen_ids.add(result['id'])
                    all_results.append(result)
        
        logging.info(f"Retrieved {len(all_results)} unique documents")
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
                    document_excerpt=result['content']
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
            # Use document synthesizer for structured context
            try:
                contexts = [
                    {
                        'text': r['content'],
                        'doc_name': r['metadata'].get('name', 'Unknown'),
                        'page': r['metadata'].get('page', 'N/A')
                    }
                    for r in results
                ]
                
                # Get synthesized summary
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
        """Fallback context preparation without synthesizer"""
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            doc_name = result['metadata'].get('name', 'Unknown')
            content = result['content'][:500]  # Limit each chunk
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
    
    def _calculate_confidence(self, results: List[Dict]) -> float:
        """Calculate confidence score based on results"""
        if not results:
            return 0.0
        
        # Simple confidence based on:
        # 1. Number of relevant results
        # 2. Average distance/similarity
        
        num_results = len(results)
        avg_distance = sum(r.get('distance', 1.0) for r in results) / num_results
        
        # Convert distance to similarity (lower distance = higher similarity)
        avg_similarity = 1.0 - min(avg_distance, 1.0)
        
        # Combine factors
        confidence = (min(num_results / 5.0, 1.0) * 0.5) + (avg_similarity * 0.5)
        
        return round(confidence, 2)


# Convenience function
def create_rag_pipeline(
    vector_db,
    llm_provider: str = "mock",
    **kwargs
) -> CompleteRAGPipeline:
    """
    Create RAG pipeline instance
    
    Args:
        vector_db: VectorMemory instance
        llm_provider: "openai", "gemini", "ollama", or "mock"
        **kwargs: Additional configuration
        
    Returns:
        CompleteRAGPipeline instance
    """
    return CompleteRAGPipeline(vector_db=vector_db, llm_provider=llm_provider, **kwargs)


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("Complete RAG Pipeline - Testing")
    print("=" * 80)
    
    # Mock vector DB for testing
    class MockVectorDB:
        def search(self, query, n_results=5):
            return [
                {
                    'id': 'doc1',
                    'content': 'Customer churn rate is 15% annually, higher than industry average of 12%.',
                    'metadata': {'name': 'Q4 Report', 'page': '23'},
                    'distance': 0.2
                },
                {
                    'id': 'doc2',
                    'content': 'Main churn reasons: poor service (35%), high pricing (28%), missing features (22%).',
                    'metadata': {'name': 'Feedback Analysis', 'page': '8'},
                    'distance': 0.3
                }
            ]
    
    # Create pipeline
    vector_db = MockVectorDB()
    rag = create_rag_pipeline(
        vector_db=vector_db,
        llm_provider="mock",
        use_query_expansion=False,  # Disable for testing
        use_relevance_filter=False,
        use_synthesis=False
    )
    
    # Test query
    query = "What is our customer churn rate?"
    response = rag.query(query)
    
    print(f"\nQuery: {query}")
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nConfidence: {response.confidence * 100}%")
    print(f"\nSources: {len(response.sources)}")
    
    print("\n" + "=" * 80)
    print("Test completed successfully")
    print("=" * 80)
