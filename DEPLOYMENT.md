# 🚀 Deployment Guide - Sigma GPT

This guide will help you deploy Sigma GPT to production using:
- **Frontend**: Vercel
- **Backend**: Render
- **AI Service**: Render (Python/FastAPI)
- **MongoDB**: MongoDB Atlas
- **Qdrant**: Qdrant Cloud

---

## 📋 Prerequisites

1. **GitHub Account** - You need to upload your code to GitHub first
2. **Vercel Account** - For frontend hosting (free tier available)
3. **Render Account** - For backend and AI service (free tier available)
4. **MongoDB Atlas Account** - Free tier available
5. **Qdrant Cloud Account** - Free tier available

---

## 📦 Step 1: Upload to GitHub

### 1.1 Initialize Git (if not already done)

```bash
cd "/Users/ankursura/Desktop/Sigma GPT"
git init
git add .
git commit -m "Initial commit - ready for deployment"
```

### 1.2 Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (e.g., `sigma-gpt`)
3. **DO NOT** initialize with README, .gitignore, or license

### 1.3 Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/sigma-gpt.git
git branch -M main
git push -u origin main
```

---

## 🗄️ Step 2: Set Up MongoDB Atlas

### 2.1 Create MongoDB Atlas Cluster

1. Go to https://www.mongodb.com/cloud/atlas
2. Sign up / Log in
3. Create a new cluster (FREE tier: M0)
4. Choose a cloud provider and region
5. Wait for cluster to be created (~5 minutes)

### 2.2 Create Database User

1. Go to **Database Access** → **Add New Database User**
2. Username: `sigma_gpt_user`
3. Password: Generate a strong password (save it!)
4. Database User Privileges: **Read and write to any database**

### 2.3 Whitelist IP Address

1. Go to **Network Access** → **Add IP Address**
2. For Render: Click **Allow Access from Anywhere** (0.0.0.0/0)
3. Click **Confirm**

### 2.4 Get Connection String

1. Go to **Clusters** → Click **Connect**
2. Choose **Connect your application**
3. Copy the connection string:
   ```
   mongodb+srv://sigma_gpt_user:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
4. Replace `<password>` with your actual password
5. Add database name: `?retryWrites=true&w=majority` → `sigma_gpt?retryWrites=true&w=majority`

**Final connection string:**
```
mongodb+srv://sigma_gpt_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority
```

---

## 🔍 Step 3: Set Up Qdrant Cloud

### 3.1 Create Qdrant Cloud Cluster

1. Go to https://cloud.qdrant.io/
2. Sign up / Log in
3. Create a new cluster (FREE tier available)
4. Choose a region
5. Wait for cluster to be created

### 3.2 Get Qdrant URL and API Key

1. Go to your cluster dashboard
2. Copy the **Cluster URL** (e.g., `https://xxxxx-xxxxx.us-east-1-0.aws.cloud.qdrant.io:6333`)
3. Copy the **API Key** (for authentication)

**Note:** For Qdrant Cloud, you'll need to use the API key in your connection.

---

## 🔧 Step 4: Deploy Backend to Render

### 4.1 Create New Web Service

1. Go to https://dashboard.render.com/
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Select the `sigma-gpt` repository

### 4.2 Configure Backend Service

**Settings:**
- **Name**: `sigma-gpt-backend`
- **Root Directory**: `Backend`
- **Environment**: `Node`
- **Build Command**: `npm install`
- **Start Command**: `npm start`
- **Plan**: Free (or paid if needed)

### 4.3 Add Environment Variables

Click **Environment** tab and add:

```env
MONGODB_URI=mongodb+srv://sigma_gpt_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority
OPENAI_API_KEY=sk-your-openai-api-key-here
AI_SERVICE_URL=https://sigma-gpt-ai-service.onrender.com
TZ=UTC
```

