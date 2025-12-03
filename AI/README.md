# 🤖 Sigma GPT AI Service

## 📚 What is this?

This is the **AI Backend Service** for Sigma GPT. It's a FastAPI server that provides AI capabilities to your application.

## 🔗 How it Connects

```
Frontend (React - port 5173)
         ↓
Backend (Node.js/Express - port 8080)
         ↓
AI Service (FastAPI/Python - port 8000)  ← THIS IS HERE!
         ↓
Qdrant Vector DB (port 6333)
```

## 📁 File Structure

```
AI/
├── main.py           # 🚀 Server entry point (like your notes/advanced_rag/main.py)
├── rag_service.py    # 📄 RAG - PDF upload & query (like your notes/04-RAG/)
├── agent_service.py  # 🤖 AI Agent with tools (like your notes/03-Agents/)
├── tools_service.py  # 🛠️ STT, OCR, Search tools
├── requirements.txt  # 📦 Python dependencies
└── README.md         # 📖 This file
```

## 🚀 How to Run

### Step 1: Install Dependencies

```bash
cd AI
pip install -r requirements.txt
```

### Step 2: Set Up Environment Variables

Create a `.env` file in the AI folder:

```env
OPENAI_API_KEY=sk-your-key-here
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=learning_vectors

# Optional for better web search:
GOOGLE_API_KEY=your-google-key
GOOGLE_CX=your-search-engine-id

# Optional for persistent memory:
REDIS_URL=redis://localhost:6379/0
```

### Step 3: Start Qdrant (Vector Database)

```bash
# Using Docker:
docker run -p 6333:6333 qdrant/qdrant
```

### Step 4: Run the Server

```bash
# Simple run:
python main.py

# Or with auto-reload (for development):
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Verify it's Running

Visit: http://localhost:8000/docs

You'll see the auto-generated API documentation!

---

## 📖 API Endpoints

### Health Check
```
GET /health
→ { "status": "ok" }
```

### RAG (Retrieval Augmented Generation)
```
POST /pdf/upload     ← Upload a PDF for indexing
POST /rag/query      ← Ask questions about ALL indexed content
POST /pdf/query      ← Ask questions about a SPECIFIC PDF
```

### AI Agent (Web Search)
```
POST /agent/web-search   ← Ask questions, agent can search the web
POST /agent/reset-memory ← Clear conversation history
```

### Tools
```
POST /stt/transcribe  ← Convert audio to text (Whisper)
POST /ocr/image       ← Extract text from images (Tesseract)
GET  /search          ← Simple web search (DuckDuckGo)
```

---

## 🎓 Learning Path: Mapping Notes to Code

### Your Notes → This Code

| Your Notes File | This Code File | What It Does |
|-----------------|----------------|--------------|
| `04-RAG/indexing.py` | `rag_service.py` → `/pdf/upload` | Upload & index PDFs |
| `04-RAG/chat.py` | `rag_service.py` → `/rag/query` | Query PDFs with RAG |
| `03-Agents/main.py` | `agent_service.py` | AI Agent with tools |
| `advanced_rag/main.py` | `main.py` | FastAPI server setup |
| `advanced_rag/server.py` | `main.py` | FastAPI routes |

### Key Concepts from Your Notes

#### 1. FastAPI (from your notes: advanced_rag/main.py)
```python
# Your notes:
uvicorn.run(app, port=8000, host="0.0.0.0")

# This code (main.py):
uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 2. RAG Pipeline (from your notes: 04-RAG/)
```python
# Your notes (indexing.py):
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=400)
split_docs = text_splitter.split_documents(documents=docs)
vector_store = QdrantVectorStore.from_documents(...)

# This code (rag_service.py):
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
# ... same pattern!
QdrantVectorStore.from_documents(...)
```

#### 3. AI Agent (from your notes: 03-Agents/main.py)
```python
# Your notes:
if parsed_response.get("step") == "plan":
    print(f"🧠: {parsed_response.get('content')}")
    continue
if parsed_response.get("step") == "action":
    tool_name = parsed_response.get("function")
    # ...

# This code (agent_service.py):
if step == "plan":
    steps.append({"step": step, "payload": parsed})
    continue
if step == "action":
    tool_name = parsed.get("function")
    # ... same pattern!
```

---

## 🔄 System Requirements

### Required
- Python 3.9+
- OpenAI API Key
- Qdrant (running on port 6333)

### Optional (for full functionality)
- **Tesseract** (for OCR):
  ```bash
  # macOS:
  brew install tesseract
  
  # Ubuntu:
  sudo apt-get install tesseract-ocr
  ```

- **Poppler** (for PDF OCR):
  ```bash
  # macOS:
  brew install poppler
  
  # Ubuntu:
  sudo apt-get install poppler-utils
  ```

- **Redis** (for persistent memory):
  ```bash
  docker run -p 6379:6379 redis
  ```

---

## 💡 Interview Talking Points

### "How does your AI service work?"

> "I built a FastAPI backend that provides AI capabilities. It has three main parts:
> 1. **RAG Service** - For PDF Q&A. It uploads PDFs, chunks them, creates embeddings, stores in Qdrant, and uses similarity search to answer questions.
> 2. **Agent Service** - An AI agent that can plan, use tools (like web search), and give grounded answers.
> 3. **Tools Service** - Speech-to-text using Whisper, OCR using Tesseract, and simple web search."

### "Explain RAG"

> "RAG stands for Retrieval Augmented Generation. LLMs only know their training data. For my specific documents, I:
> 1. Split documents into chunks
> 2. Create embeddings (vector representations) using OpenAI
> 3. Store in Qdrant vector database
> 4. When user asks a question, I find similar chunks using cosine similarity
> 5. Add those chunks to the LLM's context
> 6. LLM generates answer based on retrieved context"

### "What's an AI Agent?"

> "An AI Agent is different from a simple chatbot. It follows a plan-action-observe-output pattern:
> 1. **Plan** - Thinks about what to do
> 2. **Action** - Calls a tool (like web search)
> 3. **Observe** - Sees the results
> 4. **Output** - Gives final answer
> 
> It can take actions in the real world, not just respond to text."

### "Why FastAPI?"

> "FastAPI is a modern Python web framework with:
> - Automatic API documentation (/docs)
> - Built-in data validation with Pydantic
> - Async support for handling many requests
> - Easy integration with AI/ML libraries"

---

## 🐛 Troubleshooting

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "Connection refused to Qdrant"
```bash
# Make sure Qdrant is running:
docker run -p 6333:6333 qdrant/qdrant
```

### "OpenAI API Error"
Check your `.env` file has a valid `OPENAI_API_KEY`

### "OCR not working"
Make sure Tesseract is installed on your system (see System Requirements above)

---

Made with ❤️ for learning AI development
