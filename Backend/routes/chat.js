// =============================================================================
//                     CHAT ROUTES - Conversation & Thread Management
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * This file handles all chat-related API endpoints:
 * 1. Creating and managing chat threads
 * 2. Sending messages and getting AI responses
 * 3. Global memory across threads
 * 
 * 🔗 ENDPOINTS IN THIS FILE:
 * --------------------------
 * GET    /api/thread           → Get all threads (sidebar history)
 * GET    /api/thread/:threadId → Get messages for a specific thread
 * DELETE /api/thread/:threadId → Delete a thread
 * PATCH  /api/thread/:threadId → Rename a thread
 * POST   /api/chat             → Send message, get AI response
 * POST   /api/rag-chat         → Send question to RAG service (legacy)
 * 
 * 📌 KEY CONCEPT - THREADS:
 * -------------------------
 * A "thread" = One conversation (like a ChatGPT chat)
 * Each thread has:
 * - threadId: Unique identifier (UUID)
 * - title: Display name in sidebar
 * - messages: Array of {role, content} objects
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "I use MongoDB to persist chat threads. Each thread stores the full
 *  conversation history, and I also maintain a global memory thread
 *  for cross-thread context (like ChatGPT's memory feature)."
 */

import express from "express";
// 📖 Express framework for creating routes

import Thread from "../models/Thread.js";
// 📖 Mongoose model for Thread documents
// Defines schema: threadId, title, messages[], timestamps

import getOpenAIAPIResponse from "../utils/openai.js";
// 📖 Utility function that calls OpenAI API
// Handles system prompt, message history, API call

const router = express.Router();
// 📖 Creates a modular router
// Allows us to define routes here and mount them in server.js

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";
// 📖 Base URL for Python AI service
// 📌 Why a separate service?
// - Python has better AI/ML libraries (LangChain, etc.)
// - Node.js handles web requests, Python handles AI logic
// - Microservices pattern: each service does one thing well

// =============================================================================
//                         TEST ENDPOINT (Development)
// =============================================================================

router.post("/test", async(req, res) => {
    // 📖 Test endpoint for verifying MongoDB connection
    // Creates a sample thread to test database write operations
    try {
        const thread = new Thread({
            threadId: "abc",
            title: "Testing New Thread2"
        });

        const response = await thread.save();
        // 📖 .save() inserts the document into MongoDB
        res.send(response);
    } catch(err) {
        console.log(err);
        res.status(500).json({error: "Failed to save in DB"});
    }
});


// =============================================================================
//                         GET ALL THREADS (Sidebar)
// =============================================================================
/**
 * 📖 GET /api/thread
 * ------------------
 * Returns all chat threads for the sidebar history.
 * 
 * Used by: Frontend Sidebar component
 * When: On page load and after creating new chats
 * 
 * 📌 WHY SORT BY updatedAt?
 * Most recent chats appear at the top (like ChatGPT)
 */

router.get("/thread", async(req, res) => {
    try {
        const threads = await Thread.find({}).sort({updatedAt: -1});
        // 📖 Thread.find({}) → Get all documents
        // 📖 .sort({updatedAt: -1}) → Sort descending (newest first)
        // 📌 -1 = descending, 1 = ascending
        
        res.json(threads);
    } catch(err) {
        console.log(err);
        res.status(500).json({error: "Failed to fetch threads"});
    }
});


// =============================================================================
//                    GET SINGLE THREAD MESSAGES (Load Chat)
// =============================================================================
/**
 * 📖 GET /api/thread/:threadId
 * ----------------------------
 * Returns messages for a specific thread WITH PAGINATION.
 * 
 * Used by: Frontend when user clicks a chat in sidebar
 * Returns: { messages: [...], hasMore: boolean, totalMessages: number, page: number }
 * 
 * 📌 URL PARAMETER:
 * :threadId is a route parameter, accessed via req.params.threadId
 * 
 * 📌 QUERY PARAMETERS (for pagination):
 * ?page=1&limit=20
 * - page: Which page to load (1 = most recent messages)
 * - limit: How many messages per page
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 * 📖 PAGINATION EXPLAINED - IMPORTANT FOR INTERVIEWS!
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * 🤔 WHAT IS PAGINATION?
 * ----------------------
 * Pagination means loading data in small "pages" or chunks instead of all at once.
 * 
 * Example: A chat has 500 messages
 * WITHOUT pagination: Load all 500 → Slow! (takes 500ms+)
 * WITH pagination:    Load last 20 → Fast! (takes 50ms)
 *                     Load next 20 when user scrolls up
 * 
 * 📊 VISUAL EXAMPLE:
 * ------------------
 * Imagine messages stored like this (index 0 = oldest, index 99 = newest):
 * 
 * [msg0, msg1, msg2, ... msg80, msg81, msg82, ... msg97, msg98, msg99]
 *   ↑                            ↑                              ↑
 * Oldest                      Middle                         Newest
 * (index 0)                                                (index 99)
 * 
 * PAGE 1 (limit=20): Returns msg80 to msg99 (most recent 20)
 * PAGE 2 (limit=20): Returns msg60 to msg79 (next 20 older)
 * PAGE 3 (limit=20): Returns msg40 to msg59 (next 20 older)
 * ... and so on
 * 
 * 🔢 THE MATH:
 * ------------
 * totalMessages = 100 (total messages in thread)
 * limit = 20 (messages per page)
 * page = 1 (first page = most recent)
 * 
 * endIndex = totalMessages - ((page - 1) * limit)
 *          = 100 - ((1 - 1) * 20)
 *          = 100 - 0
 *          = 100 (exclusive, so up to index 99)
 * 
 * startIndex = max(0, endIndex - limit)
 *            = max(0, 100 - 20)
 *            = 80
 * 
 * Result: slice(80, 100) → messages from index 80 to 99 (the last 20)
 * 
 * 📱 WHY LOAD NEWEST FIRST?
 * -------------------------
 * Users want to see recent messages immediately!
 * - Open chat → See latest messages (Page 1)
 * - Scroll UP → Load older messages (Page 2, 3, ...)
 * - This is how WhatsApp, Telegram, ChatGPT work!
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "I implemented pagination for chat history to improve load times.
 *  Instead of loading all messages at once, I load the 20 most recent
 *  first, then load older messages when the user scrolls up. This
 *  reduces initial load time from ~500ms to ~50ms."
 */

router.get("/thread/:threadId", async(req, res) => {
    const {threadId} = req.params;
    // 📖 Destructure threadId from URL parameters
    // URL: /api/thread/abc123 → threadId = "abc123"

    // =========================================================================
    // PAGINATION PARAMETERS FROM QUERY STRING
    // =========================================================================
    /**
     * 📖 QUERY PARAMETERS:
     * URL: /api/thread/abc123?page=1&limit=20
     * 
     * req.query = { page: "1", limit: "20" }
     * 
     * 📌 NOTE: Query params are always strings!
     * That's why we use parseInt() to convert to numbers.
     * 
     * 📌 DEFAULT VALUES:
     * - page=1: Start with most recent messages
     * - limit=20: Load 20 messages at a time (good balance of speed vs content)
     */
    const page = parseInt(req.query.page) || 1;
    // 📖 parseInt("1") → 1 (number)
    // 📖 parseInt(undefined) → NaN, so || 1 gives us default of 1
    
    const limit = parseInt(req.query.limit) || 20;
    // 📖 How many messages to return per page
    // 📌 20 is a good default: not too few, not too many

    try {
        const thread = await Thread.findOne({threadId});
        // 📖 findOne() returns the first matching document
        // 📌 Different from find() which returns an array

        if(!thread) {
            return res.status(404).json({error: "Thread not found"});
            // 📖 Added "return" to prevent further execution!
        }

        // =====================================================================
        // CALCULATE PAGINATION INDICES
        // =====================================================================
        /**
         * 📖 THE PAGINATION MATH EXPLAINED:
         * 
         * SCENARIO: 100 messages, limit=20, page=1
         * 
         * totalMessages = 100
         * 
         * Step 1: Calculate where to END
         * endIndex = totalMessages - ((page - 1) * limit)
         *          = 100 - ((1 - 1) * 20)
         *          = 100 - 0
         *          = 100
         * 
         * Step 2: Calculate where to START
         * startIndex = max(0, endIndex - limit)
         *            = max(0, 100 - 20)
         *            = max(0, 80)
         *            = 80
         * 
         * Step 3: Slice the array
         * messages.slice(80, 100) → Returns messages at index 80-99
         * 
         * ─────────────────────────────────────────────────────────────────────
         * 
         * SCENARIO: 100 messages, limit=20, page=2
         * 
         * endIndex = 100 - ((2 - 1) * 20)
         *          = 100 - 20
         *          = 80
         * 
         * startIndex = max(0, 80 - 20)
         *            = 60
         * 
         * messages.slice(60, 80) → Returns messages at index 60-79
         * 
         * ─────────────────────────────────────────────────────────────────────
         * 
         * SCENARIO: 100 messages, limit=20, page=5 (last page)
         * 
         * endIndex = 100 - ((5 - 1) * 20)
         *          = 100 - 80
         *          = 20
         * 
         * startIndex = max(0, 20 - 20)
         *            = max(0, 0)
         *            = 0
         * 
         * messages.slice(0, 20) → Returns messages at index 0-19 (oldest)
         * hasMore = false (startIndex is 0, no more messages)
         */
        
        const totalMessages = thread.messages.length;
        // 📖 Total number of messages in this thread
        
        const endIndex = totalMessages - ((page - 1) * limit);
        // 📖 Where to stop slicing (exclusive)
        // 📌 For page 1: endIndex = total (get from end)
        // 📌 For page 2: endIndex = total - limit (skip recent, get older)
        
        const startIndex = Math.max(0, endIndex - limit);
        // 📖 Where to start slicing
        // 📖 Math.max(0, ...) ensures we don't go negative
        // 📌 If endIndex - limit < 0, we're on the last page of old messages
        
        const messages = thread.messages.slice(startIndex, endIndex);
        // 📖 Array.slice(start, end) returns elements from start to end-1
        // 📌 This gives us the "page" of messages we want
        
        const hasMore = startIndex > 0;
        // 📖 Are there more (older) messages to load?
        // 📌 If startIndex is 0, we've reached the oldest messages
        // 📌 Frontend uses this to know if it should show "Load More" option

        // =====================================================================
        // SEND PAGINATED RESPONSE
        // =====================================================================
        /**
         * 📖 RESPONSE STRUCTURE:
         * {
         *   messages: [...],      // The page of messages
         *   hasMore: true/false,  // Are there older messages?
         *   totalMessages: 100,   // Total count (for UI info)
         *   page: 1               // Current page number
         * }
         * 
         * 📌 WHY RETURN hasMore?
         * Frontend needs to know if it should:
         * - Show "scroll to load more" indicator
         * - Make another request when user scrolls up
         * - Stop requesting when all messages are loaded
         */
        res.json({
            messages,
            hasMore,
            totalMessages,
            page
        });
        
    } catch(err) {
        console.log(err);
        res.status(500).json({error: "Failed to fetch chat"});
    }
});


// =============================================================================
//                        DELETE THREAD (Delete Chat)
// =============================================================================
/**
 * 📖 DELETE /api/thread/:threadId
 * --------------------------------
 * Deletes a chat thread from the database.
 * 
 * Used by: Frontend trash icon in sidebar
 * 
 * 📌 HTTP DELETE:
 * RESTful convention for removing resources
 */

router.delete("/thread/:threadId", async (req, res) => {
    const {threadId} = req.params;

    try {
        const deletedThread = await Thread.findOneAndDelete({threadId});
        // 📖 findOneAndDelete() finds and removes in one operation
        // Returns the deleted document (or null if not found)

        if(!deletedThread) {
            res.status(404).json({error: "Thread not found"});
        }

        res.status(200).json({success : "Thread deleted successfully"});

    } catch(err) {
        console.log(err);
        res.status(500).json({error: "Failed to delete thread"});
    }
});


// =============================================================================
//                      RENAME THREAD (Edit Chat Title)
// =============================================================================
/**
 * 📖 PATCH /api/thread/:threadId
 * ------------------------------
 * Updates the title of a chat thread.
 * 
 * Used by: Frontend edit icon in sidebar
 * Body: { "title": "New Title" }
 * 
 * 📌 WHY PATCH vs PUT?
 * - PATCH = Partial update (only title)
 * - PUT = Full replacement (all fields)
 * We only update title, so PATCH is correct
 */

router.patch("/thread/:threadId", async (req, res) => {
    const {threadId} = req.params;
    const {title} = req.body || {};

    if(!title) {
        return res.status(400).json({error: "Missing title"});
        // 📖 400 = Bad Request (client error)
    }

    try {
        const updated = await Thread.findOneAndUpdate(
            {threadId},                        // 📖 Filter: which document to update
            {title, updatedAt: new Date()},    // 📖 Update: new values
            {new: true}                        // 📖 Option: return updated doc (not original)
        );
        // 📌 {new: true} is important!
        // Without it, you get the OLD document before update
        
        if(!updated) {
            return res.status(404).json({error: "Thread not found"});
        }
        return res.json({success: true, threadId, title: updated.title});
    } catch (err) {
        console.log(err);
        return res.status(500).json({error: "Failed to update thread title"});
    }
});

// =============================================================================
//                     MAIN CHAT ENDPOINT (Send Message)
// =============================================================================
/**
 * 📖 POST /api/chat
 * -----------------
 * The main chat endpoint - handles sending messages and getting AI responses.
 * 
 * Body: { "threadId": "uuid", "message": "Hello!" }
 * Returns: { "reply": "AI response..." }
 * 
 * 📌 KEY FEATURES:
 * 1. Creates new thread if doesn't exist
 * 2. Maintains conversation history
 * 3. Global memory across threads (like ChatGPT's memory!)
 * 
 * 📌 INTERVIEW TIP:
 * "My chat system maintains both thread-specific history and global memory.
 *  This allows the AI to remember user preferences across conversations,
 *  similar to ChatGPT's memory feature."
 */

router.post("/chat", async(req, res) => {
    const {threadId, message} = req.body;
    // 📖 Destructure from request body
    // threadId: UUID for this conversation
    // message: User's message text

    if(!threadId || !message) {
        res.status(400).json({error: "missing required fields"});
        // 📖 400 = Bad Request (validation error)
    }

    try {
        // =================================================================
        // STEP 1: Load or Create Thread
        // =================================================================
        let thread = await Thread.findOne({threadId});
        // 📖 Try to find existing thread

        const globalThreadId = "global-shared";
        let globalThread = await Thread.findOne({threadId: globalThreadId});
        // 📖 Global thread stores memory shared across ALL threads
        // 📌 This is like ChatGPT's "Memory" feature!

        if(!thread) {
            // Create new thread if first message
            thread = new Thread({
                threadId,
                title: message,  // 📖 First message becomes thread title
                messages: [{role: "user", content: message}]
            });
        } else {
            // Add message to existing thread
            thread.messages.push({role: "user", content: message});
        }

        // =================================================================
        // STEP 2: Build Message History (Global + Local)
        // =================================================================
        // 📌 WHY MERGE HISTORIES?
        // Global history: User preferences, name, facts from other threads
        // Local history: Current conversation context
        // Together: AI knows both user preferences AND current context
        
        const globalHistory = (globalThread?.messages || []).slice(-20);
        // 📖 Last 20 messages from global memory

        const localHistory = (thread.messages || []).slice(-20);
        // 📖 Last 20 messages from current thread

        const mergedHistory = [...globalHistory, ...localHistory];
        // 📖 Spread operator combines both arrays
        
        const assistantReply = await getOpenAIAPIResponse(message, mergedHistory.slice(0, -1));
        // 📖 Call OpenAI with full history
        // 📌 slice(0, -1): Exclude last message (already in prompt)

        // =================================================================
        // STEP 3: Save Response to Thread
        // =================================================================
        thread.messages.push({role: "assistant", content: assistantReply});
        thread.updatedAt = new Date();
        // 📖 Update timestamp so thread appears at top of sidebar

        await thread.save();
        // 📖 Persist to MongoDB

        // =================================================================
        // STEP 4: Update Global Memory
        // =================================================================
        // 📌 GLOBAL MEMORY PATTERN:
        // Everything said in ANY thread is also saved to global memory
        // This allows AI to remember user across threads
        
        if(!globalThread) {
            globalThread = new Thread({
                threadId: globalThreadId,
                title: "Global Memory",
                messages: []
            });
        }
        globalThread.messages.push({role: "user", content: message});
        globalThread.messages.push({role: "assistant", content: assistantReply});
        
        // 📖 Trim to prevent unbounded growth
        if(globalThread.messages.length > 40) {
            globalThread.messages = globalThread.messages.slice(-40);
            // 📌 Keep only last 40 messages (20 exchanges)
        }
        globalThread.updatedAt = new Date();
        await globalThread.save();

        res.json({reply: assistantReply});
    } catch(err) {
        console.log(err);
        res.status(500).json({error: "something went wrong"});
    }
});


// =============================================================================
//                       RAG CHAT ENDPOINT (Legacy)
// =============================================================================
/**
 * 📖 POST /api/rag-chat
 * ---------------------
 * Forwards questions to Python RAG service for document-grounded answers.
 * 
 * Body: { "question": "What is...?" }
 * Returns: { "reply": "...", "context": "..." }
 * 
 * 📌 RAG = Retrieval Augmented Generation
 * 1. Find relevant document chunks (retrieval)
 * 2. Give chunks to LLM as context (augmentation)
 * 3. LLM generates answer using that context (generation)
 * 
 * 📌 NOTE: This is a legacy endpoint.
 * Current PDF Q&A uses /api/pdf-query in pdf.js instead.
 */

router.post("/rag-chat", async (req, res) => {
    const {question} = req.body;

    if(!question) {
        return res.status(400).json({error: "missing required fields"});
    }

    try {
        const response = await fetch(`${AI_SERVICE_URL}/rag/query`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({question})
        });
        // 📖 Forward request to Python AI service
        // 📌 This is the "Backend as Proxy" pattern:
        // Frontend → Backend → AI Service
        // Why? Keeps AI service URL hidden, adds auth, logging, etc.

        const data = await response.json();

        return res.json({reply: data.answer, context: data.context_used});
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "RAG service call failed"});
    }
});


// =============================================================================
//                              EXPORT ROUTER
// =============================================================================

export default router;
// 📖 ES Module export (not CommonJS module.exports)
// Imported in server.js: import chatRoutes from "./routes/chat.js"


// =============================================================================
//                         SUMMARY FOR INTERVIEWS
// =============================================================================
/**
 * 📌 ENDPOINTS SUMMARY:
 * 
 * | Method | Endpoint              | Purpose                    |
 * |--------|-----------------------|----------------------------|
 * | GET    | /api/thread           | Get all threads (sidebar)  |
 * | GET    | /api/thread/:id       | Get thread messages        |
 * | DELETE | /api/thread/:id       | Delete a thread            |
 * | PATCH  | /api/thread/:id       | Rename thread title        |
 * | POST   | /api/chat             | Send message, get reply    |
 * | POST   | /api/rag-chat         | Query with RAG context     |
 * 
 * 📌 KEY CONCEPTS:
 * - Thread = One conversation (like ChatGPT chat)
 * - Global memory = Shared across all threads
 * - RESTful design: GET read, POST create, PATCH update, DELETE remove
 * - Mongoose for MongoDB operations
 * - Proxy pattern: Backend forwards to AI service
 */
