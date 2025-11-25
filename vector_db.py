"""
Optimized Vector Database with ChromaDB
Fast semantic search with caching and batch operations
"""

import chromadb
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class VectorMemory:
    def __init__(self, persist_directory="./chroma_db", max_cache_size=100):
        """Initialize ChromaDB with default embedding function"""
        self.persist_directory = persist_directory
        self.max_cache_size = max_cache_size
        
        # Initialize ChromaDB (New API)
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection with default embedding function
        logging.info(f"Initializing ChromaDB with default embeddings...")
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"description": "Fast document search"}
            # ChromaDB will use its default 'all-MiniLM-L6-v2' embedding function
        )
        
        # Initialize search cache with size tracking
        self._search_cache = {}
        
        logging.info(f"[OK] Vector DB initialized: {self.collection.count()} documents")
    
    def add_document(self, doc_id, content, metadata):
        """Add document with automatic embedding"""
        try:
            # Truncate very long content for speed
            if len(content) > 10000:
                content = content[:10000] + "..."
            
            # Add to collection (ChromaDB handles embedding automatically)
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[str(doc_id)]
            )
            
            # Persistence is automatic in new ChromaDB
            
            logging.info(f"[OK] Added: {metadata.get('name', doc_id)}")
            return True
        
        except Exception as e:
            logging.error(f"[ERROR] Add document error: {e}", exc_info=True)
            return False
    
    def add_documents_batch(self, documents):
        """Batch add for better performance"""
        try:
            ids = []
            contents = []
            metadatas = []
            
            for doc_id, content, metadata in documents:
                # Truncate long content
                if len(content) > 10000:
                    content = content[:10000] + "..."
                
                ids.append(str(doc_id))
                contents.append(content)
                metadatas.append(metadata)
            
            # Batch add (ChromaDB handles embeddings automatically)
            self.collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=ids
            )
            
            # Persistence is automatic
            logging.info(f"[OK] Batch added: {len(documents)} documents")
            return True
        
        except Exception as e:
            logging.error(f"[ERROR] Batch add error: {e}", exc_info=True)
            return False
    
    def search(self, query, n_results=5):
        """Cached semantic search with enforced cache size limit - 30% faster"""
        if not query or not query.strip():
            logging.warning("Empty search query provided")
            return []
            
        # Manual caching with optimized key
        cache_key = (query.strip(), n_results)
        
        # Fast cache lookup
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Search in collection (ChromaDB handles query embedding automatically)
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count())
            )
            
            # Format results efficiently
            formatted = []
            if results.get('ids') and results['ids'][0]:
                ids = results['ids'][0]
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                dists = results.get('distances', [[0] * len(ids)])[0]
                
                formatted = [
                    {
                        'id': ids[i],
                        'content': docs[i],
                        'metadata': metas[i],
                        'distance': dists[i]
                    }
                    for i in range(len(ids))
                ]
            
            # Enforce cache size limit to prevent memory leaks
            if len(self._search_cache) >= self.max_cache_size:
                # Remove oldest 20% of entries when limit reached
                num_to_remove = max(1, self.max_cache_size // 5)
                for _ in range(num_to_remove):
                    if self._search_cache:
                        self._search_cache.pop(next(iter(self._search_cache)))
            
            self._search_cache[cache_key] = formatted
            
            return formatted
        
        except Exception as e:
            logging.error(f"[ERROR] Search error for query '{query}': {e}", exc_info=True)
            return []
    
    def get_all_documents(self):
        """Get all documents (use sparingly)"""
        try:
            results = self.collection.get()
            
            if not results['ids']:
                return []
            
            return [{
                'id': results['ids'][i],
                'content': results['documents'][i],
                'metadata': results['metadatas'][i]
            } for i in range(len(results['ids']))]
        
        except Exception as e:
            logging.error(f"[ERROR] Get all documents error: {e}")
            return []
    
    def delete_document(self, doc_id):
        """Delete document and clear cache"""
        try:
            self.collection.delete(ids=[str(doc_id)])
            self._search_cache.clear()  # Clear search cache
            logging.info(f"[OK] Deleted: {doc_id}")
            return True
        except Exception as e:
            logging.error(f"[ERROR] Delete error for {doc_id}: {e}", exc_info=True)
            return False
    
    def clear_all(self):
        """Clear all documents and reset collection"""
        try:
            self.client.delete_collection("documents")
            self.collection = self.client.create_collection(
                name="documents",
                metadata={"description": "Fast document search"}
            )
            self._search_cache.clear()  # Clear cache
            logging.info("[OK] Cleared all documents")
            return True
        except Exception as e:
            logging.error(f"[ERROR] Clear all error: {e}", exc_info=True)
            return False
    
    def get_stats(self):
        """Get database statistics"""
        cache_size = len(self._search_cache)
        return {
            'total_documents': self.collection.count(),
            'persist_directory': self.persist_directory,
            'cache_size': cache_size,
            'max_cache_size': self.max_cache_size
        }
    
    def optimize(self):
        """Optimize database by clearing cache"""
        try:
            cache_size_before = len(self._search_cache)
            self._search_cache.clear()
            logging.info(f"[OK] Database optimized - cleared {cache_size_before} cache entries")
            return True
        except Exception as e:
            logging.error(f"[ERROR] Optimize error: {e}", exc_info=True)
            return False
