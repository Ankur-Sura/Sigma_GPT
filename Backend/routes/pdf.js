// =============================================================================
//                     PDF ROUTES - RAG Document Upload & Query
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * Handles PDF upload and question-answering using RAG.
 * 
 * 🔗 ENDPOINTS:
 * -------------
 * POST /api/upload-pdf  → Upload PDF, extract text, create embeddings
 * POST /api/pdf-query   → Ask questions about uploaded PDF
 * 
 * 📌 RAG PIPELINE:
 * ----------------
 *     1. User uploads PDF
 *            ↓
 *     2. Backend forwards to Python AI service
 *            ↓
 *     3. AI service: Extract text → Chunk → Embed → Store in Qdrant
 *            ↓
 *     4. Returns pdf_id for future queries
 *            ↓
 *     5. User asks question with pdf_id
 *            ↓
 *     6. AI service: Embed question → Search Qdrant → Get relevant chunks
 *            ↓
 *     7. LLM generates answer using chunks as context
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "My RAG system uses vector embeddings for semantic search. When a user
 *  uploads a PDF, I chunk it, embed each chunk with OpenAI, and store in
 *  Qdrant. Questions are answered by finding similar chunks and using
 *  them as context for the LLM."
 */

import express from "express";
// 📖 Express for routing

import multer from "multer";
// 📖 Multer: Middleware for handling file uploads
// 📌 Why multer?
// - Parses multipart/form-data (file uploads)
// - Stores files in memory or disk
// - Provides file info (name, size, mimetype)

import Thread from "../models/Thread.js";
// 📖 For persisting Q&A to chat history

const router = express.Router();

const upload = multer({storage: multer.memoryStorage()});
// 📖 memoryStorage(): Keep file in RAM, don't save to disk
// 📌 Why memory?
// - We're forwarding to AI service immediately
// - No need to persist file on Backend
// - Faster than disk I/O

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";
// 📖 Python AI service URL (FastAPI)


// =============================================================================
//                         PDF UPLOAD ENDPOINT
// =============================================================================
/**
 * 📖 POST /api/upload-pdf
 * -----------------------
 * Uploads a PDF file and forwards it to the AI service for processing.
 * 
 * Request: multipart/form-data with "pdf" field
 * Response: { pdf_id, filename, status, chunk_count }
 * 
 * 📌 WHAT HAPPENS IN AI SERVICE:
 * 1. Extract text from PDF (PyPDFLoader)
 * 2. Split into chunks (RecursiveCharacterTextSplitter)
 * 3. Create embeddings (OpenAI text-embedding-3-small)
 * 4. Store in Qdrant vector database
 * 5. Return pdf_id for future queries
 */

router.post("/upload-pdf", upload.single("pdf"), async (req, res) => {
// 📖 upload.single("pdf"): Multer middleware
// - Expects file in form field named "pdf"
// - Makes file available as req.file
    const file = req.file;
    // 📖 req.file: The uploaded file (from multer middleware)
    // Contains: buffer, originalname, mimetype, size

    // 📌 Get threadId for persistence
    const threadId = req.body?.threadId;

    if(!file) {
        return res.status(400).json({error: "No file uploaded"});
    }

    try {
        // =================================================================
        // Forward PDF to Python AI Service
        // =================================================================
        const formData = new FormData();
        // 📖 FormData: Web API for multipart/form-data
        // 📌 Why FormData? AI service expects multipart file upload

        formData.append("file", new Blob([file.buffer], {type: file.mimetype}), file.originalname);
        // 📖 Blob: Binary Large Object
        // - file.buffer: Raw file bytes from multer
        // - file.mimetype: "application/pdf"
        // - file.originalname: "document.pdf"
        // 
        // 📌 WHY BLOB?
        // Convert buffer to Blob so fetch can send it as multipart

        // =================================================================
        // 🔗 CONNECTION: BACKEND → AI SERVICE (Python FastAPI)
        // =================================================================
        // This is where Node.js Backend calls the Python AI Service!
        // 
        // FLOW:
        // Frontend (React) → [You are here: Backend] → AI Service (Python)
        //                                                    ↓
        //                                            RAG Pipeline:
        //                                            Extract → Chunk → Embed → Qdrant
        //
        // 📌 AI endpoint: AI/rag_service.py → upload_pdf()
        // =================================================================
        const response = await fetch(`${AI_SERVICE_URL}/pdf/upload`, {
            method: "POST",
            body: formData
            // 📌 Note: No "Content-Type" header!
            // fetch automatically sets multipart/form-data with boundary
        });

        const data = await response.json();
        console.log("📄 PDF Upload response:", {pdf_id: data.pdf_id, filename: data.filename, status: data.status});

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "PDF upload failed"});
        }

        // =================================================================
        // 🆕 Persist PDF Upload to MongoDB
        // =================================================================
        /**
         * 📖 WHY PERSIST PDF UPLOAD?
         * --------------------------
         * So when user reopens the chat thread, they see:
         * - What PDF they uploaded
         * - That they can ask questions about it
         * 
         * Without this, PDF upload notifications disappear on refresh!
         * 
         * 📌 INTERVIEW TIP:
         * "I persist all AI tool interactions to MongoDB, including file
         *  uploads, so the complete conversation history is preserved."
         */
        if(threadId) {
            try {
                let thread = await Thread.findOne({threadId});
                const filename = data.filename || file.originalname;
                
                if(!thread) {
                    thread = new Thread({
                        threadId,
                        title: `PDF: ${filename}`,
                        messages: []
                    });
                }
                
                // Add assistant message for upload notification
                const uploadMessage = `📄 **${filename}** uploaded.\nAsk about specific pages or content.`;
                thread.messages.push({role: "assistant", content: uploadMessage});
                
                thread.updatedAt = new Date();
                await thread.save();
                console.log("✅ PDF upload saved to thread:", threadId);
            } catch(saveErr) {
                console.log("⚠️ Failed to save PDF upload to thread:", saveErr);
                // Don't fail the request
            }
        }

        return res.json(data);
        // 📖 Returns: { pdf_id, filename, status, chunk_count }
        // Frontend stores pdf_id for future queries
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Failed to forward PDF to AI service"});
    }
});


