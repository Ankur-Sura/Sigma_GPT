"""
===================================================================================
                    RAG_SERVICE.PY - RAG (Retrieval Augmented Generation)
===================================================================================

📚 WHAT IS RAG?
--------------
RAG = Retrieval Augmented Generation

It's a technique where:
1. User asks a question
2. We RETRIEVE relevant information from a database (like PDF chunks)
3. We AUGMENT the LLM's prompt with this retrieved context
4. LLM GENERATES an answer based on the context

📌 WHY RAG?
-----------
LLMs (like GPT) only know what they were trained on.
They don't know about:
- Your personal PDFs
- Your company documents
- Recent information

RAG solves this! We give the LLM the relevant context, and it answers based on that.

🔗 THIS IS EXACTLY WHAT YOU LEARNED IN:
    - Notes Compare/04-RAG/indexing.py (for PDF indexing)
    - Notes Compare/04-RAG/chat.py (for querying)

===================================================================================
                            THE RAG PIPELINE
===================================================================================

Step 1: INDEXING (one-time, when PDF is uploaded)
-------------------------------------------------
    PDF File
        ↓
    Extract Text (page by page)
        ↓
    Split into Chunks (smaller pieces)
        ↓
    Create Embeddings (convert text to numbers/vectors)
        ↓
    Store in Vector Database (Qdrant)

Step 2: QUERYING (every time user asks a question)
--------------------------------------------------
    User Question: "What is Node.js?"
        ↓
    Create Embedding of Question
        ↓
    Similarity Search in Qdrant (find similar chunks)
        ↓
    Get Top K Matching Chunks
        ↓
    Send (Question + Context) to LLM
        ↓
    LLM Generates Answer
        ↓
    Return Answer to User

===================================================================================
"""

# =============================================================================
#                           IMPORTS SECTION
# =============================================================================

# ----- Standard Library Imports -----
import os
from io import BytesIO  # For reading file bytes in memory
from uuid import uuid4  # For generating unique IDs

# ----- MongoDB for Checkpointing -----
from pymongo import MongoClient
"""
📖 Why MongoDB in RAG Service?
------------------------------
We use MongoDB to save PDF Q&A conversations so that follow-up
questions can reference previous answers.

Example:
- User uploads resume.pdf
- User asks: "What are my skills?"
- AI answers: "Python, JavaScript, React..."
- User asks: "Tell me more about my Python experience"
- AI needs to remember what "my" refers to (the resume)!

This is the same checkpointing pattern used in agent_service.py!
"""

# ----- Redis/Valkey for Async Message Queue -----
import redis
from rq import Queue
import json
"""
📖 Why Redis/Valkey + RQ for Async RAG?
----------------------------------------
Following your Notes Compare pattern for asynchronous processing:

Problem with synchronous RAG:
    - User uploads PDF → waits 2-5 minutes for processing
    - OCR, chunking, embedding all happen in request handler
    - Server blocked, user sees timeout errors

Solution: Async RAG with message queue
    - User uploads PDF → returns job_id immediately
    - Background worker processes: OCR → chunk → embed → store
    - User polls status endpoint or gets notified when done

🔗 Your Notes Compare pattern:
    from redis import Redis
    from rq import Queue
    queue = Queue(connection=Redis())
    job = queue.enqueue(process_pdf, pdf_bytes, filename)
    
This is exactly what we're implementing here!
"""

# ----- FastAPI Imports -----
from fastapi import APIRouter, HTTPException, UploadFile, File
"""
📖 What are these FastAPI imports?
----------------------------------

APIRouter:
    - Creates a "sub-application" with its own routes
    - Later we include this router in the main app
    - Keeps code organized (all RAG routes in one place)

HTTPException:
    - For returning HTTP error responses
    - Example: HTTPException(status_code=400, detail="Bad request")

UploadFile:
    - Represents an uploaded file from the user
    - Has properties like: filename, content_type, read()

File:
    - A dependency that tells FastAPI to expect a file upload
    - Used with UploadFile in endpoint parameters
"""

from pydantic import BaseModel
from typing import Optional
"""
📖 What is Pydantic?
--------------------
Pydantic is a data validation library.

✔ It defines the SHAPE of data you expect
✔ FastAPI uses it to validate incoming requests
✔ If data doesn't match, FastAPI automatically returns an error

Example:
    class RAGQuery(BaseModel):
        question: str        # MUST be a string
        k: Optional[int] = 4 # Optional, defaults to 4
        
    If someone sends {"question": 123}, FastAPI says:
    "Error: question must be a string"

🔗 In your notes (06-LangGraph/codegraph.py), you used Pydantic:
    class ClassifyMessageResponse(BaseModel):
        is_coding_question: bool
"""

# ----- LangChain Imports -----
from langchain_text_splitters import RecursiveCharacterTextSplitter
"""
📖 What is RecursiveCharacterTextSplitter?
------------------------------------------
From langchain_text_splitters library.

✔ Splits long text into smaller chunks
✔ Keeps paragraphs and sentences together when possible
✔ Uses "recursive" approach - tries to split by paragraph, then sentence, then character

Why split?
    - LLMs have token limits (can't process huge texts)
    - Smaller chunks = more precise similarity search
    - Better matches to user's question

🔗 In your notes (04-RAG/indexing.py), you did EXACTLY this:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,    # Each chunk up to 1000 characters
        chunk_overlap=400   # Overlap so we don't lose context at boundaries
    )
"""

from langchain_openai import OpenAIEmbeddings
"""
📖 What is OpenAIEmbeddings?
----------------------------
From langchain_openai library.

✔ Converts text into vectors (numbers) using OpenAI's embedding model
✔ These vectors represent the "meaning" of the text
✔ Similar meanings = similar vectors (close in vector space)

How it works:
    "I love programming"  →  [0.1, 0.5, -0.3, 0.8, ...]  (1536 numbers)
    "Coding is my passion" → [0.12, 0.48, -0.28, 0.79, ...] (similar numbers!)
    "I hate cooking"       → [-0.5, 0.2, 0.7, -0.1, ...]  (different numbers)

🔗 In your notes (04-RAG/indexing.py), you did EXACTLY this:
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
    
📌 Note: We use "text-embedding-3-small" here for cost efficiency.
         "large" is more accurate but costs more.
"""

from langchain_qdrant import QdrantVectorStore
"""
📖 What is QdrantVectorStore?
-----------------------------
From langchain_qdrant library.

✔ Connects LangChain to Qdrant vector database
✔ Qdrant stores vectors and enables similarity search
✔ When we search, Qdrant finds the closest vectors to our query

Why Qdrant?
    - Open source and free
    - Very fast similarity search
    - Can handle millions of vectors
    - Has a nice REST API

🔗 In your notes (04-RAG/indexing.py), you did EXACTLY this:
    vector_store = QdrantVectorStore.from_documents(
        documents=split_docs,
        url="http://localhost:6333",
        collection_name="learning_vectors",
        embedding=embedding_model
    )
"""

from langchain_core.documents import Document
"""
📖 What is Document?
--------------------
From langchain_core library.

✔ A simple class that holds:
    - page_content: The actual text
    - metadata: Extra info (page number, source file, etc.)

When we split a PDF, each chunk becomes a Document object.
"""

from qdrant_client.http.models import Filter, FieldCondition, MatchValue, PayloadSchemaType
from qdrant_client import QdrantClient
"""
📖 What are these Qdrant filter classes?
----------------------------------------
From qdrant_client library.

✔ Used to FILTER search results
✔ Example: Only search in a specific PDF

Filter = The overall filter container
FieldCondition = A condition to check (like "pdf_id must equal 'abc'")
MatchValue = The value to match against

📌 Why filter?
    - User might have uploaded multiple PDFs
    - When they ask about one PDF, we only want chunks from THAT PDF
    - Filter ensures we don't mix up information from different sources
"""

# ----- PDF Processing -----
from pypdf import PdfReader
"""
📖 What is PdfReader?
--------------------
From pypdf library (pip install pypdf).

✔ Reads PDF files and extracts text
✔ Can process page-by-page
✔ Handles most PDF formats

🔗 Your notes use PyPDFLoader from langchain, but it's the same concept!
"""

# ----- OCR Support for Scanned PDFs -----
try:
    from PIL import Image
except Exception:
    Image = None

# =============================================================================
# OCR.space API for scanned PDFs (fast, cloud-based)
# =============================================================================
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "K85482928388957")  # Free demo key

def ocr_space_for_pdf(image_bytes: bytes) -> str:
    """Call OCR.space API for PDF page OCR with optimized settings"""
    import base64
    import requests
    
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Optimized payload for better PDF OCR accuracy
        payload = {
            'apikey': OCR_SPACE_API_KEY,
            'base64Image': f'data:image/png;base64,{base64_image}',
            'language': 'eng',
            'isOverlayRequired': False,  # Don't need overlay for text extraction
            'detectOrientation': True,   # Auto-rotate if needed
            'scale': True,               # Scale up small text
            'OCREngine': 2,              # Engine 2: Better for documents
            'detectCheckbox': False,     # Not needed for code/text
            'isCreateSearchablePdf': False,  # We only need text
            'isSearchablePdfHideTextLayer': False,
        }
        
        response = requests.post(
            'https://api.ocr.space/parse/image',
            data=payload,
            timeout=60  # Increased timeout for better quality processing
        )
        
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            error_msg = result.get('ErrorMessage', ['Unknown error'])
            print(f"⚠️ OCR.space error: {error_msg}")
            return ""
        
        parsed_results = result.get('ParsedResults', [])
        if parsed_results:
            text = parsed_results[0].get('ParsedText', '').strip()
            
            # Clean up common OCR artifacts
            # Remove excessive whitespace but preserve line breaks
            import re
            text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces → single space
            text = re.sub(r' +([\n\r])', r'\1', text)  # Remove trailing spaces before newlines
            
            return text
        
        return ""
    except Exception as e:
        print(f"⚠️ OCR.space API failed for PDF: {e}")
        return ""

