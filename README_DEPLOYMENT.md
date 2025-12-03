# 🚀 Quick Deployment Checklist

## ✅ Pre-Deployment Checklist

### 1. Code Changes Made ✓
- [x] Created root `.gitignore` to exclude `.env` files
- [x] Updated Frontend to use environment variables (`VITE_API_URL`)
- [x] Created `Frontend/src/config.js` for centralized API configuration
- [x] Updated all fetch calls in `Sidebar.jsx` and `ChatWindow.jsx` to use `API_URL`
- [x] Updated `AI/main.py` to use `PORT` environment variable for Render
- [x] Created deployment documentation

### 2. Environment Variables Setup
- [x] Backend: `MONGODB_URI`, `OPENAI_API_KEY`, `AI_SERVICE_URL`
- [x] AI Service: `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `MONGODB_URI`, etc.
- [x] Frontend: `VITE_API_URL`

### 3. Documentation Created
- [x] `DEPLOYMENT.md` - Complete deployment guide
- [x] `ENVIRONMENT_VARIABLES.md` - Environment variables reference

---

## 📋 Deployment Steps Summary

### Step 1: Upload to GitHub
```bash
cd "/Users/ankursura/Desktop/Sigma GPT"
git init  # if not already initialized
git add .
git commit -m "Ready for deployment"
git remote add origin https://github.com/YOUR_USERNAME/sigma-gpt.git
git push -u origin main
```

### Step 2: Set Up Services
1. **MongoDB Atlas**: Create cluster, get connection string
2. **Qdrant Cloud**: Create cluster, get URL and API key
3. **Render Backend**: Deploy with environment variables
4. **Render AI Service**: Deploy with environment variables
5. **Vercel Frontend**: Deploy with `VITE_API_URL`

### Step 3: Update URLs
After deploying AI service, update Backend's `AI_SERVICE_URL` in Render dashboard.

---

## 🔍 Testing Locally (Before Deployment)

### Test Backend:
```bash
cd Backend
npm install
npm start
# Should run on http://localhost:8080
```

### Test AI Service:
```bash
cd AI
pip install -r requirements.txt
python main.py
# Should run on http://localhost:8000
# Visit http://localhost:8000/health to verify
```

### Test Frontend:
```bash
cd Frontend
npm install
npm run dev
# Should run on http://localhost:5173
# Make sure VITE_API_URL=http://localhost:8080 in .env
```

---

## ⚠️ Important Notes

1. **GitHub is Required**: Both Vercel and Render need GitHub integration
2. **Free Tier Limitations**: Render services sleep after 15 min inactivity (cold start ~30s)
3. **Environment Variables**: Never commit `.env` files, always use platform's env vars
4. **CORS**: Already configured in Backend, should work automatically

---

## 📚 Full Documentation

- **Complete Guide**: See `DEPLOYMENT.md`
- **Environment Variables**: See `ENVIRONMENT_VARIABLES.md`

---

## 🎯 Next Steps

1. Upload code to GitHub
2. Follow `DEPLOYMENT.md` step-by-step
3. Test each service after deployment
4. Update environment variables as needed

Good luck! 🚀