// =============================================================================
//                         PDF QUERY ENDPOINT
// =============================================================================
/**
 * 📖 POST /api/pdf-query
 * ----------------------
 * Asks a question about an uploaded PDF.
 * 
 * Body: { pdf_id, question, threadId }
 * Response: { answer, context, sources }
 * 
 * 📌 RAG QUERY FLOW:
 * 1. Embed the question (same model as chunks)
 * 2. Search Qdrant for similar chunks (vector similarity)
 * 3. Take top-k most similar chunks
 * 4. Give chunks to LLM as context
 * 5. LLM generates answer grounded in the document
 * 
 * 📌 INTERVIEW TIP:
 * "When querying, I embed the question using the same model as the documents.
 *  Then I use cosine similarity to find the most relevant chunks. This ensures
 *  the LLM answers based on actual document content, not hallucinations."
 */

router.post("/pdf-query", async (req, res) => {
    const {pdf_id, question, threadId} = req.body || {};
    // 📖 pdf_id: Identifier returned from upload
    // 📖 question: User's question about the PDF
    // 📖 threadId: For persisting to chat history
    
    console.log("📝 PDF Query received:", {pdf_id, question, threadId});
    
    if(!pdf_id || !question) {
        console.log("❌ Missing pdf_id or question");
        return res.status(400).json({error: "missing pdf_id or question"});
    }

    try {
        // =================================================================
        // 🔗 CONNECTION: BACKEND → AI SERVICE (Python FastAPI)
        // =================================================================
        // This is where Node.js Backend calls the Python AI Service!
        // 
        // FLOW:
        // Frontend (React) → [You are here: Backend] → AI Service (Python)
        //                                                    ↓
        //                                            RAG Query Pipeline:
        //                                            Embed Question → Search Qdrant
        //                                            → Get Context → LLM Answer
        //
        // 📌 AI endpoint: AI/rag_service.py → query_pdf()
        // =================================================================
        /**
         * 🆕 Now passing thread_id for conversation memory!
         * -------------------------------------------------
         * This allows follow-up questions about the PDF:
         * 
         * User: "What skills are in this resume?"
         * AI:   "Python, JavaScript, React..."
         * User: "Tell me more about Python"  ← This now works!
         * 
         * The AI service saves Q&A to MongoDB and loads history
         * for subsequent questions in the same thread.
         */
        console.log("🔄 Forwarding to AI service with thread_id...");
        const response = await fetch(`${AI_SERVICE_URL}/pdf/query`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                pdf_id, 
                question,
                thread_id: threadId || "default"  // 🆕 Pass thread for memory!
            })
        });
        // 📖 AI service does the RAG magic:
        // - Embeds question
        // - Searches Qdrant
        // - 🆕 Loads conversation history for this thread
        // - Calls LLM with context + history
        // - 🆕 Saves Q&A for future follow-ups
        // - Returns grounded answer

        const data = await response.json();

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "PDF query failed"});
        }

        // =================================================================
        // Persist Q&A to Thread History
        // =================================================================
        // 📌 WHY PERSIST?
        // So user sees PDF Q&A in chat history after refresh
        
        if(threadId) {
            try {
                let thread = await Thread.findOne({threadId});
                if(!thread) {
                    thread = new Thread({
                        threadId,
                        title: question,
                        messages: [{role: "user", content: question}]
                    });
                } else {
                    thread.messages.push({role: "user", content: question});
                }
                thread.messages.push({role: "assistant", content: data.answer || "No answer"});
                thread.updatedAt = new Date();
                await thread.save();
            } catch (persistErr) {
                console.log("Failed to persist PDF Q&A:", persistErr);
                // 📌 Don't fail the request just because persistence failed
            }
        }

        return res.json(data);
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Failed to query AI service"});
    }
});


// =============================================================================
//                              EXPORT ROUTER
// =============================================================================

export default router;


// =============================================================================
//                         SUMMARY FOR INTERVIEWS
// =============================================================================
/**
 * 📌 RAG PIPELINE SUMMARY:
 * 
 * UPLOAD PHASE:
 *     PDF File → PyPDFLoader → Text → Chunking → Embeddings → Qdrant
 * 
 * QUERY PHASE:
 *     Question → Embed → Search Qdrant → Top-K Chunks → LLM → Answer
 * 
 * 📌 KEY TECHNOLOGIES:
 * - Multer: File upload handling
 * - FormData/Blob: Binary data transfer
 * - OpenAI Embeddings: text-embedding-3-small
 * - Qdrant: Vector similarity search
 * - LangChain: Document loading and chunking
 * 
 * 📌 WHY RAG?
 * - LLMs have training cutoff date
 * - LLMs can hallucinate facts
 * - RAG grounds answers in real documents
 * - User can verify from source
 */
