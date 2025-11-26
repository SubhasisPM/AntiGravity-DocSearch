"""
Enhanced Ingestion Module with Multi-Granularity Chunking

Features:
- Multi-granularity chunking (small, medium, large)
- Enhanced metadata extraction
- Document structure analysis
- Table and code block detection
- Document hashing for deduplication
"""

import os
import hashlib
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import mimetypes

import pandas as pd
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

# Import vector DB wrapper
from vector_db import VectorMemory

# Import advanced retrieval for hybrid indexing
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    logging.warning("rank_bm25 not available, BM25 search disabled")
    BM25_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@dataclass
class ChunkGranularity:
    """Chunk size configurations"""
    SMALL = 256   # tokens - for precise facts
    MEDIUM = 512  # tokens - balanced chunks  
    LARGE = 1024  # tokens - broader context


@dataclass
class DocumentMetadata:
    """Enhanced document metadata"""
    doc_id: str
    title: str
    file_path: str
    file_size: int
    file_hash: str
    mime_type: Optional[str]
    num_pages: Optional[int]
    has_tables: bool
    has_code: bool
    section_count: int
    indexed_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'doc_id': self.doc_id,
            'title': self.title,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'mime_type': self.mime_type,
            'num_pages': self.num_pages,
            'has_tables': self.has_tables,
            'has_code': self.has_code,
            'section_count': self.section_count,
            'indexed_at': self.indexed_at
        }


