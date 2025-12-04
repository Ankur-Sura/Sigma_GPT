// =============================================================================
//                   TOOLS ROUTES - Web Search, STT, OCR
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * Handles utility tool endpoints that proxy to the Python AI service:
 * 
 * 🔗 ENDPOINTS:
 * -------------
 * POST /api/search     → Web search using AI agent
 * POST /api/stt        → Speech-to-Text (Whisper)
 * POST /api/image-ocr  → Image text extraction (Tesseract)
 * 
 * 📌 PROXY PATTERN:
 * -----------------
 * Frontend → Backend (Node.js) → AI Service (Python)
 * 
 * 📌 WHY PROXY THROUGH BACKEND?
 * 1. Hide AI service URL from frontend
 * 2. Add authentication/rate limiting
 * 3. Log requests centrally
 * 4. Transform data if needed
 * 5. Persist results to MongoDB
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "I use a microservices architecture where Node.js handles web requests
 *  and proxies AI operations to a Python FastAPI service. This separates
 *  concerns and lets each language do what it's best at."
 */

import express from "express";
// 📖 Express for routing

import multer from "multer";
// 📖 Multer for handling file uploads (audio, images)

import Thread from "../models/Thread.js";
// 📖 For persisting search results to chat history

const router = express.Router();

const upload = multer({storage: multer.memoryStorage()});
// 📖 Keep files in RAM for immediate forwarding
// 📌 No disk I/O = faster processing

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";
// 📖 Python AI service (FastAPI)


// =============================================================================
//                         WEB SEARCH ENDPOINT
// =============================================================================
/**
 * 📖 POST /api/search
 * -------------------
 * Performs web search using the AI agent.
 * 
 * Body: { query, session_id }
 * Response: { answer, steps, sources }
 * 
 * 📌 AGENT FLOW:
 * 1. User asks: "What's the weather in NYC?"
 * 2. Agent PLANS: "I need to search the web"
 * 3. Agent ACTIONS: Calls web_search("weather NYC")
 * 4. Agent OBSERVES: Gets search results
 * 5. Agent OUTPUTS: Synthesized answer
 * 
 * 📌 INTERVIEW TIP:
 * "My agent follows the Plan-Action-Observe-Output loop. It can autonomously
 *  decide to use tools like web search, observe results, and synthesize answers."
 */

router.post("/search", async (req, res) => {
    const {query, session_id} = req.body || {};
    // 📖 query: User's search question
    // 📖 session_id: For agent memory persistence

    if(!query) {
        return res.status(400).json({error: "missing query"});
    }

    try {
        // =================================================================
        // 🔗 CONNECTION: BACKEND → AI SERVICE (Python FastAPI)
        // =================================================================
        // This is where Node.js Backend calls the Python AI Service!
        // 
        // FLOW:
        // Frontend (React) → [You are here: Backend] → AI Service (Python)
        //
        // 📌 AI endpoint: AI/agent_service.py → run_agent()
        // 📌 AI Service uses: Tavily/DuckDuckGo search + LLM to synthesize
        // =================================================================
        const response = await fetch(`${AI_SERVICE_URL}/agent/web-search`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({query, session_id: session_id || "default"})
            // 📖 session_id: Agent keeps memory per session
            // 📌 Same session = Agent remembers previous queries
        });
        const data = await response.json();

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "Search failed"});
        }

        // =================================================================
        // Persist Search Result to MongoDB
        // =================================================================
        // 📌 WHY PERSIST?
        // So user sees search results in chat history after refresh
        
        const threadId = session_id || "default";
        let thread = await Thread.findOne({threadId});
        if(!thread) {
            thread = new Thread({
                threadId,
                title: query,
                messages: [{role: "user", content: query}]
            });
        } else {
            thread.messages.push({role: "user", content: query});
        }
        thread.messages.push({role: "assistant", content: data.answer || "No answer"});
        thread.updatedAt = new Date();
        await thread.save();

        return res.json(data);
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Search proxy failed"});
    }
});


// =============================================================================
//                      SPEECH-TO-TEXT ENDPOINT
// =============================================================================
/**
 * 📖 POST /api/stt
 * ----------------
 * Converts audio to text using OpenAI Whisper.
 * 
 * Request: multipart/form-data with "audio" file
 * Response: { text: "transcribed text" }
 * 
 * 📌 WHISPER MODEL:
 * - OpenAI's speech recognition model
 * - Supports 50+ languages
 * - Works with various audio formats
 * 
 * 📌 USE CASE IN APP:
 * User clicks mic → Records audio → Sends to STT → Gets text → Sends to chat
 */

