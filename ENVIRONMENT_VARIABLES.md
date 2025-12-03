# 🔐 Environment Variables Reference

This document lists all environment variables needed for Sigma GPT.

---

## 📁 Backend Environment Variables

**File:** `Backend/.env`

```env
# MongoDB Connection String
# Local: mongodb://localhost:27017/sigma_gpt
# Production: mongodb+srv://username:password@cluster.mongodb.net/sigma_gpt?retryWrites=true&w=majority
MONGODB_URI=mongodb://localhost:27017/sigma_gpt

# OpenAI API Key
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# AI Service URL
# Local: http://localhost:8000
# Production: https://your-ai-service.onrender.com
AI_SERVICE_URL=http://localhost:8000

# Timezone (optional)
TZ=UTC
```

---

## 🤖 AI Service Environment Variables

**File:** `AI/.env`

```env
# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Qdrant Vector Database
# Local: http://localhost:6333
# Production (Qdrant Cloud): https://xxxxx-xxxxx.us-east-1-0.aws.cloud.qdrant.io:6333
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-api-key-here  # Required for Qdrant Cloud
QDRANT_COLLECTION=learning_vectors

# MongoDB (for checkpointing)
# Same as Backend MONGODB_URI
MONGODB_URI=mongodb://localhost:27017/sigma_gpt
MONGO_URI=mongodb://localhost:27017/sigma_gpt  # Some services use this name
MONGODB_DB=sigma_gpt

# Optional: Web Search APIs
GOOGLE_API_KEY=your-google-api-key  # Optional
GOOGLE_CX=your-google-cx-id  # Optional
TAVILY_API_KEY=your-tavily-key  # Optional
EXA_API_KEY=your-exa-key  # Optional

# Optional: Redis (for persistent memory)
REDIS_URL=redis://localhost:6379/0  # Optional

# Optional: Agent Configuration
AGENT_MAX_TURNS=12  # Max conversation turns to remember
AGENT_MEMORY_TTL_SECONDS=21600  # 6 hours default

# Render/Heroku: Port (automatically set by platform)
PORT=8000  # Don't set manually, Render sets this
```

---

## 🎨 Frontend Environment Variables

**File:** `Frontend/.env`

```env
# Backend API URL
# Local: http://localhost:8080
# Production: https://your-backend.onrender.com
VITE_API_URL=http://localhost:8080
```

**Important:** In Vite, environment variables must be prefixed with `VITE_` to be exposed to the frontend code.

---

## 📝 Quick Setup Guide

### For Local Development:

1. **Backend:**
   ```bash
   cd Backend
   cp .env.example .env  # If .env.example exists
   # Edit .env with your values
   ```

2. **AI Service:**
   ```bash
   cd AI
   cp .env.example .env  # If .env.example exists
   # Edit .env with your values
   ```

3. **Frontend:**
   ```bash
   cd Frontend
   cp .env.example .env  # If .env.example exists
   # Edit .env with your values
   ```

### For Production (Render/Vercel):

Set these in your platform's dashboard:
- **Render (Backend)**: Set `MONGODB_URI`, `OPENAI_API_KEY`, `AI_SERVICE_URL`
- **Render (AI Service)**: Set all AI service variables
- **Vercel (Frontend)**: Set `VITE_API_URL`

---

## 🔒 Security Notes

1. **Never commit `.env` files to Git**
   - They're already in `.gitignore`
   - Use `.env.example` files as templates

2. **Use different values for development and production**
   - Development: Local MongoDB, localhost URLs
   - Production: MongoDB Atlas, Render URLs

3. **Rotate API keys regularly**
   - Especially if exposed or compromised

4. **Use environment variables in deployment platforms**
   - Never hardcode secrets in code
   - Use platform's environment variable settings

---

## ✅ Verification Checklist

Before deploying, verify:

- [ ] All `.env` files are in `.gitignore`
- [ ] No hardcoded API keys in code
- [ ] All services can access their required environment variables
- [ ] Production URLs are correct (not localhost)
- [ ] MongoDB Atlas IP whitelist includes Render IPs (0.0.0.0/0)
- [ ] Qdrant Cloud API key is set (if using Qdrant Cloud)

---

## 🆘 Troubleshooting

### "Environment variable not found"
- Check variable name spelling (case-sensitive!)
- Verify `.env` file is in correct directory
- Restart the service after changing `.env`

### "Connection refused" or "Cannot connect"
- Check URLs are correct (not localhost in production)
- Verify services are running
- Check firewall/network settings

### "API key invalid"
- Verify key is correct (no extra spaces)
- Check key hasn't expired
- Verify key has correct permissions