class EnhancedIngestionPipeline:
    """
    Enhanced document ingestion with multi-granularity chunking
    """
    
    def __init__(self, vector_db: VectorMemory):
        """
        Initialize ingestion pipeline
        
        Args:
            vector_db: VectorMemory instance
        """
        self.vector_db = vector_db
        self.local_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.chunk_id_counter = 0
        self.bm25_corpus = []
        self.bm25_index = None
        
        logging.info("Enhanced Ingestion Pipeline initialized")
    
    def index_document(
        self,
        file_path: str,
        doc_id: str,
        title: Optional[str] = None,
        enable_multi_granularity: bool = True
    ) -> DocumentMetadata:
        """
        Index a document with multi-granularity chunking
        
        Args:
            file_path: Path to document file
            doc_id: Unique document ID
            title: Document title (optional)
            enable_multi_granularity: Enable multi-size chunking
            
        Returns:
            DocumentMetadata with indexing information
        """
        logging.info(f"Indexing document: {file_path}")
        
        # Extract document text and metadata
        raw_text = self.normalize_file(file_path)
        if not raw_text:
            logging.warning(f"No text extracted from {file_path}")
            return None
        
        # Analyze document structure
        structure = self._analyze_structure(raw_text)
        
        # Calculate file hash
        file_hash = self._calculate_hash(file_path)
        
        # Create document metadata
        doc_metadata = DocumentMetadata(
            doc_id=doc_id,
            title=title or os.path.basename(file_path),
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_hash=file_hash,
            mime_type=mimetypes.guess_type(file_path)[0],
            num_pages=structure.get('num_pages'),
            has_tables=structure.get('has_tables', False),
            has_code=structure.get('has_code', False),
            section_count=len(structure.get('sections', [])),
            indexed_at=datetime.now().isoformat()
        )
        
        # Generate chunks with different granularities
        if enable_multi_granularity:
            all_chunks = self._multi_granularity_chunks(raw_text, structure)
        else:
            all_chunks = self._fixed_size_chunks(raw_text, ChunkGranularity.MEDIUM)
            all_chunks = [{'text': chunk, 'granularity': 'medium', 'tokens': ChunkGranularity.MEDIUM} 
                         for chunk in all_chunks]
        
        if not all_chunks:
            logging.warning(f"No chunks generated for {file_path}")
            return doc_metadata
        
        # Generate embeddings
        chunk_texts = [chunk['text'] for chunk in all_chunks]
        embeddings = self._embed_texts(chunk_texts)
        
        # Index chunks in vector DB
        for i, (chunk_data, embedding) in enumerate(zip(all_chunks, embeddings)):
            chunk_id = f"{doc_id}_c{self.chunk_id_counter}"
            self.chunk_id_counter += 1
            
            # Build chunk metadata
            chunk_metadata = {
                **doc_metadata.to_dict(),
                'chunk_id': chunk_id,
                'chunk_index': i,
                'chunk_size': chunk_data['granularity'],
                'granularity_tokens': chunk_data['tokens'],
                'section_header': chunk_data.get('section_header'),
                'chunk_start': chunk_data.get('start_pos', 0),
                'chunk_end': chunk_data.get('end_pos', 0),
                'name': title or os.path.basename(file_path)  # For compatibility
            }
            
            # Add to vector store
            self.vector_db.add_document(
                doc_id=chunk_id,
                content=chunk_data['text'],
                metadata=chunk_metadata
            )
            
            # Add to BM25 corpus
            if BM25_AVAILABLE:
                self.bm25_corpus.append(self._tokenize(chunk_data['text']))
        
        # Rebuild BM25 index
        if BM25_AVAILABLE and self.bm25_corpus:
            self.bm25_index = BM25Okapi(self.bm25_corpus)
        
        logging.info(f"Indexed {len(all_chunks)} chunks for document {doc_id}")
        return doc_metadata
    
    def normalize_file(self, file_path: str) -> str:
        """
        Extract text from various file formats
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted text content
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # PDF files
        if mime_type == "application/pdf" or file_path.lower().endswith('.pdf'):
            return self._read_pdf(file_path)
        
        # HTML files
        if mime_type == "text/html" or file_path.lower().endswith('.html'):
            return self._read_html(file_path)
        
        # Spreadsheets (CSV, Excel)
        if mime_type in ("text/csv", "application/vnd.ms-excel", 
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
            return self._read_spreadsheet(file_path)
        
        # Plain text (default)
        return self._read_text(file_path)
    
    # ========================================================================
    # File Readers  
    # ========================================================================
    
    def _read_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        try:
            reader = PdfReader(file_path)
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n".join(text)
        except Exception as e:
            logging.error(f"PDF extraction failed for {file_path}: {e}")
            return ""
    
    def _read_html(self, file_path: str) -> str:
        """Extract text from HTML"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                # Remove scripts and styles
                for script in soup(["script", "style"]):
                    script.decompose()
                return soup.get_text(separator="\n")
        except Exception as e:
            logging.error(f"HTML extraction failed for {file_path}: {e}")
            return ""
    
    def _read_spreadsheet(self, file_path: str) -> str:
        """Extract text from spreadsheets"""
        try:
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Convert to text representation
            return "\n".join(df.apply(lambda row: "\t".join(row.astype(str)), axis=1).tolist())
        except Exception as e:
            logging.error(f"Spreadsheet extraction failed for {file_path}: {e}")
            return ""
    
    def _read_text(self, file_path: str) -> str:
        """Read plain text file"""
        try:
            with open(file_path, "r", encoding="utf-8", errors='ignore') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Text file read failed for {file_path}: {e}")
            return ""
    
    # ========================================================================
    # Document Analysis
    # ========================================================================
    
    def _analyze_structure(self, text: str) -> Dict[str, Any]:
        """
        Analyze document structure
        
        Returns:
            Dictionary with structure information
        """
        # Detect sections (headers)
        sections = self._extract_sections(text)
        
        # Detect tables
        has_tables = self._detect_tables(text)
        
        # Detect code blocks
        has_code = self._detect_code(text)
        
        # Estimate pages (rough estimate: 500 words per page)
        word_count = len(text.split())
        estimated_pages = max(1, word_count // 500)
        
        return {
            'sections': sections,
            'has_tables': has_tables,
            'has_code': has_code,
            'num_pages': estimated_pages,
            'word_count': word_count
        }
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract section headers from document"""
        sections = []
        
        # Common header patterns
        patterns = [
            r'^#+\s+(.+)$',  # Markdown headers
            r'^([A-Z][A-Z\s]+)$',  # ALL CAPS headers
            r'^(\d+\.?\s+[A-Z].+)$',  # Numbered sections
        ]
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line)
                if match and len(line) < 100:  # Headers are typically short
                    sections.append({
                        'header': line,
                        'line_num': i,
                        'position': text.find(line)
                    })
                    break
        
        return sections
    
    def _detect_tables(self, text: str) -> bool:
        """Detect if document contains tables"""
        # Look for table indicators: pipes, multiple tabs, grid patterns
        indicators = [
            r'\|.*\|.*\|',  # Markdown tables
            r'\t.*\t.*\t',  # Tab-separated tables
            r'─+\s*─+',  # Table borders
        ]
        
        for pattern in indicators:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_code(self, text: str) -> bool:
        """Detect if document contains code blocks"""
        # Look for code indicators
        indicators = [
            r'```',  # Fenced code blocks
            r'^\s{4,}\w+',  # Indented code
            r'(def|class|function|import|#include)\s+\w+',  # Programming keywords
        ]
        
        for pattern in indicators:
            if re.search(pattern, text, re.MULTILINE):
                return True
        
        return False
    
    # ========================================================================
    # Chunking Strategies
    # ========================================================================
    
    def _multi_granularity_chunks(
        self,
        text: str,
        structure: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate chunks at multiple granularities
        
        Returns:
            List of chunk dictionaries with metadata
        """
        all_chunks = []
        sections = structure.get('sections', [])
        
        # Generate chunks at each granularity
        for granularity_name, token_size in [
            ('small', ChunkGranularity.SMALL),
            ('medium', ChunkGranularity.MEDIUM),
            ('large', ChunkGranularity.LARGE)
        ]:
            chunks = self._fixed_size_chunks(text, chunk_tokens=token_size, overlap=75)
            
            for i, chunk_text in enumerate(chunks):
                # Find relevant section header
                section_header = self._find_section_header(text, chunk_text, sections)
                
                # Calculate position in document
                start_pos = text.find(chunk_text)
                end_pos = start_pos + len(chunk_text) if start_pos >= 0 else 0
                
                all_chunks.append({
                    'text': chunk_text,
                    'granularity': granularity_name,
                    'tokens': token_size,
                    'section_header': section_header,
                    'start_pos': start_pos,
                    'end_pos': end_pos
                })
        
        return all_chunks
    
    def _fixed_size_chunks(
        self,
        text: str,
        chunk_tokens: int = 512,
        overlap: int = 75
    ) -> List[str]:
        """
        Create overlapping token-based chunks
        
        Args:
            text: Text to chunk
            chunk_tokens: Target chunk size in tokens
            overlap: Overlap size in tokens
            
        Returns:
            List of chunk strings
        """
        tokens = self._tokenize(text)
        
        if not tokens:
            return []
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = min(start + chunk_tokens, len(tokens))
            chunk = " ".join(tokens[start:end])
            chunks.append(chunk)
            
            # Move with overlap
            start = end - overlap if end - overlap > start else end
        
        return chunks
    
    def _find_section_header(
        self,
        full_text: str,
        chunk_text: str,
        sections: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find the most relevant section header for a chunk"""
        chunk_pos = full_text.find(chunk_text)
        
        if chunk_pos < 0 or not sections:
            return None
        
        # Find the closest preceding section
        closest_section = None
        min_distance = float('inf')
        
        for section in sections:
            if section['position'] <= chunk_pos:
                distance = chunk_pos - section['position']
                if distance < min_distance:
                    min_distance = distance
                    closest_section = section['header']
        
        return closest_section
    
    # ========================================================================
    # Embeddings
    # ========================================================================
    
    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks
        
        Uses OpenAI if API key available, otherwise local model
        """
        try:
            # Try OpenAI embeddings
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            
            if api_key:
                openai.api_key = api_key
                response = openai.Embedding.create(
                    model="text-embedding-ada-002",
                    input=texts
                )
                return [e["embedding"] for e in response["data"]]
        except Exception as e:
            logging.debug(f"OpenAI embedding failed, using local model: {e}")
        
        # Fallback to local model
        return self.local_model.encode(texts).tolist()
    
    # ========================================================================
    # Utilities
    # ========================================================================
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace tokenization"""
        return text.split()
    
    def _calculate_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logging.error(f"Hash calculation failed for {file_path}: {e}")
            return ""


# ============================================================================
# Convenience Functions (for backward compatibility)
# ============================================================================

# Global instance
_pipeline = None

def get_pipeline(vector_db: VectorMemory = None) -> EnhancedIngestionPipeline:
    """Get or create ingestion pipeline instance"""
    global _pipeline
    if _pipeline is None:
        if vector_db is None:
            vector_db = VectorMemory()
        _pipeline = EnhancedIngestionPipeline(vector_db)
    return _pipeline


def index_document(file_path: str, doc_id: str, title: str = None) -> None:
    """
    Backward compatible index_document function
    
    Args:
        file_path: Path to document
        doc_id: Document ID
        title: Document title
    """
    pipeline = get_pipeline()
    pipeline.index_document(file_path, doc_id, title)


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Enhanced Ingestion Module - Testing")
    print("=" * 80)
    
    # Test document structure analysis
    test_text = """
# Introduction to Machine Learning

Machine learning is a subset of artificial intelligence.

## Supervised Learning

Supervised learning uses labeled data...

## Unsupervised Learning  

Unsupervised learning finds patterns without labels...

| Algorithm | Type | Accuracy |
|-----------|------|----------|
| SVM       | Supervised | 95% |
| K-Means   | Unsupervised | 85% |

```python
def train_model(data):
    return model.fit(data)
```
    """
    
    pipeline = EnhancedIngestionPipeline(VectorMemory())
    structure = pipeline._analyze_structure(test_text)
    
    print(f"\nDocument Analysis:")
    print(f"  Sections: {len(structure['sections'])}")
    print(f"  Has Tables: {structure['has_tables']}")
    print(f"  Has Code: {structure['has_code']}")
    print(f"  Word Count: {structure['word_count']}")
    
    # Test multi-granularity chunking
    chunks = pipeline._multi_granularity_chunks(test_text, structure)
    print(f"\nGenerated {len(chunks)} chunks:")
    
    granularity_counts = {}
    for chunk in chunks:
        gran = chunk['granularity']
        granularity_counts[gran] = granularity_counts.get(gran, 0) + 1
    
    for gran, count in granularity_counts.items():
        print(f"  {gran}: {count} chunks")
    
    print("\n" + "=" * 80)
    print("Test completed successfully")
    print("=" * 80)