router.post("/stt", upload.single("audio"), async (req, res) => {
    // 📖 upload.single("audio"): Multer middleware for audio file
    
    const file = req.file;
    if(!file) {
        return res.status(400).json({error: "No audio provided"});
    }
    
    const language = (req.body?.language || "").toString().trim();
    // 📖 Optional language hint for better accuracy
    // e.g., "en" for English, "hi" for Hindi

    try {
        // =================================================================
        // 🔗 CONNECTION: BACKEND → AI SERVICE (Python FastAPI)
        // =================================================================
        // This is where Node.js Backend calls the Python AI Service!
        // 
        // FLOW:
        // Frontend (React) → [You are here: Backend] → AI Service (Python)
        //                                                    ↓
        //                                            OpenAI Whisper API
        //
        // 📌 AI endpoint: AI/tools_service.py → transcribe_audio()
        // =================================================================
        const formData = new FormData();
        const audioBlob = new Blob([file.buffer], {type: file.mimetype || "audio/webm"});
        // 📖 Convert buffer to Blob for multipart upload
        
        formData.append("file", audioBlob, file.originalname || "audio.webm");
        if(language) {
            formData.append("language", language);
        }

        const response = await fetch(`${AI_SERVICE_URL}/stt/transcribe`, {
            method: "POST",
            body: formData
        });
        // 📖 AI service uses OpenAI Whisper API:
        // client.audio.transcriptions.create(file=audio, model="whisper-1")

        const data = await response.json();

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "Transcription failed"});
        }

        return res.json(data);
        // 📖 Returns: { text: "Hello, how are you?" }
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "STT proxy failed"});
    }
});


// =============================================================================
//                         IMAGE OCR ENDPOINT
// =============================================================================
/**
 * 📖 POST /api/image-ocr
 * ----------------------
 * Extracts text from images using Tesseract OCR.
 * 
 * Request: multipart/form-data with "image" file
 * Response: { text: "extracted text" }
 * 
 * 📌 TESSERACT:
 * - Open-source OCR engine
 * - Supports 100+ languages
 * - Works with photos, scans, screenshots
 * 
 * 📌 USE CASE IN APP:
 * User uploads image → OCR extracts text → Shows in chat
 * Useful for: screenshots, handwritten notes, document photos
 */

router.post("/image-ocr", upload.single("image"), async (req, res) => {
    // 📖 upload.single("image"): Multer middleware for image file
    
    const file = req.file;
    if(!file) {
        return res.status(400).json({error: "No image provided"});
    }

    // 📌 NEW: Get threadId for persistence
    const threadId = req.body?.threadId || req.query?.threadId;
    const fileName = file.originalname || "image.png";

    try {
        // =================================================================
        // 🔗 CONNECTION: BACKEND → AI SERVICE (Python FastAPI)
        // =================================================================
        // This is where Node.js Backend calls the Python AI Service!
        // 
        // FLOW:
        // Frontend (React) → [You are here: Backend] → AI Service (Python)
        //                                                    ↓
        //                                            Tesseract OCR Engine
        //
        // 📌 AI endpoint: AI/tools_service.py → ocr_image()
        // =================================================================
        const formData = new FormData();
        const imageBlob = new Blob([file.buffer], {type: file.mimetype || "image/png"});
        formData.append("file", imageBlob, fileName);

        const response = await fetch(`${AI_SERVICE_URL}/ocr/image`, {
            method: "POST",
            body: formData
        });
        // 📖 AI service uses Tesseract:
        // pytesseract.image_to_string(image)

        const data = await response.json();

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "OCR failed"});
        }

        // =================================================================
        // 🆕 Persist OCR Result to MongoDB
        // =================================================================
        /**
         * 📖 WHY PERSIST OCR RESULTS?
         * ---------------------------
         * So when user reopens the chat thread, they see:
         * - What image they uploaded
         * - The extracted text
         * 
         * Without this, OCR results would disappear on refresh!
         * 
         * 📌 INTERVIEW TIP:
         * "I ensure all AI tool outputs are persisted to MongoDB, so users
         *  can see their complete conversation history including OCR results,
         *  web searches, and PDF queries."
         */
        if(threadId) {
            try {
                let thread = await Thread.findOne({threadId});
                if(!thread) {
                    thread = new Thread({
                        threadId,
                        title: `Image OCR: ${fileName}`,
                        messages: []
                    });
                }
                
                // Add user message (image upload)
                const userMessage = `📷 Uploaded image: ${fileName}`;
                thread.messages.push({role: "user", content: userMessage});
                
                // Add assistant message (OCR result)
                const ocrText = (data.text || "").trim();
                const clipped = ocrText.slice(0, 1500) + (ocrText.length > 1500 ? " ..." : "");
                const assistantMessage = `📷 **Image Uploaded:** \`${fileName}\`\n\n📝 **Extracted Text:**\n\n${clipped}`;
                thread.messages.push({role: "assistant", content: assistantMessage});
                
                thread.updatedAt = new Date();
                await thread.save();
                console.log("✅ OCR result saved to thread:", threadId);
            } catch(saveErr) {
                console.log("⚠️ Failed to save OCR to thread:", saveErr);
                // Don't fail the request, just log the error
            }
        }

        return res.json(data);
        // 📖 Returns: { text: "Text from image..." }
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Image OCR proxy failed"});
    }
});


