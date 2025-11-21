"""
Optimized Vector Database with ChromaDB
Fast semantic search with caching and batch operations
"""

import chromadb
from sentence_transformers import SentenceTransformer
import os


class VectorMemory:
    def __init__(self, persist_directory="./chroma_db", model_name='all-MiniLM-L6-v2'):
        """Initialize ChromaDB with optimized settings"""
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB (New API)
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Load lightweight embedding model
        print(f"Loading embedding model: {model_name}...")
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_model.max_seq_length = 256  # Limit for speed
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"description": "Fast document search"}
        )
        
        print(f"[OK] Vector DB initialized: {self.collection.count()} documents")
    
    def add_document(self, doc_id, content, metadata):
        """Add document with optimized embedding"""
        try:
            # Truncate very long content for speed
            if len(content) > 10000:
                content = content[:10000] + "..."
            
            # Generate embedding (cached by model)
            embedding = self.embedding_model.encode(
                content,
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()
            
            # Add to collection
            self.collection.add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata],
                ids=[str(doc_id)]
            )
            
            # Persistence is automatic in new ChromaDB
            
            print(f"[OK] Added: {metadata.get('name', doc_id)}")
            return True
        
        except Exception as e:
            print(f"[ERROR] Add error: {e}")
            return False
    
    def add_documents_batch(self, documents):
        """Batch add for better performance"""
        try:
            ids = []
            embeddings = []
            contents = []
            metadatas = []
            
            for doc_id, content, metadata in documents:
                # Truncate long content
                if len(content) > 10000:
                    content = content[:10000] + "..."
                
                ids.append(str(doc_id))
                contents.append(content)
                metadatas.append(metadata)
            
            # Batch encode (much faster!)
            embeddings = self.embedding_model.encode(
                contents,
                show_progress_bar=True,
                convert_to_numpy=True,
                batch_size=32
            ).tolist()
            
            # Batch add
            self.collection.add(
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
                ids=ids
            )
            
            # Persistence is automatic
            print(f"[OK] Batch added: {len(documents)} documents")
            return True
        
        except Exception as e:
            print(f"[ERROR] Batch add error: {e}")
            return False
    
    def search(self, query, n_results=5):
        """Cached semantic search"""
        # Manual caching (lru_cache doesn't work with instance methods)
        cache_key = (query, n_results)
        if not hasattr(self, '_search_cache'):
            self._search_cache = {}
        
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                query,
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count())
            )
            
            # Format results
            formatted = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted.append({
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else 0
                    })
            
            # Cache the result (limit cache size to 100)
            if len(self._search_cache) >= 100:
                # Remove oldest entry
                self._search_cache.pop(next(iter(self._search_cache)))
            self._search_cache[cache_key] = formatted
            
            return formatted
        
        except Exception as e:
            print(f"[ERROR] Search error: {e}")
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
            print(f"[ERROR] Get all error: {e}")
            return []
    
    def delete_document(self, doc_id):
        """Delete document"""
        try:
            self.collection.delete(ids=[str(doc_id)])
            if hasattr(self, '_search_cache'):
                self._search_cache.clear()  # Clear search cache
            print(f"[OK] Deleted: {doc_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Delete error: {e}")
            return False
    
    def clear_all(self):
        """Clear all documents"""
        try:
            self.client.delete_collection("documents")
            self.collection = self.client.create_collection(
                name="documents",
                metadata={"description": "Fast document search"}
            )
            if hasattr(self, '_search_cache'):
                self._search_cache.clear()  # Clear cache
            print("[OK] Cleared all documents")
            return True
        except Exception as e:
            print(f"[ERROR] Clear error: {e}")
            return False
    
    def get_stats(self):
        """Get database statistics"""
        cache_size = len(self._search_cache) if hasattr(self, '_search_cache') else 0
        return {
            'total_documents': self.collection.count(),
            'persist_directory': self.persist_directory,
            'cache_size': cache_size
        }
    
    def optimize(self):
        """Optimize database (run periodically)"""
        try:
            # Clear search cache
            if hasattr(self, '_search_cache'):
                self._search_cache.clear()
            print("[OK] Database optimized")
            return True
        except Exception as e:
            print(f"[ERROR] Optimize error: {e}")
            return False
