import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")

try:
    print("Attempting to import chromadb...")
    import chromadb
    print("SUCCESS: chromadb imported.")
except ImportError as e:
    print(f"ERROR: Failed to import chromadb: {e}")
except Exception as e:
    print(f"CRITICAL: Error importing chromadb: {e}")

try:
    print("Attempting to import sentence_transformers...")
    from sentence_transformers import SentenceTransformer
    print("SUCCESS: sentence_transformers imported.")
except ImportError as e:
    print(f"ERROR: Failed to import sentence_transformers: {e}")
except Exception as e:
    print(f"CRITICAL: Error importing sentence_transformers: {e}")

try:
    print("Attempting to import vector_db...")
    from vector_db import VectorMemory
    print("SUCCESS: vector_db imported.")
    
    print("Attempting to initialize VectorMemory...")
    vm = VectorMemory()
    print(f"SUCCESS: VectorMemory initialized. Stats: {vm.get_stats()}")
except ImportError as e:
    print(f"ERROR: Failed to import vector_db: {e}")
except Exception as e:
    print(f"CRITICAL: Error initializing vector_db: {e}")
    import traceback
    traceback.print_exc()
