# 🚀 Quick Start Guide

## ✅ Automated Setup Complete!

I've automatically set up your environment variables with your MongoDB connection string.

## 📋 What Was Done

1. ✅ Created `Backend/.env` with MongoDB connection string
2. ✅ Created `AI/.env` with MongoDB connection string  
3. ✅ Created `Frontend/.env` with API URL configuration
4. ✅ Created setup scripts for future use
5. ✅ Verified project structure

## 🔧 Next Steps

### 1. Add Your OpenAI API Key

Edit these files and replace `sk-your-openai-api-key-here` with your actual key:

- `Backend/.env` - Line with `OPENAI_API_KEY`
- `AI/.env` - Line with `OPENAI_API_KEY`

Get your key from: https://platform.openai.com/api-keys

### 2. Install Dependencies

```bash
# Backend
cd Backend
npm install

# AI Service
cd ../AI
pip install -r requirements.txt

# Frontend
cd ../Frontend
npm install
```

### 3. Start Services

**Terminal 1 - Backend:**
```bash
cd Backend
npm start
# Should run on http://localhost:8080
# Should see: "Connected with Database!"
```

**Terminal 2 - AI Service:**
```bash
cd AI
python main.py
# Should run on http://localhost:8000
# Visit http://localhost:8000/health to verify
```

**Terminal 3 - Frontend:**
```bash
cd Frontend
npm run dev
# Should run on http://localhost:5173
```

### 4. Verify Everything Works

1. Open http://localhost:5173 in your browser
2. Try sending a message
3. Check backend logs for "Connected with Database!"
4. Check AI service logs for startup messages

## 🔍 Verify Setup

Run the verification script:
```bash
bash verify_setup.sh
```

## 📝 Environment Files Created

- ✅ `Backend/.env` - Backend configuration
- ✅ `AI/.env` - AI service configuration
- ✅ `Frontend/.env` - Frontend configuration

All files include your MongoDB connection string!

## ⚠️ Important Notes

1. **OpenAI API Key Required**: You must add your OpenAI API key to both Backend and AI .env files
2. **MongoDB Atlas Network Access**: Make sure MongoDB Atlas allows connections from your IP (or 0.0.0.0/0 for development)
3. **Qdrant**: If using Qdrant Cloud, update `QDRANT_URL` and `QDRANT_API_KEY` in `AI/.env`

## 🐛 Troubleshooting

### Backend can't connect to MongoDB
- Check MongoDB Atlas Network Access (should allow your IP)
- Verify connection string in `Backend/.env`
- Check MongoDB Atlas cluster is running

### AI Service can't connect to MongoDB
- Same as above, but check `AI/.env`
- Verify both `MONGODB_URI` and `MONGO_URI` are set

### Frontend can't connect to Backend
- Verify `VITE_API_URL=http://localhost:8080` in `Frontend/.env`
- Make sure Backend is running on port 8080
- Check browser console for CORS errors

## 🎯 Ready for Deployment?

Once everything works locally, follow `DEPLOYMENT.md` to deploy to:
- Frontend → Vercel
- Backend → Render
- AI Service → Render

Your MongoDB connection string is already configured! 🎉

