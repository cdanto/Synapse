#!/bin/bash

# Railway Deployment Script - Optimized for 4GB limit
# This script deploys Synapse to Railway with minimal image size

set -e

echo "🚀 Deploying Synapse to Railway with size optimizations..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install it first:"
    echo "   npm install -g @railway/cli"
    echo "   railway login"
    exit 1
fi

# Check if we're logged in
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway. Please run: railway login"
    exit 1
fi

echo "✅ Railway CLI found and authenticated"

# Clean up any existing build artifacts
echo "🧹 Cleaning up build artifacts..."
rm -rf .railway/
rm -rf __pycache__/
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Check if we're in the right directory
if [ ! -f "Dockerfile.railway" ]; then
    echo "❌ Dockerfile.railway not found. Please run this script from the project root."
    exit 1
fi

if [ ! -f "railway-requirements-minimal.txt" ]; then
    echo "❌ railway-requirements-minimal.txt not found. Please run this script from the project root."
    exit 1
fi

echo "✅ All required files found"

# Deploy to Railway
echo "🚂 Deploying to Railway..."
echo "   Using: Dockerfile.railway"
echo "   Requirements: railway-requirements-minimal.txt"
echo "   Target: 4GB limit"

# Deploy with the optimized configuration
railway up --detach

echo "✅ Deployment initiated!"
echo ""
echo "📊 Monitor your deployment:"
echo "   railway status"
echo "   railway logs"
echo ""
echo "🌐 Your app will be available at the URL shown above"
echo "   (Note: First deployment may take 5-10 minutes)"
echo ""
echo "💡 If you still hit the 4GB limit, consider:"
echo "   - Upgrading to a paid Railway plan"
echo "   - Using external APIs instead of local models"
echo "   - Further reducing dependencies"
