# 🚨 CRITICAL: Fix MongoDB URI in Render - INCOMPLETE URI DETECTED!

## The Problem

Your MongoDB URIs in Render are **INCOMPLETE** - they end with `?` but are missing the query parameters!

**Current (WRONG):**
```
mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?
```

**Should be (CORRECT):**
```
mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
```

## How to Fix in Render Dashboard

### Step 1: Go to Environment Variables
1. Go to https://dashboard.render.com/
2. Click on **sigma-gpt-ai-service**
3. Go to **Environment** tab

### Step 2: Fix MONGODB_URI

**Variable Name:** `MONGODB_URI`

**Delete the current value and paste this COMPLETE URI:**
```
mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
```

**Important:**
- NO quotes around it
- NO spaces before/after
- Must include ALL query parameters: `?retryWrites=true&w=majority&appName=Cluster0`

### Step 3: Fix MONGO_URI

**Variable Name:** `MONGO_URI`

**Set to the SAME complete URI:**
```
mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
```

### Step 4: Remove Separate appName Variable

**Delete this variable:**
- `appName` = `Cluster0`

**Why?** The `appName` is already part of the MongoDB URI query string. Having it as a separate variable does nothing and can cause confusion.

## ✅ Complete MongoDB URI (Copy This)

```
mongodb+srv://ankursura09_db_user:0vKIm6fo7anlwqpc@cluster0.c9iqfea.mongodb.net/sigma_gpt?retryWrites=true&w=majority&appName=Cluster0
```

## 📋 Checklist

- [ ] `MONGODB_URI` has the COMPLETE URI (ends with `appName=Cluster0`)
- [ ] `MONGO_URI` has the COMPLETE URI (same as above)
- [ ] No separate `appName` variable (delete it)
- [ ] No quotes around the URI values
- [ ] No spaces before/after

## After Fixing

1. Click **Save Changes** in Render
2. Render will automatically redeploy
3. Check logs - you should see:
   - `✅ RAG Checkpointer: Connected to MongoDB`
   - `✅ Connected to MongoDB checkpointer`
   - `✅ Connected to Global Memory`

## Why This Happened

The URI was probably cut off when you pasted it, or Render's UI truncated it. Make sure to paste the COMPLETE URI including all query parameters.

