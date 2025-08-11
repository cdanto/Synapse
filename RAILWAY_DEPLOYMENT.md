# 🚀 Deploying Synapse to Railway

Railway is the **BEST choice** for Synapse deployment - it provides full Python support, persistent storage, and no timeout limitations!

## ✨ **Why Railway is Perfect for Synapse:**

- ✅ **Full Python support** - Native Python runtime
- ✅ **Persistent storage** - Knowledge base files are preserved
- ✅ **No timeout limits** - Can run long AI inference tasks
- ✅ **Easy deployment** - Git-based, automatic builds
- ✅ **Cost-effective** - Pay-per-use pricing
- ✅ **Database support** - Built-in PostgreSQL, Redis
- ✅ **Custom domains** - SSL certificates included

## 🚀 **Quick Start (5 minutes):**

### 1. **Install Railway CLI**
```bash
npm install -g @railway/cli
```

### 2. **Login to Railway**
```bash
railway login
```

### 3. **Initialize Railway Project**
```bash
railway init
```

### 4. **Deploy to Railway**
```bash
railway up
```

### 5. **Get Your URL**
```bash
railway status
```

## 🔧 **Configuration Files Created:**

- `railway.toml` - Railway service configuration (recommended)
- `railway.json` - Alternative JSON configuration
- `railway-build-requirements.txt` - Minimal build dependencies (stays under 4GB limit)
- `railway-requirements-ultra-minimal.txt` - Ultra-minimal runtime dependencies (installed at startup)
- `railway.env.example` - Environment variables template

## 🐳 **Image Size Optimization (4GB Limit):**

**Problem:** Railway free plan has a 4GB build image limit, but AI/ML dependencies can exceed this.

**Solution:** We use **external embedding APIs** instead of heavy local models:
1. **Build Phase:** Install only essential dependencies (`railway-build-requirements.txt`) - **~50MB total**
2. **Runtime Phase:** Install ultra-minimal dependencies (`railway-requirements-ultra-minimal.txt`)
3. **Embeddings:** Use OpenAI, Cohere, or Hugging Face APIs instead of local `sentence-transformers`

This keeps the build image **well under 4GB** while providing **100% RAG functionality**.

## 🌐 **Environment Variables Setup:**

In your Railway dashboard, add these environment variables:

```bash
# Core Configuration
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=*

# LLM Configuration
LLAMA_URL=https://your-llm-service.com/v1/chat/completions
LLAMA_MODEL=qwen2.5-3b-instruct-q4_k_m

# Embedding Model
EMB_MODEL=BAAI/bge-base-en-v1.5

# Context Size
CTX_SIZE=32768

# Guardian Configuration
GUARDIAN_ENABLED=false

# Optional: External Services
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=synapse-kb
```

## 📁 **File Structure for Railway:**

```
Synapse/
├── backend/
│   ├── app.py              # Main FastAPI app
│   ├── chat_core/          # Core chat functionality
│   └── requirements.txt    # Backend dependencies
├── railway.json            # Railway configuration
├── railway-requirements-ultra-minimal.txt # Railway ultra-minimal dependencies
└── railway.env.example     # Environment template
```

## 🚀 **Deployment Commands:**

### **First Time Setup:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Link to existing project (if you have one)
railway link

# Deploy
railway up
```

### **Subsequent Deployments:**
```bash
# Deploy changes
railway up

# Check status
railway status

# View logs
railway logs

# Open in browser
railway open
```

## 🔄 **Continuous Deployment:**

Railway automatically deploys when you push to your main branch:

1. **Connect GitHub repo** in Railway dashboard
2. **Push to main branch** - automatic deployment
3. **Preview deployments** for pull requests
4. **Rollback** to previous versions if needed

## 📊 **Monitoring & Logs:**

```bash
# View real-time logs
railway logs --follow

# Check service status
railway status

# Monitor resource usage
railway metrics
```

## 🌍 **Custom Domain Setup:**

1. **Add custom domain** in Railway dashboard
2. **Configure DNS** to point to Railway
3. **SSL certificate** is automatically provisioned
4. **Update CORS** to include your domain

## 💰 **Pricing & Limits:**

- **Free tier**: $5 credit monthly
- **Pay-per-use**: Only pay for actual usage
- **No hidden fees**: Transparent pricing
- **Auto-scaling**: Handles traffic spikes

## 🧪 **Testing Your Deployment:**

### **Health Check:**
```bash
curl https://your-app.railway.app/health
```

### **Configuration:**
```bash
curl https://your-app.railway.app/config
```

### **Chat Test:**
```bash
curl -X POST https://your-app.railway.app/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello, Synapse!"}]}'
```

## 🔧 **Troubleshooting:**

### **Common Issues:**

1. **Build Failures**: Check `railway-requirements-ultra-minimal.txt` for missing dependencies
2. **Import Errors**: Ensure all Python packages are in requirements
3. **Port Issues**: Railway sets `$PORT` environment variable automatically
4. **Memory Issues**: Railway provides adequate memory for AI workloads

### **Debug Commands:**
```bash
# Check build logs
railway logs --build

# Restart service
railway service restart

# Check environment variables
railway variables
```

## 🚀 **Advanced Features:**

### **Database Integration:**
```bash
# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis

# View connection strings
railway variables
```

### **Multiple Environments:**
```bash
# Create staging environment
railway environment create staging

# Deploy to staging
railway up --environment staging

# Promote to production
railway promote
```

## 📚 **Additional Resources:**

- [Railway Documentation](https://docs.railway.app/)
- [Python on Railway](https://docs.railway.app/deploy/deployments/python)
- [Environment Variables](https://docs.railway.app/deploy/environments)
- [Custom Domains](https://docs.railway.app/deploy/custom-domains)

## 🎯 **Next Steps After Deployment:**

1. **Test all endpoints** - Ensure functionality works
2. **Set up external services** - LLM APIs, vector databases
3. **Configure custom domain** - Professional URL
4. **Set up monitoring** - Track performance and errors
5. **Configure backups** - Database and file backups

---

## 🎉 **You're Ready to Deploy!**

Railway will give you **100% of Synapse's functionality** in the cloud. No compromises, no limitations - just pure AI assistant power!

**Ready to deploy?** Run:
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```
