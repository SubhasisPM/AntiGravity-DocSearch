"""
Antigravity-Expand Usage Examples
Demonstrates how to use the query expansion feature
"""

import requests
import json

# Base URL for local development
BASE_URL = "http://localhost:5000"

def test_query_expansion(keyword):
    """Test the query expansion endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing Query Expansion for: '{keyword}'")
    print(f"{'='*80}")
    
    # Make API request
    response = requests.post(
        f"{BASE_URL}/expand-query",
        json={"keyword": keyword},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Success! Generated {len(result['queries'])} variations:\n")
        
        for i, query in enumerate(result['queries'], 1):
            print(f"  {i}. {query}")
        
        print(f"\nExpander Available: {result.get('expander_available', False)}")
        print(f"Original Keyword: {result.get('original_keyword', keyword)}")
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.text)
    
    return response.json() if response.status_code == 200 else None


def check_system_status():
    """Check if query expander is enabled"""
    print(f"\n{'='*80}")
    print("Checking System Status")
    print(f"{'='*80}")
    
    response = requests.get(f"{BASE_URL}/stats")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"\n✓ System Status:")
        print(f"  - Total Documents: {stats.get('total_documents', 0)}")
        print(f"  - Cache Size: {stats.get('cache_size', 0)}")
        print(f"  - Query Expander Enabled: {stats.get('query_expander_enabled', False)}")
    else:
        print(f"\n✗ Error: {response.status_code}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ANTIGRAVITY-EXPAND: API Usage Examples")
    print("="*80)
    print("\nMake sure the Flask app is running: python app.py")
    print("Then run this script to test the query expansion feature.")
    print("="*80)
    
    # Test keywords
    test_keywords = [
        "churn",
        "revenue growth",
        "customer satisfaction",
        "data analysis",
        "system performance"
    ]
    
    try:
        # Check system status first
        check_system_status()
        
        # Test each keyword
        for keyword in test_keywords:
            test_query_expansion(keyword)
            input("\nPress Enter to continue...")
        
        print(f"\n{'='*80}")
        print("✓ All tests completed successfully!")
        print(f"{'='*80}\n")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to Flask app.")
        print("Make sure the app is running: python app.py")
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