def is_ocr_space_available():
    return bool(OCR_SPACE_API_KEY)


def fix_ocr_code_formatting(text: str) -> str:
    """
    Fix PDF/OCR text that concatenates words without spaces.
    """
    import re
    
    if not text:
        return text
    
    # ==========================================================================
    # Simple regex-based approach: Insert spaces around known keywords
    # ==========================================================================
    
    # Keywords followed by uppercase letter need space: "staticNode" → "static Node"
    keywords = ['public', 'private', 'protected', 'static', 'final', 'abstract',
                'void', 'int', 'long', 'short', 'byte', 'float', 'double', 'boolean', 'char',
                'class', 'interface', 'enum', 'extends', 'implements',
                'return', 'throw', 'throws', 'try', 'catch', 'finally',
                'new', 'this', 'super', 'null', 'true', 'false']
    
    # Add space AFTER keyword when followed by uppercase
    for kw in keywords:
        text = re.sub(rf'({kw})([A-Z])', rf'\1 \2', text)
    
    # Add space BEFORE keyword when preceded by lowercase letter and keyword at word start
    # "publicstatic" → "public static"
    for kw in sorted(keywords, key=len, reverse=True):  # Longest first
        # Look for: lowercase + keyword + (uppercase or keyword or end)
        text = re.sub(rf'([a-z])({kw})([A-Z])', rf'\1 \2 \3', text)
        text = re.sub(rf'([a-z])({kw})$', rf'\1 \2', text)
        # Handle keyword at start of what looks like concatenation
        for kw2 in keywords:
            if kw != kw2:
                text = re.sub(rf'({kw})({kw2})', rf'\1 \2', text)
    
    # ==========================================================================
    # Handle type names: "Noderoot" → "Node root"
    # ==========================================================================
    types = ['Node', 'String', 'Integer', 'Boolean', 'Object', 'List', 'Math', 'System', 'Arrays']
    
    for tn in types:
        # Type followed by lowercase: "Noderoot" → "Node root"
        text = re.sub(rf'({tn})([a-z])', rf'\1 \2', text)
        # Lowercase followed by Type: "xNode" → "x Node"
        text = re.sub(rf'([a-z])({tn})', rf'\1 \2', text)
    
    # ==========================================================================
    # Specific fixes
    # ==========================================================================
    
    # "intgetBalance" → "int getBalance"
    text = re.sub(r'\bint([a-z])', r'int \1', text)
    # "voidmain" → "void main"  
    text = re.sub(r'\bvoid([a-z])', r'void \1', text)
    # "returnroot" → "return root", "return0" → "return 0"
    text = re.sub(r'\breturn([a-zA-Z0-9])', r'return \1', text)
    # "newNode" → "new Node"
    text = re.sub(r'\bnew([A-Z])', r'new \1', text)
    
    # ==========================================================================
    # Fix method names that got split incorrectly
    # ==========================================================================
    
    # "getMin Node" → "getMinNode" (method name, not two words)
    text = re.sub(r'\b(getMin|getMax|delete|insert|search|find|remove)\s+Node\b', r'\1Node', text)
    # "Node T2" → "Node T2" (keep as is - T2 is a variable name)
    # But "NodeT2" → "Node T2"
    text = re.sub(r'\bNode([A-Z]\d)', r'Node \1', text)
    
    # ==========================================================================
    # Fix common word concatenations in explanations (BE CAREFUL!)
    # ==========================================================================
    
    # "BSTdeleteisarecursivefunction" → "BST delete is a recursive function"
    # Only split when word boundaries are clear
    common_words = ['is', 'are', 'in', 'of', 'the', 'to', 'and', 'or', 'for', 'with', 'from', 'by', 'at', 'on', 'a', 'an']
    for word in sorted(common_words, key=len, reverse=True):
        # Only split if word is between lowercase letters (not breaking valid words)
        # "deleteis" → "delete is" but don't break "this" or "island"
        text = re.sub(rf'([a-z]{{3,}})({word})([a-z]{{3,}})', rf'\1 \2 \3', text, flags=re.IGNORECASE)
    
    # "BalanceFactorinAVLtree" → "Balance Factor in AVL tree"
    # Split CamelCase: lowercase followed by uppercase
    text = re.sub(r'([a-z]{2,})([A-Z][a-z]{2,})', r'\1 \2', text)
    # "AVLtree" → "AVL tree" (all caps followed by lowercase)
    text = re.sub(r'([A-Z]{2,})([a-z]{2,})', r'\1 \2', text)
    
    # ==========================================================================
    # Fix operators and brackets
    # ==========================================================================
    
    # Operators
    text = re.sub(r'([a-zA-Z0-9])=([a-zA-Z0-9])', r'\1 = \2', text)
    text = re.sub(r'([a-zA-Z0-9])==([a-zA-Z0-9])', r'\1 == \2', text)
    text = re.sub(r'([a-zA-Z0-9])!=([a-zA-Z0-9])', r'\1 != \2', text)
    text = re.sub(r'([a-zA-Z0-9])<([a-zA-Z0-9])', r'\1 < \2', text)
    text = re.sub(r'([a-zA-Z0-9])>([a-zA-Z0-9])', r'\1 > \2', text)
    text = re.sub(r'([a-zA-Z0-9])&&([a-zA-Z0-9])', r'\1 && \2', text)
    text = re.sub(r'([a-zA-Z0-9])\|\|([a-zA-Z0-9])', r'\1 || \2', text)
    
    # Brackets
    text = re.sub(r'\b(if|while|for|switch|catch)\(', r'\1 (', text)
    text = re.sub(r'\)\{', r') {', text)
    
    # Cleanup
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r' +([;,\.\)])', r'\1', text)
    
    return text


def clean_ocr_text(text: str) -> str:
    """
    Clean and improve PDF/OCR text quality.
    PRESERVES line breaks and fixes word splitting issues.
    """
    import re
    
    if not text:
        return ""
    
    # Basic cleanup - PRESERVE line breaks!
    text = text.strip()
    
    # Remove common OCR/PDF artifacts but keep newlines
    text = text.replace('\x0c', '\n')  # Form feed → newline
    text = text.replace('\r\n', '\n')  # Windows line breaks
    text = text.replace('\r', '\n')    # Mac line breaks
    
    # ==========================================================================
    # FIX: Words with spaces inserted in middle (OCR error)
    # ==========================================================================
    # Examples: "bal an cing" → "balancing", "Bal a nce" → "Balance"
    # "AVLT rees" → "AVLTrees", "this. data" → "this.data"
    
    # Fix common word splits with single letters
    # "bal an cing" → "balancing" (a + n + cing)
    text = re.sub(r'([a-z])\s+an\s+([a-z])', r'\1an\2', text, flags=re.IGNORECASE)
    # "Bal a nce" → "Balance" (a + nce)
    text = re.sub(r'([A-Z][a-z]*)\s+a\s+([a-z]{2,})', r'\1a\2', text)
    # "bal an cing" → "balancing" (an + cing)
    text = re.sub(r'([a-z])\s+an\s+([a-z]{3,})', r'\1an\2', text, flags=re.IGNORECASE)
    
    # Fix common suffixes split incorrectly
    # "rot at ion" → "rotation"
    text = re.sub(r'([a-z]+)\s+at\s+ion\b', r'\1ation', text, flags=re.IGNORECASE)
    # "Bal a nce" → "Balance"  
    text = re.sub(r'([A-Z][a-z]*)\s+a\s+nce\b', r'\1ance', text)
    # "return ed" → "returned"
    text = re.sub(r'([a-z]+)\s+ed\b', r'\1ed', text, flags=re.IGNORECASE)
    # "bal an cing" → "balancing"
    text = re.sub(r'([a-z]+)\s+an\s+cing\b', r'\1ancing', text, flags=re.IGNORECASE)
    # "ing " patterns
    text = re.sub(r'([a-z]+)\s+ing\b', r'\1ing', text, flags=re.IGNORECASE)
    
    # Fix class names split: "AVLT rees" → "AVLTrees"
    text = re.sub(r'([A-Z]{2,})\s+([a-z]+)', r'\1\2', text)
    
    # Fix property access: "this. data" → "this.data"
    text = re.sub(r'([a-z]+)\.\s+([a-z])', r'\1.\2', text, flags=re.IGNORECASE)
    
    # Fix words split by single letter: "word a word" → "wordaword" (if it makes sense)
    # Only if the letter is 'a', 'i', 'o' (common in words)
    text = re.sub(r'([a-z]{2,})\s+a\s+([a-z]{2,})', r'\1a\2', text)  # "bal ancing" → "balancing"
    text = re.sub(r'([a-z]{2,})\s+i\s+([a-z]{2,})', r'\1i\2', text)  # "do ing" → "doing"
    text = re.sub(r'([a-z]{2,})\s+o\s+([a-z]{2,})', r'\1o\2', text)  # "go ing" → "going"
    
    # ALWAYS apply code formatting fix
    text = fix_ocr_code_formatting(text)
    
    # Clean up excessive newlines (but preserve intentional line breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text


