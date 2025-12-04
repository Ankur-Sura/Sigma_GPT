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
    """Call OCR.space API for PDF page OCR"""
    import base64
    import requests
    
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        payload = {
            'apikey': OCR_SPACE_API_KEY,
            'base64Image': f'data:image/png;base64,{base64_image}',
            'language': 'eng',
            'isOverlayRequired': False,
            'OCREngine': 2
        }
        
        response = requests.post(
            'https://api.ocr.space/parse/image',
            data=payload,
            timeout=30
        )
        
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            return ""
        
        parsed_results = result.get('ParsedResults', [])
        if parsed_results:
            return parsed_results[0].get('ParsedText', '').strip()
        
        return ""
    except Exception as e:
        print(f"⚠️ OCR.space API failed for PDF: {e}")
        return ""

def is_ocr_space_available():
    return bool(OCR_SPACE_API_KEY)


def fix_ocr_code_formatting(text: str) -> str:
    """
    Fix OCR output that concatenates words without spaces.
    Especially important for code where 'publicstaticvoid' should be 'public static void'
    
    Examples:
    - publicstaticNoderightRotate → public static Node rightRotate
    - returnroot → return root
    - intgetBalance → int getBalance
    """
    import re
    
    # ==========================================================================
    # STEP 1: Add spaces before/after Java keywords
    # ==========================================================================
    # Keywords that should ALWAYS have space before AND after
    keywords = [
        # Access modifiers
        'public', 'private', 'protected',
        # Other modifiers
        'static', 'final', 'abstract', 'synchronized', 'volatile', 'transient',
        # Types
        'void', 'int', 'long', 'short', 'byte', 'float', 'double', 'boolean', 'char',
        # Control flow
        'if', 'else', 'while', 'for', 'do', 'switch', 'case', 'default', 'break', 'continue',
        # Class/object
        'class', 'interface', 'enum', 'extends', 'implements', 'new', 'this', 'super',
        # Exception
        'try', 'catch', 'finally', 'throw', 'throws',
        # Other
        'return', 'import', 'package', 'instanceof',
        # Literals
        'null', 'true', 'false',
        # Common class names
        'String', 'Integer', 'Boolean', 'Object', 'List', 'ArrayList', 'HashMap', 'Map',
        'Node', 'Math', 'System', 'Arrays',
    ]
    
    # Sort by length (longest first) to avoid partial matches
    keywords = sorted(set(keywords), key=len, reverse=True)
    
    # Add space BEFORE keyword if preceded by letter/digit (not already space)
    for kw in keywords:
        # Pattern: letter/digit immediately before keyword
        text = re.sub(rf'([a-zA-Z0-9])({kw})\b', rf'\1 \2', text, flags=re.IGNORECASE)
        # Pattern: keyword immediately followed by uppercase letter
        text = re.sub(rf'\b({kw})([A-Z])', rf'\1 \2', text)
    
    # ==========================================================================
    # STEP 2: Fix specific stuck patterns
    # ==========================================================================
    
    # Fix "returnroot" -> "return root"
    text = re.sub(r'\breturn([a-z])', r'return \1', text)
    
    # Fix "elseif" -> "else if"
    text = re.sub(r'\belse\s*if\b', 'else if', text)
    
    # Fix "){"  -> ") {"
    text = re.sub(r'\)\{', ') {', text)
    
    # Fix "){" patterns
    text = re.sub(r'\)\s*\{', ') {', text)
    
    # Fix "if(" -> "if ("
    text = re.sub(r'\b(if|while|for|switch|catch)\(', r'\1 (', text)
    
    # ==========================================================================
    # STEP 3: Fix operators without spaces
    # ==========================================================================
    
    # Fix "x=y" -> "x = y" (but not == or !=)
    text = re.sub(r'(\w)([+\-*/%]?=)(?!=)(\w)', r'\1 \2 \3', text)
    
    # Fix comparison operators: "x<y" -> "x < y"
    text = re.sub(r'(\w)(<|>|<=|>=|==|!=)(\w)', r'\1 \2 \3', text)
    
    # Fix "x+y" -> "x + y"
    text = re.sub(r'(\w)([+\-])(\w)', r'\1 \2 \3', text)
    
    # ==========================================================================
    # STEP 4: Fix merged words (CamelCase that got stuck)
    # ==========================================================================
    
    # Fix "NodeT2" -> "Node T2" (uppercase followed by uppercase+digit)
    text = re.sub(r'([a-z])([A-Z][A-Z0-9])', r'\1 \2', text)
    
    # Fix general merged words: "heightMath" -> "height Math"
    text = re.sub(r'([a-z])([A-Z][a-z]{2,})', r'\1 \2', text)
    
    # ==========================================================================
    # STEP 5: Clean up
    # ==========================================================================
    
    # Fix multiple spaces
    text = re.sub(r'  +', ' ', text)
    
    # Fix spaces before punctuation
    text = re.sub(r' +([;,\.\)])', r'\1', text)
    
    # Fix spaces after opening brackets
    text = re.sub(r'([(\[]) +', r'\1', text)
    
    return text


