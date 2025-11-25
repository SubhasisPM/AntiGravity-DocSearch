"""
Antigravity-Filter: Relevance Filtering Engine
Determines if document excerpts contain relevant information to answer user queries
"""

import re
import logging
from typing import Literal

logging.basicConfig(level=logging.INFO)


class RelevanceFilter:
    """
    Filters search results by determining if document excerpts
    are truly relevant to the user's query
    """
    
    def __init__(self):
        # Patterns that indicate low-quality matches
        self.noise_patterns = [
            r'table of contents',
            r'index',
            r'page \d+',
            r'chapter \d+',
            r'section \d+',
            r'copyright',
            r'all rights reserved',
            r'footer',
            r'header',
            r'references',
            r'bibliography',
            r'see also',
            r'^\d+$',  # Just page numbers
            r'^[a-z]\.$',  # Just list markers
        ]
        
        # Patterns that indicate high-quality matches
        self.quality_patterns = [
            r'is defined as',
            r'refers to',
            r'means',
            r'indicates',
            r'shows that',
            r'demonstrates',
            r'according to',
            r'data shows',
            r'results in',
            r'caused by',
            r'leads to',
            r'because',
            r'therefore',
            r'consequently',
            r'for example',
            r'such as',
            r'including',
        ]
        
        # Stop words that don't add meaning
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'it', 'its', 'they', 'them', 'their'
        }
    
    def filter_relevance(
        self, 
        user_query: str, 
        document_excerpt: str
    ) -> Literal["YES", "NO"]:
        """
        Determine if document excerpt is relevant to user query
        
        Args:
            user_query: The search query from user
            document_excerpt: Text chunk from document
            
        Returns:
            "YES" if relevant, "NO" if not relevant
        """
        # Input validation
        if not user_query or not user_query.strip():
            logging.warning("Empty query provided")
            return "NO"
        
        if not document_excerpt or not document_excerpt.strip():
            logging.warning("Empty excerpt provided")
            return "NO"
        
        query = user_query.strip().lower()
        excerpt = document_excerpt.strip().lower()
        
        # Check 1: Is excerpt too short to be meaningful?
        if len(excerpt) < 20:
            return "NO"
        
        # Check 2: Is it just noise (TOC, footer, etc.)?
        if self._is_noise(excerpt):
            return "NO"
        
        # Check 3: Extract query keywords
        query_keywords = self._extract_keywords(query)
        
        if not query_keywords:
            # If no meaningful keywords, do basic presence check
            return "YES" if query in excerpt else "NO"
        
        # Check 4: Do query keywords appear in excerpt?
        keyword_matches = sum(1 for kw in query_keywords if kw in excerpt)
        keyword_coverage = keyword_matches / len(query_keywords)
        
        if keyword_coverage == 0:
            # No keywords found at all
            return "NO"
        
        # Check 5: Is it just a passing mention or actual content?
        if keyword_coverage < 0.3:
            # Less than 30% of keywords - likely not relevant
            return "NO"
        
        # Check 6: Check for quality indicators
        has_quality_indicators = self._has_quality_indicators(excerpt)
        
        # Check 7: Check for contextual relevance
        has_context = self._has_contextual_relevance(query_keywords, excerpt)
        
        # Decision logic
        if keyword_coverage >= 0.5:
            # More than 50% keyword match - likely relevant
            return "YES"
        
        if keyword_coverage >= 0.3 and (has_quality_indicators or has_context):
            # 30-50% match with quality indicators - relevant
            return "YES"
        
        if has_quality_indicators and has_context:
            # Has both quality and context - relevant
            return "YES"
        
        # Default: not relevant enough
        return "NO"
    
    def _is_noise(self, text: str) -> bool:
        """Check if text is just noise (TOC, footer, etc.)"""
        text_lower = text.lower()
        
        for pattern in self.noise_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Check if it's mostly numbers and punctuation
        alphanumeric = sum(c.isalnum() for c in text)
        if alphanumeric < len(text) * 0.5:
            return True
        
        return False
    
    def _extract_keywords(self, query: str) -> list:
        """Extract meaningful keywords from query"""
        # Remove punctuation and split
        words = re.findall(r'\b[a-z]+\b', query.lower())
        
        # Filter out stop words and short words
        keywords = [
            w for w in words 
            if w not in self.stop_words and len(w) > 2
        ]
        
        return keywords
    
    def _has_quality_indicators(self, text: str) -> bool:
        """Check if text has quality indicators (definitions, explanations)"""
        text_lower = text.lower()
        
        for pattern in self.quality_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _has_contextual_relevance(self, keywords: list, text: str) -> bool:
        """
        Check if keywords appear in meaningful context
        (not just isolated mentions)
        """
        text_lower = text.lower()
        
        # Check if keywords appear near each other
        for i, kw1 in enumerate(keywords):
            for kw2 in keywords[i+1:]:
                # Find positions of both keywords
                pos1 = text_lower.find(kw1)
                pos2 = text_lower.find(kw2)
                
                if pos1 != -1 and pos2 != -1:
                    # If keywords are within 100 characters, they're contextually related
                    if abs(pos1 - pos2) < 100:
                        return True
        
        # Check if keywords appear in sentences with quality indicators
        sentences = re.split(r'[.!?]+', text_lower)
        for sentence in sentences:
            keyword_count = sum(1 for kw in keywords if kw in sentence)
            if keyword_count >= 2:
                # Multiple keywords in same sentence - good context
                return True
        
        return False
    
    def filter_batch(
        self, 
        user_query: str, 
        excerpts: list[str]
    ) -> list[dict]:
        """
        Filter multiple excerpts and return results
        
        Args:
            user_query: The search query
            excerpts: List of document excerpts
            
        Returns:
            List of dicts with excerpt and relevance decision
        """
        results = []
        
        for i, excerpt in enumerate(excerpts):
            decision = self.filter_relevance(user_query, excerpt)
            results.append({
                'excerpt_id': i,
                'excerpt': excerpt,
                'relevant': decision,
                'is_relevant': decision == "YES"
            })
        
        # Log statistics
        relevant_count = sum(1 for r in results if r['is_relevant'])
        logging.info(
            f"Filtered {len(excerpts)} excerpts: "
            f"{relevant_count} relevant, {len(excerpts) - relevant_count} filtered out"
        )
        
        return results
    
    def get_relevant_only(
        self, 
        user_query: str, 
        excerpts: list[str]
    ) -> list[str]:
        """
        Return only relevant excerpts
        
        Args:
            user_query: The search query
            excerpts: List of document excerpts
            
        Returns:
            List of relevant excerpts only
        """
        results = self.filter_batch(user_query, excerpts)
        return [r['excerpt'] for r in results if r['is_relevant']]