# Tesseract - Local fallback (requires system install)
try:
    import pytesseract
except Exception:
    pytesseract = None

# PDF to Image conversion
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

"""
📖 What is OCR?
--------------
OCR = Optical Character Recognition

✔ Converts IMAGES of text into actual text
✔ Used when PDF pages are scanned (images, not text)

EasyOCR: Pure Python deep learning OCR - WORKS ON RENDER!
pdf2image: Converts PDF pages to images (requires Poppler)
pytesseract: Fallback OCR (requires Tesseract on system)
PIL (Pillow): Python Imaging Library for image processing

📌 These are OPTIONAL because not all PDFs need OCR.
   If the PDF has normal text, we don't need OCR.
"""

# ----- OpenAI for LLM Responses -----
from openai import OpenAI
"""
📖 What is OpenAI?
------------------
From openai library (pip install openai).

✔ Official OpenAI Python client
✔ Used to call GPT models for generating responses

🔗 In your notes (04-RAG/chat.py), you did EXACTLY this:
    client = OpenAI()
    chat_completion = client.chat.completions.create(...)
"""

# =============================================================================
#                     CONFIGURATION VARIABLES
# =============================================================================

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
"""
📖 Qdrant URL
-------------
✔ Where our vector database is running
✔ Default is localhost:6333 (standard Qdrant port)
✔ Can be overridden via environment variable

🔗 In your notes (04-RAG/indexing.py):
    url="http://localhost:6333"
"""

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "learning_vectors")
"""
📖 Collection Name
------------------
✔ Like a "table" in a regular database
✔ All our PDF vectors go into this collection
✔ We use "learning_vectors" (same as your notes!)

🔗 In your notes (04-RAG/indexing.py):
    collection_name="learning_vectors"
"""

QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
"""
📖 Qdrant API Key (for Qdrant Cloud)
-------------------------------------
✔ Required when using Qdrant Cloud (not needed for local Qdrant)
✔ Get from Qdrant Cloud dashboard
✔ Set in .env file: QDRANT_API_KEY=your-api-key-here
"""

# =============================================================================
#                     REDIS/VALKEY QUEUE SETUP (Async RAG)
# =============================================================================

REDIS_URL = os.getenv("REDIS_URL")  # e.g., redis://localhost:6379/0 or valkey://...
"""
📖 Redis/Valkey URL for Message Queue
--------------------------------------
Following your Notes Compare pattern for async RAG processing.

If REDIS_URL is set, we use async RAG (queue jobs, process in background).
If not set, we fall back to synchronous processing (current behavior).

🔗 Your Notes Compare pattern:
    from redis import Redis
    from rq import Queue
    queue = Queue(connection=Redis.from_url(REDIS_URL))
"""

_redis_connection = None
_pdf_queue = None

if REDIS_URL:
    try:
        _redis_connection = redis.Redis.from_url(REDIS_URL)
        _redis_connection.ping()  # Test connection
        _pdf_queue = Queue("pdf_processing", connection=_redis_connection)
        print(f"✅ Redis/Valkey queue connected: {REDIS_URL}")
    except Exception as e:
        print(f"⚠️ Redis/Valkey queue unavailable: {e}")
        print("   → Falling back to synchronous PDF processing")
        _redis_connection = None
        _pdf_queue = None
else:
    print("ℹ️ REDIS_URL not set - using synchronous PDF processing")

# 🆕 Debug: Print Qdrant configuration at startup
print("=" * 60)
print("📊 RAG Service Configuration:")
print(f"   QDRANT_URL: {QDRANT_URL}")
print(f"   QDRANT_COLLECTION: {QDRANT_COLLECTION}")
print(f"   QDRANT_API_KEY: {'✅ Set' if QDRANT_API_KEY else '❌ NOT SET'}")
print(f"   OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ NOT SET'}")
print(f"   REDIS_URL: {'✅ Set (Async RAG enabled)' if REDIS_URL and _pdf_queue else '❌ NOT SET (Sync mode)'}")
print("=" * 60)

# =============================================================================
#                     CREATE OPENAI CLIENT
# =============================================================================

client = OpenAI()
"""
📖 Creating OpenAI Client
-------------------------
✔ Automatically reads OPENAI_API_KEY from environment
✔ This client is used to call GPT models

🔗 In your notes (04-RAG/chat.py):
    client = OpenAI()
"""

# =============================================================================
#                     CREATE EMBEDDING MODEL
# =============================================================================

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
"""
📖 Creating Embedding Model
---------------------------
✔ This model converts text to vectors
✔ We use "text-embedding-3-small" (cost-effective)
✔ Alternatively, "text-embedding-3-large" is more accurate but costs more

📌 IMPORTANT: Use the SAME embedding model for indexing AND querying!
             If you index with "large" and query with "small", it won't work!

🔗 In your notes (04-RAG/indexing.py):
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
"""

# =============================================================================
#                     CREATE API ROUTER
# =============================================================================

rag_router = APIRouter(
    prefix="",  # No prefix, routes are at root level
    tags=["RAG"]  # Groups routes in API docs
)

# =============================================================================
#                     🆕 PDF CONVERSATION CHECKPOINTER
# =============================================================================
"""
📖 Why Checkpointing for PDF Q&A?
---------------------------------
When a user asks questions about a PDF, they often ask follow-up questions:

Example Conversation:
--------------------
User: "What are the key points in this PDF?"
AI:   "The PDF discusses 1) Machine Learning, 2) Neural Networks, 3) Deep Learning"
User: "Tell me more about point 2"  ← FOLLOW-UP!
AI:   Needs to remember what "point 2" refers to!

Without checkpointing, the AI wouldn't know that "point 2" = Neural Networks.

🔗 THIS IS THE SAME PATTERN AS agent_service.py:
    state = _checkpointer.load(thread_id)
    state["messages"].append(...)
    _checkpointer.save(thread_id, state)

📌 FOR YOUR INTERVIEW:
"I implemented conversation persistence for PDF Q&A so that follow-up
questions work naturally. The conversation is stored in MongoDB with
the thread_id, allowing users to ask 'tell me more about X' after
an initial question."
"""

# MongoDB connection for RAG checkpointing
MONGO_URI = os.getenv("MONGO_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
"""
📖 MongoDB URI for RAG Checkpointing
------------------------------------
Uses MONGO_URI if set, otherwise falls back to MONGODB_URI.
This allows using the same MongoDB connection string for all features.
"""

def _sanitize_mongo_uri(uri: str) -> str:
    """
    📖 Sanitize MongoDB URI
    -----------------------
    Removes any whitespace and validates the URI format.
    pymongo is strict about URI format, so we clean it up.
    
    Common issues fixed:
    - Extra quotes from environment variables
    - Leading/trailing whitespace
    - Newlines or special characters
    - Multi-line URIs (joins them together)
    """
    if not uri:
        return uri
    
    # Remove all newlines and carriage returns (handles multi-line URIs)
    uri = uri.replace('\n', '').replace('\r', '')
    
    # Remove leading/trailing whitespace
    uri = uri.strip()
    
    # Remove any quotes that might have been added by Render/environment
    while (uri.startswith('"') and uri.endswith('"')) or (uri.startswith("'") and uri.endswith("'")):
        uri = uri[1:-1].strip()
    
    # Remove any spaces (URI should have no spaces)
    uri = uri.replace(' ', '')
    
    # Ensure URI starts with mongodb:// or mongodb+srv://
    if not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
        raise ValueError(f"Invalid MongoDB URI format: must start with mongodb:// or mongodb+srv://")
    
    return uri

try:
    # Sanitize URI to ensure proper format
    sanitized_uri = _sanitize_mongo_uri(MONGO_URI)
    _rag_mongo_client = MongoClient(sanitized_uri, serverSelectionTimeoutMS=5000)
    # Test connection immediately
    _rag_mongo_client.admin.command('ping')
    _rag_db = _rag_mongo_client["sigma_gpt_db"]
    _rag_checkpoints = _rag_db["rag_checkpoints"]  # Separate collection for RAG
    print("✅ RAG Checkpointer: Connected to MongoDB")
except Exception as e:
    print(f"⚠️ RAG Checkpointer: MongoDB connection failed: {e}")
    print(f"   Raw URI from env: {MONGO_URI[:80]}..." if len(MONGO_URI) > 80 else f"   Raw URI from env: {MONGO_URI}")
    print(f"   URI length: {len(MONGO_URI)} characters (should be ~130-140)")
    if len(MONGO_URI) < 130:
        print(f"   ⚠️  URI appears incomplete - missing query parameters!")
        print(f"   Expected: ...sigma_gpt?retryWrites=true&w=majority&appName=Cluster0")
    print(f"   Check Render Dashboard → Environment → MONGO_URI or MONGODB_URI")
    _rag_checkpoints = None


def _save_rag_conversation(thread_id: str, pdf_id: str, question: str, answer: str):
    """
    📖 Save PDF Q&A to Checkpointer
    ===============================
    
    Saves the question and answer to MongoDB so follow-up questions
    have context about what was discussed.
    
    Parameters:
    -----------
    thread_id: str
        The conversation thread ID (from frontend)
    pdf_id: str
        The PDF being discussed
    question: str
        User's question about the PDF
    answer: str
        AI's answer based on PDF content
    
    MongoDB Document Structure:
    ---------------------------
    {
        "thread_id": "abc123",
        "pdf_id": "resume-xyz",
        "messages": [
            {"role": "user", "content": "What are my skills?"},
            {"role": "assistant", "content": "Python, JavaScript..."},
            {"role": "user", "content": "Tell me more about Python"},
            {"role": "assistant", "content": "You have 3 years of..."}
        ]
    }
    """
    if _rag_checkpoints is None:
        print("⚠️ RAG Checkpointer not available, skipping save")
        return
    
    try:
        # Find existing conversation or create new
        existing = _rag_checkpoints.find_one({"thread_id": thread_id})
        
        if existing:
            # Append to existing conversation
            messages = existing.get("messages", [])
            messages.append({"role": "user", "content": question})
            messages.append({"role": "assistant", "content": answer})
            
            _rag_checkpoints.update_one(
                {"thread_id": thread_id},
                {"$set": {"messages": messages, "pdf_id": pdf_id}}
            )
        else:
            # Create new conversation
            _rag_checkpoints.insert_one({
                "thread_id": thread_id,
                "pdf_id": pdf_id,
                "messages": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer}
                ]
            })
        
        print(f"💾 RAG Checkpointer: Saved Q&A for thread {thread_id}")
        
    except Exception as e:
        print(f"⚠️ RAG Checkpointer: Save failed: {e}")


