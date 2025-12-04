# 🔧 How to Fix MongoDB URI in Render Dashboard

## The Problem

The error "MongoDB URI options are key=value pairs" usually means:
1. **Extra quotes** in the environment variable
2. **Whitespace** before/after the URI
3. **Copy-paste issues** adding hidden characters

## ✅ Correct Way to Add MongoDB URI in Render

### Step 1: Go to Render Dashboard
1. Go to https://dashboard.render.com/
2. Click on your **sigma-gpt-ai-service**
3. Go to **Environment** tab

### Step 2: Check MONGODB_URI Variable

**Variable Name:** `MONGODB_URI`

**Value (EXACTLY like this - NO QUOTES):**
```
mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
```

### Step 3: Also Check MONGO_URI Variable

**Variable Name:** `MONGO_URI`

**Value (SAME as MONGODB_URI - NO QUOTES):**
```
mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
```

## ⚠️ Common Mistakes

### ❌ WRONG (with quotes):
```
"mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0"
```

### ❌ WRONG (with spaces):
```
 mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0 
```

### ✅ CORRECT (no quotes, no spaces):
```
mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
```

## 📋 Checklist

- [ ] Variable name is exactly: `MONGODB_URI` (case-sensitive)
- [ ] Value starts with `mongodb+srv://` (no quotes)
- [ ] No spaces before or after the URI
- [ ] No quotes around the value
- [ ] Copy the URI exactly as shown above

## 🔍 How to Verify

After updating, check the deployment logs. You should see:
- `✅ RAG Checkpointer: Connected to MongoDB`
- `✅ Connected to MongoDB checkpointer`
- `✅ Connected to Global Memory`

Instead of warnings!

## 💡 Pro Tip

If you're still getting errors, check the logs for:
- `Raw URI from env: ...` - This shows what Render is actually passing
- `URI length: ...` - Should be around 120-130 characters

If the URI looks wrong in the logs, it means Render has it stored incorrectly.

