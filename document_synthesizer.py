"""
Antigravity-Synthesize: Document Intelligence Engine
Synthesizes information from multiple document excerpts into clear, cited summaries
"""

import re
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)


class DocumentSynthesizer:
    """
    Synthesizes information from document excerpts into executive-ready summaries
    with proper citations
    """
    
    def __init__(self):
        # Patterns for extracting key information
        self.number_patterns = [
            r'\d+%',  # Percentages
            r'\$[\d,]+(?:\.\d{2})?',  # Money
            r'\d{4}',  # Years
            r'\d+(?:,\d{3})*(?:\.\d+)?',  # Numbers with commas
        ]
        
        # Patterns for identifying definitions
        self.definition_patterns = [
            r'is defined as',
            r'refers to',
            r'means',
            r'is a',
            r'is an',
            r'represents',
            r'indicates',
        ]
        
        # Patterns for identifying key facts
        self.fact_patterns = [
            r'according to',
            r'shows that',
            r'demonstrates',
            r'reveals',
            r'indicates that',
            r'found that',
            r'reported',
        ]
    
    def synthesize(
        self,
        user_keyword: str,
        relevant_contexts: List[Dict[str, str]]
    ) -> str:
        """
        Generate executive summary from relevant document excerpts
        
        Args:
            user_keyword: Original search keyword
            relevant_contexts: List of dicts with 'text', 'doc_name', 'page' keys
            
        Returns:
            Formatted summary with citations
        """
        if not user_keyword or not user_keyword.strip():
            return "Error: No search keyword provided."
        
        if not relevant_contexts:
            return (
                f"The uploaded documents do not contain specific details on "
                f"'{user_keyword}'."
            )
        
        # Build the summary
        summary_parts = []
        
        # 1. Direct Answer/Definition
        definition = self._extract_definition(user_keyword, relevant_contexts)
        if definition:
            summary_parts.append(f"**Direct Answer:**\n{definition}\n")
        
        # 2. Key Details
        key_details = self._extract_key_details(relevant_contexts)
        if key_details:
            summary_parts.append("**Key Details:**")
            for detail in key_details:
                summary_parts.append(f"• {detail}")
            summary_parts.append("")  # Empty line
        
        # 3. Data Points
        data_points = self._extract_data_points(relevant_contexts)
        if data_points:
            summary_parts.append("**Data Points:**")
            for point in data_points:
                summary_parts.append(f"• {point}")
            summary_parts.append("")
        
        # 4. Additional Context
        if len(relevant_contexts) > 1:
            summary_parts.append(
                f"**Sources:** Information synthesized from {len(relevant_contexts)} "
                f"document excerpt(s)."
            )
        
        # If no meaningful content extracted
        if len(summary_parts) <= 1:
            return (
                f"The uploaded documents mention '{user_keyword}' but do not "
                f"provide detailed information. Please upload more comprehensive "
                f"documents for better results."
            )
        
        return '\n'.join(summary_parts)
    
    def _extract_definition(
        self,
        keyword: str,
        contexts: List[Dict[str, str]]
    ) -> Optional[str]:
        """Extract definition or direct answer about the keyword"""
        keyword_lower = keyword.lower()
        
        for context in contexts:
            text = context.get('text', '')
            doc_name = context.get('doc_name', 'Unknown Document')
            page = context.get('page', 'N/A')
            
            text_lower = text.lower()
            
            # Look for definition patterns
            for pattern in self.definition_patterns:
                if pattern in text_lower and keyword_lower in text_lower:
                    # Extract the sentence containing the definition
                    sentences = self._split_sentences(text)
                    for sentence in sentences:
                        if pattern in sentence.lower() and keyword_lower in sentence.lower():
                            # Clean and format
                            clean_sentence = sentence.strip()
                            if not clean_sentence.endswith('.'):
                                clean_sentence += '.'
                            
                            citation = self._format_citation(doc_name, page)
                            return f"{clean_sentence} {citation}"
        
        # If no definition found, return first relevant sentence
        if contexts:
            first_context = contexts[0]
            text = first_context.get('text', '')
            doc_name = first_context.get('doc_name', 'Unknown Document')
            page = first_context.get('page', 'N/A')
            
            sentences = self._split_sentences(text)
            if sentences:
                first_sentence = sentences[0].strip()
                if not first_sentence.endswith('.'):
                    first_sentence += '.'
                
                citation = self._format_citation(doc_name, page)
                return f"{first_sentence} {citation}"
        
        return None
    
    def _extract_key_details(
        self,
        contexts: List[Dict[str, str]]
    ) -> List[str]:
        """Extract key facts and details from contexts"""
        details = []
        seen_facts = set()  # Avoid duplicates
        
        for context in contexts:
            text = context.get('text', '')
            doc_name = context.get('doc_name', 'Unknown Document')
            page = context.get('page', 'N/A')
            
            # Split into sentences
            sentences = self._split_sentences(text)
            
            for sentence in sentences:
                # Skip very short sentences
                if len(sentence.split()) < 5:
                    continue
                
                # Check if sentence contains fact patterns
                sentence_lower = sentence.lower()
                is_fact = any(pattern in sentence_lower for pattern in self.fact_patterns)
                
                # Check if sentence contains important info (names, dates, numbers)
                has_important_info = (
                    self._contains_numbers(sentence) or
                    self._contains_proper_nouns(sentence) or
                    is_fact
                )
                
                if has_important_info:
                    # Create a normalized version for duplicate detection
                    normalized = re.sub(r'\s+', ' ', sentence.lower().strip())
                    
                    if normalized not in seen_facts:
                        seen_facts.add(normalized)
                        citation = self._format_citation(doc_name, page)
                        clean_sentence = sentence.strip()
                        if not clean_sentence.endswith('.'):
                            clean_sentence += '.'
                        details.append(f"{clean_sentence} {citation}")
                        
                        # Limit to top 5 details
                        if len(details) >= 5:
                            break
            
            if len(details) >= 5:
                break
        
        return details
    
    def _extract_data_points(
        self,
        contexts: List[Dict[str, str]]
    ) -> List[str]:
        """Extract specific data points (numbers, percentages, money)"""
        data_points = []
        seen_data = set()
        
        for context in contexts:
            text = context.get('text', '')
            doc_name = context.get('doc_name', 'Unknown Document')
            page = context.get('page', 'N/A')
            
            # Find all numbers/data
            for pattern in self.number_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    data_value = match.group()
                    
                    # Get surrounding context (30 chars before and after)
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    context_snippet = text[start:end].strip()
                    
                    # Clean up
                    context_snippet = re.sub(r'\s+', ' ', context_snippet)
                    
                    if context_snippet not in seen_data:
                        seen_data.add(context_snippet)
                        citation = self._format_citation(doc_name, page)
                        data_points.append(f"{context_snippet} {citation}")
                        
                        # Limit to top 5 data points
                        if len(data_points) >= 5:
                            break
            
            if len(data_points) >= 5:
                break
        
        return data_points
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _format_citation(self, doc_name: str, page: str) -> str:
        """Format citation in [Doc Name, Page X] format"""
        if page and page != 'N/A':
            return f"[{doc_name}, Page {page}]"
        else:
            return f"[{doc_name}]"
    
    def _contains_numbers(self, text: str) -> bool:
        """Check if text contains numbers"""
        return bool(re.search(r'\d', text))
    
    def _contains_proper_nouns(self, text: str) -> bool:
        """Check if text contains proper nouns (capitalized words)"""
        # Look for capitalized words that aren't at sentence start
        words = text.split()
        for i, word in enumerate(words):
            if i > 0 and word[0].isupper() and len(word) > 1:
                return True
        return False
    
    def synthesize_from_template(
        self,
        user_keyword: str,
        concatenated_chunks: str,
        doc_metadata: Optional[List[Dict]] = None
    ) -> str:
        """
        Synthesize from concatenated text chunks (template format)
        
        Args:
            user_keyword: Original search keyword
            concatenated_chunks: All relevant text concatenated
            doc_metadata: Optional list of {doc_name, page} for each chunk
            
        Returns:
            Formatted summary
        """
        if not concatenated_chunks or not concatenated_chunks.strip():
            return (
                f"The uploaded documents do not contain specific details on "
                f"'{user_keyword}'."
            )
        
        # Split concatenated chunks back into individual contexts
        # Assume chunks are separated by double newlines or similar
        chunks = [c.strip() for c in concatenated_chunks.split('\n\n') if c.strip()]
        
        # Create context dicts
        contexts = []
        for i, chunk in enumerate(chunks):
            if doc_metadata and i < len(doc_metadata):
                meta = doc_metadata[i]
                contexts.append({
                    'text': chunk,
                    'doc_name': meta.get('doc_name', f'Document {i+1}'),
                    'page': meta.get('page', 'N/A')
                })
            else:
                contexts.append({
                    'text': chunk,
                    'doc_name': f'Document {i+1}',
                    'page': 'N/A'
                })
        
        return self.synthesize(user_keyword, contexts)


