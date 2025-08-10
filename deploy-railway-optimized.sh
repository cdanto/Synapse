#!/bin/bash

# Synapse Railway Deployment Script (Optimized for 4GB Limit)
echo "🚀 Deploying Synapse to Railway (Optimized Build)..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${YELLOW}📦 Railway CLI not found. Installing...${NC}"
    npm install -g @railway/cli
fi

# Check Railway CLI version
echo -e "${BLUE}🔍 Railway CLI version:${NC}"
railway --version

# Check if user is logged in
if ! railway whoami &> /dev/null; then
    echo -e "${YELLOW}🔐 Please login to Railway...${NC}"
    railway login
fi

# Show current user
echo -e "${BLUE}👤 Logged in as:${NC}"
railway whoami

# Check if project is already linked
if [ -f ".railway" ]; then
    echo -e "${GREEN}✅ Project already linked to Railway${NC}"
else
    echo -e "${YELLOW}🔗 Linking project to Railway...${NC}"
    railway init
fi

# Show project status
echo -e "${BLUE}📊 Project status:${NC}"
railway status

echo -e "${YELLOW}🚀 Deploying to Railway (using optimized build)...${NC}"
echo -e "${BLUE}📝 This deployment uses:${NC}"
echo "   • Minimal build dependencies (stays under 4GB limit)"
echo "   • Full runtime dependencies (installed at startup)"
echo "   • Railway TOML configuration for optimal control"

# Deploy to Railway
railway up

# Wait for deployment to complete
echo -e "${BLUE}⏳ Waiting for deployment to complete...${NC}"
sleep 15

# Show final status
echo -e "${BLUE}📊 Final deployment status:${NC}"
railway status

# Get the deployment URL
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo -e "${BLUE}🌐 Your Synapse API is now available at:${NC}"
railway status | grep -o 'https://[^[:space:]]*' | head -1

echo ""
echo -e "${BLUE}📝 Next steps:${NC}"
echo "1. Set environment variables in Railway dashboard"
echo "2. Test your API endpoints"
echo "3. Configure external LLM services"
echo "4. Set up custom domain (optional)"
echo ""
echo -e "${BLUE}📚 See RAILWAY_DEPLOYMENT.md for detailed configuration${NC}"
echo ""
echo -e "${GREEN}🚀 Welcome to Railway! Your Synapse is now in the cloud!${NC}"
echo ""
echo -e "${YELLOW}💡 Note: This deployment uses the optimized build approach${NC}"
echo "   to stay under Railway's 4GB image size limit."
