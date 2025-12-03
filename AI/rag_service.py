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

from qdrant_client.http.models import Filter, FieldCondition, MatchValue
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
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image
except Exception:
    # These are optional - some systems might not have them
    convert_from_bytes = None
    pytesseract = None
    Image = None

"""
📖 What is OCR?
--------------
OCR = Optical Character Recognition

✔ Converts IMAGES of text into actual text
✔ Used when PDF pages are scanned (images, not text)

pdf2image: Converts PDF pages to images
pytesseract: Python wrapper for Tesseract OCR engine
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
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

try:
    _rag_mongo_client = MongoClient(MONGO_URI)
    _rag_db = _rag_mongo_client["sigma_gpt_db"]
    _rag_checkpoints = _rag_db["rag_checkpoints"]  # Separate collection for RAG
    print("✅ RAG Checkpointer: Connected to MongoDB")
except Exception as e:
    print(f"⚠️ RAG Checkpointer: MongoDB connection failed: {e}")
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
    if not _rag_checkpoints:
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
    if not _rag_checkpoints:
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
        ocr_available = convert_from_bytes is not None and pytesseract is not None
        
        for idx, page in enumerate(reader.pages):
            # Try to extract text normally first
            page_text = page.extract_text() or ""
            
            # OCR Fallback: If page has no text and OCR is available
            if len(page_text.strip()) < 10 and ocr_available:
                try:
                    # Convert PDF page to image
                    images = convert_from_bytes(
                        content,
                        first_page=idx + 1,
                        last_page=idx + 1,
                        dpi=300  # Higher DPI = better OCR accuracy
                    )
                    if images:
                        # Run OCR on the image
                        ocr_text = pytesseract.image_to_string(images[0])
                        if ocr_text.strip():
                            page_text = ocr_text
                except Exception:
                    pass  # OCR failed, continue with empty text
            
            pages.append({"page": idx + 1, "text": page_text})
            full_text_parts.append(f"[Page {idx + 1}]\n{page_text}")
        
        full_text = "\n\n".join(full_text_parts)
        
        # Check if we got any text
        if not any((p["text"] or "").strip() for p in pages):
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the PDF"
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
        
        if docs:
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
            
            QdrantVectorStore.from_documents(**doc_connection_kwargs)
            print(f"✅ Successfully stored {len(docs)} chunks in Qdrant")
        
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
    
    try:
        # Connect to existing collection
        vector_db = QdrantVectorStore.from_existing_collection(
            url=QDRANT_URL,
            collection_name=QDRANT_COLLECTION,
            embedding=embedding_model
        )
        
        # Create filter to search ONLY in this PDF
        # -----------------------------------------
        # This ensures we only get chunks from the specified PDF
        # Uses Qdrant's filtering capability
        
        qdrant_filter = Filter(
            must=[
                FieldCondition(
                    key="metadata.pdf_id",  # LangChain stores metadata here
                    match=MatchValue(value=pdf_id)
                )
            ]
        )
        
        print(f"🔍 Searching with filter for pdf_id: {pdf_id}")
        
        # Search with filter
        results = vector_db.similarity_search(
            query=question,
            k=8,  # Get more chunks for detailed answers
            filter=qdrant_filter
        )
        
        print(f"📊 Found {len(results)} results")
        
        if not results:
            return {"answer": "I couldn't find any content for that PDF. Try re-uploading."}
        
        # Sort by page number for logical flow
        sorted_results = sorted(results, key=lambda r: r.metadata.get("page", 0))
        
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
        
        # Generate answer
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

