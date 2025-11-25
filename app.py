"""
DocSearch - Optimized Flask Backend
Fast, clean document search with AI-powered vector database
"""

import sys
import os
import re
from functools import lru_cache
import logging

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import PyPDF2
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Optional Vector DB import
try:
    from vector_db import VectorMemory
    VECTOR_DB_AVAILABLE = True
except ImportError:
    print("Warning: Vector Database dependencies not found. Running in limited mode.")
    VECTOR_DB_AVAILABLE = False
    VectorMemory = None

# Import enhanced search
try:
    from enhanced_search import enhanced_search
    ENHANCED_SEARCH_AVAILABLE = True
except ImportError:
    print("Warning: Enhanced search not available.")
    ENHANCED_SEARCH_AVAILABLE = False
    enhanced_search = None

# Flask app configuration
app = Flask(__name__)
app.config.update(
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB limit
    ALLOWED_EXTENSIONS={'txt', 'pdf', 'md', 'json', 'jpg', 'jpeg', 'png'}
)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize vector database (singleton pattern)
vector_db = None
if VECTOR_DB_AVAILABLE:
    try:
        vector_db = VectorMemory()
        print(f"[OK] Vector DB ready: {vector_db.get_stats()['total_documents']} documents")
    except Exception as e:
        print(f"Warning: Failed to initialize Vector DB: {e}")
        VECTOR_DB_AVAILABLE = False
else:
    print("Running without Vector Database")


# ============================================================================
# UTILITY FUNCTIONS (Optimized)
# ============================================================================

def allowed_file(filename):
    """Fast file extension validation"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@lru_cache(maxsize=128)
def sanitize_text(text):
    """Cached text sanitization for performance"""
    if not text:
        return ''
    # Single-pass regex for speed
    text = re.sub(r'[^\w\s]+', ' ', text.lower())
    return ' '.join(text.split())  # Faster than multiple regex


def read_pdf_fast(file_path):
    """Optimized PDF reading with smart OCR fallback"""
    text_parts = []
    
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Use enumerate for O(1) page indexing instead of O(n) index lookup
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                
                # Only OCR if page is mostly empty
                if len(page_text.strip()) < 20:
                    page_text = perform_ocr_on_page(file_path, page_num)
                
                text_parts.append(page_text)
        
        return ' '.join(text_parts)
    
    except Exception as e:
        logging.error(f"PDF reading error for {file_path}: {e}")
        return perform_ocr_full(file_path)


def perform_ocr_on_page(file_path, page_num):
    """OCR single page (lazy loading)"""
    try:
        with open(file_path, 'rb') as file:
            images = convert_from_bytes(
                file.read(),
                first_page=page_num + 1,
                last_page=page_num + 1,
                dpi=200  # Lower DPI for speed
            )
        return pytesseract.image_to_string(images[0]) if images else ''
    except Exception as e:
        logging.warning(f"OCR error on page {page_num} of {file_path}: {e}")
        return ''


def perform_ocr_full(file_path):
    """Full document OCR (fallback)"""
    try:
        with open(file_path, 'rb') as file:
            images = convert_from_bytes(file.read(), dpi=200)
        return ' '.join(pytesseract.image_to_string(img) for img in images)
    except Exception as e:
        logging.error(f"Full OCR error for {file_path}: {e}")
        return ''


def read_image_ocr(file_path):
    """Fast image OCR"""
    try:
        image = Image.open(file_path)
        # Resize large images for speed
        if image.width > 2000 or image.height > 2000:
            image.thumbnail((2000, 2000))
        return pytesseract.image_to_string(image)
    except Exception as e:
        logging.warning(f"Image OCR error for {file_path}: {e}")
        return ''


def read_file_content(file_path, filename):
    """Smart file reader with type detection"""
    try:
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    except IndexError:
        logging.error(f"Invalid filename format: {filename}")
        return ''
    
    readers = {
        'pdf': lambda: read_pdf_fast(file_path),
        'jpg': lambda: read_image_ocr(file_path),
        'jpeg': lambda: read_image_ocr(file_path),
        'png': lambda: read_image_ocr(file_path),
    }
    
    if ext in readers:
        return readers[ext]()
    
    # Default: text file
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        logging.error(f"File read error for {file_path}: {e}")
        return ''


def extract_context(content, query_words, max_sentences=3):
    """Fast context extraction with sentence scoring"""
    # Split into sentences efficiently
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if not sentences:
        return "No relevant context found."
    
    # Score sentences (vectorized for speed)
    scored = []
    for sentence in sentences[:100]:  # Limit to first 100 for speed
        lower = sentence.lower()
        score = sum(1 for word in query_words if word in lower)
        if score > 0:
            scored.append((score, sentence))
    
    # Get top sentences
    scored.sort(reverse=True, key=lambda x: x[0])
    top = [s[1] for s in scored[:max_sentences]]
    
    return ' '.join(top) if top else sentences[0]


# ============================================================================
# API ROUTES (Clean & Fast)
# ============================================================================

@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload with validation"""
    # Fast validation
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Secure filename and save
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Extract content (async in production)
        content = read_file_content(file_path, filename)
        
        if not content.strip():
            return jsonify({'error': 'Empty or unreadable file'}), 400
        
        # Generate unique ID
        doc_id = f"doc_{os.urandom(4).hex()}"
        if vector_db:
             doc_id = f"doc_{vector_db.get_stats()['total_documents'] + 1}"
        
        # Store in vector DB
        metadata = {
            'name': filename,
            'size': os.path.getsize(file_path),
            'path': file_path
        }
        
        if vector_db:
            vector_db.add_document(doc_id, content, metadata)
        
        return jsonify({
            'success': True,
            'document': {
                'id': doc_id,
                'name': filename,
                'size': metadata['size']
            }
        })
    
    except Exception as e:
        logging.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@app.route('/search', methods=['POST'])
