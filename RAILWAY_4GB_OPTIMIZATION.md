# Railway 4GB Image Size Optimization Guide

## Problem
Your Railway deployment is failing because the Docker image exceeds the 4GB size limit. This commonly happens with Python applications that have heavy dependencies.

## Solution
I've created an optimized deployment strategy that should keep your image under 4GB:

### 1. Custom Dockerfile (`Dockerfile.railway`)
- **Multi-stage build**: Separates build and runtime environments
- **Base image**: Uses `python:3.11-slim` (smaller than full Python image)
- **Minimal dependencies**: Only installs essential build tools
- **Cleanup**: Removes build artifacts and package caches

### 2. Minimal Requirements (`railway-requirements-minimal.txt`)
- **Pinned versions**: Exact versions to prevent dependency bloat
- **Essential only**: Removed heavy ML libraries (torch, transformers)
- **CPU-only FAISS**: Uses `faiss-cpu` instead of GPU version
- **Lightweight alternatives**: Minimal document processing libraries

### 3. Aggressive `.dockerignore` (`.dockerignore.railway`)
- **Excludes frontend**: No Next.js/node_modules
- **Excludes docs**: No markdown files or documentation
- **Excludes scripts**: No shell scripts or deployment files
- **Excludes tests**: No test files or development tools

### 4. Updated Railway Config (`railway.json`)
- **Docker builder**: Uses custom Dockerfile instead of Nixpacks
- **Health checks**: Maintains existing health check configuration
- **No start command**: Handled by Dockerfile CMD

## Deployment Steps

### Option 1: Use the Optimized Script
```bash
./deploy-railway-optimized.sh
```

### Option 2: Manual Deployment
```bash
# 1. Make sure you're logged in
railway login

# 2. Deploy with the new configuration
railway up --detach

# 3. Monitor deployment
railway status
railway logs
```

## Expected Results
- **Image size**: Should be under 4GB (typically 2-3GB)
- **Build time**: Faster due to multi-stage optimization
- **Runtime**: Same functionality, smaller footprint

## If You Still Hit 4GB Limit

### 1. Upgrade Railway Plan
- Free tier: 4GB limit
- Pro plan: 8GB limit
- Team plan: 16GB limit

### 2. Further Optimizations
- Remove FAISS entirely, use external vector DB
- Use external embedding APIs instead of local models
- Split into microservices

### 3. Alternative Platforms
- **Render**: 10GB limit on paid plans
- **Heroku**: 500MB limit (requires external services)
- **DigitalOcean App Platform**: 10GB limit
- **AWS App Runner**: No strict size limits

## Current Configuration Files
- `Dockerfile.railway` - Optimized Docker build
- `railway-requirements-minimal.txt` - Minimal dependencies
- `.dockerignore.railway` - Aggressive file exclusion
- `railway.json` - Updated Railway configuration
- `deploy-railway-optimized.sh` - Automated deployment script

## Monitoring
After deployment, check:
```bash
# Check deployment status
railway status

# View logs
railway logs

# Check image size in Railway dashboard
# (Go to your project → Deployments → Latest deployment)
```

## Troubleshooting
- **Build fails**: Check Railway logs for specific errors
- **App won't start**: Verify environment variables are set
- **Still too large**: Consider removing more dependencies
- **CORS issues**: Ensure CORS_ORIGINS includes your frontend URL

This optimization should resolve your 4GB limit issue while maintaining full Synapse functionality.
