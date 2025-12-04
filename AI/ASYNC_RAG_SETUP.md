# 🚀 Async RAG Setup Guide (Valkey/Redis + RQ)

## 📋 What You Need

### ✅ Required:
1. **Redis or Valkey Server** - Message queue storage
2. **RQ Worker Process** - Background job processor
3. **REDIS_URL environment variable** - Connection string

### ❌ NOT Required:
- ❌ Separate API - RQ handles everything
- ❌ Complex setup - Just Redis + Worker

---

## 🛠️ Setup Options

### Option 1: Local Redis (Development)

#### Step 1: Install & Start Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Docker (Any OS):**
```bash
docker run -d -p 6379:6379 redis:latest
```

#### Step 2: Set Environment Variable

Add to your `.env` file:
```env
REDIS_URL=redis://localhost:6379/0
```

#### Step 3: Start RQ Worker

Create a worker script or run directly:

```bash
# In the AI directory
cd AI
rq worker pdf_processing --url redis://localhost:6379/0
```

Or create `AI/worker.py`:
```python
from rq import Worker, Queue, Connection
import redis

redis_conn = redis.Redis.from_url('redis://localhost:6379/0')
queue = Queue('pdf_processing', connection=redis_conn)

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker([queue])
        worker.work()
```

Run worker:
```bash
python AI/worker.py
```

---

### Option 2: Cloud Redis (Production - Render)

#### Step 1: Add Redis to Render

1. Go to Render Dashboard
2. Click "New +" → "Redis"
3. Choose free tier (if available) or paid
4. Copy the **Internal Redis URL** (e.g., `redis://red-xxxxx:6379`)

#### Step 2: Set Environment Variable

In Render Dashboard → Your AI Service → Environment:
```env
REDIS_URL=redis://red-xxxxx:6379
```

#### Step 3: Start RQ Worker on Render

**Option A: Separate Worker Service (Recommended)**

1. Create new "Background Worker" service on Render
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `rq worker pdf_processing --url $REDIS_URL`
4. Use same Redis URL as your AI service

**Option B: Same Service (Not Recommended)**
- Run worker in background thread (complex, not ideal)

---

### Option 3: Valkey (Redis Fork)

Valkey is 100% Redis-compatible, just use `valkey://` instead of `redis://`:

```env
REDIS_URL=valkey://localhost:6379/0
```

Everything else is the same!

---

## 🔄 How It Works

```
User uploads PDF
    ↓
FastAPI endpoint queues job → Redis
    ↓
Returns job_id immediately ✅
    ↓
RQ Worker picks up job from queue
    ↓
Processes: OCR → Chunk → Embed → Store
    ↓
Updates status in Redis
    ↓
User polls /pdf/job/{job_id} for status
```

---

## 📝 Quick Test

### 1. Start Redis:
```bash
redis-server
# Or: docker run -d -p 6379:6379 redis
```

### 2. Start RQ Worker:
```bash
cd AI
rq worker pdf_processing --url redis://localhost:6379/0
```

### 3. Start AI Service:
```bash
cd AI
python main.py
```

### 4. Upload PDF:
```bash
curl -X POST http://localhost:8000/pdf/upload \
  -F "file=@test.pdf"
```

**Response (Async Mode):**
```json
{
  "status": "queued",
  "job_id": "abc-123-def",
  "message": "PDF upload queued for processing",
  "check_status_url": "/pdf/job/abc-123-def"
}
```

### 5. Check Status:
```bash
curl http://localhost:8000/pdf/job/abc-123-def
```

---

## ⚠️ Fallback Behavior

**If REDIS_URL is NOT set:**
- ✅ System works in **synchronous mode**
- ✅ PDFs process immediately (but user waits 2-5 minutes)
- ✅ No Redis/Worker needed
- ⚠️ May timeout on large PDFs

**If REDIS_URL IS set but worker not running:**
- ✅ Jobs queue successfully
- ❌ Jobs never process (stuck in queue)
- ⚠️ User sees "queued" status forever

**Always ensure worker is running when using async mode!**

---

## 🎯 Summary

| Component | Required? | What It Does |
|-----------|-----------|--------------|
| **Redis/Valkey** | ✅ Yes (for async) | Stores job queue |
| **RQ Worker** | ✅ Yes (for async) | Processes jobs |
| **Separate API** | ❌ No | RQ handles it |
| **REDIS_URL** | ✅ Yes (for async) | Connection string |

**Without Redis:** System works synchronously (slower, but works)
**With Redis:** System works asynchronously (faster, better UX)