// =============================================================================
//                    🆕 TRAVEL PLANNER ENDPOINT (LangGraph)
// =============================================================================
/**
 * 📖 POST /api/travel-planner
 * ---------------------------
 * Runs the LangGraph-based travel planner workflow.
 * 
 * Body: { 
 *   query: "Plan a trip to Goa from Mumbai",
 *   source: "Mumbai",           // optional
 *   destination: "Goa",         // optional
 *   preferences: {              // optional (Human-in-Loop)
 *     vehicle_type: "petrol",
 *     food_preference: "veg",
 *     is_smoker: false,
 *     budget: "midrange",
 *     interested_in_adventure: true,
 *     travel_mode: "car"
 *   }
 * }
 * 
 * 📌 THIS USES LANGGRAPH! (8-Node Workflow)
 * 
 * The workflow has 8 nodes:
 * 1. Destination Researcher - Places, weather, safety
 * 2. Transport Finder - Flights, trains, buses, car routes
 * 3. Accommodation Finder - Hotels (central, secure)
 * 4. Activities Planner - Sports, attractions
 * 5. Food & Shopping Guide - Restaurants, markets
 * 6. Travel Requirements - Visa, SIM, currency
 * 7. Emergency & Safety - Hospitals, police
 * 8. Package Builder - Creates 3 packages
 */

router.post("/travel-planner", async (req, res) => {
    const {query, source, destination, preferences, thread_id} = req.body || {};

    if(!query) {
        return res.status(400).json({error: "missing query"});
    }

    try {
        console.log(`🧳 Travel planner requested: ${query}`);
        console.log(`   From: ${source || "auto"} → To: ${destination || "auto"}`);
        
        // 🆕 Create or use existing thread
        let savedThreadId = thread_id;
        let thread = null;
        
        if(!thread_id || thread_id === "null" || thread_id.length !== 24) {
            // Create new thread
            const newThreadId = `travel_${Date.now()}`;
            thread = new Thread({
                threadId: newThreadId,
                title: query.slice(0, 50),
                messages: [{role: "user", content: query}]
            });
            await thread.save();
            savedThreadId = thread._id.toString();
            console.log(`✅ Created new thread for travel: ${savedThreadId}`);
        } else {
            // Use existing thread
            try {
                await Thread.findByIdAndUpdate(thread_id, {
                    $push: {
                        messages: {
                            role: "user",
                            content: query
                        }
                    }
                });
            } catch(dbErr) {
                console.log("⚠️ Could not save to thread:", dbErr.message);
            }
        }
        
        // =================================================================
        // 🔗 CONNECTION: BACKEND → AI SERVICE (Python FastAPI + LangGraph)
        // =================================================================
        const response = await fetch(`${AI_SERVICE_URL}/agent/travel-planner`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({query, source, destination, preferences})
        });
        
        const data = await response.json();

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "Travel planner failed"});
        }

        // 🆕 Save AI response to chat history
        if(data.final_package) {
            try {
                if(thread) {
                    // New thread
                    thread.messages.push({role: "assistant", content: data.final_package});
                    await thread.save();
                } else if(savedThreadId && savedThreadId.length === 24) {
                    // Existing thread
                    await Thread.findByIdAndUpdate(savedThreadId, {
                        $push: {
                            messages: {
                                role: "assistant",
                                content: data.final_package
                            }
                        }
                    });
                }
            } catch(dbErr) {
                console.log("⚠️ Could not save to thread:", dbErr.message);
            }
        }

        // Return the full LangGraph response
        return res.json(data);
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Travel planner proxy failed"});
    }
});


