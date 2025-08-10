#!/bin/bash

# Synapse Vercel Deployment Script
echo "🚀 Deploying Synapse to Vercel..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Check if user is logged in
if ! vercel whoami &> /dev/null; then
    echo "🔐 Please login to Vercel..."
    vercel login
fi

# Deploy to Vercel
echo "📦 Deploying to Vercel..."
vercel --prod

echo "✅ Deployment complete!"
echo "🌐 Your Synapse API should now be available at the URL provided above."
echo ""
echo "📝 Next steps:"
echo "1. Set environment variables in your Vercel dashboard"
echo "2. Test your API endpoints"
echo "3. Update your frontend to use the new API URL"
echo ""
echo "📚 See VERCEL_DEPLOYMENT.md for detailed configuration instructions."