def search():
    """Enhanced semantic search with intelligent context extraction"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Empty query'}), 400
    
    if not vector_db:
        return jsonify({'error': 'Vector Database not available. Please check server logs.'}), 503

    if vector_db.get_stats()['total_documents'] == 0:
        return jsonify({'error': 'No documents uploaded'}), 400
    
    try:
        # Vector search (fast!)
        raw_results = vector_db.search(query, n_results=5)
        
        if not raw_results:
            return jsonify({'results': [], 'explanation': 'No results found.'})
        
        # Use enhanced search if available
        if ENHANCED_SEARCH_AVAILABLE and enhanced_search:
            # Enhanced results with context and summaries
            enhanced_results = enhanced_search.enhance_search_results(query, raw_results)
            
            # Generate overall explanation
            explanation = enhanced_search.get_overall_explanation(query, enhanced_results)
            
            # Generate aggregate summary for data reduction
            aggregate_summary = enhanced_search.generate_aggregate_summary(query, enhanced_results)
            
            # Format results for frontend
            formatted = []
            for idx, result in enumerate(enhanced_results):
                formatted.append({
                    'name': result['name'],
                    'score': result['score'],
                    'occurrences': result['occurrences'],
                    'summary': result['summary'],
                    'keywords': result['keywords'],
                    'contexts': result['contexts'],
                    'relevance': 'high' if idx == 0 else ('medium' if idx < 3 else 'low')
                })
            
            return jsonify({
                'explanation': explanation,
                'results': formatted,
                'aggregate_summary': aggregate_summary
            })
        
        else:
            # Fallback to basic search (original implementation)
            top = raw_results[0]
            context = extract_context(top['content'], query.split())
            
            formatted = []
            for idx, result in enumerate(raw_results):
                score = int((1 - result['distance']) * 100) if result['distance'] else 100
                formatted.append({
                    'name': result['metadata']['name'],
                    'score': score,
                    'relevance': 'high' if idx == 0 else 'medium',
                    'occurrences': 0,
                    'summary': '',
                    'keywords': [],
                    'contexts': []
                })
            
            return jsonify({
                'explanation': context,
                'results': formatted
            })
    
    except Exception as e:
        logging.error(f"Search error: {e}", exc_info=True)
        return jsonify({'error': f'Search failed: {str(e)}'}), 500


@app.route('/documents', methods=['GET'])
def get_documents():
    """Get all documents (cached)"""
    try:
        if not vector_db:
            return jsonify({'documents': []})

        docs = vector_db.get_all_documents()
        
        doc_list = [{
            'id': doc['id'],
            'name': doc['metadata']['name'],
            'size': doc['metadata']['size']
        } for doc in docs]
        
        return jsonify({'documents': doc_list})
    
    except Exception as e:
        logging.error(f"Error loading documents: {e}")
        return jsonify({'documents': []})


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    if not vector_db:
        return jsonify({'total_documents': 0, 'status': 'disabled'})
    return jsonify(vector_db.get_stats())


# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    logging.info("DocSearch starting...")
    logging.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    logging.info(f"Supported formats: {', '.join(app.config['ALLOWED_EXTENSIONS'])}")
    logging.info(f"Vector DB available: {VECTOR_DB_AVAILABLE}")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
