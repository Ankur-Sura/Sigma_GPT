#!/usr/bin/env python3
"""
📖 RQ Worker for Async PDF Processing
------------------------------------
This worker processes PDF jobs from the Redis/Valkey queue.

🔗 Following your Notes Compare async RAG pattern!

Usage:
    python worker.py
    
Or with custom Redis URL:
    REDIS_URL=redis://localhost:6379/0 python worker.py
"""

import os
from rq import Worker, Queue, Connection
import redis

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

print("=" * 60)
print("🚀 Starting RQ Worker for PDF Processing")
print(f"   Redis URL: {REDIS_URL}")
print(f"   Queue: pdf_processing")
print("=" * 60)

try:
    # Connect to Redis
    redis_conn = redis.Redis.from_url(REDIS_URL)
    redis_conn.ping()  # Test connection
    print("✅ Connected to Redis/Valkey")
    
    # Create queue
    queue = Queue("pdf_processing", connection=redis_conn)
    print(f"✅ Queue 'pdf_processing' ready")
    
    # Start worker
    print("👷 Worker started - waiting for jobs...")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    
    with Connection(redis_conn):
        worker = Worker([queue])
        worker.work()
        
except KeyboardInterrupt:
    print("\n👋 Worker stopped by user")
except redis.ConnectionError as e:
    print(f"❌ Failed to connect to Redis: {e}")
    print(f"   Make sure Redis is running at: {REDIS_URL}")
    print("   Start Redis with: redis-server")
    print("   Or Docker: docker run -d -p 6379:6379 redis")
except Exception as e:
    print(f"❌ Worker error: {e}")