def clean_ocr_text(text: str) -> str:
    """
    Clean and improve OCR text quality.
    Detects if text is code and applies appropriate formatting.
    """
    import re
    
    if not text:
        return ""
    
    # Basic cleanup
    text = text.strip()
    
    # Remove common OCR artifacts
    text = text.replace('\x0c', '\n')  # Form feed
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    # Detect if this looks like code (has programming keywords)
    code_indicators = ['public', 'private', 'class', 'def ', 'function', 'return', 'import', 'void', 'static']
    looks_like_code = any(indicator in text.lower() for indicator in code_indicators)
    
    if looks_like_code:
        text = fix_ocr_code_formatting(text)
    
    # Clean up excessive newlines
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

# 🆕 Debug: Print Qdrant configuration at startup
print("=" * 60)
print("📊 RAG Service Configuration:")
print(f"   QDRANT_URL: {QDRANT_URL}")
print(f"   QDRANT_COLLECTION: {QDRANT_COLLECTION}")
print(f"   QDRANT_API_KEY: {'✅ Set' if QDRANT_API_KEY else '❌ NOT SET'}")
print(f"   OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ NOT SET'}")
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

@rag_router.get("/pdf/status")
async def pdf_status():
    """
    📖 PDF Service Status Endpoint
    ------------------------------
    Returns the status of the PDF/RAG service including:
    - Qdrant connection status
    - Collection info
    - Environment configuration
    
    HTTP GET to: http://localhost:8000/pdf/status
    """
    status = {
        "service": "RAG/PDF Service",
        "qdrant_url": QDRANT_URL,
        "qdrant_collection": QDRANT_COLLECTION,
        "qdrant_api_key_set": bool(QDRANT_API_KEY),
        "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "ocr_available": convert_from_bytes is not None and pytesseract is not None,
        "qdrant_connected": False,
        "collection_exists": False,
        "collection_points": 0,
        "error": None
    }
    
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
#                     ENDPOINT: PDF UPLOAD
# =============================================================================

@rag_router.post("/pdf/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    📖 PDF Upload Endpoint
    ----------------------
    Uploads and indexes a PDF for RAG queries.
    
    HTTP POST to: http://localhost:8000/pdf/upload
    Body: multipart/form-data with file
    
    THE INDEXING PIPELINE:
    1. Receive PDF file
    2. Extract text page-by-page (with OCR fallback for scanned PDFs)
    3. Split text into chunks
    4. Create embeddings for each chunk
    5. Store embeddings in Qdrant
    6. Return PDF ID for future queries
    
    🔗 THIS IS EXACTLY YOUR NOTES (04-RAG/indexing.py)!
    """
    
    # Validate file type
    if file.content_type and "pdf" not in file.content_type.lower():
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Step 1: Read PDF Content
        # ------------------------
        # Read the uploaded file into memory as bytes
        content = await file.read()
        
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
                    
                    # Convert PDF page to image
                    images = convert_from_bytes(
                        content,
                        first_page=idx + 1,
                        last_page=idx + 1,
                        dpi=200  # Good balance of quality and speed
                    )
                    
                    if images:
                        # Convert PIL image to bytes for OCR.space
                        img_buffer = BytesIO()
                        images[0].save(img_buffer, format='PNG')
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
            # ═══════════════════════════════════════════════════════════════
            combined_text = ""
            
            if pdf_text and ocr_text:
                # Both have text - combine them, avoid duplicates
                # If OCR text is much longer, it probably captured more (use it)
                # If they're similar length, prefer PDF text (cleaner)
                if len(ocr_text) > len(pdf_text) * 1.5:
                    combined_text = ocr_text
                    print(f"📝 Page {idx + 1}: Using OCR text (more complete)")
                else:
                    # Combine both - PDF text first, then unique OCR content
                    combined_text = pdf_text
                    # Add OCR text that's not already in PDF text (simple dedup)
                    ocr_lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
                    pdf_lower = pdf_text.lower()
                    for line in ocr_lines:
                        if line.lower() not in pdf_lower and len(line) > 10:
                            combined_text += f"\n{line}"
                    print(f"📝 Page {idx + 1}: Combined PDF + OCR text")
            elif pdf_text:
                combined_text = pdf_text
                print(f"📝 Page {idx + 1}: Using PDF text only")
            elif ocr_text:
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

