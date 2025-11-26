# ingestion.py
"""Document ingestion pipeline.

- Normalizes supported formats (PDF, HTML, CSV/Excel spreadsheets) to plain text.
- Performs semantic chunking (paragraph based) and fixed-size token chunking with overlap.
- Generates metadata for each chunk.
- Embeds chunks using OpenAI embeddings if API key is present, otherwise falls back to a local SentenceTransformer model.
- Stores chunks in the vector DB (Chroma) with metadata.
- Updates a BM25 sparse index for lexical search.
"""

import os
import logging
import mimetypes
from typing import List, Dict, Any

import pandas as pd
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

# Local embedding fallback
from sentence_transformers import SentenceTransformer

# Import vector DB wrapper
from vector_db import VectorMemory

# Sparse index (BM25)
from rank_bm25 import BM25Okapi

# LLM key handling
from rag_llm import RAGLLMIntegration

# Initialize logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Global objects (singleton for the app lifetime)
vector_store = VectorMemory()
# BM25 will be built on the fly; we keep documents' tokenized texts
bm25_corpus: List[List[str]] = []
chunk_id_counter = 0

# ---------------------------------------------------------------------------
# Normalization utilities
# ---------------------------------------------------------------------------

def _read_pdf(file_path: str) -> str:
    """Extract text from a PDF using PyPDF2."""
    try:
        reader = PdfReader(file_path)
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text)
    except Exception as e:
        logging.error(f"[ERROR] PDF extraction failed for {file_path}: {e}")
        return ""


def _read_html(file_path: str) -> str:
    """Extract visible text from an HTML file using BeautifulSoup."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(separator="\n")
    except Exception as e:
        logging.error(f"[ERROR] HTML extraction failed for {file_path}: {e}")
        return ""


def _read_spreadsheet(file_path: str) -> str:
    """Read CSV or Excel and convert to a plain‑text representation.
    Each row becomes a line of tab‑separated values.
    """
    try:
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        # Convert dataframe to a string, one row per line
        return "\n".join(df.apply(lambda row: "\t".join(row.astype(str)), axis=1).tolist())
    except Exception as e:
        logging.error(f"[ERROR] Spreadsheet extraction failed for {file_path}: {e}")
        return ""


def normalize_file(file_path: str) -> str:
    """Detect file type and return cleaned plain text.
    Supports PDF, HTML, CSV, XLSX, and plain text.
    """
    mime, _ = mimetypes.guess_type(file_path)
    if mime:
        if mime == "application/pdf" or file_path.lower().endswith('.pdf'):
            return _read_pdf(file_path)
        if mime == "text/html" or file_path.lower().endswith('.html'):
            return _read_html(file_path)
        if mime in ("text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
            return _read_spreadsheet(file_path)
    # Fallback to plain‑text read
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"[ERROR] Could not read file {file_path}: {e}")
        return ""

# ---------------------------------------------------------------------------
# Chunking utilities
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Very simple whitespace tokenization used for BM25 and fixed‑size chunking."""
    return text.split()


def semantic_chunks(text: str) -> List[str]:
    """Split text into paragraphs (semantic units)."""
    # Paragraphs are separated by double newlines
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs


def fixed_size_chunks(text: str, chunk_tokens: int = 500, overlap: int = 75) -> List[str]:
    """Create overlapping token chunks of a given size.
    Overlap is expressed in tokens.
    """
    tokens = _tokenize(text)
    if not tokens:
        return []
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_tokens, len(tokens))
        chunk = " ".join(tokens[start:end])
        chunks.append(chunk)
        # Move start forward with overlap
        start = end - overlap if end - overlap > start else end
    return chunks

# ---------------------------------------------------------------------------
# Embedding utilities
# ---------------------------------------------------------------------------