# Singleton instance
relevance_filter = RelevanceFilter()


def filter_relevance(user_query: str, document_excerpt: str) -> Literal["YES", "NO"]:
    """
    Convenience function to filter a single excerpt
    
    Args:
        user_query: The search query
        document_excerpt: Text chunk from document
        
    Returns:
        "YES" if relevant, "NO" if not
    """
    return relevance_filter.filter_relevance(user_query, document_excerpt)


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("ANTIGRAVITY-FILTER: Relevance Filtering Engine")
    print("=" * 80)
    
    # Test cases
    test_cases = [
        {
            "query": "customer churn rate",
            "excerpt": "The customer churn rate is defined as the percentage of customers who stop using a service during a given time period. Our analysis shows a churn rate of 15% annually.",
            "expected": "YES"
        },
        {
            "query": "customer churn rate",
            "excerpt": "Table of Contents: Chapter 3 - Customer Churn... Page 45",
            "expected": "NO"
        },
        {
            "query": "revenue growth",
            "excerpt": "Revenue growth has been strong this quarter, with a 25% increase compared to last year. This growth is attributed to new product launches.",
            "expected": "YES"
        },
        {
            "query": "revenue growth",
            "excerpt": "See also: revenue, growth, profit margins",
            "expected": "NO"
        },
        {
            "query": "Apple stock price",
            "excerpt": "The best apple pie recipe includes fresh apples and cinnamon.",
            "expected": "NO"
        },
        {
            "query": "machine learning algorithms",
            "excerpt": "Machine learning algorithms such as neural networks and decision trees are used for pattern recognition. These algorithms learn from data.",
            "expected": "YES"
        },
        {
            "query": "data analysis",
            "excerpt": "45",
            "expected": "NO"
        },
        {
            "query": "customer satisfaction",
            "excerpt": "Customer satisfaction scores improved by 20% after implementing the new feedback system. Customers reported higher satisfaction with response times.",
            "expected": "YES"
        }
    ]
    
    print("\nRunning test cases...\n")
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        query = test['query']
        excerpt = test['excerpt']
        expected = test['expected']
        
        result = relevance_filter.filter_relevance(query, excerpt)
        
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"Test {i}: {status}")
        print(f"  Query: '{query}'")
        print(f"  Excerpt: '{excerpt[:60]}...'")
        print(f"  Expected: {expected}, Got: {result}")
        print()
    
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
