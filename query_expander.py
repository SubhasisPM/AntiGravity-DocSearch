"""
Antigravity-Expand: Search Query Optimization Engine
Generates semantically rich search variations for better vector database retrieval
"""

import json
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)


class QueryExpander:
    """
    Expands user search keywords into multiple semantic variations
    to improve vector database search accuracy
    """
    
    def __init__(self):
        # Common question patterns
        self.question_patterns = {
            'what': ['what is', 'what are', 'what does', 'what means'],
            'how': ['how to', 'how does', 'how can'],
            'why': ['why is', 'why does', 'why are'],
            'when': ['when to', 'when should', 'when does'],
            'where': ['where is', 'where can', 'where to find']
        }
        
        # Business/technical synonym mappings
        self.synonym_map = {
            'churn': ['attrition', 'retention', 'customer loss', 'turnover'],
            'revenue': ['income', 'earnings', 'sales', 'profit'],
            'user': ['customer', 'client', 'subscriber', 'member'],
            'growth': ['expansion', 'increase', 'scaling', 'development'],
            'cost': ['expense', 'spending', 'budget', 'investment'],
            'performance': ['efficiency', 'productivity', 'metrics', 'KPI'],
            'data': ['information', 'analytics', 'statistics', 'insights'],
            'strategy': ['plan', 'approach', 'methodology', 'framework'],
            'risk': ['threat', 'vulnerability', 'exposure', 'liability'],
            'quality': ['standard', 'excellence', 'reliability', 'consistency']
        }
    
    def expand_query(self, user_keyword: str) -> Dict[str, List[str]]:
        """
        Generate 3 semantic variations of the search keyword
        
        Args:
            user_keyword: The original search term from user
            
        Returns:
            Dictionary with 'queries' key containing 3 variations
        """
        if not user_keyword or not user_keyword.strip():
            logging.warning("Empty keyword provided")
            return {"queries": [user_keyword, user_keyword, user_keyword]}
        
        keyword = user_keyword.strip().lower()
        
        # Variation 1: Direct keyword with context
        variation_1 = self._create_direct_variation(keyword)
        
        # Variation 2: Question form
        variation_2 = self._create_question_variation(keyword)
        
        # Variation 3: Conceptual expansion with synonyms
        variation_3 = self._create_conceptual_variation(keyword)
        
        result = {
            "queries": [
                variation_1,
                variation_2,
                variation_3
            ]
        }
        
        logging.info(f"Expanded '{user_keyword}' into {len(result['queries'])} variations")
        return result
    
    def _create_direct_variation(self, keyword: str) -> str:
        """
        Create direct keyword variation with context
        Examples:
        - "churn" -> "customer churn rate statistics"
        - "revenue" -> "revenue growth and trends"
        """
        # Check if keyword is already a phrase
        if len(keyword.split()) > 2:
            return keyword
        
        # Add contextual terms based on keyword type
        if any(term in keyword for term in ['rate', 'ratio', 'percentage']):
            return f"{keyword} statistics and metrics"
        elif any(term in keyword for term in ['customer', 'user', 'client']):
            return f"{keyword} data and analytics"
        elif any(term in keyword for term in ['revenue', 'cost', 'profit']):
            return f"{keyword} analysis and trends"
        else:
            # Generic enhancement
            words = keyword.split()
            if len(words) == 1:
                return f"{keyword} information and details"
            else:
                return f"{keyword} overview"
    
    def _create_question_variation(self, keyword: str) -> str:
        """
        Convert keyword to question form
        Examples:
        - "churn" -> "why are customers leaving the platform?"
        - "revenue" -> "what is the revenue growth trend?"
        """
        keyword_lower = keyword.lower()
        
        # Specific question patterns for common business terms
        question_patterns = {
            'churn': "why are customers leaving the platform?",
            'attrition': "why is customer attrition increasing?",
            'revenue': "what is the revenue growth trend?",
            'growth': "how can we achieve growth?",
            'cost': "what are the main cost drivers?",
            'performance': "how is the performance measured?",
            'risk': "what are the key risks?",
            'quality': "how do we ensure quality?",
            'data': "what does the data show?",
            'user': "who are our users?",
            'customer': "what do customers need?",
            'strategy': "what is the strategy?",
            'metric': "what metrics should we track?",
            'trend': "what are the current trends?",
            'issue': "what issues have been identified?",
            'solution': "what solutions are available?",
            'feature': "what features are included?",
            'process': "how does the process work?",
            'system': "how does the system function?",
            'report': "what does the report show?"
        }
        
        # Check for exact matches
        for key, question in question_patterns.items():
            if key in keyword_lower:
                return question
        
        # Generic question formation
        words = keyword.split()
        if len(words) == 1:
            # Single word - use "what is"
            return f"what is {keyword}?"
        else:
            # Multi-word - use "what are" or "how to"
            if any(word in keyword_lower for word in ['increase', 'improve', 'optimize', 'reduce']):
                return f"how to {keyword}?"
            else:
                return f"what are {keyword}?"
    
    def _create_conceptual_variation(self, keyword: str) -> str:
        """
        Expand with synonyms and related concepts
        Examples:
        - "churn" -> "customer retention and attrition data"
        - "revenue" -> "income and earnings analysis"
        """
        keyword_lower = keyword.lower()
        
        # Find synonyms from our map
        synonyms = []
        for key, syn_list in self.synonym_map.items():
            if key in keyword_lower:
                synonyms = syn_list[:2]  # Take first 2 synonyms
                break
        
        if synonyms:
            # Create phrase with synonyms
            if len(synonyms) >= 2:
                return f"{synonyms[0]} and {synonyms[1]} analysis"
            else:
                return f"{synonyms[0]} and {keyword} data"
        
        # If no synonyms found, create contextual expansion
        business_contexts = {
            'analysis': 'detailed analysis and insights',
            'report': 'comprehensive reporting and metrics',
            'data': 'data analytics and statistics',
            'trend': 'trends and patterns',
            'metric': 'key performance indicators',
            'rate': 'rates and percentages',
            'cost': 'costs and expenses',
            'time': 'timeline and schedule',
            'user': 'user behavior and engagement',
            'system': 'system architecture and design'
        }
        
        for key, expansion in business_contexts.items():
            if key in keyword_lower:
                return expansion
        
        # Default: add "related information"
        return f"{keyword} related information and context"
    
    def expand_to_json(self, user_keyword: str) -> str:
        """
        Generate expanded queries and return as JSON string
        
        Args:
            user_keyword: The original search term
            
        Returns:
            JSON string with expanded queries
        """
        result = self.expand_query(user_keyword)
        return json.dumps(result, indent=2)


# Singleton instance for easy import
query_expander = QueryExpander()


def expand_search_keyword(keyword: str) -> Dict[str, List[str]]:
    """
    Convenience function to expand a search keyword
    
    Args:
        keyword: User's search term
        
    Returns:
        Dictionary with 'queries' list containing 3 variations
    """
    return query_expander.expand_query(keyword)


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_keywords = [
        "churn",
        "revenue growth",
        "customer satisfaction",
        "data analysis",
        "system performance",
        "cost reduction"
    ]
    
    print("=" * 80)
    print("ANTIGRAVITY-EXPAND: Search Query Optimization Engine")
    print("=" * 80)
    
    for keyword in test_keywords:
        print(f"\nUSER_KEYWORD: \"{keyword}\"")
        print("-" * 80)
        result = query_expander.expand_to_json(keyword)
        print(result)
        print("-" * 80)
