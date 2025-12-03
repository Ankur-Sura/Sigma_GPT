#!/bin/bash

# =============================================================================
#                     SIGMA GPT - AUTOMATED SETUP SCRIPT
# =============================================================================
# This script sets up environment variables for local development
# Run: bash setup.sh

set -e  # Exit on error

echo "🚀 Sigma GPT - Automated Setup"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# MongoDB Connection String
# IMPORTANT: Replace with your own MongoDB Atlas connection string
# Format: mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
MONGODB_URI="mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0"

# =============================================================================
# BACKEND SETUP
# =============================================================================
echo "📦 Setting up Backend..."
BACKEND_ENV="Backend/.env"

if [ -f "$BACKEND_ENV" ]; then
    echo "   ⚠️  .env file already exists, backing up..."
    cp "$BACKEND_ENV" "$BACKEND_ENV.backup"
fi

cat > "$BACKEND_ENV" << EOF
# MongoDB Connection String
MONGODB_URI=${MONGODB_URI}

# OpenAI API Key (REPLACE WITH YOUR KEY)
OPENAI_API_KEY=sk-your-openai-api-key-here

# AI Service URL
AI_SERVICE_URL=http://localhost:8000

# Timezone
TZ=UTC
EOF

echo "   ✅ Backend .env created at $BACKEND_ENV"
echo ""

# =============================================================================
# AI SERVICE SETUP
# =============================================================================
echo "🤖 Setting up AI Service..."
AI_ENV="AI/.env"

if [ -f "$AI_ENV" ]; then
    echo "   ⚠️  .env file already exists, backing up..."
    cp "$AI_ENV" "$AI_ENV.backup"
fi

cat > "$AI_ENV" << EOF
# MongoDB Connection String
MONGODB_URI=${MONGODB_URI}
MONGO_URI=${MONGODB_URI}
MONGODB_DB=sigma_gpt

# OpenAI API Key (REPLACE WITH YOUR KEY)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Qdrant Vector Database
# For local: http://localhost:6333
# For Qdrant Cloud: https://your-cluster.qdrant.io:6333
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-api-key-here
QDRANT_COLLECTION=learning_vectors

# Optional: Web Search APIs
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CX=your-google-cx-id
TAVILY_API_KEY=your-tavily-key
EXA_API_KEY=your-exa-key

# Optional: Redis
REDIS_URL=redis://localhost:6379/0

# Optional: Agent Configuration
AGENT_MAX_TURNS=12
AGENT_MEMORY_TTL_SECONDS=21600
EOF

echo "   ✅ AI Service .env created at $AI_ENV"
echo ""

# =============================================================================
# FRONTEND SETUP
# =============================================================================
echo "🎨 Setting up Frontend..."
FRONTEND_ENV="Frontend/.env"

if [ -f "$FRONTEND_ENV" ]; then
    echo "   ⚠️  .env file already exists, backing up..."
    cp "$FRONTEND_ENV" "$FRONTEND_ENV.backup"
fi

cat > "$FRONTEND_ENV" << EOF
# Backend API URL
# For local development: http://localhost:8080
# For production: https://your-backend.onrender.com
VITE_API_URL=http://localhost:8080
EOF

echo "   ✅ Frontend .env created at $FRONTEND_ENV"
echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo "${GREEN}✅ Setup Complete!${NC}"
echo ""
echo "📝 Next Steps:"
echo "   1. Edit Backend/.env and add your OPENAI_API_KEY"
echo "   2. Edit AI/.env and add your OPENAI_API_KEY"
echo "   3. (Optional) Add Qdrant Cloud credentials if using Qdrant Cloud"
echo "   4. Install dependencies:"
echo "      - Backend: cd Backend && npm install"
echo "      - AI: cd AI && pip install -r requirements.txt"
echo "      - Frontend: cd Frontend && npm install"
echo ""
echo "🔒 Security Note:"
echo "   - .env files are in .gitignore and won't be committed"
echo "   - Backups created as .env.backup (you can delete these)"
echo ""