def _get_rag_conversation_history(thread_id: str) -> list:
    """
    📖 Load Previous PDF Q&A from Checkpointer
    ==========================================
    
    Returns the conversation history for a thread so the LLM
    can understand follow-up questions in context.
    
    Returns:
    --------
    List of message dicts: [{"role": "user", "content": "..."}, ...]
    """
    if _rag_checkpoints is None:
        return []
    
    try:
        existing = _rag_checkpoints.find_one({"thread_id": thread_id})
        if existing:
            return existing.get("messages", [])
        return []
    except Exception as e:
        print(f"⚠️ RAG Checkpointer: Load failed: {e}")
        return []
"""
📖 Creating API Router
----------------------
✔ APIRouter creates a "sub-application" for related routes
✔ All RAG endpoints (upload, query) go here
✔ tags=["RAG"] groups them nicely in /docs

Later in main.py, we do:
    app.include_router(rag_router)
    
This adds all these routes to the main app!
"""

# =============================================================================
#                     SYSTEM PROMPT FOR PDF Q&A
# =============================================================================

SYSTEM_PROMPT = """
You are a helpful AI Assistant who answers user queries based on the available context
retrieved from a PDF file along with page_contents and page number.

📌 RULES:
1. Answer ONLY using the provided context
2. If the context doesn't contain the answer, say "I don't have enough information"
3. Always mention the page number(s) where you found the information
4. Keep the answer clear and well-structured

When explaining concepts:
1. First explain the concept clearly
2. If there's code, show it formatted properly
3. Explain each part step by step
4. Mention common mistakes to avoid
"""
"""
📖 What is a System Prompt?
---------------------------
✔ The system prompt sets the AI's behavior and personality
✔ It tells the AI HOW to respond
✔ It's like giving instructions to a new employee

🔗 In your notes (04-RAG/chat.py), you had:
    SYSTEM_PROMPT = '''
        You are a helpfull AI Assistant who answers user query based on...
    '''
"""

# =============================================================================
#                     PYDANTIC MODELS (Request/Response Schemas)
# =============================================================================

class RAGQuery(BaseModel):
    """
    📖 Request Schema for RAG Query
    -------------------------------
    Defines what data we expect when user asks a question about a PDF.
    
    ✔ question: The user's question (required)
    ✔ k: How many chunks to retrieve (optional, default 4)
    ✔ pdf_id: Which PDF to search in (optional)
    """
    question: str                   # Required: The question to answer
    k: Optional[int] = 4           # Optional: Number of chunks to retrieve
    pdf_id: Optional[str] = None   # Optional: Specific PDF to search


# =============================================================================
#                     HELPER FUNCTION: GET VECTOR STORE
# =============================================================================

def get_vector_store() -> QdrantVectorStore:
    """
    📖 Get Vector Store Connection
    ------------------------------
    Creates a connection to an EXISTING Qdrant collection.
    
    ✔ Use this when you want to QUERY (search) the database
    ✔ Don't use this for creating new collections
    
    🔗 In your notes (04-RAG/chat.py):
        vector_db = QdrantVectorStore.from_existing_collection(
            url="http://localhost:6333",
            collection_name="learning_vectors",
            embedding=embedding_model
        )
    """
    # Build connection kwargs
    connection_kwargs = {
        "url": QDRANT_URL,
        "collection_name": QDRANT_COLLECTION,
        "embedding": embedding_model  # Must match the model used for indexing!
    }
    
    # Add API key if provided (for Qdrant Cloud)
    if QDRANT_API_KEY:
        connection_kwargs["api_key"] = QDRANT_API_KEY
    
    return QdrantVectorStore.from_existing_collection(**connection_kwargs)


# =============================================================================
#                     ENDPOINT: RAG QUERY
# =============================================================================

@rag_router.post("/rag/query")
def rag_query(payload: RAGQuery):
    """
    📖 RAG Query Endpoint
    ---------------------
    Answers questions based on indexed PDF content.
    
    HTTP POST to: http://localhost:8000/rag/query
    Body: { "question": "What is Node.js?", "k": 4 }
    
    THE RAG PIPELINE:
    1. Take user's question
    2. Search Qdrant for similar chunks (similarity_search)
    3. Build context from retrieved chunks
    4. Send (question + context) to GPT
    5. Return GPT's answer
    
    🔗 THIS IS EXACTLY YOUR NOTES (04-RAG/chat.py)!
    """
    try:
        # Step 1: Connect to vector database
        vector_db = get_vector_store()
        
        # Step 2: Similarity Search
        # --------------------------
        # This finds the chunks most similar to the user's question
        # k = how many chunks to retrieve (default 4)
        #
        # 🔗 In your notes (04-RAG/chat.py):
        #     search_results = vector_db.similarity_search(query=query)
        
        search_results = vector_db.similarity_search(
            query=payload.question,
            k=payload.k or 4
        )
        
        # Step 3: Build Context String
        # ----------------------------
        # Convert the search results into a readable context for the LLM
        # Each result has: page_content, metadata (page number, source file)
        #
        # 🔗 In your notes (04-RAG/chat.py):
        #     context = "\n\n\n".join([
        #         f"Page Content: {result.page_content}\nPage Number: {result.metadata['page_label']}..."
        #         for result in search_results
        #     ])
        
        context = "\n\n".join([
            f"Page Content: {result.page_content}\n"
            f"Page Number: {result.metadata.get('page', result.metadata.get('page_label', 'N/A'))}\n"
            f"Source: {result.metadata.get('source', result.metadata.get('filename', 'Unknown'))}"
            for result in search_results
        ])
        
        # Step 4: Create Full System Prompt with Context
        system_prompt_with_context = f"""
            {SYSTEM_PROMPT}
            
            CONTEXT FROM PDF:
            {context}
        """
        
        # Step 5: Call OpenAI GPT to Generate Answer
        # ------------------------------------------
        # We send the system prompt (with context) and user's question
        # GPT generates an answer based ONLY on the provided context
        #
        # 🔗 In your notes (04-RAG/chat.py):
        #     chat_completion = client.chat.completions.create(
        #         model="gpt-4.1",
        #         messages=[
        #             { "role": "system", "content": SYSTEM_PROMPT },
        #             { "role": "user", "content": query },
        #         ]
        #     )
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # Using gpt-4o-mini for cost efficiency
            messages=[
                {"role": "system", "content": system_prompt_with_context},
                {"role": "user", "content": payload.question}
            ]
        )
        
        # Step 6: Extract and Return Answer
        answer = completion.choices[0].message.content
        
        return {
            "answer": answer,
            "context_used": context  # Also return context so user can verify
        }
        
    except Exception as err:
        # Return HTTP 500 error if something goes wrong
        raise HTTPException(status_code=500, detail=f"RAG query failed: {err}")


# =============================================================================
#                     ENDPOINT: PDF STATUS (Diagnostic)
# =============================================================================

