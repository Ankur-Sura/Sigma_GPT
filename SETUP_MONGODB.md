# 🔐 MongoDB Atlas Setup Complete

## ✅ MongoDB Connection String Format

Your MongoDB Atlas connection string should follow this format:

```
mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
```

**⚠️ IMPORTANT:** Replace `YOUR_USERNAME`, `YOUR_PASSWORD`, and `xxxxx` with your actual MongoDB Atlas credentials.

## 📝 Where to Add This

### 1. Backend Environment Variables

**File:** `Backend/.env`

```env
MONGODB_URI=mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
OPENAI_API_KEY=sk-your-openai-api-key-here
AI_SERVICE_URL=http://localhost:8000
TZ=UTC
```

### 2. AI Service Environment Variables

**File:** `AI/.env`

```env
MONGODB_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
MONGO_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
MONGODB_DB=sigma_gpt
OPENAI_API_KEY=sk-your-openai-api-key-here
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=learning_vectors
```

### 3. For Production (Render Dashboard)

When deploying to Render, add this connection string in the **Environment Variables** section:

**Backend Service:**
- Variable: `MONGODB_URI`
- Value: `mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0`

**AI Service:**
- Variable: `MONGODB_URI`
- Value: `mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0`
- Variable: `MONGO_URI`
- Value: `mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0`

## 🔒 Security Checklist

- [x] Connection string includes database name (`sigma_gpt`)
- [x] Connection string includes retry writes and write concern
- [ ] **IMPORTANT:** Make sure MongoDB Atlas Network Access allows Render IPs
  - Go to MongoDB Atlas → Network Access
  - Add IP: `0.0.0.0/0` (allows all IPs) OR add specific Render IPs
  - This is required for Render to connect!

## 🧪 Test Connection Locally

### Test Backend Connection:
```bash
cd Backend
npm install
npm start
# Should see: "Connected with Database!"
```

### Test AI Service Connection:
```bash
cd AI
pip install -r requirements.txt
python main.py
# Check logs for MongoDB connection messages
```

## ⚠️ Important Notes

1. **Never commit `.env` files** - They're already in `.gitignore`
2. **Password Security** - This password is now in your connection string. Keep it secure!
3. **Network Access** - Make sure MongoDB Atlas allows connections from Render (0.0.0.0/0)
4. **Database Name** - Your database is `sigma_gpt` (already in connection string)

## 🎯 Next Steps

1. Add this connection string to your local `.env` files
2. Test the connection locally
3. When deploying to Render, add it to the environment variables
4. Verify MongoDB Atlas Network Access settings

Your MongoDB is ready to use! 🚀

