# 🔍 DocSearch - AI-Powered Document Search Engine

> Intelligent document search with semantic vector database, OCR support, and beautiful UI

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-orange.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Features

- 🧠 **AI-Powered Semantic Search** - Understands context, not just keywords
- 💾 **Persistent Vector Database** - ChromaDB with sentence transformers
- 📄 **Multi-Format Support** - PDF, TXT, MD, JSON, JPG, PNG
- 🔍 **OCR Support** - Extract text from scanned documents and images
- ⚡ **Optimized Performance** - 2-5x faster with LRU caching
- 🎨 **Beautiful UI** - Deep green/blue dark theme
- 🚀 **Production Ready** - Deploy to Render, Railway, or Fly.io for free

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/SubhasisPM/DocSearch.git
cd DocSearch

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py

# Visit http://localhost:5000
```

### Deploy to Render.com (Free)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

1. Fork this repository
2. Create account at [render.com](https://render.com)
3. New Web Service → Connect GitHub
4. Deploy!

**Your URL:** `https://your-docsearch.onrender.com`

## 📋 Requirements

- Python 3.11+
- Tesseract OCR (for image/PDF processing)
- 500MB RAM minimum
- 1GB disk space (for vector database)

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Vector DB:** ChromaDB
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **OCR:** Tesseract + pytesseract
- **PDF Processing:** PyPDF2 + pdf2image
- **Production Server:** Gunicorn

## 📊 Performance

| Operation | Speed |
|-----------|-------|
| Document Upload | ~1.5s |
| Search Query | ~50ms |
| PDF Processing | ~0.8s |
| Image OCR | ~1.2s |

**2-5x faster** than standard implementations!

## 🎨 Screenshots

*Beautiful deep green/blue dark theme with modern UI*

## 📖 Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Free hosting options
- [Optimization Summary](OPTIMIZATION_SUMMARY.md) - Performance improvements
- [Vector DB Guide](VECTOR_DB_README.md) - Database documentation
- [Architecture Guide](REBUILD_GUIDE.md) - System design

## 🌐 Supported File Types

- `.txt` - Text files
- `.pdf` - PDF documents (with OCR for scanned docs)
- `.md` - Markdown files
- `.json` - JSON files
- `.jpg`, `.jpeg`, `.png` - Images (with OCR)

## 🔧 Configuration

Edit `app.py` to customize:

```python
app.config.update(
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB limit
    ALLOWED_EXTENSIONS={'txt', 'pdf', 'md', 'json', 'jpg', 'jpeg', 'png'}
)
```

## 🚀 Deployment Options

### Free Hosting Platforms

1. **Render.com** ⭐ (Recommended)
   - Free tier: 750 hours/month
   - URL: `*.onrender.com`

2. **Railway.app**
   - Free: $5 credit/month
   - URL: `*.up.railway.app`

3. **Fly.io**
   - Free: 3 VMs
   - URL: `*.fly.dev`

4. **PythonAnywhere**
   - Free: 1 web app
   - URL: `*.pythonanywhere.com`

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions.

## 📝 API Endpoints

- `GET /` - Main application
- `POST /upload` - Upload document
- `POST /search` - Search documents
- `GET /documents` - List all documents
- `GET /stats` - Database statistics

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - feel free to use this project for personal or commercial purposes.

## 👤 Author

**Subhasis PM**
- GitHub: [@SubhasisPM](https://github.com/SubhasisPM)

## 🙏 Acknowledgments

- ChromaDB for vector database
- Sentence Transformers for embeddings
- Tesseract OCR for text extraction
- Flask community

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation files

---

**⭐ Star this repository if you find it helpful!**

Made with ❤️ using Python, Flask, and AI