# Load a lightweight local model once (fallback)
_local_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Return embeddings for a list of texts.
    Uses OpenAI embeddings if an API key is configured, otherwise the local model.
    """
    # Detect OpenAI key via environment (the RAGLLMIntegration already loads it)
    llm = RAGLLMIntegration(provider="openai", api_key=None, model="text-embedding-ada-002")
    if llm.provider.value == "openai" and llm.api_key:
        # OpenAI embeddings endpoint
        import openai
        try:
            response = openai.Embedding.create(model="text-embedding-ada-002", input=texts)
            return [e["embedding"] for e in response["data"]]
        except Exception as e:
            logging.error(f"[ERROR] OpenAI embedding failed: {e}")
    # Fallback to local model
    return _local_model.encode(texts).tolist()

# ---------------------------------------------------------------------------
# Indexing functions
# ---------------------------------------------------------------------------

def index_document(file_path: str, doc_id: str, title: str = None) -> None:
    """Process a file, generate chunks, embed them, and store in both vector and BM25 indexes.
    Metadata stored per chunk includes:
        doc_id, chunk_id, chunk_start, chunk_end, title, section (if any).
    """
    global chunk_id_counter, bm25_corpus
    raw_text = normalize_file(file_path)
    if not raw_text:
        logging.warning(f"[WARN] No text extracted from {file_path}")
        return

    # First semantic split, then fixed‑size chunking on each paragraph
    paragraphs = semantic_chunks(raw_text)
    all_chunks = []
    for para in paragraphs:
        # Fixed‑size token chunks within paragraph
        para_chunks = fixed_size_chunks(para)
        all_chunks.extend(para_chunks)

    if not all_chunks:
        logging.warning(f"[WARN] No chunks generated for {file_path}")
        return

    # Generate embeddings
    embeddings = embed_texts(all_chunks)

    # Store in vector DB with metadata
    for i, (chunk, emb) in enumerate(zip(all_chunks, embeddings)):
        chunk_id = f"{doc_id}_c{chunk_id_counter}"
        chunk_id_counter += 1
        metadata = {
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "title": title or os.path.basename(file_path),
            "chunk_index": i,
            # Approximate character offsets (could be refined)
            "chunk_start": raw_text.find(chunk),
            "chunk_end": raw_text.find(chunk) + len(chunk),
        }
        # Add to vector store (Chroma handles embedding internally, but we pass the text and metadata)
        vector_store.add_document(chunk_id, chunk, metadata)
        # Keep raw text for BM25
        bm25_corpus.append(_tokenize(chunk))

    logging.info(f"[OK] Indexed document {doc_id} with {len(all_chunks)} chunks")

# ---------------------------------------------------------------------------
# Query utilities (lightweight placeholders)
# ---------------------------------------------------------------------------

def rewrite_query(query: str) -> str:
    """Placeholder for LLM‑based query rewriting. Currently returns the original query.
    In the future this could call the LLM to rephrase or expand the query.
    """
    return query

def retrieve(query: str, top_k: int = 20) -> List[Dict[str, Any]]:
    """Hybrid retrieval: dense (vector) + sparse (BM25) then simple merge.
    Returns a list of candidate chunks with combined scores.
    """
    # Dense retrieval
    dense_hits = vector_store.search(query, n_results=top_k)
    # Sparse retrieval using BM25
    tokenized_q = _tokenize(query)
    bm25 = BM25Okapi(bm25_corpus)
    bm25_scores = bm25.get_scores(tokenized_q)
    # Get top indices
    top_sparse_idx = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
    # Build result list
    results = []
    # Add dense hits (they already contain metadata)
    for hit in dense_hits:
        results.append({"source": "dense", "score": -hit.get("distance", 0), "metadata": hit.get("metadata", {}), "content": hit.get("content", "")})
    # Add sparse hits
    for idx in top_sparse_idx:
        # Retrieve the original chunk text from bm25_corpus (join tokens)
        chunk_text = " ".join(bm25_corpus[idx])
        results.append({"source": "sparse", "score": bm25_scores[idx], "metadata": {}, "content": chunk_text})
    # Simple deduplication by content hash (placeholder)
    seen = set()
    unique = []
    for r in results:
        h = hash(r["content"])
        if h not in seen:
            seen.add(h)
            unique.append(r)
    # Sort by score descending
    unique.sort(key=lambda x: x["score"], reverse=True)
    return unique[:top_k]

# End of ingestion.py