@rag_router.get("/pdf/job/{job_id}")
async def get_pdf_job_status(job_id: str):
    """
    📖 PDF Job Status Endpoint (Async RAG)
    --------------------------------------
    Check the status of a PDF processing job.
    
    HTTP GET to: http://localhost:8000/pdf/job/{job_id}
    
    Returns:
    - "queued": Job is waiting in queue
    - "processing": Job is being processed
    - "completed": Job finished successfully (includes pdf_id, chunks, etc.)
    - "failed": Job failed (includes error message)
    
    🔗 Used with async RAG when REDIS_URL is set
    """
    if not _redis_connection:
        raise HTTPException(
            status_code=400,
            detail="Async RAG not enabled. Set REDIS_URL to use job status tracking."
        )
    
    try:
        # Get job status from Redis
        status_data = _redis_connection.get(f"pdf_job:{job_id}:status")
        
        if not status_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found. It may have expired (TTL: 1 hour) or never existed."
            )
        
        status = json.loads(status_data)
        return status
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid job status data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@rag_router.get("/pdf/status")
async def pdf_status():
    """
    📖 PDF Service Status Endpoint
    ------------------------------
    Returns the status of the PDF/RAG service including:
    - Qdrant connection status
    - Collection info
    - Environment configuration
    - Redis/Valkey queue status
    
    HTTP GET to: http://localhost:8000/pdf/status
    """
    status = {
        "service": "RAG/PDF Service",
        "qdrant_url": QDRANT_URL,
        "qdrant_collection": QDRANT_COLLECTION,
        "qdrant_api_key_set": bool(QDRANT_API_KEY),
        "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "ocr_available": convert_from_bytes is not None and pytesseract is not None,
        "async_rag_enabled": bool(_pdf_queue and _redis_connection),
        "redis_url_set": bool(REDIS_URL),
        "redis_connected": False,
        "qdrant_connected": False,
        "collection_exists": False,
        "collection_points": 0,
        "error": None
    }
    
    # Test Redis connection
    if REDIS_URL:
        try:
            test_redis = redis.Redis.from_url(REDIS_URL)
            test_redis.ping()
            status["redis_connected"] = True
        except Exception as e:
            status["redis_error"] = str(e)
    
    try:
        # Test Qdrant connection
        qdrant_client_kwargs = {"url": QDRANT_URL}
        if QDRANT_API_KEY:
            qdrant_client_kwargs["api_key"] = QDRANT_API_KEY
        
        qdrant_client = QdrantClient(**qdrant_client_kwargs)
        collections = qdrant_client.get_collections()
        status["qdrant_connected"] = True
        
        # Check if our collection exists
        collection_names = [c.name for c in collections.collections]
        status["all_collections"] = collection_names
        
        if QDRANT_COLLECTION in collection_names:
            status["collection_exists"] = True
            # Get collection info
            collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
            status["collection_points"] = collection_info.points_count
            status["collection_status"] = collection_info.status.value if collection_info.status else "unknown"
        
    except Exception as e:
        status["error"] = str(e)
    
    return status


# =============================================================================
#                     BACKGROUND WORKER: PDF PROCESSING
# =============================================================================

def process_pdf_background(pdf_bytes: bytes, filename: str, job_id: str):
    """
    📖 Background Worker Function for Async PDF Processing
    -------------------------------------------------------
    This function runs in a background worker (RQ) to process PDFs asynchronously.
    
    Following your Notes Compare pattern:
        - Extract text + OCR
        - Chunk text
        - Create embeddings
        - Store in Qdrant
        - Update job status in Redis
    
    Args:
        pdf_bytes: PDF file content as bytes
        filename: Original filename
        job_id: Unique job identifier for status tracking
    """
    try:
        # Update status: processing
        if _redis_connection:
            _redis_connection.setex(
                f"pdf_job:{job_id}:status",
                3600,  # 1 hour TTL
                json.dumps({"status": "processing", "progress": "Extracting text..."})
            )
        
        # This is the EXACT same logic from the synchronous upload_pdf function
        # We extract it here so it can run in background
        
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        full_text_parts = []
        
        # Check OCR availability
        ocr_space_available = is_ocr_space_available()
        tesseract_available = pytesseract is not None
        can_convert_to_image = convert_from_bytes is not None
        ocr_available = (ocr_space_available or tesseract_available) and can_convert_to_image
        
        print(f"📄 [Job {job_id}] Processing {len(reader.pages)} pages...")
        
        # Process each page (same logic as before)
        for idx, page in enumerate(reader.pages):
            pdf_text = (page.extract_text() or "").strip()
            ocr_text = ""
            
            if ocr_available:
                try:
                    images = convert_from_bytes(
                        pdf_bytes,
                        first_page=idx + 1,
                        last_page=idx + 1,
                        dpi=500
                    )
                    if images:
                        from PIL import ImageEnhance, ImageFilter
                        processed_image = ImageEnhance.Contrast(images[0]).enhance(1.5)
                        processed_image = processed_image.filter(ImageFilter.SHARPEN)
                        
                        img_buffer = BytesIO()
                        processed_image.save(img_buffer, format='PNG')
                        img_bytes = img_buffer.getvalue()
                        
                        if ocr_space_available:
                            ocr_text = ocr_space_for_pdf(img_bytes)
                        if not ocr_text.strip() and tesseract_available:
                            ocr_text = pytesseract.image_to_string(processed_image) or ""
                except Exception as e:
                    print(f"⚠️ [Job {job_id}] Page {idx + 1}: OCR failed - {e}")
                    ocr_text = ""
            
            # Clean text
            if pdf_text.strip():
                pdf_text = clean_ocr_text(pdf_text)
            if ocr_text.strip():
                ocr_text = clean_ocr_text(ocr_text)
            
            # Combine text (same logic as before)
            combined_text = ""
            def looks_like_code(text: str) -> bool:
                code_indicators = [
                    'public ', 'private ', 'class ', 'static ', 'void ', 'int ',
                    'def ', 'function ', 'return ', 'import ', 'from ',
                    '{', '}', '()', ';', '==', '!=', '&&', '||',
                    'this.', 'self.', 'Node ', 'String ', 'boolean '
                ]
                return sum(1 for ind in code_indicators if ind in text) >= 3
            
            def format_as_code(text: str) -> str:
                if 'public class' in text or 'static void' in text:
                    lang = 'java'
                elif 'def ' in text and ':' in text:
                    lang = 'python'
                elif 'function ' in text or 'const ' in text:
                    lang = 'javascript'
                else:
                    lang = ''
                return f"\n```{lang}\n{text}\n```\n"
            
            if pdf_text and ocr_text:
                combined_text = f"**📄 Text Content:**\n{pdf_text}"
                ocr_lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
                pdf_lower = pdf_text.lower()
                unique_ocr_lines = [
                    line for line in ocr_lines
                    if (len(line) > 5 and any(c.isalpha() for c in line) and
                        not any(line.lower() in pdf_lower or pdf_lower in line.lower()[:50] for _ in [1]))
                ]
                if unique_ocr_lines:
                    ocr_content = "\n".join(unique_ocr_lines)
                    if looks_like_code(ocr_content):
                        combined_text += "\n\n**📝 Code from Image:**" + format_as_code(ocr_content)
                    else:
                        combined_text += "\n\n**📷 Additional content from images:**\n" + ocr_content
            elif pdf_text:
                combined_text = pdf_text
            elif ocr_text:
                if looks_like_code(ocr_text):
                    combined_text = "**📝 Code extracted from scanned page:**" + format_as_code(ocr_text)
                else:
                    combined_text = ocr_text
            else:
                combined_text = ""
            
            pages.append({"page": idx + 1, "text": combined_text})
            full_text_parts.append(f"[Page {idx + 1}]\n{combined_text}")
        
        full_text = "\n\n".join(full_text_parts)
        
        if not any((p["text"] or "").strip() for p in pages):
            if not ocr_available:
                raise Exception("Scanned PDF but OCR unavailable")
            else:
                raise Exception("No text extracted from PDF")
        
        # Update status: chunking
        if _redis_connection:
            _redis_connection.setex(
                f"pdf_job:{job_id}:status",
                3600,
                json.dumps({"status": "processing", "progress": "Chunking text..."})
            )
        
        # Chunk text
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=200
        )
        
        pdf_id = str(uuid4())
        docs = []
        for p in pages:
            chunks = splitter.split_text(p["text"])
            for chunk in chunks:
                docs.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "pdf_id": pdf_id,
                            "filename": filename,
                            "page": p["page"]
                        }
                    )
                )
        
        # Update status: embedding
        if _redis_connection:
            _redis_connection.setex(
                f"pdf_job:{job_id}:status",
                3600,
                json.dumps({"status": "processing", "progress": f"Creating embeddings for {len(docs)} chunks..."})
            )
        
        # Store in Qdrant
        if docs:
            qdrant_client_kwargs = {"url": QDRANT_URL}
            if QDRANT_API_KEY:
                qdrant_client_kwargs["api_key"] = QDRANT_API_KEY
            
            qdrant_client = QdrantClient(**qdrant_client_kwargs)
            
            # Ensure collection exists with indexes
            try:
                collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
                for index_path in ["metadata.pdf_id", "pdf_id"]:
                    try:
                        qdrant_client.create_payload_index(
                            collection_name=QDRANT_COLLECTION,
                            field_name=index_path,
                            field_schema=PayloadSchemaType.KEYWORD
                        )
                    except Exception:
                        pass
            except Exception:
                pass
            
            doc_connection_kwargs = {
                "documents": docs,
                "embedding": embedding_model,
                "url": QDRANT_URL,
                "collection_name": QDRANT_COLLECTION
            }
            if QDRANT_API_KEY:
                doc_connection_kwargs["api_key"] = QDRANT_API_KEY
            
            QdrantVectorStore.from_documents(**doc_connection_kwargs)
            print(f"✅ [Job {job_id}] Stored {len(docs)} chunks in Qdrant")
        
        # Update status: completed
        result = {
            "status": "completed",
            "pdf_id": pdf_id,
            "filename": filename,
            "total_pages": len(pages),
            "total_chunks": len(docs),
            "pages": pages,
            "full_text": full_text
        }
        
        if _redis_connection:
            _redis_connection.setex(
                f"pdf_job:{job_id}:status",
                3600,
                json.dumps(result)
            )
            _redis_connection.setex(
                f"pdf_job:{job_id}:result",
                3600,
                json.dumps(result)
            )
        
        return result
        
    except Exception as e:
        error_result = {
            "status": "failed",
            "error": str(e)
        }
        if _redis_connection:
            _redis_connection.setex(
                f"pdf_job:{job_id}:status",
                3600,
                json.dumps(error_result)
            )
        print(f"❌ [Job {job_id}] PDF processing failed: {e}")
        raise


