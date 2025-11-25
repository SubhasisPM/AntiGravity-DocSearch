# Enhanced Search Functionality - DocSearch

## Overview
The search functionality in DocSearch has been significantly enhanced to provide more relevant results with better context understanding and intelligent summarization.

## New Features

### 1. **Intelligent Context Extraction**
- Finds all occurrences of search terms in documents
- Extracts complete sentences containing the search terms
- Shows the actual context where words appear
- Provides up to 3 context snippets per document

### 2. **Keyword Identification**
- Automatically extracts related keywords from document contexts
- Filters out common stop words
- Identifies the most relevant terms associated with your search
- Displays up to 8 related keywords per result

### 3. **Enhanced Summarization**
- Generates intelligent summaries explaining what the search term means in context
- Shows:
  - Number of occurrences
  - First occurrence context
  - Additional context snippets
  - Related terminology

### 4. **Improved Relevance Scoring**
- **Semantic Similarity** (50% weight): Uses vector embeddings for meaning-based matching
- **Exact Word Match** (30% weight): Rewards documents containing exact search terms
- **Frequency Score** (20% weight): Considers how often terms appear
- Results are ranked from 0-100% relevance

### 5. **Visual Enhancements**
- **Relevance Badges**: Visual indicators (High/Medium/Low)
- **Keyword Tags**: Clickable tags for related terms
- **Context Snippets**: Highlighted excerpts showing word usage
- **Summary Cards**: Comprehensive summaries for each result

## How It Works

### Backend (Python)
**File**: `enhanced_search.py`

The `EnhancedSearch` class provides:

1. `find_word_contexts()` - Locates all word occurrences with surrounding context
2. `extract_keywords_from_context()` - Identifies important related terms
3. `generate_summary()` - Creates intelligent summaries
4. `calculate_relevance_score()` - Computes multi-factor relevance scores
5. `enhance_search_results()` - Orchestrates all enhancements

### Integration (Flask)
**File**: `app.py`

The `/search` endpoint now:
- Performs vector database search (semantic similarity)
- Applies enhanced search processing
- Returns enriched results with:
  - Context snippets
  - Related keywords
  - Detailed summaries
  - Relevance scores

### Frontend (JavaScript)
**File**: `static/app.js`

The `displayResults()` function now shows:
- **Summary Section**: Multi-line summaries with context
- **Keywords Section**: Related terms as interactive tags
- **Contexts Section**: Actual excerpts from documents
- **Metadata**: Occurrence count and relevance badges

## Example Search Result

When you search for "machine learning", you might see:

```
📚 Found 'machine learning' in 2 document(s). Most relevant: AI_Research.pdf

The word 'machine learning' appears 5 times in the document.

First occurrence context: "Machine learning algorithms can automatically improve through experience..."

🔑 Key concepts: algorithms, neural, training, models, data, prediction

📝 Context Snippets:
- "...machine learning is a subset of artificial intelligence that enables..."
- "...deep learning, a branch of machine learning, uses neural networks..."

Score: 95%
Relevance: High
```

## Benefits

1. **More Relevant Results**: Multi-factor scoring ensures best matches appear first
2. **Better Understanding**: Context and summaries help you understand search term usage
3. **Related Discovery**: Keywords help discover related concepts
4. **Time Saving**: Summaries let you quickly assess relevance without opening documents

## Configuration

The enhanced search module is automatically initialized in `app.py`. No configuration needed!

If vector database dependencies are missing, the system gracefully falls back to basic search.

## Technical Details

### Dependencies
- `re` - Regular expressions for text processing
- `collections.Counter` - Frequency counting
- No additional installs required!

### Performance
- Context extraction: O(n) where n = document length
- Keyword extraction: O(m) where m = context length
- Caching: Search results are cached for repeated queries

### Customization

You can customize these parameters in `enhanced_search.py`:

```python
# Context window size (characters on each side of found word)
context_window=150

# Maximum sentences to extract
max_sentences=2

# Number of top keywords
top_n=10
```

## Future Enhancements

Planned improvements:
- [ ] Highlighting of search terms in context snippets
- [ ] Export search results to different formats
- [ ] Search history and saved searches
- [ ] Advanced filtering options
- [ ] Multi-language support

## Troubleshooting

**Q: Search is slow**
A: For large documents, the system truncates content to 10,000 characters for faster processing.

**Q: No keywords showing**
A: The system filters out common words. Try searching for more specific terms.

**Q: Low relevance scores**
A: This means the term appears but isn't semantically central to the document's main topic.

## Credits

Enhanced search powered by:
- Sentence Transformers ('all-MiniLM-L6-v2') for semantic search
- ChromaDB for vector storage
- Custom NLP algorithms for context extraction and summarization

---

**Last Updated**: 2025-11-24
**Version**: 1.0.0