// =============================================================================
//                    🆕 SOLO TRIP PLANNER (Human-in-the-Loop)
// =============================================================================
/**
 * 📖 POST /api/solo-trip/start
 * ----------------------------
 * Starts the solo trip planner. Runs initial research, then PAUSES
 * for user preferences (Human-in-the-Loop).
 * 
 * Body: { query: "Plan a solo trip from Delhi to Goa" }
 * 
 * Response: {
 *   status: "awaiting_input" | "complete",
 *   thread_id: string,
 *   origin, destination, distance_km,
 *   destination_info, transport_options
 * }
 */
router.post("/solo-trip/start", async (req, res) => {
    const {query, thread_id} = req.body || {};

    if(!query) {
        return res.status(400).json({error: "missing query"});
    }

    try {
        console.log(`🎒 Solo trip planner (HITL) started: ${query}`);
        
        // 🆕 Create or find thread for saving history
        let savedThreadId = thread_id;
        let thread = null;
        
        // If no thread_id or invalid, create a new thread
        if(!thread_id || thread_id === "null" || thread_id.length !== 24) {
            // Generate a unique threadId
            const newThreadId = `solo_${Date.now()}`;
            thread = new Thread({
                threadId: newThreadId,
                title: query.slice(0, 50),
                messages: [{role: "user", content: query}]
            });
            await thread.save();
            savedThreadId = thread._id.toString();
            console.log(`✅ Created new thread for solo trip: ${savedThreadId}`);
        } else {
            // Use existing thread
            try {
                await Thread.findByIdAndUpdate(thread_id, {
                    $push: {
                        messages: {
                            role: "user",
                            content: query
                        }
                    }
                });
            } catch(dbErr) {
                console.log("⚠️ Could not save to thread:", dbErr.message);
            }
        }
        
        const response = await fetch(`${AI_SERVICE_URL}/agent/solo-trip/start`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({query, thread_id})
        });
        
        const data = await response.json();

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "Solo trip start failed"});
        }

        // 🆕 Save initial response to chat history
        if(data.status === "awaiting_input") {
            const infoMsg = `🎒 **Solo Trip Planning Started!**\n\n` +
                `📍 **From:** ${data.origin}\n` +
                `📍 **To:** ${data.destination}\n` +
                `📏 **Distance:** ${data.distance_km || 'calculating...'} km\n\n` +
                `Please select your preferences to continue...`;
            
            try {
                if(thread) {
                    // New thread - push to existing reference
                    thread.messages.push({role: "assistant", content: infoMsg});
                    await thread.save();
                } else if(savedThreadId && savedThreadId.length === 24) {
                    // Existing thread - update by ID
                    await Thread.findByIdAndUpdate(savedThreadId, {
                        $push: {
                            messages: {
                                role: "assistant",
                                content: infoMsg
                            }
                        }
                    });
                }
            } catch(dbErr) {
                console.log("⚠️ Could not save to thread:", dbErr.message);
            }
        }

        // 🆕 Return the saved thread ID so frontend can use it
        return res.json({
            ...data,
            chat_thread_id: savedThreadId
        });
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Solo trip start proxy failed"});
    }
});

/**
 * 📖 POST /api/solo-trip/resume
 * -----------------------------
 * Resumes the solo trip planner with user preferences.
 * 
 * Body: {
 *   thread_id: string,
 *   preferences: {
 *     travel_mode, vehicle_make, vehicle_model, fuel_type,
 *     ev_range, current_charge, food_preference, budget_level,
 *     accommodation_type
 *   }
 * }
 * 
 * Response: { status: "complete", final_package: string }
 */
router.post("/solo-trip/resume", async (req, res) => {
    const {thread_id, chat_thread_id, preferences} = req.body || {};

    if(!thread_id || !preferences) {
        return res.status(400).json({error: "missing thread_id or preferences"});
    }

    try {
        console.log(`🎒 Solo trip planner resuming: ${thread_id}`);
        
        const response = await fetch(`${AI_SERVICE_URL}/agent/solo-trip/resume`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({thread_id, preferences})
        });
        
        const data = await response.json();

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "Solo trip resume failed"});
        }

        // 🆕 Save final package to chat history
        if(chat_thread_id && chat_thread_id !== "null" && chat_thread_id.length === 24 && data.final_package) {
            try {
                await Thread.findByIdAndUpdate(chat_thread_id, {
                    $push: {
                        messages: {
                            role: "assistant",
                            content: data.final_package
                        }
                    }
                });
            } catch(dbErr) {
                console.log("⚠️ Could not save to thread:", dbErr.message);
            }
        }

        return res.json(data);
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Solo trip resume proxy failed"});
    }
});