**Important:** Replace:
- `YOUR_PASSWORD` with your MongoDB password
- `sk-your-openai-api-key-here` with your OpenAI API key
- `sigma-gpt-ai-service` with your actual AI service name (you'll create this next)

### 4.4 Deploy

Click **Create Web Service** and wait for deployment (~5 minutes)

**Note the URL:** `https://sigma-gpt-backend.onrender.com`

---

## 🤖 Step 5: Deploy AI Service to Render

### 5.1 Create New Web Service

1. Go to https://dashboard.render.com/
2. Click **New +** → **Web Service**
3. Connect the same GitHub repository

### 5.2 Configure AI Service

**Settings:**
- **Name**: `sigma-gpt-ai-service`
- **Root Directory**: `AI`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Plan**: Free (or paid if needed)

**Note:** Render sets `$PORT` automatically, but FastAPI needs to use it.

### 5.3 Update main.py for Render

The AI service needs to use the PORT environment variable. Update `AI/main.py`:

```python
# In the main() function, change:
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000  # Change this to use PORT from environment
)
```

To:

```python
import os
port = int(os.getenv("PORT", 8000))
uvicorn.run(
    app,
    host="0.0.0.0",
    port=port
)
```

### 5.4 Add Environment Variables

Click **Environment** tab and add:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
QDRANT_URL=https://xxxxx-xxxxx.us-east-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key-here
QDRANT_COLLECTION=learning_vectors
MONGODB_URI=mongodb+srv://sigma_gpt_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority
MONGO_URI=mongodb+srv://sigma_gpt_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority
MONGODB_DB=sigma_gpt

# Optional but recommended:
GOOGLE_API_KEY=your-google-api-key (optional)
GOOGLE_CX=your-google-cx-id (optional)
TAVILY_API_KEY=your-tavily-key (optional)
EXA_API_KEY=your-exa-key (optional)
REDIS_URL=redis://localhost:6379/0 (optional, for persistent memory)
AGENT_MAX_TURNS=12
AGENT_MEMORY_TTL_SECONDS=21600
```

### 5.5 Deploy

Click **Create Web Service** and wait for deployment (~10 minutes)

**Note the URL:** `https://sigma-gpt-ai-service.onrender.com`

---

## 🎨 Step 6: Deploy Frontend to Vercel

### 6.1 Import Project

1. Go to https://vercel.com/
2. Sign up / Log in
3. Click **Add New** → **Project**
4. Import your GitHub repository

### 6.2 Configure Frontend

**Settings:**
- **Framework Preset**: Vite
- **Root Directory**: `Frontend`
- **Build Command**: `npm run build` (auto-detected)
- **Output Directory**: `dist` (auto-detected)

### 6.3 Add Environment Variables

Click **Environment Variables** and add:

```env
VITE_API_URL=https://sigma-gpt-backend.onrender.com
```

**Important:** Replace `sigma-gpt-backend` with your actual Render backend service name.

### 6.4 Deploy

Click **Deploy** and wait (~2 minutes)

**Note the URL:** `https://sigma-gpt.vercel.app` (or your custom domain)

---

## 🔄 Step 7: Update Backend Environment Variable

After deploying the AI service, update the Backend's `AI_SERVICE_URL`:

1. Go to Render Dashboard → Your Backend Service
2. Click **Environment**
3. Update `AI_SERVICE_URL` to: `https://sigma-gpt-ai-service.onrender.com`
4. Click **Save Changes**
5. Render will automatically redeploy

---

## ✅ Step 8: Verify Deployment

### 8.1 Test Backend

Visit: `https://sigma-gpt-backend.onrender.com/api/thread`

Should return: `[]` (empty array) or list of threads

### 8.2 Test AI Service

Visit: `https://sigma-gpt-ai-service.onrender.com/health`

Should return: `{"status": "ok", "message": "Sigma GPT AI Service is running!"}`

### 8.3 Test Frontend

Visit: `https://sigma-gpt.vercel.app`

Should load the chat interface

---

## 🔐 Environment Variables Summary

### Backend (.env)
```env
MONGODB_URI=mongodb+srv://...
OPENAI_API_KEY=sk-...
AI_SERVICE_URL=https://sigma-gpt-ai-service.onrender.com
TZ=UTC
```

### AI Service (.env)
```env
OPENAI_API_KEY=sk-...
QDRANT_URL=https://...
QDRANT_API_KEY=...
QDRANT_COLLECTION=learning_vectors
MONGODB_URI=mongodb+srv://...
MONGO_URI=mongodb+srv://...
MONGODB_DB=sigma_gpt
```

### Frontend (.env)
```env
VITE_API_URL=https://sigma-gpt-backend.onrender.com
```

---

## 🐛 Troubleshooting

### Backend can't connect to MongoDB
- Check MongoDB Atlas IP whitelist (should allow 0.0.0.0/0)
- Verify connection string has correct password
- Check database name in connection string

### Backend can't connect to AI Service
- Verify `AI_SERVICE_URL` is correct
- Check AI service is running (visit `/health` endpoint)
- Check CORS settings in AI service

### Frontend can't connect to Backend
- Verify `VITE_API_URL` is correct
- Check backend is running
- Check CORS settings in backend

### AI Service fails to start
- Check Python version (should be 3.9+)
- Verify all dependencies in `requirements.txt`
- Check logs in Render dashboard

### Qdrant connection fails
- Verify QDRANT_URL is correct (include port 6333)
- Check QDRANT_API_KEY is set (for Qdrant Cloud)
- Verify network access in Qdrant Cloud dashboard

---

## 📝 Notes

1. **Free Tier Limitations:**
   - Render free tier: Services sleep after 15 minutes of inactivity
   - First request after sleep takes ~30 seconds (cold start)
   - Consider upgrading to paid plan for production

2. **GitHub is Required:**
   - Both Vercel and Render need GitHub integration
   - They auto-deploy on every push to main branch

3. **Environment Variables:**
   - Never commit `.env` files to GitHub
   - Always use environment variables in deployment platforms
   - Use `.env.example` files as templates

4. **CORS:**
   - Backend already has `cors()` middleware enabled
   - Should work with Vercel frontend automatically

---

## 🎉 You're Done!

Your Sigma GPT application should now be live at:
- **Frontend**: https://sigma-gpt.vercel.app
- **Backend**: https://sigma-gpt-backend.onrender.com
- **AI Service**: https://sigma-gpt-ai-service.onrender.com

Happy deploying! 🚀

