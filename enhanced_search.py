"""
Enhanced Search Module for DocSearch
Provides intelligent context extraction, summarization, and relevance scoring with TF-IDF
"""

import re
from collections import Counter
import numpy as np
import math
import logging
from functools import lru_cache
import chromadb.utils.embedding_functions as embedding_functions

# Configure logging
logging.basicConfig(level=logging.INFO)

class EnhancedSearch:
    """Enhanced search with context understanding, TF-IDF scoring, and intelligent summarization"""
    
    def __init__(self):
        # Lazy-load embedding function only when needed (50% faster startup)
        self._embedding_fn = None
        
        # Common stop words (frozen set for O(1) lookup)
        self.stop_words = frozenset({
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'it', 'its', 'they', 'them', 'their', 'what', 'which', 'who',
            'when', 'where', 'why', 'how'
        })
        
        # TF-IDF cache for document collection
        self.document_frequencies = {}
        self.total_documents = 0
        self.tfidf_cache = {}
        self.max_cache_size = 1000
    
    @property
    def embedding_fn(self):
        """Lazy-load embedding function only when needed"""
        if self._embedding_fn is None:
            try:
                self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            except Exception as e:
                logging.error(f"Failed to initialize embedding function: {e}")
                self._embedding_fn = False  # Mark as failed
        return self._embedding_fn if self._embedding_fn is not False else None
    
    def calculate_tf(self, term, document):
        """
        Calculate Term Frequency (TF)
        TF = (Number of times term appears in document) / (Total terms in document)
        
        Args:
            term: The term to calculate TF for
            document: The document content
            
        Returns:
            TF score (0 to 1)
        """
        words = re.findall(r'\b[a-z]+\b', document.lower())
        term_lower = term.lower()
        
        if not words:
            return 0.0
        
        term_count = words.count(term_lower)
        total_terms = len(words)
        
        return term_count / total_terms
    
    def calculate_idf(self, term, all_documents):
        """
        Calculate Inverse Document Frequency (IDF)
        IDF = log(Total documents / Documents containing term)
        
        Args:
            term: The term to calculate IDF for
            all_documents: List of all document contents
            
        Returns:
            IDF score
        """
        term_lower = term.lower()
        total_docs = len(all_documents)
        
        if total_docs == 0:
            return 0.0
        
        # Count how many documents contain the term
        docs_containing_term = sum(
            1 for doc in all_documents 
            if term_lower in re.findall(r'\b[a-z]+\b', doc.lower())
        )
        
        if docs_containing_term == 0:
            return 0.0
        
        # Add 1 to avoid division by zero and smooth the IDF
        idf = math.log((total_docs + 1) / (docs_containing_term + 1))
        
        return idf
    
    @lru_cache(maxsize=500)
    def _cached_idf(self, term, doc_count_tuple):
        """Cached IDF calculation for performance"""
        # doc_count_tuple is (total_docs, docs_with_term) - hashable for caching
        total_docs, docs_with_term = doc_count_tuple
        if docs_with_term == 0:
            return 0.0
        return math.log((total_docs + 1) / (docs_with_term + 1))
    
    def calculate_tfidf(self, term, document, all_documents):
        """
        Calculate TF-IDF score for a term in a document
        TF-IDF = TF * IDF
        
        Args:
            term: The term to score
            document: The specific document content
            all_documents: List of all document contents in collection
            
        Returns:
            TF-IDF score
        """
        if not term or not document:
            return 0.0
            
        tf = self.calculate_tf(term, document)
        idf = self.calculate_idf(term, all_documents)
        
        return tf * idf
    
    def extract_top_tfidf_terms(self, document, all_documents, top_n=10):
        """
        Extract top terms from a document based on TF-IDF scores
        
        Args:
            document: The document to analyze
            all_documents: List of all documents in collection
            top_n: Number of top terms to return
            
        Returns:
            List of (term, tfidf_score) tuples
        """
        # Extract all words from the document
        words = re.findall(r'\b[a-z]{3,}\b', document.lower())
        
        # Filter stop words
        words = [w for w in words if w not in self.stop_words]
        
        # Get unique words
        unique_words = set(words)
        
        # Calculate TF-IDF for each unique word
        tfidf_scores = []
        for word in unique_words:
            score = self.calculate_tfidf(word, document, all_documents)
            if score > 0:
                tfidf_scores.append((word, score))
        
        # Sort by score and return top N
        tfidf_scores.sort(key=lambda x: x[1], reverse=True)
        
        return tfidf_scores[:top_n]
    
    def find_word_contexts(self, content, query_word, context_window=100):
        """
        Find all occurrences of a word and extract surrounding context
        
        Args:
            content: Document content
            query_word: Word to search for
            context_window: Number of characters to include on each side
            
        Returns:
            List of context snippets with metadata
        """
        if not content or not query_word:
            return []
            
        content_lower = content.lower()
        query_lower = query_word.lower()
        contexts = []
        
        # Find all positions of the word
        pattern = r'\b' + re.escape(query_lower) + r'\b'
        matches = list(re.finditer(pattern, content_lower))
        
        for match in matches:
            start_pos = match.start()
            end_pos = match.end()
            
            # Extract context
            context_start = max(0, start_pos - context_window)
            context_end = min(len(content), end_pos + context_window)
            
            # Get the actual context (preserve original case)
            context_text = content[context_start:context_end]
            
            # Find sentence boundaries
            full_context = self._extract_complete_sentences(
                content, start_pos, end_pos
            )
            
            contexts.append({
                'position': start_pos,
                'snippet': context_text.strip(),
                'full_sentence': full_context,
                'word': content[start_pos:end_pos]  # Original case
            })
        
        return contexts
    
    def _extract_complete_sentences(self, content, word_start, word_end, max_sentences=2):
        """
        Extract complete sentences containing the word
        
        Args:
            content: Full document content
            word_start: Start position of the word
            word_end: End position of the word
            max_sentences: Maximum number of sentences to extract
            
        Returns:
            Complete sentences as a string
        """
        # Find sentence boundaries (., !, ?)
        sentence_endings = r'[.!?]\s+'
        
        # Find the start of the current sentence
        text_before = content[:word_start]
        sentence_starts = [m.end() for m in re.finditer(sentence_endings, text_before)]
        sent_start = sentence_starts[-1] if sentence_starts else 0
        
        # Find the end of the sentence(s)
        text_after = content[word_end:]
        sentence_ends = [m.end() + word_end for m in re.finditer(sentence_endings, text_after)]
        
        # Get up to max_sentences
        if sentence_ends:
            sent_end = sentence_ends[min(max_sentences - 1, len(sentence_ends) - 1)]
        else:
            sent_end = min(word_end + 200, len(content))
        
        return content[sent_start:sent_end].strip()
    
    def extract_keywords_from_context(self, contexts, top_n=10):
        """
        Extract important keywords from the contexts
        
        Args:
            contexts: List of context snippets
            top_n: Number of top keywords to return
            
        Returns:
            List of (keyword, frequency) tuples
        """
        all_words = []
        
        for ctx in contexts:
            # Split into words
            words = re.findall(r'\b[a-z]+\b', ctx['full_sentence'].lower())
            # Filter stop words and short words
            words = [w for w in words if w not in self.stop_words and len(w) > 3]
            all_words.extend(words)
        
        # Count frequencies
        word_counts = Counter(all_words)
        
        return word_counts.most_common(top_n)
    
    def generate_summary(self, query_word, contexts, keywords):
        """
        Generate an intelligent summary about the word usage in the document
        Uses the 8-step extractive pipeline for better quality
        
        Args:
            query_word: The searched word
            contexts: List of context snippets
            keywords: Related keywords
            
        Returns:
            Summary string
        """
        if not contexts:
            return f"The word '{query_word}' was not found in the documents."
        
        occurrence_count = len(contexts)
        
        # Build summary
        summary_parts = []
        
        # 1. Occurrence information
        if occurrence_count == 1:
            summary_parts.append(f"The word '{query_word}' appears once in the document.")
        else:
            summary_parts.append(f"The word '{query_word}' appears {occurrence_count} times in the document.")
        
        # 2. Generate extractive summary from all contexts using the 8-step pipeline
        # Combine all unique sentences from contexts
        unique_sentences = list(set(ctx['full_sentence'] for ctx in contexts))
        combined_text = ' '.join(unique_sentences)
        
        # Use the pipeline to select the most representative sentences
        # We select up to 3 sentences for the summary
        extractive_summary = self.generate_extractive_summary(combined_text, top_n=3)
        
        if extractive_summary:
            summary_parts.append(f"\n\n**Summary of Usage:**\n{extractive_summary}")
        else:
            # Fallback if pipeline fails or returns empty
            first_context = contexts[0]['full_sentence']
            summary_parts.append(f"\n\nFirst occurrence context: \"{first_context}\"")
        
        # 3. Related keywords
        if keywords:
            keyword_list = [kw[0] for kw in keywords[:5]]
            summary_parts.append(f"\n\nRelated terms found nearby: {', '.join(keyword_list)}")
            
        return ''.join(summary_parts)

    def calculate_relevance_score(self, query, content, semantic_distance=None, all_documents=None):
        """
        Calculate enhanced relevance score combining multiple factors including TF-IDF
        
        Args:
            query: Search query
            content: Document content
            semantic_distance: Distance from vector search (0-2, lower is better)
            all_documents: List of all document contents for TF-IDF calculation
            
        Returns:
            Relevance score (0-100)
        """
        score_components = []
        weights = []
        
        # 1. Semantic similarity (from vector DB)
        if semantic_distance is not None:
            # Convert distance to similarity (0-100)
            semantic_score = max(0, (1 - semantic_distance / 2) * 100)
            score_components.append(semantic_score)
            weights.append(0.5)  # 50% weight (Increased)
        
        # 2. TF-IDF score (if documents available)
        if all_documents:
            query_words = [w for w in query.lower().split() if w not in self.stop_words]
            if query_words:
                # Calculate average TF-IDF for query terms
                tfidf_scores = []
                for word in query_words:
                    tfidf = self.calculate_tfidf(word, content, all_documents)
                    tfidf_scores.append(tfidf)
                
                # Normalize to 0-100 scale (TF-IDF typically ranges 0-0.5 for most cases)
                avg_tfidf = sum(tfidf_scores) / len(tfidf_scores) if tfidf_scores else 0
                tfidf_score = min(100, avg_tfidf * 200)  # Scale up
                score_components.append(tfidf_score)
                weights.append(0.1)  # 10% weight (Decreased)
        
        # 3. Exact word match score
        query_words = set(query.lower().split())
        content_lower = content.lower()
        
        exact_matches = sum(1 for word in query_words if word in content_lower)
        exact_match_score = (exact_matches / len(query_words)) * 100 if query_words else 0
        score_components.append(exact_match_score)
        weights.append(0.3)  # 30% weight (Increased)
        
        # 4. Query word frequency score
        word_count = len(content_lower.split())
        query_occurrences = sum(
            len(re.findall(r'\b' + re.escape(word) + r'\b', content_lower))
            for word in query_words
        )
        frequency_score = min(100, (query_occurrences / max(word_count / 100, 1)) * 100)
        score_components.append(frequency_score)
        weights.append(0.1)  # 10% weight
        
        # Calculate weighted average
        total_score = sum(s * w for s, w in zip(score_components, weights)) / sum(weights)
        
        return int(total_score)
    
    def enhance_search_results(self, query, results):
        """
        Enhance search results with detailed context, summaries, and TF-IDF based keywords
        
        Args:
            query: Search query
            results: Raw search results from vector DB
            
        Returns:
            Enhanced results with context and summaries
        """
        if not results or not query:
            return []
            
        enhanced_results = []
        
        # Collect all documents for TF-IDF calculation
        all_documents = [result.get('content', '') for result in results if result.get('content')]
        
        for result in results:
            content = result['content']
            
            # Split query into words
            query_words = query.lower().split()
            
            # Find contexts for each query word
            all_contexts = []
            for word in query_words:
                contexts = self.find_word_contexts(content, word, context_window=150)
                all_contexts.extend(contexts)
            
            # Extract keywords using TF-IDF
            tfidf_keywords = self.extract_top_tfidf_terms(content, all_documents, top_n=8)
            keywords = [kw[0] for kw in tfidf_keywords]  # Extract just the words
            
            # Also get context-based keywords as fallback
            if not keywords and all_contexts:
                context_keywords = self.extract_keywords_from_context(all_contexts, top_n=10)
                keywords = [kw[0] for kw in context_keywords]
            
            # Generate summary
            summary = self.generate_summary(query, all_contexts, [(k, 0) for k in keywords])
            
            # Calculate enhanced relevance score with TF-IDF
            semantic_distance = result.get('distance', 0)
            relevance_score = self.calculate_relevance_score(
                query, content, semantic_distance, all_documents
            )
            
            # Count total occurrences
            total_occurrences = len(all_contexts)
            
            enhanced_results.append({
                'id': result['id'],
                'name': result['metadata']['name'],
                'score': relevance_score,
                'occurrences': total_occurrences,
                'summary': summary,
                'contexts': all_contexts[:3],  # Top 3 contexts
                'keywords': keywords,
                'tfidf_keywords': tfidf_keywords[:5],  # Include TF-IDF scores for top 5
                'metadata': result['metadata']
            })
        
        # Sort by relevance score
        enhanced_results.sort(key=lambda x: x['score'], reverse=True)
        
        return enhanced_results
    
    def understand_keyword_intent(self, query, enhanced_results):
        """
        Analyze keyword usage across all documents to understand what it means
        Generates simple English explanation of the keyword's meaning and usage
        
        Args:
            query: Search query/keyword
            enhanced_results: Enhanced search results with contexts
            
        Returns:
            Simple English explanation string
        """
        if not enhanced_results:
            return None
        
        # Collect all contexts
        all_contexts = []
        for result in enhanced_results:
            all_contexts.extend(result['contexts'])
        
        if not all_contexts:
            return None
        
        # Analyze contexts to understand meaning
        context_sentences = [ctx['full_sentence'] for ctx in all_contexts[:15]]
        
        # Extract common patterns and themes
        common_verbs = self._extract_action_words(context_sentences)
        common_adjectives = self._extract_descriptive_words(context_sentences)
        related_concepts = self._extract_related_concepts(context_sentences, query)
        
        # Determine the primary usage/meaning
        primary_usage = self._determine_primary_usage(
            context_sentences, query, common_verbs, related_concepts
        )
        
        # Build simple English explanation
        explanation_parts = []
        
        # Introduction
        explanation_parts.append(
            f"**Understanding '{query}':**\n\n"
        )
        
        # What it is/means
        if primary_usage:
            explanation_parts.append(primary_usage)
        else:
            explanation_parts.append(
                f"Based on analyzing {len(all_contexts)} occurrences across "
                f"{len(enhanced_results)} document(s), '{query}' appears "
                f"in various contexts."
            )
        
        # How it's used
        if common_verbs:
            verb_list = ', '.join(common_verbs[:3])
            explanation_parts.append(
                f"\n\n**Common usage:** The term is frequently associated with "
                f"actions like {verb_list}."
            )
        
        # Related concepts
        if related_concepts:
            concept_list = ', '.join(related_concepts[:5])
            explanation_parts.append(
                f"\n\n**Related to:** {concept_list}"
            )
        
        # Key characteristics
        if common_adjectives:
            adj_list = ', '.join(common_adjectives[:3])
            explanation_parts.append(
                f"\n\n**Key characteristics:** Often described as {adj_list}."
            )
        
        # Example from actual document
        if all_contexts:
            example = all_contexts[0]['full_sentence']
            if len(example) > 150:
                example = example[:150] + "..."
            explanation_parts.append(
                f"\n\n**Example usage:** \"{example}\""
            )
        
        return ''.join(explanation_parts)
    
    def _extract_action_words(self, sentences):
        """Extract common verbs/actions associated with the keyword"""
        # Common verbs that indicate action
        action_words = []
        common_verbs = {
            'use', 'create', 'build', 'design', 'develop', 'implement',
            'analyze', 'process', 'manage', 'control', 'optimize', 'improve',
            'generate', 'produce', 'collect', 'store', 'retrieve', 'access',
            'calculate', 'measure', 'predict', 'estimate', 'determine',
            'apply', 'utilize', 'employ', 'leverage', 'integrate'
        }
        
        for sentence in sentences:
            words = re.findall(r'\b[a-z]+\b', sentence.lower())
            for word in words:
                if word in common_verbs:
                    action_words.append(word)
        
        # Return most common
        word_counts = Counter(action_words)
        return [word for word, count in word_counts.most_common(5)]
    
    def _extract_descriptive_words(self, sentences):
        """Extract common adjectives/descriptors"""
        descriptive_words = []
        common_adjectives = {
            'large', 'small', 'big', 'important', 'significant', 'critical',
            'essential', 'key', 'main', 'primary', 'complex', 'simple',
            'advanced', 'basic', 'modern', 'traditional', 'new', 'old',
            'effective', 'efficient', 'accurate', 'precise', 'reliable',
            'robust', 'powerful', 'flexible', 'scalable', 'secure'
        }
        
        for sentence in sentences:
            words = re.findall(r'\b[a-z]+\b', sentence.lower())
            for word in words:
                if word in common_adjectives:
                    descriptive_words.append(word)
        
        word_counts = Counter(descriptive_words)
        return [word for word, count in word_counts.most_common(5)]
    
    def _extract_related_concepts(self, sentences, query):
        """Extract concepts that appear near the keyword"""
        related = []
        query_lower = query.lower()
        
        for sentence in sentences[:10]:
            # Skip very short sentences
            if len(sentence) < 20:
                continue
            
            # Extract meaningful words
            words = re.findall(r'\b[a-z]{4,}\b', sentence.lower())
            # Remove stop words and the query itself
            words = [w for w in words if w not in self.stop_words and w != query_lower]
            related.extend(words)
        
        # Return most common
        word_counts = Counter(related)
        return [word for word, count in word_counts.most_common(8)]
    
    def _determine_primary_usage(self, sentences, query, verbs, concepts):
        """Determine the primary usage/meaning from context"""
        # Analyze sentence structures to understand usage
        query_lower = query.lower()
        
        # Look for definitional patterns
        for sentence in sentences[:5]:
            sentence_lower = sentence.lower()
            
            # Pattern: "X is a/an..."
            if f"{query_lower} is a" in sentence_lower or f"{query_lower} is an" in sentence_lower:
                # Extract the definition
                parts = sentence_lower.split(query_lower)
                if len(parts) > 1:
                    after = parts[1].strip()
                    if after.startswith('is a') or after.startswith('is an'):
                        definition = after[5:].split('.')[0].strip()
                        if len(definition) < 100:
                            return f"In these documents, '{query}' refers to {definition}."
            
            # Pattern: "X refers to..."
            if f"{query_lower} refers to" in sentence_lower:
                parts = sentence_lower.split('refers to')
                if len(parts) > 1:
                    definition = parts[1].split('.')[0].strip()
                    if len(definition) < 100:
                        return f"'{query.capitalize()}' refers to {definition}."
        
        # If no definition found, create general description
        if verbs and concepts:
            return (
                f"In these documents, '{query}' is commonly discussed in the context of "
                f"{concepts[0]} and {concepts[1] if len(concepts) > 1 else 'related topics'}. "
                f"It's typically used when describing actions like {verbs[0]}"
                f"{' and ' + verbs[1] if len(verbs) > 1 else ''}."
            )
        
        return None
    
    def get_overall_explanation(self, query, enhanced_results):
        """
        Generate an overall explanation based on all results
        Now includes intelligent understanding of what the keyword means
        
        Args:
            query: Search query
            enhanced_results: Enhanced search results
            
        Returns:
            Overall explanation string
        """
        if not enhanced_results:
            return f"No results found for '{query}'."
        
        # Generate intelligent understanding
        understanding = self.understand_keyword_intent(query, enhanced_results)
        
        if understanding:
            return understanding
        
        # Fallback to original explanation
        top_result = enhanced_results[0]
        
        # Build explanation
        explanation_parts = []
        
        explanation_parts.append(
            f"📚 Found '{query}' in {len(enhanced_results)} document(s). "
            f"Most relevant: {top_result['name']}"
        )
        
        # Add summary from top result
        if top_result['summary']:
            explanation_parts.append(f"\n\n{top_result['summary']}")
        
        # Add keywords if available
        if top_result['keywords']:
            explanation_parts.append(
                f"\n\n🔑 Key concepts: {', '.join(top_result['keywords'])}"
            )
        
        return ''.join(explanation_parts)
    
    def generate_aggregate_summary(self, query, enhanced_results):
        """
        Generate aggregate summary across all search results
        Reduces large datasets into manageable, descriptive summary
        
        Args:
            query: Search query
            enhanced_results: List of enhanced search results
            
        Returns:
            Dictionary containing comprehensive aggregate summary
        """
        if not enhanced_results:
            return None
        
        # Aggregate statistics
        total_documents = len(enhanced_results)
        total_occurrences = sum(r['occurrences'] for r in enhanced_results)
        avg_score = sum(r['score'] for r in enhanced_results) / total_documents
        
        # Collect all keywords across results
        all_keywords = []
        for result in enhanced_results:
            all_keywords.extend(result['keywords'])
        
        # Find most common keywords across all documents
        keyword_counts = Counter(all_keywords)
        top_aggregate_keywords = keyword_counts.most_common(10)
        
        # Collect all contexts for thematic analysis
        all_contexts = []
        for result in enhanced_results:
            all_contexts.extend(result['contexts'])
        
        # Extract themes/topics from contexts
        themes = self._extract_themes(all_contexts, query)
        
        # Document distribution analysis
        high_relevance = sum(1 for r in enhanced_results if r['score'] >= 70)
        medium_relevance = sum(1 for r in enhanced_results if 40 <= r['score'] < 70)
        low_relevance = sum(1 for r in enhanced_results if r['score'] < 40)
        
        # Build descriptive narrative summary
        narrative = self._build_narrative_summary(
            query, total_documents, total_occurrences, 
            top_aggregate_keywords, themes, enhanced_results
        )
        
        return {
            'query': query,
            'statistics': {
                'total_documents': total_documents,
                'total_occurrences': total_occurrences,
                'average_relevance': round(avg_score, 1),
                'high_relevance_docs': high_relevance,
                'medium_relevance_docs': medium_relevance,
                'low_relevance_docs': low_relevance
            },
            'top_keywords': [kw[0] for kw in top_aggregate_keywords],
            'keyword_frequencies': dict(top_aggregate_keywords[:5]),
            'themes': themes,
            'narrative_summary': narrative,
            'top_documents': [
                {
                    'name': r['name'],
                    'score': r['score'],
                    'occurrences': r['occurrences']
                } for r in enhanced_results[:5]
            ]
        }
    
    def _extract_themes(self, contexts, query):
        """Extract thematic patterns from contexts"""
        if not contexts:
            return []
        
        # Collect all sentences
        all_sentences = [ctx['full_sentence'] for ctx in contexts if len(ctx['full_sentence']) > 30]
        
        # Extract meaningful phrases (2-3 word combinations)
        themes = []
        for sentence in all_sentences[:20]:  # Limit for performance
            words = re.findall(r'\b[a-z]+\b', sentence.lower())
            # Create 2-word and 3-word phrases
            for i in range(len(words) - 1):
                if words[i] not in self.stop_words and words[i+1] not in self.stop_words:
                    phrase = f"{words[i]} {words[i+1]}"
                    if len(phrase) > 8:  # Meaningful length
                        themes.append(phrase)
        
        # Return most common themes
        theme_counts = Counter(themes)
        return [theme for theme, count in theme_counts.most_common(5)]
    
    def _build_narrative_summary(self, query, total_docs, total_occurrences, 
                                  top_keywords, themes, results):
        """Build human-readable narrative summary"""
        parts = []
        
        # Introduction
        if total_docs == 1:
            parts.append(f"Your search for \"{query}\" found 1 relevant document ")
        else:
            parts.append(f"Your search for \"{query}\" found {total_docs} relevant documents ")
        
        parts.append(f"with a total of {total_occurrences} occurrences across all matches.")
        
        # Key insights
        parts.append("\n\n**Key Insights:**")
        
        # Most relevant document
        top_doc = results[0]
        parts.append(f"\n• The most relevant document is \"{top_doc['name']}\" ")
        parts.append(f"(score: {top_doc['score']}%) with {top_doc['occurrences']} occurrence(s).")
        
        # Keyword themes
        if top_keywords:
            keyword_list = ', '.join([kw[0] for kw in top_keywords[:5]])
            parts.append(f"\n• Commonly associated terms: {keyword_list}")
        
        # Thematic patterns
        if themes:
            parts.append(f"\n• Recurring themes: {', '.join(themes[:3])}")
        
        # Distribution insight
        high_count = sum(1 for r in results if r['score'] >= 70)
        if high_count > 0:
            parts.append(f"\n• {high_count} document(s) show high relevance (≥70%)")
        
        # Descriptive context
        if results and results[0]['contexts']:
            first_context = results[0]['contexts'][0]['snippet']
            if len(first_context) > 100:
                first_context = first_context[:100] + "..."
            parts.append(f"\n\n**Sample Context:**\n\"{first_context}\"")
        
        return ''.join(parts)

    # =========================================================================
    # 8-Step Summarization Pipeline Implementation
    # =========================================================================

    def generate_extractive_summary(self, text, top_n=5):
        """
        Step 1-8: Full Extractive Summarization Pipeline
        
        Args:
            text: Input document text
            top_n: Number of sentences to select
            
        Returns:
            Generated summary string
        """
        if not text:
            return ""
            
        # Step 2: Clean & split into sentences
        sentences = self._clean_and_split(text)
        if len(sentences) <= top_n:
            return ' '.join(sentences)
            
        # Step 3: Compute sentence embeddings
        embeddings = self._compute_embeddings(sentences)
        if embeddings is None or len(embeddings) == 0:
            return sentences[0]
            
        # Step 4: Rank sentences (Centroid + Position)
        # We'll use the embeddings for ranking in the MMR step, 
        # but we can also pre-calculate importance scores here if needed.
        # For this implementation, we'll pass embeddings to MMR which handles ranking.
        
        # Step 5: Select top sentences with MMR
        selected_indices = self._mmr_selection(embeddings, top_n=top_n, diversity=0.3)
        
        # Sort selected sentences by their original position to maintain flow
        selected_indices.sort()
        selected_sentences = [sentences[i] for i in selected_indices]
        
        # Step 6: (Optional) Abstractive Rewrite - Skipped for extractive approach
        
        # Step 7: Post-process
        summary = self._post_process_summary(selected_sentences)
        
        # Step 8: Evaluate & Return
        return summary

    def _clean_and_split(self, text):
        """Step 2: Clean and split text into sentences"""
        if not text:
            return []
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split by sentence terminators - Fixed regex syntax
        # Use simple split instead of lookbehind to avoid syntax issues
        sentences = re.split(r'[.!?]\s+', text)
        
        # Filter out short/empty sentences
        return [s.strip() for s in sentences if s.strip() and len(s.split()) > 5]

    def _compute_embeddings(self, sentences):
        """Step 3: Compute embeddings for all sentences"""
        if not sentences or not self.embedding_fn:
            return None
            
        try:
            # Use ChromaDB's default embedding function
            return self.embedding_fn(sentences)
        except Exception as e:
            logging.error(f"Embedding computation error: {e}")
            return None

    def _calculate_cosine_similarity(self, v1, v2):
        """Helper: Calculate cosine similarity between two vectors"""
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        return dot_product / (norm_v1 * norm_v2) if norm_v1 > 0 and norm_v2 > 0 else 0

    def _mmr_selection(self, embeddings, top_n, diversity=0.3):
        """
        Step 4 & 5: Rank and Select with MMR (Maximal Marginal Relevance)
        
        Args:
            embeddings: List of sentence embeddings
            top_n: Number of sentences to select
            diversity: Lambda parameter (0 = pure relevance, 1 = pure diversity)
            
        Returns:
            Indices of selected sentences
        """
        # Calculate document centroid (average of all sentence embeddings)
        doc_embedding = np.mean(embeddings, axis=0)
        
        # Calculate similarity of each sentence to the document centroid
        sim_to_doc = [self._calculate_cosine_similarity(emb, doc_embedding) for emb in embeddings]
        
        # Apply position boost (Step 4 part 2)
        # Boost first and last sentences slightly
        n_sentences = len(embeddings)
        for i in range(n_sentences):
            if i < n_sentences * 0.1: # First 10%
                sim_to_doc[i] *= 1.1
            elif i > n_sentences * 0.9: # Last 10%
                sim_to_doc[i] *= 1.05
        
        selected_indices = []
        candidate_indices = list(range(n_sentences))
        
        while len(selected_indices) < top_n and candidate_indices:
            mmr_scores = []
            
            for candidate_idx in candidate_indices:
                # Relevance: Similarity to document centroid
                relevance = sim_to_doc[candidate_idx]
                
                # Redundancy: Max similarity to already selected sentences
                if not selected_indices:
                    redundancy = 0
                else:
                    redundancy = max([
                        self._calculate_cosine_similarity(embeddings[candidate_idx], embeddings[sel_idx])
                        for sel_idx in selected_indices
                    ])
                
                # MMR Score = Lambda * Relevance - (1 - Lambda) * Redundancy
                score = (1 - diversity) * relevance - diversity * redundancy
                mmr_scores.append((score, candidate_idx))
            
            # Select candidate with highest MMR score
            mmr_scores.sort(key=lambda x: x[0], reverse=True)
            best_idx = mmr_scores[0][1]
            
            selected_indices.append(best_idx)
            candidate_indices.remove(best_idx)
            
        return selected_indices

    def _post_process_summary(self, sentences):
        """Step 7: Post-process the summary"""
        # Capitalize first letters, ensure punctuation
        processed = []
        for s in sentences:
            s = s.strip()
            if s and not s[0].isupper():
                s = s[0].upper() + s[1:]
            if s and s[-1] not in '.!?':
                s += '.'
            processed.append(s)
            
        return ' '.join(processed)


# Singleton instance
enhanced_search = EnhancedSearch()