# =============================================================================
#                     ENDPOINT: PDF UPLOAD
# =============================================================================

@rag_router.post("/pdf/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    📖 PDF Upload Endpoint (Async RAG with Valkey/Redis Queue)
    -----------------------------------------------------------
    Uploads and indexes a PDF for RAG queries.
    
    🔄 ASYNC MODE (if REDIS_URL is set):
        - Queues job in Redis/Valkey message queue
        - Returns job_id immediately
        - User polls /pdf/job/{job_id} for status
        - Background worker processes: OCR → chunk → embed → store
    
    🔄 SYNC MODE (if REDIS_URL not set):
        - Processes PDF synchronously (original behavior)
        - Returns result immediately (may take 2-5 minutes)
    
    HTTP POST to: http://localhost:8000/pdf/upload
    Body: multipart/form-data with file
    
    🔗 Following your Notes Compare async RAG pattern!
    """
    
    # Validate file type
    if file.content_type and "pdf" not in file.content_type.lower():
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Read PDF content
    content = await file.read()
    
    # =============================================================================
    # ASYNC MODE: Queue job in Redis/Valkey
    # =============================================================================
    if _pdf_queue and _redis_connection:
        try:
            job_id = str(uuid4())
            
            # Queue the job
            job = _pdf_queue.enqueue(
                process_pdf_background,
                pdf_bytes=content,
                filename=file.filename or "uploaded.pdf",
                job_id=job_id,
                job_timeout="10m"  # 10 minute timeout for large PDFs
            )
            
            # Set initial status
            _redis_connection.setex(
                f"pdf_job:{job_id}:status",
                3600,
                json.dumps({
                    "status": "queued",
                    "progress": "Job queued, waiting for worker...",
                    "job_id": job_id
                })
            )
            
            print(f"✅ PDF upload queued: job_id={job_id}, filename={file.filename}")
            
            return {
                "status": "queued",
                "job_id": job_id,
                "message": "PDF upload queued for processing. Use /pdf/job/{job_id} to check status.",
                "check_status_url": f"/pdf/job/{job_id}"
            }
        except Exception as e:
            print(f"⚠️ Failed to queue PDF job: {e}")
            print("   → Falling back to synchronous processing")
            # Fall through to synchronous processing
    
    # =============================================================================
    # SYNC MODE: Process immediately (original behavior)
    # =============================================================================
    try:
        
        # Create a BytesIO object (acts like a file in memory)
        # PdfReader needs a file-like object
        reader = PdfReader(BytesIO(content))
        
        # Step 2: Extract Text Page by Page
        # ----------------------------------
        # We process each page separately to:
        # - Track page numbers (for citations)
        # - Use OCR on pages with no text (scanned documents)
        #
        # 🔗 In your notes (04-RAG/indexing.py):
        #     loader = PyPDFLoader(file_path=pdf_path)
        #     docs = loader.load()  # Reads PDF page by page
        
        pages = []
        full_text_parts = []
        
        # Check which OCR engines are available
        ocr_space_available = is_ocr_space_available()
        tesseract_available = pytesseract is not None
        can_convert_to_image = convert_from_bytes is not None
        ocr_available = (ocr_space_available or tesseract_available) and can_convert_to_image
        
        print(f"📄 Processing {len(reader.pages)} pages...")
        print(f"   OCR available: {ocr_available} (OCR.space: {ocr_space_available}, Tesseract: {tesseract_available})")
        
        for idx, page in enumerate(reader.pages):
            # ═══════════════════════════════════════════════════════════════
            # STEP 1: Extract regular text using pypdf
            # ═══════════════════════════════════════════════════════════════
            pdf_text = (page.extract_text() or "").strip()
            print(f"📄 Page {idx + 1}: Extracted {len(pdf_text)} chars from PDF text layer")
            
            # ═══════════════════════════════════════════════════════════════
            # STEP 2: ALWAYS try OCR to capture text from images
            # ═══════════════════════════════════════════════════════════════
            # This captures text in diagrams, screenshots, figures, etc.
            ocr_text = ""
            
            if ocr_available:
                try:
                    print(f"🔍 Page {idx + 1}: Running OCR to capture image text...")
                    
                    # Convert PDF page to image at HIGH DPI for better OCR
                    images = convert_from_bytes(
                        content,
                        first_page=idx + 1,
                        last_page=idx + 1,
                        dpi=500  # High DPI for maximum OCR accuracy (67% increase from 300)
                    )
                    
                    if images:
                        # Preprocess image for better OCR results
                        from PIL import Image, ImageEnhance, ImageFilter
                        img = images[0]
                        
                        # Convert to RGB if needed
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Enhance contrast for better text recognition
                        enhancer = ImageEnhance.Contrast(img)
                        img = enhancer.enhance(1.5)  # Increase contrast
                        
                        # Sharpen image slightly
                        img = img.filter(ImageFilter.SHARPEN)
                        
                        # Convert PIL image to bytes for OCR.space
                        img_buffer = BytesIO()
                        img.save(img_buffer, format='PNG', optimize=False, quality=95)
                        img_bytes = img_buffer.getvalue()
                        
                        # Try OCR.space API first (fast!)
                        if ocr_space_available:
                            ocr_text = ocr_space_for_pdf(img_bytes)
                            if ocr_text.strip():
                                print(f"✅ Page {idx + 1}: OCR.space extracted {len(ocr_text)} chars")
                        
                        # Fallback to Tesseract
                        if not ocr_text.strip() and tesseract_available:
                            ocr_text = pytesseract.image_to_string(images[0]) or ""
                            if ocr_text.strip():
                                print(f"✅ Page {idx + 1}: Tesseract extracted {len(ocr_text)} chars")
                                
                except Exception as e:
                    print(f"⚠️ Page {idx + 1}: OCR failed - {e}")
                    ocr_text = ""
            
            # ═══════════════════════════════════════════════════════════════
            # STEP 2.5: Clean BOTH PDF text AND OCR text
            # ═══════════════════════════════════════════════════════════════
            # PDF text can also have concatenation issues (publicstaticNode)
            if pdf_text.strip():
                pdf_text = clean_ocr_text(pdf_text)
                print(f"🧹 Page {idx + 1}: Cleaned PDF text")
            
            if ocr_text.strip():
                ocr_text = clean_ocr_text(ocr_text)
                print(f"🧹 Page {idx + 1}: Cleaned OCR text")
            
            # ═══════════════════════════════════════════════════════════════
            # STEP 3: Combine PDF text + OCR text (capture everything!)
            # IMPROVED: Better handling for pages with text + code images
            # ═══════════════════════════════════════════════════════════════
            combined_text = ""
            
            # Helper: Check if text looks like code
            def looks_like_code(text: str) -> bool:
                code_indicators = [
                    'public ', 'private ', 'class ', 'static ', 'void ', 'int ',
                    'def ', 'function ', 'return ', 'import ', 'from ',
                    '{', '}', '()', ';', '==', '!=', '&&', '||',
                    'this.', 'self.', 'Node ', 'String ', 'boolean '
                ]
                indicator_count = sum(1 for ind in code_indicators if ind in text)
                return indicator_count >= 3
            
            # Helper: Format code block properly
            def format_as_code(text: str) -> str:
                # Detect language
                if 'public class' in text or 'static void' in text:
                    lang = 'java'
                elif 'def ' in text and ':' in text:
                    lang = 'python'
                elif 'function ' in text or 'const ' in text:
                    lang = 'javascript'
                else:
                    lang = ''
                return f"\n```{lang}\n{text}\n```\n"
            
            if pdf_text and ocr_text:
                # Both have text - ALWAYS include PDF text first, then add OCR content
                # PRESERVE line breaks from PDF text!
                combined_text = f"**📄 Text Content:**\n{pdf_text}"
                
                # Check if OCR is significantly longer (means it captured image content too)
                # Or if OCR has code-like content not in PDF text
                # PRESERVE line structure from OCR too!
                ocr_lines = ocr_text.split('\n')  # Keep empty lines for structure
                pdf_lower = pdf_text.lower()
                unique_ocr_lines = []
                
                for line in ocr_lines:
                    line_clean = line.strip()
                    # Skip empty lines for duplicate check, but preserve structure
                    if not line_clean:
                        continue
                    
                    # Only add lines that are:
                    # 1. Not already in PDF text (fuzzy match)
                    # 2. Long enough to be meaningful
                    # 3. Has some letters (not just symbols)
                    is_duplicate = any(
                        line_clean.lower() in pdf_lower or 
                        pdf_lower in line_clean.lower()[:50] 
                        for _ in [1]
                    )
                    if (not is_duplicate 
                        and len(line_clean) > 5 
                        and any(c.isalpha() for c in line_clean)):
                        unique_ocr_lines.append(line_clean)  # Keep original line, not stripped
                
                if unique_ocr_lines:
                    # Join with newlines to preserve line structure
                    ocr_content = "\n".join(unique_ocr_lines)
                    
                    # Check if OCR content is code
                    if looks_like_code(ocr_content):
                        combined_text += "\n\n**📝 Code from Image:**"
                        combined_text += format_as_code(ocr_content)
                        print(f"📝 Page {idx + 1}: PDF text ({len(pdf_text)} chars) + CODE from image ({len(unique_ocr_lines)} lines)")
                    else:
                        combined_text += "\n\n**📷 Content from Images:**\n"
                        combined_text += ocr_content
                        print(f"📝 Page {idx + 1}: PDF text ({len(pdf_text)} chars) + {len(unique_ocr_lines)} lines from OCR")
                else:
                    print(f"📝 Page {idx + 1}: Using PDF text only ({len(pdf_text)} chars)")
                    
            elif pdf_text:
                combined_text = pdf_text
                print(f"📝 Page {idx + 1}: Using PDF text only")
            elif ocr_text:
                # Only OCR text - might be scanned page with code
                if looks_like_code(ocr_text):
                    combined_text = "**📝 Code extracted from scanned page:**"
                    combined_text += format_as_code(ocr_text)
                    print(f"📝 Page {idx + 1}: Using OCR text as CODE (scanned page)")
                else:
                    combined_text = ocr_text
                    print(f"📝 Page {idx + 1}: Using OCR text only (scanned page)")
            else:
                combined_text = ""
                print(f"⚠️ Page {idx + 1}: No text extracted")
            
            pages.append({"page": idx + 1, "text": combined_text})
            full_text_parts.append(f"[Page {idx + 1}]\n{combined_text}")
        
        full_text = "\n\n".join(full_text_parts)
        
        # Check if we got any text
        if not any((p["text"] or "").strip() for p in pages):
            # Check if this is likely a scanned PDF
            if not ocr_available:
                raise HTTPException(
                    status_code=422,
                    detail="This appears to be a scanned PDF (image-based). OCR is not available on this server. Please upload a text-based PDF instead, or copy-paste the text content."
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail="No text could be extracted from the PDF. The file may be corrupted or contain only images."
                )
        
        # Step 3: Split into Chunks
        # -------------------------
        # Use RecursiveCharacterTextSplitter to split text into smaller chunks
        # - chunk_size: Maximum size of each chunk
        # - chunk_overlap: Overlap between chunks (maintains context)
        #
        # 🔗 In your notes (04-RAG/indexing.py):
        #     text_splitter = RecursiveCharacterTextSplitter(
        #         chunk_size=1000,
        #         chunk_overlap=400
        #     )
        #     split_docs = text_splitter.split_documents(documents=docs)
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,      # Smaller chunks for more precise matching
            chunk_overlap=200    # Overlap to maintain context between chunks
        )
        
        # Generate unique ID for this PDF
        pdf_id = str(uuid4())
        
        # Create Document objects for each chunk
        docs = []
        for p in pages:
            # Split each page's text into chunks
            chunks = splitter.split_text(p["text"])
            
            for chunk in chunks:
                docs.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "pdf_id": pdf_id,           # Link to this specific PDF
                            "filename": file.filename, # Original filename
                            "page": p["page"]          # Page number for citation
                        }
                    )
                )
        
        # Step 4: Create Embeddings and Store in Qdrant
        # ----------------------------------------------
        # This does two things:
        # 1. Converts each chunk to a vector using embedding_model
        # 2. Stores the vectors in Qdrant
        #
        # 🔗 In your notes (04-RAG/indexing.py):
        #     vector_store = QdrantVectorStore.from_documents(
        #         documents=split_docs,
        #         url="http://localhost:6333",
        #         collection_name="learning_vectors",
        #         embedding=embedding_model
        #     )
        
        print(f"📤 Uploading {len(docs)} chunks with pdf_id: {pdf_id}")
        print(f"   → Target: {QDRANT_URL} / collection: {QDRANT_COLLECTION}")
        print(f"   → API Key: {'✅ Set' if QDRANT_API_KEY else '❌ NOT SET (using localhost?)'}")
        
        if docs:
            # 🆕 Ensure collection exists with proper payload schema for filtering
            # This creates the index on metadata.pdf_id if it doesn't exist
            qdrant_client_kwargs = {"url": QDRANT_URL}
            if QDRANT_API_KEY:
                qdrant_client_kwargs["api_key"] = QDRANT_API_KEY
            
            try:
                print(f"🔌 Connecting to Qdrant at {QDRANT_URL}...")
                qdrant_client = QdrantClient(**qdrant_client_kwargs)
                print(f"✅ Connected to Qdrant")
            except Exception as conn_err:
                print(f"❌ Failed to connect to Qdrant: {conn_err}")
                raise HTTPException(status_code=500, detail=f"Failed to connect to Qdrant: {conn_err}")
            
            # Check if collection exists, create with payload schema if needed
            try:
                collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
                print(f"✅ Collection '{QDRANT_COLLECTION}' exists")
                # Collection exists, check if payload schema has pdf_id index
                payload_schema = collection_info.config.params.payload_schema
                # Try to create index for both possible paths
                for index_path in ["metadata.pdf_id", "pdf_id"]:
                    try:
                        qdrant_client.create_payload_index(
                            collection_name=QDRANT_COLLECTION,
                            field_name=index_path,
                            field_schema=PayloadSchemaType.KEYWORD
                        )
                        print(f"✅ Added index for {index_path}")
                    except Exception as idx_err:
                        if "already exists" not in str(idx_err).lower():
                            print(f"ℹ️ Index {index_path}: {idx_err}")
            except Exception as e:
                # Collection doesn't exist or error accessing it
                # LangChain will create it with from_documents
                print(f"ℹ️ Collection '{QDRANT_COLLECTION}' doesn't exist yet, will be created")
            
            # Build connection kwargs for from_documents
            doc_connection_kwargs = {
                "documents": docs,
                "embedding": embedding_model,
                "url": QDRANT_URL,
                "collection_name": QDRANT_COLLECTION
            }
            
            # Add API key if provided (for Qdrant Cloud)
            if QDRANT_API_KEY:
                doc_connection_kwargs["api_key"] = QDRANT_API_KEY
            
            print(f"📦 Creating embeddings and storing {len(docs)} chunks...")
            try:
                QdrantVectorStore.from_documents(**doc_connection_kwargs)
                print(f"✅ Successfully stored {len(docs)} chunks in Qdrant")
            except Exception as embed_err:
                print(f"❌ Failed to store chunks in Qdrant: {embed_err}")
                raise HTTPException(status_code=500, detail=f"Failed to store in Qdrant: {embed_err}")
        
        # Step 5: Return Success Response
        return {
            "status": "ingested",
            "pdf_id": pdf_id,              # Use this ID for queries
            "filename": file.filename,
            "total_pages": len(pages),
            "total_chunks": len(docs),
            "pages": pages,                # Page-wise text breakdown
            "full_text": full_text         # Complete text
        }
        
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {err}")


# =============================================================================
#                     ENDPOINT: PDF QUERY (Specific PDF)
# =============================================================================

@rag_router.post("/pdf/query")
async def query_pdf(payload: dict):
    """
    📖 PDF Query Endpoint (with Conversation Memory!)
    ==================================================
    
    Query a SPECIFIC PDF by its pdf_id.
    
    HTTP POST to: http://localhost:8000/pdf/query
    Body: { 
        "pdf_id": "abc-123", 
        "question": "What is this about?",
        "thread_id": "optional-thread-id"  ← 🆕 For conversation memory!
    }
    
    📌 DIFFERENCE FROM /rag/query:
    - /rag/query: Searches ALL indexed PDFs
    - /pdf/query: Searches ONLY the specified PDF
    
    🆕 NEW FEATURE: Conversation Memory!
    ------------------------------------
    If thread_id is provided, we:
    1. Load previous Q&A for this thread
    2. Include it in the prompt so LLM has context
    3. Save the new Q&A for future follow-ups
    
    Example:
    --------
    User: "What skills are in this resume?"
    AI:   "The resume shows Python, JavaScript, React..."
    User: "Tell me more about React"  ← Follow-up works!
    AI:   "The candidate used React for 2 years..."
    
    Uses Qdrant filters to limit search to one PDF.
    """
    pdf_id = payload.get("pdf_id")
    question = payload.get("question")
    thread_id = payload.get("thread_id", "default")  # 🆕 Get thread ID
    
    print(f"📝 PDF Query received - pdf_id: {pdf_id}, question: {question}, thread: {thread_id}")
    
    if not pdf_id or not question:
        raise HTTPException(status_code=400, detail="Missing pdf_id or question")
    
    # 🆕 Handle "extract text" type requests specially
    question_lower = question.lower().strip()
    extract_patterns = ["extract", "show text", "full text", "all text", "get text", "read text", "what does it say", "what's in it", "what is in it", "contents", "content of"]
    is_extract_request = any(pattern in question_lower for pattern in extract_patterns)
    
    try:
        # 🆕 Ensure collection has pdf_id index before querying
        qdrant_client_kwargs = {"url": QDRANT_URL}
        if QDRANT_API_KEY:
            qdrant_client_kwargs["api_key"] = QDRANT_API_KEY
        
        qdrant_client = QdrantClient(**qdrant_client_kwargs)
        
        # 🆕 Check if collection exists first (FIXED: use proper None comparison)
        try:
            collections = qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections] if collections is not None else []
            if QDRANT_COLLECTION not in collection_names:
                print(f"⚠️ Collection '{QDRANT_COLLECTION}' does not exist. Please upload a PDF first.")
                return {"answer": "No PDFs have been uploaded yet. Please upload a PDF first before querying."}
        except Exception as col_err:
            print(f"⚠️ Error checking collections: {col_err}")
        
        # Try to create index if it doesn't exist (idempotent)
        # Try both possible paths: "metadata.pdf_id" and "pdf_id"
        index_paths = ["metadata.pdf_id", "pdf_id"]
        for index_path in index_paths:
            try:
                qdrant_client.create_payload_index(
                    collection_name=QDRANT_COLLECTION,
                    field_name=index_path,
                    field_schema=PayloadSchemaType.KEYWORD
                )
                print(f"✅ Created index for {index_path}")
            except Exception as idx_err:
                # Index might already exist, that's fine
                err_str = str(idx_err).lower()
                if "already exists" in err_str or "duplicate" in err_str:
                    print(f"ℹ️ Index {index_path} already exists")
                else:
                    print(f"ℹ️ Index check for {index_path}: {idx_err}")
        
        # Connect to existing collection (with API key for Qdrant Cloud)
        connection_kwargs = {
            "url": QDRANT_URL,
            "collection_name": QDRANT_COLLECTION,
            "embedding": embedding_model
        }
        if QDRANT_API_KEY:
            connection_kwargs["api_key"] = QDRANT_API_KEY
        vector_db = QdrantVectorStore.from_existing_collection(**connection_kwargs)
        
        # Create filter to search ONLY in this PDF
        # -----------------------------------------
        # This ensures we only get chunks from the specified PDF
        # Uses Qdrant's filtering capability
        # Try metadata.pdf_id first (LangChain's standard), fallback to pdf_id
        
        filter_key = "metadata.pdf_id"  # Default to LangChain's standard path
        qdrant_filter = None
        
        try:
            # Try with metadata.pdf_id first (most common in LangChain)
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.pdf_id",
                        match=MatchValue(value=pdf_id)
                    )
                ]
            )
            # Test if this filter works by doing a quick search
            test_results = vector_db.similarity_search(
                query=question,
                k=1,
                filter=qdrant_filter
            )
            filter_key = "metadata.pdf_id"
        except Exception as filter_err:
            # If metadata.pdf_id fails, try pdf_id directly
            if "index" in str(filter_err).lower() or "not found" in str(filter_err).lower():
                print(f"ℹ️ metadata.pdf_id filter failed, trying pdf_id: {filter_err}")
                try:
                    qdrant_filter = Filter(
                        must=[
                            FieldCondition(
                                key="pdf_id",
                                match=MatchValue(value=pdf_id)
                            )
                        ]
                    )
                    filter_key = "pdf_id"
                except Exception as fallback_err:
                    # If both fail, try without filter (search all PDFs)
                    print(f"⚠️ Both filter paths failed, searching without filter: {fallback_err}")
                    qdrant_filter = None
                    filter_key = "none (no filter)"
            else:
                raise
        
        print(f"🔍 Searching with filter for pdf_id: {pdf_id} (using key: {filter_key})")
        
        # Search with filter (or without if filter creation failed)
        if qdrant_filter:
            results = vector_db.similarity_search(
                query=question,
                k=8,  # Get more chunks for detailed answers
                filter=qdrant_filter
            )
        else:
            # Fallback: search without filter, then filter results manually
            all_results = vector_db.similarity_search(
                query=question,
                k=20  # Get more results to filter manually
            )
            # Filter by pdf_id in metadata
            results = [
                r for r in all_results 
                if r.metadata.get("pdf_id") == pdf_id
            ][:8]  # Limit to 8 results
        
        print(f"📊 Found {len(results)} results")
        
        if not results:
            return {"answer": "I couldn't find any content for that PDF. The PDF might be empty or failed to upload. Please try re-uploading."}
        
        # Sort by page number for logical flow
        sorted_results = sorted(results, key=lambda r: r.metadata.get("page", 0))
        
        # 🆕 If user wants to extract/see the text, return it directly
        if is_extract_request:
            print("📄 Extract request detected - returning full text")
            text_by_page = {}
            for r in sorted_results:
                pg = r.metadata.get("page", 0)
                if pg not in text_by_page:
                    text_by_page[pg] = []
                text_by_page[pg].append(r.page_content)
            
            # Build formatted output
            output_parts = ["**📄 Extracted Text from PDF:**\n"]
            for page_num in sorted(text_by_page.keys()):
                page_text = "\n".join(text_by_page[page_num])
                output_parts.append(f"**Page {page_num}:**\n{page_text}\n")
            
            full_text = "\n".join(output_parts)
            # Limit to 4000 chars to avoid token limits
            if len(full_text) > 4000:
                full_text = full_text[:4000] + "\n\n... (text truncated, ask about specific sections)"
            
            return {"answer": full_text}
        
        # Build context
        context_chunks = []
        for r in sorted_results:
            pg = r.metadata.get("page")
            fname = r.metadata.get("filename")
            context_chunks.append(f"Page {pg} ({fname}): {r.page_content}")
        
        context = "\n\n".join(context_chunks)
        
        # ================================================================
        # 🆕 Load Conversation History for Follow-up Questions
        # ================================================================
        """
        📖 Why Load History?
        --------------------
        If user asked "What skills are in this resume?" and got an answer,
        then asks "Tell me more about Python", we need the history so the
        LLM knows what "Python" refers to from the previous answer.
        
        🔗 This is the same pattern as agent_service.py checkpointing!
        """
        conversation_history = _get_rag_conversation_history(thread_id)
        
        # Build history string for prompt
        history_text = ""
        if conversation_history:
            history_text = "\n📜 PREVIOUS CONVERSATION:\n"
            for msg in conversation_history[-6:]:  # Last 3 exchanges
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content'][:500]}...\n\n"
        
        # ================================================================
        # 🆕 SMART DETECTION: Is this question about the PDF?
        # ================================================================
        # Check if the question seems unrelated to the PDF content
        # If unrelated, tell user to use regular chat instead
        
        # First, let the LLM decide if it can answer from context
        relevance_check_prompt = f"""
        You are checking if a question can be answered using the given PDF context.
        
        PDF Context (first 1000 chars):
        {context[:1000]}
        
        Question: {question}
        
        Can this question be answered using the PDF context above?
        Reply with ONLY one word: "YES" or "NO"
        
        - If the question is about the PDF content, topics in the PDF, or asks to explain/summarize something from the PDF → YES
        - If the question is completely unrelated (like weather, stocks, news, general knowledge) → NO
        """
        
        relevance_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": relevance_check_prompt}],
            max_tokens=10
        )
        
        is_related = "YES" in relevance_response.choices[0].message.content.upper()
        
        if not is_related:
            # Question is not about the PDF - provide helpful response
            print(f"ℹ️ Question '{question}' is not related to PDF content")
            answer = f"""This question doesn't seem to be related to the uploaded PDF.

**Your question:** "{question}"

📌 **To answer this question:**
- Go back to the main chat (click "New Chat" or close the PDF viewer)
- Ask your question there using the Smart AI feature

📄 **For PDF-related questions, try asking:**
- "What is this PDF about?"
- "Summarize the main points"
- "Explain [specific topic from the PDF]"
"""
            _save_rag_conversation(thread_id, pdf_id, question, answer)
            return {"answer": answer, "thread_id": thread_id, "not_pdf_related": True}
        
        # Generate answer (question IS related to PDF)
        system_prompt = f"""
            {SYSTEM_PROMPT}
            
            PDF Context:
            {context}
            {history_text}
            
            📌 IMPORTANT: If the user asks a follow-up question (like "tell me more" 
            or "what about X"), refer to the previous conversation for context.
        """
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
        )
        
        answer = completion.choices[0].message.content
        
        # ================================================================
        # 🆕 Save to Checkpointer for Future Follow-ups
        # ================================================================
        """
        📖 Why Save?
        ------------
        So the next question in this thread can reference this Q&A.
        
        Before: Each PDF question was isolated
        After:  Questions build on previous answers!
        """
        _save_rag_conversation(thread_id, pdf_id, question, answer)
        
        return {"answer": answer, "thread_id": thread_id}
        
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to query PDF: {err}")


"""
===================================================================================
                        SUMMARY: RAG SERVICE
===================================================================================

This file implements the RAG (Retrieval Augmented Generation) pattern:

ENDPOINTS:
----------
1. POST /rag/query      - Ask questions, search all indexed content
2. POST /pdf/upload     - Upload and index a PDF
3. POST /pdf/query      - Ask questions about a specific PDF

KEY CONCEPTS:
-------------
1. Embeddings: Convert text to vectors (numbers) that represent meaning
2. Vector Database: Store and search vectors by similarity
3. Similarity Search: Find the most similar chunks to a query
4. Context Augmentation: Add retrieved chunks to the LLM prompt
5. Chunking: Split long documents into smaller, searchable pieces

🔗 MAPPED TO YOUR NOTES:
------------------------
- Notes Compare/04-RAG/indexing.py → /pdf/upload endpoint
- Notes Compare/04-RAG/chat.py → /rag/query endpoint
- Notes Compare/advanced_rag/worker.py → Same RAG logic with queue

===================================================================================
"""

