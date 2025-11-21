# 🌐 Free Deployment Guide for DocSearch

## 🆓 **Best Free Hosting Platforms**

### **Option 1: Render.com (RECOMMENDED)**
✅ **Best for:** Python Flask apps  
✅ **Free Tier:** 750 hours/month  
✅ **Features:** Auto-deploy from GitHub, PostgreSQL, persistent storage  
✅ **Domain:** `your-app.onrender.com`  

**Steps:**
1. Create account at [render.com](https://render.com)
2. Connect GitHub repository
3. Select "Web Service"
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Deploy!

**Custom Domain:** Free with Render

---

### **Option 2: Railway.app**
✅ **Best for:** Quick deployment  
✅ **Free Tier:** $5 credit/month  
✅ **Features:** Auto-scaling, databases  
✅ **Domain:** `your-app.up.railway.app`  

**Steps:**
1. Visit [railway.app](https://railway.app)
2. Deploy from GitHub
3. Auto-detects Python
4. Done!

---

### **Option 3: Fly.io**
✅ **Best for:** Global deployment  
✅ **Free Tier:** 3 VMs, 3GB storage  
✅ **Features:** Edge locations worldwide  
✅ **Domain:** `your-app.fly.dev`  

**Steps:**
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Deploy
fly launch
fly deploy
```

---

### **Option 4: PythonAnywhere**
✅ **Best for:** Beginners  
✅ **Free Tier:** 1 web app  
✅ **Features:** Easy setup, no credit card  
✅ **Domain:** `your-username.pythonanywhere.com`  

**Steps:**
1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)
2. Upload files via web interface
3. Configure web app
4. Done!

---

### **Option 5: Vercel (For Static Frontend)**
✅ **Best for:** Client-side version  
✅ **Free Tier:** Unlimited  
✅ **Features:** CDN, auto-deploy  
✅ **Domain:** `your-app.vercel.app`  

---

## 🎯 **Recommended Setup**

### **Best Combination:**
- **Backend:** Render.com (Flask + Vector DB)
- **Frontend:** Vercel (if separate)
- **Database:** Render PostgreSQL (free)
- **Storage:** Render Disk (persistent)

---

## 📦 **Deployment Files Needed**

### **1. Create `Procfile`**
```
web: gunicorn app:app --bind 0.0.0.0:$PORT
```

### **2. Create `runtime.txt`**
```
python-3.11.0
```

### **3. Update `requirements.txt`**
```
Flask==3.0.0
gunicorn==21.2.0
PyPDF2==3.0.1
pytesseract==0.3.10
Pillow==10.1.0
pdf2image==1.16.3
Werkzeug==3.0.1
chromadb==0.4.22
sentence-transformers==2.2.2
```

### **4. Create `.gitignore`**
```
__pycache__/
*.pyc
uploads/
chroma_db/
.env
venv/
```

### **5. Create `render.yaml`** (for Render)
```yaml
services:
  - type: web
    name: docsearch
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

---

## 🔧 **Pre-Deployment Checklist**

- [ ] Update `app.py` to use optimized version
- [ ] Add `gunicorn` to requirements.txt
- [ ] Create `Procfile`
- [ ] Test locally: `gunicorn app:app`
- [ ] Push to GitHub
- [ ] Connect to hosting platform
- [ ] Configure environment variables
- [ ] Deploy!

---

## 🌍 **Free Custom Domain Options**

### **1. Freenom** (Free .tk, .ml, .ga domains)
- Website: [freenom.com](https://www.freenom.com)
- Duration: 12 months free
- Renewal: Free

### **2. Dot.tk** (Free .tk domains)
- Website: [dot.tk](http://www.dot.tk)
- Duration: 12 months free

### **3. Use Subdomain Services**
- **Afraid.org** - Free subdomains
- **DuckDNS** - Free dynamic DNS
- **No-IP** - Free hostnames

### **4. Platform Domains (Included)**
- Render: `*.onrender.com`
- Railway: `*.up.railway.app`
- Fly.io: `*.fly.dev`
- Vercel: `*.vercel.app`

---

## 🚀 **Quick Deploy Commands**

### **For Render:**
```bash
# 1. Install Render CLI
npm install -g render

# 2. Login
render login

# 3. Deploy
render deploy
```

### **For Railway:**
```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Deploy
railway up
```

### **For Fly.io:**
```bash
# 1. Install Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. Login
fly auth login

# 3. Deploy
fly launch
fly deploy
```

---

## 💡 **Important Notes**

### **For Vector Database:**
- Render: Use persistent disk (free 1GB)
- Railway: Volumes included
- Fly.io: Volumes available
- PythonAnywhere: Limited storage

### **For File Uploads:**
- Most platforms: Ephemeral storage
- Solution: Use persistent volumes or cloud storage (S3, Cloudinary)

### **For OCR (Tesseract):**
Add to `Dockerfile` or buildpack:
```dockerfile
RUN apt-get update && apt-get install -y tesseract-ocr
```

---

## 🎁 **Bonus: Free SSL Certificate**

All platforms provide **free HTTPS** automatically!
- Render: Auto SSL
- Railway: Auto SSL
- Fly.io: Auto SSL
- Vercel: Auto SSL

---

## 📊 **Platform Comparison**

| Platform | Free Tier | Storage | Database | Best For |
|----------|-----------|---------|----------|----------|
| **Render** | 750h/mo | 1GB | PostgreSQL | Production |
| **Railway** | $5/mo | Volumes | Any | Quick deploy |
| **Fly.io** | 3 VMs | 3GB | Any | Global apps |
| **PythonAnywhere** | 1 app | 512MB | MySQL | Beginners |
| **Vercel** | Unlimited | N/A | N/A | Frontend |

---

## 🎯 **Recommended: Render.com**

**Why Render?**
1. ✅ Best free tier for Python
2. ✅ Persistent storage for vector DB
3. ✅ Auto-deploy from GitHub
4. ✅ Free PostgreSQL
5. ✅ Custom domains supported
6. ✅ Auto SSL certificates
7. ✅ No credit card required

**Deploy URL:** `https://your-docsearch.onrender.com`

---

## 🚀 **Ready to Deploy?**

1. Choose platform (Render recommended)
2. Create deployment files
3. Push to GitHub
4. Connect and deploy
5. Get your free URL!

**Your DocSearch will be live in minutes! 🎉**
