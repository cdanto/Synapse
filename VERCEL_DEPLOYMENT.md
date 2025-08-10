# Deploying Synapse to Vercel

This guide will help you deploy Synapse to Vercel's serverless platform.

## ⚠️ Important Limitations

**Vercel deployment has several limitations compared to local deployment:**

- ❌ **No local file storage** - Knowledge base documents cannot be stored locally
- ❌ **No llama.cpp integration** - Cannot run local AI models
- ❌ **No persistent memory** - Chat history and memory are not persistent
- ❌ **Limited execution time** - Functions timeout after 30 seconds
- ❌ **No GPU access** - Cannot use GPU acceleration for AI models

**For full functionality, consider:**
- 🚀 **Railway** - Better for Python apps with persistent storage
- 🐳 **DigitalOcean App Platform** - Full container deployment
- ☁️ **Google Cloud Run** - Serverless with longer timeouts
- 🏠 **Self-hosted** - Full control and functionality

## 🚀 Deployment Steps

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Login to Vercel

```bash
vercel login
```

### 3. Deploy to Vercel

```bash
vercel --prod
```

### 4. Set Environment Variables

In your Vercel dashboard, go to your project settings and add these environment variables:

```bash
# Copy from vercel.env.example
PORT=9000
HOST=0.0.0.0
CORS_ORIGINS=*
LLAMA_URL=https://your-llm-service.com/v1/chat/completions
LLAMA_MODEL=qwen2.5-3b-instruct-q4_k_m
EMB_MODEL=BAAI/bge-base-en-v1.5
CTX_SIZE=32768
GUARDIAN_ENABLED=false
```

## 🔧 Configuration Files

The deployment uses these Vercel-specific files:

- `vercel.json` - Vercel configuration
- `api/index.py` - API entry point
- `vercel-requirements.txt` - Minimal dependencies
- `runtime.txt` - Python version specification

## 🌐 External Services Setup

Since Vercel can't run local services, you'll need:

### LLM Service
- **OpenAI API** - Set `LLAMA_URL=https://api.openai.com/v1/chat/completions`
- **Anthropic Claude** - Use their API endpoint
- **Hugging Face** - Use their inference API
- **Custom API** - Your own hosted LLM service

### Vector Database
- **Pinecone** - For document embeddings and RAG
- **Weaviate** - Open-source vector database
- **Qdrant** - Fast vector similarity search

### File Storage
- **AWS S3** - For document storage
- **Google Cloud Storage** - Alternative cloud storage
- **Supabase Storage** - Open-source alternative

## 📝 Example External Service Configuration

```bash
# OpenAI Configuration
LLAMA_URL=https://api.openai.com/v1/chat/completions
OPENAI_API_KEY=your_api_key_here

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=synapse-kb

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_BUCKET_NAME=synapse-documents
```

## 🧪 Testing the Deployment

After deployment, test your endpoints:

```bash
# Test the config endpoint
curl https://your-vercel-app.vercel.app/config

# Test a simple chat
curl -X POST https://your-vercel-app.vercel.app/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, Synapse!"}'
```

## 🔄 Redeployment

To update your deployment:

```bash
vercel --prod
```

## 🆘 Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure all dependencies are in `vercel-requirements.txt`
2. **Timeout Errors**: Functions are limited to 30 seconds
3. **Memory Issues**: Vercel has memory limitations
4. **File System Errors**: No local file system access

### Debug Commands:

```bash
# Check deployment status
vercel ls

# View logs
vercel logs

# Check function status
vercel functions
```

## 🎯 Alternative Deployment Options

### For Full Functionality:

1. **Railway** - Better Python support, persistent storage
2. **DigitalOcean App Platform** - Full container deployment
3. **Google Cloud Run** - Serverless with longer timeouts
4. **AWS Lambda** - Serverless with more configuration options
5. **Self-hosted VPS** - Full control and functionality

### For Development/Testing:

1. **Local deployment** - Full functionality for development
2. **Docker deployment** - Containerized local deployment
3. **GitHub Codespaces** - Cloud development environment

## 📚 Additional Resources

- [Vercel Python Documentation](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Vercel Environment Variables](https://vercel.com/docs/projects/environment-variables)
- [Vercel Functions Configuration](https://vercel.com/docs/functions/configuration)