# Singleton instance
document_synthesizer = DocumentSynthesizer()


def synthesize_summary(
    user_keyword: str,
    relevant_contexts: List[Dict[str, str]]
) -> str:
    """
    Convenience function to generate summary
    
    Args:
        user_keyword: Search keyword
        relevant_contexts: List of context dicts
        
    Returns:
        Formatted summary with citations
    """
    return document_synthesizer.synthesize(user_keyword, relevant_contexts)


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("ANTIGRAVITY-SYNTHESIZE: Document Intelligence Engine")
    print("=" * 80)
    
    # Test case 1: Customer Churn
    test_contexts_1 = [
        {
            'text': "Customer churn rate is defined as the percentage of customers who stop using a service during a given time period. Our analysis shows a churn rate of 15% annually, which is higher than the industry average of 12%.",
            'doc_name': "Q4 Analytics Report",
            'page': "23"
        },
        {
            'text': "The primary reasons for customer churn include poor customer service (35%), high pricing (28%), and lack of features (22%). According to the survey, 67% of churned customers cited multiple reasons.",
            'doc_name': "Customer Feedback Analysis",
            'page': "8"
        },
        {
            'text': "Retention strategies implemented in Q3 resulted in a 5% reduction in churn. The most effective strategy was personalized outreach, which saved approximately $2.3 million in potential lost revenue.",
            'doc_name': "Retention Strategy Results",
            'page': "15"
        }
    ]
    
    print("\nTest 1: Customer Churn")
    print("-" * 80)
    summary1 = document_synthesizer.synthesize("customer churn", test_contexts_1)
    print(summary1)
    print("-" * 80)
    
    # Test case 2: Revenue Growth
    test_contexts_2 = [
        {
            'text': "Revenue growth for fiscal year 2024 reached 25%, exceeding our target of 20%. Total revenue was $45.2 million, up from $36.1 million in 2023.",
            'doc_name': "Annual Financial Report",
            'page': "5"
        },
        {
            'text': "The growth was primarily driven by new product launches, which contributed $6.5 million in additional revenue. Enterprise sales grew by 35%, while SMB segment grew by 18%.",
            'doc_name': "Revenue Breakdown",
            'page': "12"
        }
    ]
    
    print("\nTest 2: Revenue Growth")
    print("-" * 80)
    summary2 = document_synthesizer.synthesize("revenue growth", test_contexts_2)
    print(summary2)
    print("-" * 80)
    
    # Test case 3: No relevant data
    print("\nTest 3: No Relevant Data")
    print("-" * 80)
    summary3 = document_synthesizer.synthesize("quantum computing", [])
    print(summary3)
    print("-" * 80)
    
    print("\n" + "=" * 80)
    print("All tests completed successfully")
    print("=" * 80)