// =============================================================================
//                    🆕 STOCK RESEARCH ENDPOINT (LangGraph)
// =============================================================================
/**
 * 📖 POST /api/stock-research
 * ---------------------------
 * Runs the LangGraph-based stock research workflow.
 * 
 * Body: { query, company_name? }
 * Response: { 
 *   success, workflow, nodes_executed,
 *   sector_analysis, company_research, policy_analysis,
 *   final_recommendation
 * }
 * 
 * 📌 THIS USES LANGGRAPH!
 * The workflow has 4 nodes:
 * 1. Sector Analyst - Identifies sector trends
 * 2. Company Researcher - Gets data from MoneyControl, Screener
 * 3. Policy Watchdog - Checks government policies
 * 4. Final Advisor - Combines all and recommends
 * 
 * 📌 DIFFERENCE FROM /api/search:
 * /api/search - Uses prompt-based agent, flexible
 * /api/stock-research - Uses LangGraph nodes, structured workflow
 */

router.post("/stock-research", async (req, res) => {
    const {query, company_name, thread_id} = req.body || {};

    if(!query) {
        return res.status(400).json({error: "missing query"});
    }

    try {
        console.log(`📈 Stock research requested: ${query}`);
        
        // 🆕 Create or use existing thread
        let savedThreadId = thread_id;
        let thread = null;
        
        if(!thread_id || thread_id === "null" || thread_id.length !== 24) {
            // Create new thread
            const newThreadId = `stock_${Date.now()}`;
            thread = new Thread({
                threadId: newThreadId,
                title: query.slice(0, 50),
                messages: [{role: "user", content: query}]
            });
            await thread.save();
            savedThreadId = thread._id.toString();
            console.log(`✅ Created new thread for stock: ${savedThreadId}`);
        } else {
            // Use existing thread
            try {
                await Thread.findByIdAndUpdate(thread_id, {
                    $push: {
                        messages: {
                            role: "user",
                            content: query
                        }
                    }
                });
            } catch(dbErr) {
                console.log("⚠️ Could not save to thread:", dbErr.message);
            }
        }
        
        // =================================================================
        // 🔗 CONNECTION: BACKEND → AI SERVICE (Python FastAPI + LangGraph)
        // =================================================================
        const response = await fetch(`${AI_SERVICE_URL}/agent/stock-research`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({query, company_name})
        });
        
        const data = await response.json();

        if(!response.ok) {
            return res.status(response.status).json({error: data.detail || "Stock research failed"});
        }

        // 🆕 Save AI response to chat history
        if(data.final_recommendation) {
            try {
                if(thread) {
                    // New thread
                    thread.messages.push({role: "assistant", content: data.final_recommendation});
                    await thread.save();
                } else if(savedThreadId && savedThreadId.length === 24) {
                    // Existing thread
                    await Thread.findByIdAndUpdate(savedThreadId, {
                        $push: {
                            messages: {
                                role: "assistant",
                                content: data.final_recommendation
                            }
                        }
                    });
                }
            } catch(dbErr) {
                console.log("⚠️ Could not save to thread:", dbErr.message);
            }
        }

        // Return the full LangGraph response
        return res.json(data);
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Stock research proxy failed"});
    }
});


// =============================================================================
//                    🆕 SMART AI CHAT ENDPOINT
// =============================================================================
/**
 * 📖 POST /api/smart-chat
 * -----------------------
 * Smart AI that automatically detects when tools are needed.
 * 
 * Body: { 
 *   query: "What is the stock price of Tata Motors?",
 *   thread_id: "abc123",
 *   user_id: "default",
 *   force_tool: null // Optional: "search", "stock", "weather", "news"
 * }
 * 
 * Response: { 
 *   answer, intent, tool_used, auto_detected, steps
 * }
 * 
 * 📌 THIS IS THE MAIN SMART AI ENDPOINT!
 * 
 * 🧠 HOW IT WORKS:
 * 1. Analyzes the query to detect intent (stock, weather, news, general)
 * 2. Routes to appropriate tool automatically
 * 3. If LLM says "I don't know" → Falls back to web search
 * 
 * 📌 INTENTS:
 * - STOCK → Uses LangGraph stock research workflow
 * - WEATHER → Uses weather tool
 * - NEWS → Uses news search
 * - CURRENT_INFO → Uses web search (needs live data)
 * - GENERAL → Uses LLM knowledge, falls back to search if needed
 * 
 * 📌 FOR INTERVIEWS:
 * "I implemented Smart AI that automatically detects query intent and
 *  routes to appropriate tools. If the LLM admits it doesn't have current
 *  information, we automatically fall back to web search."
 */

router.post("/smart-chat", async (req, res) => {
    const {query, thread_id, user_id, force_tool} = req.body || {};

    if(!query) {
        return res.status(400).json({error: "missing query"});
    }

    try {
        console.log(`🧠 Smart AI request: ${query}`);
        console.log(`   Thread: ${thread_id || "default"}, Force: ${force_tool || "auto"}`);
        
        // =================================================================
        // 🔗 CONNECTION: BACKEND → AI SERVICE (Python FastAPI)
        // =================================================================
        // This is where Node.js Backend calls the Python AI Service!
        // 
        // FLOW:
        // Frontend (React) → [You are here: Backend] → AI Service (Python)
        //                                                    ↓
        //                                            Smart Intent Detection:
        //                                            STOCK → LangGraph stock workflow
        //                                            TRAVEL → LangGraph travel workflow
        //                                            WEATHER → Weather tool
        //                                            NEWS → News search
        //                                            GENERAL → LLM + fallback search
        //
        // 📌 AI endpoint: AI/agent_service.py → run_smart_chat()
        // =================================================================
        
        // 🆕 Retry logic for cold start handling
        const maxRetries = 2;
        let lastError = null;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`🔄 Smart chat attempt ${attempt}/${maxRetries}`);
                
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 120000); // 2 min timeout
                
                const response = await fetch(`${AI_SERVICE_URL}/agent/smart-chat`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        query,
                        thread_id: thread_id || "default",
                        user_id: user_id || "default",
                        force_tool: force_tool || null
                    }),
                    signal: controller.signal
                });
                
                clearTimeout(timeout);
                
                const data = await response.json();

                if(!response.ok) {
                    return res.status(response.status).json({error: data.detail || "Smart chat failed"});
                }
                
                // Success - continue with the rest of the function
                var smartData = data;
                break;
                
            } catch (fetchErr) {
                lastError = fetchErr;
                console.log(`⚠️ Attempt ${attempt} failed: ${fetchErr.message}`);
                
                if (attempt < maxRetries) {
                    console.log(`⏳ Waiting 3s before retry...`);
                    await new Promise(r => setTimeout(r, 3000));
                }
            }
        }
        
        if (!smartData) {
            console.log(`❌ All ${maxRetries} attempts failed`);
            return res.status(503).json({
                error: "AI service temporarily unavailable. Please try again in a few seconds."
            });
        }
        
        const data = smartData;

        // =================================================================
        // Persist Smart Chat Result to MongoDB
        // =================================================================
        const threadIdToUse = thread_id || "default";
        
        let thread = await Thread.findOne({threadId: threadIdToUse});
        if(!thread) {
            thread = new Thread({
                threadId: threadIdToUse,
                title: query,
                messages: []
            });
        }
        thread.messages.push({role: "user", content: query});
        thread.messages.push({role: "assistant", content: data.answer || "No answer"});
        thread.updatedAt = new Date();
        await thread.save();

        // Return the full Smart AI response
        return res.json(data);
    } catch(err) {
        console.log(err);
        return res.status(500).json({error: "Smart chat proxy failed"});
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
 * 📌 TOOLS SUMMARY:
 * 
 * | Tool       | Technology      | Use Case                    |
 * |------------|-----------------|-----------------------------| 
 * | Web Search | DuckDuckGo API  | Real-time info, current events |
 * | STT        | OpenAI Whisper  | Voice input, accessibility  |
 * | OCR        | Tesseract       | Image text, document photos |
 * 
 * 📌 PROXY PATTERN BENEFITS:
 * 1. Security: Hide API keys from frontend
 * 2. Logging: Central place for request logging
 * 3. Caching: Can add caching layer in backend
 * 4. Rate Limiting: Control API usage
 * 5. Data Transformation: Normalize responses
 * 
 * 📌 INTERVIEW TIP:
 * "I chose a microservices architecture where Node.js handles HTTP routing
 *  and Python handles AI processing. This lets me use the best tools for
 *  each job - Express for web APIs, Python for AI/ML libraries."
 */
