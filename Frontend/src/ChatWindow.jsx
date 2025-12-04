import "./ChatWindow.css";
import Chat from "./Chat.jsx";
import { MyContext } from "./MyContext.jsx";
import { useContext, useState, useEffect, useRef } from "react";
import {ScaleLoader} from "react-spinners";
import TripPreferencesModal from "./TripPreferencesModal.jsx";
import { API_URL } from "./config.js";

function ChatWindow() {
    const {prompt, setPrompt, reply, setReply, currThreadId, setPrevChats, setNewChat, userId} = useContext(MyContext);
    const [loading, setLoading] = useState(false);

    // Feature buttons
    const [uploading, setUploading] = useState(false);
    const [searching, setSearching] = useState(false);
    const [searchMode, setSearchMode] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [ragMode, setRagMode] = useState(false);
    const [pdfId, setPdfId] = useState(null);
    const [pdfName, setPdfName] = useState(null);
    const [imageUploading, setImageUploading] = useState(false);
    const [showUploadMenu, setShowUploadMenu] = useState(false);
    
    // 🆕 Stock Research Mode (LangGraph)
    const [stockMode, setStockMode] = useState(false);
    const [stockResearching, setStockResearching] = useState(false);
    const [thinkingSteps, setThinkingSteps] = useState([]);
    
    // 🆕 Travel Planner Mode (LangGraph)
    const [travelMode, setTravelMode] = useState(false);
    const [travelPlanning, setTravelPlanning] = useState(false);
    
    // 🆕 Solo Trip Mode with Human-in-the-Loop
    const [soloTripMode, setSoloTripMode] = useState(false);
    const [soloTripPlanning, setSoloTripPlanning] = useState(false);
    const [showPreferencesModal, setShowPreferencesModal] = useState(false);
    const [soloTripThreadId, setSoloTripThreadId] = useState(null);
    const [soloTripInfo, setSoloTripInfo] = useState(null);
    
    // 🆕 Smart AI State
    const [smartIntent, setSmartIntent] = useState(null);
    const [toolUsed, setToolUsed] = useState(null);
    /**
     * 📖 Smart AI Mode
     * ----------------
     * Smart AI automatically detects when tools are needed:
     * - Stock queries → LangGraph Stock Research
     * - Weather queries → Weather Tool
     * - News queries → News Search
     * - Current info → Web Search
     * - General → LLM (with fallback to web search if outdated)
     * 
     * 📖 Stock Research Mode (Manual Override)
     * ----------------------------------------
     * When enabled, queries go through the LangGraph stock workflow:
     * 1. Sector Analyst
     * 2. Company Researcher (MoneyControl, Screener)
     * 3. Policy Watchdog
     * 4. Final Advisor
     * 
     * thinkingSteps shows the progress in the UI!
     */
    const fileInputRef = useRef(null);
    const imageInputRef = useRef(null);
    const uploadMenuRef = useRef(null);
    const uploadButtonRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const abortControllerRef = useRef(null);
    const recordTimeoutRef = useRef(null);

    const getReply = async (forcedPrompt) => {
        // If already loading and user clicks send, treat it as cancel.
        if(loading) {
            if(abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            setLoading(false);
            return;
        }

        // Only use forcedPrompt if it's a valid string (not an event object)
        const validForcedPrompt = typeof forcedPrompt === "string" ? forcedPrompt : null;
        const currentPrompt = String(validForcedPrompt ?? prompt ?? "").trim();
        
        // Don't do anything if prompt is empty
        if(!currentPrompt) return;
        setNewChat(false);

        // If search mode is armed, run web search instead of normal chat send.
        if(searchMode) {
            await performWebSearch(currentPrompt);
            setSearchMode(false);
            return;
        }

        // 🆕 If stock mode is armed, run LangGraph stock research
        if(stockMode) {
            await performStockResearch(currentPrompt);
            setStockMode(false);
            return;
        }
        
        // 🆕 If solo trip mode is armed, run Human-in-the-Loop planner
        if(soloTripMode) {
            await performSoloTrip(currentPrompt);
            setSoloTripMode(false);
            return;
        }
        
        // 🆕 If travel mode is armed, run LangGraph travel planner
        if(travelMode) {
            await performTravelPlanner(currentPrompt);
            setTravelMode(false);
            return;
        }

        // If RAG mode is active and pdfId present, ask PDF instead of normal chat.
        if(ragMode && pdfId) {
            await performRagQuestion(currentPrompt);
            return;
        }

        // 🆕 USE SMART AI BY DEFAULT!
        // Smart AI automatically detects when tools are needed
        await performSmartChat(currentPrompt);
    }

    /**
     * 🆕 Smart AI Chat
     * ================
     * Automatically detects when tools are needed and routes accordingly.
     * 
     * 📌 HOW IT WORKS:
     * 1. Sends query to /api/smart-chat
     * 2. Backend detects intent (stock, weather, news, general)
     * 3. Routes to appropriate tool automatically
     * 4. If LLM says "I don't know" → Falls back to web search
     * 
     * 📌 INTENT TYPES:
     * - STOCK → LangGraph stock workflow
     * - WEATHER → Weather tool
     * - NEWS → News search
     * - CURRENT_INFO → Web search
     * - GENERAL → LLM knowledge (fallback to search if outdated)
     */
    const performSmartChat = async (queryText) => {
        if(!queryText) return;

        setLoading(true);
        setPrompt("");
        setPrevChats(prev => [...prev, {role: "user", content: queryText}]);
        
        // Reset smart state
        setSmartIntent(null);
        setToolUsed(null);
        setThinkingSteps([]);

        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            // ═══════════════════════════════════════════════════════════════
            // 🔗 CONNECTION: FRONTEND → BACKEND → AI SERVICE
            // ═══════════════════════════════════════════════════════════════
            // 
            // FLOW:
            // ┌──────────┐      POST /api/smart-chat     ┌──────────┐
            // │ FRONTEND │ ───────────────────────────▶  │ BACKEND  │
            // │ (React)  │                               │ (Node.js)│
            // └──────────┘                               └────┬─────┘
            //                                                 │
            //                    POST /agent/smart-chat       ▼
            //                                            ┌──────────┐
            //                                            │ AI SRVCE │
            //                                            │ (Python) │
            //                                            └──────────┘
            //
            // 📌 Backend file: Backend/routes/tools.js (line ~491)
            // 📌 AI endpoint: AI/agent_service.py → run_smart_chat()
            // ═══════════════════════════════════════════════════════════════
            const response = await fetch(`${API_URL}/api/smart-chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    query: queryText,
                    thread_id: currThreadId,
                    user_id: userId || "default"
                }),
                signal: controller.signal
            });
            
            const data = await response.json();

            if(!response.ok) {
                const msg = typeof data?.error === "string" 
                    ? data.error 
                    : typeof data?.detail === "string"
                        ? data.detail
                        : "Smart AI failed. Please try again.";
                setPrevChats(prev => [...prev, {role: "assistant", content: msg}]);
                setReply(null);
                return;
            }

            // Update smart intent info for UI
            if(data.intent) {
                setSmartIntent(data.intent);
            }
            if(data.tool_used) {
                setToolUsed(data.tool_used);
            }
            
            // If we got steps (from stock research), show them
            if(data.steps && data.steps.length > 0) {
                setThinkingSteps(data.steps.map(s => ({
                    step: s.step,
                    status: s.status || "complete",
                    label: getStepLabel(s.step)
                })));
            }

            // Build the response
            let fullResponse = data.answer || "";
            
            // If this was a stock query with detailed analysis, format it nicely
            if(data.intent === "STOCK" && data.final_recommendation) {
                fullResponse = "";
                if(data.sector_analysis) {
                    fullResponse += `### 🏭 Sector Analysis\n${data.sector_analysis}\n\n`;
                }
                if(data.company_research) {
                    fullResponse += `### 🕵️ Company Research\n${data.company_research}\n\n`;
                }
                if(data.policy_analysis) {
                    fullResponse += `### ⚖️ Policy Analysis\n${data.policy_analysis}\n\n`;
                }
                if(data.final_recommendation) {
                    fullResponse += `---\n\n${data.final_recommendation}`;
                }
            }
            
            // 🆕 If this was a travel query with detailed info, format it nicely
            if(data.intent === "TRAVEL" && data.final_summary) {
                fullResponse = data.final_summary;
            }

            if(!fullResponse.trim()) {
                fullResponse = "No response received. Please try again.";
            }

            setPrevChats(prev => [...prev, {role: "assistant", content: fullResponse}]);
            setReply(fullResponse);
            
        } catch(err) {
            if(err.name === "AbortError") {
                setPrevChats(prev => [...prev, {role: "assistant", content: "Response cancelled."}]);
            } else {
                console.log(err);
                setPrevChats(prev => [...prev, {role: "assistant", content: "Smart AI failed: network error"}]);
            }
            setReply(null);
        } finally {
            setLoading(false);
            abortControllerRef.current = null;
            // Clear thinking steps after a short delay
            setTimeout(() => setThinkingSteps([]), 2000);
        }
    }
    
    /**
     * Helper to get display label for step names
     */
    const getStepLabel = (stepName) => {
        const labels = {
            // Stock Research steps (Enhanced 6 nodes!)
            "company_intro": "🏢 Company Introduction",
            "sector_analyst": "🏭 Sector Analysis",
            "company_researcher": "🕵️ Company Research",
            "policy_watchdog": "⚖️ Policy Analysis",
            "investor_sentiment": "📊 Investor Sentiment",
            "investment_suggestion": "💡 Investment Suggestion",
            "final_advisor": "🎓 Final Advisor",
            // General tools
            "web_search": "🔍 Web Search",
            "get_weather": "🌤️ Weather",
            "search_news": "📰 News Search",
            // Travel Planner steps (8 nodes)
            "destination_researcher": "📍 Destination Researcher",
            "transport_finder": "🚗 Transport Finder",
            "accommodation_finder": "🏨 Accommodation Finder",
            "activities_planner": "🏃 Activities Planner",
            "food_shopping_guide": "🍽️ Food & Shopping Guide",
            "travel_requirements": "🌍 Travel Requirements",
            "emergency_safety": "🆘 Emergency & Safety",
            "package_builder": "📦 Package Builder"
        };
        return labels[stepName] || stepName;
    }

    const handleInputKeyDown = (e) => {
        if(e.key === "Enter") {
            e.preventDefault();
            getReply();
        }
    }


    // When user switches threads, clear any PDF context chip/state.
    useEffect(() => {
        setPdfId(null);
        setPdfName(null);
        setRagMode(false);
    }, [currThreadId]);

    // Toggle search mode for globe button (highlight only, no chat spam)
    const toggleSearchMode = () => {
        setSearchMode(prev => !prev);
        setStockMode(false); // Disable stock mode if search is enabled
    }

    // 🆕 Toggle stock research mode
    const toggleStockMode = () => {
        setStockMode(prev => !prev);
        setSearchMode(false);
        setTravelMode(false); // Disable travel if stock is enabled
    }
    
    // 🆕 Toggle travel planner mode
    const toggleTravelMode = () => {
        setTravelMode(prev => !prev);
        setSearchMode(false);
        setStockMode(false); // Disable stock if travel is enabled
    }

    const toggleUploadMenu = () => {
        setShowUploadMenu(prev => !prev);
    }

    const handlePdfClick = () => {
        setShowUploadMenu(false);
        fileInputRef.current?.click();
    }

    const handleImageClick = () => {
        setShowUploadMenu(false);
        imageInputRef.current?.click();
    }

    // Close upload menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if(!showUploadMenu) return;
            const menuEl = uploadMenuRef.current;
            const buttonEl = uploadButtonRef.current;
            if(menuEl && menuEl.contains(e.target)) return;
            if(buttonEl && buttonEl.contains(e.target)) return;
            setShowUploadMenu(false);
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [showUploadMenu]);

    // PDF upload handler
    const handlePdfUpload = async (event) => {
        const file = event.target.files?.[0];
        if(!file) return;
        const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
        if(!isPdf) {
            setPrevChats(prev => [...prev, {role: "assistant", content: "Please upload a PDF file only."}]);
            return;
        }

        const formData = new FormData();
        formData.append("pdf", file);
        // 📌 Pass threadId so backend can save upload notification to MongoDB
        formData.append("threadId", currThreadId);

        try {
            setUploading(true);
            // ═══════════════════════════════════════════════════════════════
            // 🔗 CONNECTION: FRONTEND → BACKEND → AI SERVICE
            // ═══════════════════════════════════════════════════════════════
            // STEP 1: Frontend sends PDF to Backend (Node.js)
            // STEP 2: Backend forwards to AI Service (Python FastAPI)
            // STEP 3: AI Service: Extract → Chunk → Embed → Store in Qdrant
            // 
            // 📌 Backend endpoint: Backend/routes/pdf.js → POST /upload-pdf
            // 📌 AI endpoint: AI/rag_service.py → upload_pdf()
            // ═══════════════════════════════════════════════════════════════
            const response = await fetch(`${API_URL}/api/upload-pdf`, {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if(!response.ok) {
                const errMsg = typeof data?.error === "string"
                    ? data.error
                    : typeof data?.detail === "string"
                        ? data.detail
                        : JSON.stringify(data || {});
                setPrevChats(prev => [...prev, {role: "assistant", content: `PDF upload failed: ${errMsg}`}]);
                return;
            }

            if(data.pdf_id) {
                setPdfId(data.pdf_id);
                setRagMode(true);
                setPdfName(data.filename || file.name);
            }

            setPrevChats(prev => [
                ...prev,
                {role: "assistant", content: `📄 **${data.filename || file.name}** uploaded.\nAsk about specific pages or content.`}
            ]);
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: "PDF upload failed: network error"}]);
        } finally {
            setUploading(false);
            if(fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        }
    }

    // Image OCR handler
    const handleImageUpload = async (event) => {
        const file = event.target.files?.[0];
        if(!file) return;
        const isImage = (file.type || "").startsWith("image/") || /\.(png|jpe?g|webp|bmp|tiff?)$/i.test(file.name);
        if(!isImage) {
            setPrevChats(prev => [...prev, {role: "assistant", content: "Please upload an image file (png/jpg/webp/bmp)."}]);
            return;
        }

        const toDataUrl = (blobFile) => new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blobFile);
        });

        const formData = new FormData();
        formData.append("image", file);
        // 📌 Pass threadId so backend can save OCR result to MongoDB
        formData.append("threadId", currThreadId);

        try {
            setImageUploading(true);
            // ═══════════════════════════════════════════════════════════════
            // 🔗 CONNECTION: FRONTEND → BACKEND → AI SERVICE
            // ═══════════════════════════════════════════════════════════════
            // STEP 1: Frontend sends image to Backend (Node.js)
            // STEP 2: Backend forwards to AI Service (Python FastAPI)
            // STEP 3: AI Service: Preprocess → Tesseract OCR → Return text
            // 
            // 📌 Backend endpoint: Backend/routes/tools.js → POST /image-ocr
            // 📌 AI endpoint: AI/tools_service.py → ocr_image()
            // ═══════════════════════════════════════════════════════════════
            const response = await fetch(`${API_URL}/api/image-ocr`, {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if(!response.ok) {
                const errMsg = typeof data?.error === "string"
                    ? data.error
                    : typeof data?.detail === "string"
                        ? data.detail
                        : JSON.stringify(data || {});
                setPrevChats(prev => [...prev, {role: "assistant", content: `Image OCR failed: ${errMsg}`}]);
                return;
            }

            const ocrText = (data.text || "").trim();
            if(!ocrText) {
                setPrevChats(prev => [...prev, {role: "assistant", content: "No text detected in the image."}]);
                return;
            }

            // 📖 Format the OCR result nicely
            // Note: Markdown images with data URLs often break in React, so we use emoji instead
            const clipped = `${ocrText.slice(0, 1500)}${ocrText.length > 1500 ? " ..." : ""}`;
            const fileName = file.name || "image";
            const markdown = `📷 **Image Uploaded:** \`${fileName}\`\n\n📝 **Extracted Text:**\n\n${clipped}`;
            setPrevChats(prev => [
                ...prev,
                {role: "assistant", content: markdown}
            ]);
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: "Image OCR failed: network error"}]);
        } finally {
            setImageUploading(false);
            if(imageInputRef.current) {
                imageInputRef.current.value = "";
            }
        }
    }

    // Web search handler (agent-backed)
    const performWebSearch = async (queryText) => {
        if(!queryText) {
            setPrevChats(prev => [...prev, {role: "assistant", content: "Type a query before running web search."}]);
            return;
        }

        // ✅ Clear input IMMEDIATELY when sending
        setPrompt("");
        
        // Show user's query in UI
        setPrevChats(prev => [...prev, {role: "user", content: queryText}]);

        try {
            setSearching(true);
            // ═══════════════════════════════════════════════════════════════
            // 🔗 CONNECTION: FRONTEND → BACKEND → AI SERVICE
            // ═══════════════════════════════════════════════════════════════
            // STEP 1: Frontend sends search query to Backend (Node.js)
            // STEP 2: Backend forwards to AI Service (Python FastAPI)
            // STEP 3: AI Service: Agent decides → Tavily/DuckDuckGo search → LLM synthesizes
            // 
            // 📌 Backend endpoint: Backend/routes/tools.js → POST /search
            // 📌 AI endpoint: AI/agent_service.py → run_agent()
            // ═══════════════════════════════════════════════════════════════
            const response = await fetch(`${API_URL}/api/search`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({query: queryText, session_id: currThreadId})
            });
            const data = await response.json();

            if(!response.ok || data.error) {
                const msg = typeof data.error === "string" 
                    ? data.error 
                    : typeof data.detail === "string"
                        ? data.detail
                        : "Live search is unavailable. Please try again later.";
                setPrevChats(prev => [...prev, {role: "assistant", content: msg}]);
                return;
            }

            setPrevChats(prev => [...prev, {role: "assistant", content: data.answer || "No answer"}]);
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: "Search failed: network error"}]);
        } finally {
            setSearching(false);
        }
    }

    // RAG question handler (ask the uploaded PDF)
    const performRagQuestion = async (queryText) => {
        if(!queryText) {
            setPrevChats(prev => [...prev, {role: "assistant", content: "Type a question to ask about the PDF."}]);
            return;
        }

        // ✅ Clear input IMMEDIATELY when sending
        setPrompt("");
        
        setPrevChats(prev => [...prev, {role: "user", content: queryText}]);

        try {
            setLoading(true);
            // ═══════════════════════════════════════════════════════════════
            // 🔗 CONNECTION: FRONTEND → BACKEND → AI SERVICE
            // ═══════════════════════════════════════════════════════════════
            // STEP 1: Frontend sends question + pdf_id to Backend (Node.js)
            // STEP 2: Backend forwards to AI Service (Python FastAPI)
            // STEP 3: AI Service: Embed question → Search Qdrant → LLM answers with context
            // 
            // 📌 Backend endpoint: Backend/routes/pdf.js → POST /pdf-query
            // 📌 AI endpoint: AI/rag_service.py → query_pdf()
            // ═══════════════════════════════════════════════════════════════
            const response = await fetch(`${API_URL}/api/pdf-query`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({pdf_id: pdfId, question: queryText, threadId: currThreadId})
            });
            const data = await response.json();

            if(!response.ok || data.error) {
                const msg = typeof data.error === "string" 
                    ? data.error 
                    : typeof data.detail === "string"
                        ? data.detail
                        : "PDF question failed. Please try again.";
                setPrevChats(prev => [...prev, {role: "assistant", content: msg}]);
                return;
            }

            setPrevChats(prev => [...prev, {role: "assistant", content: data.answer || "No answer"}]);
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: "PDF question failed: network error"}]);
        } finally {
            setLoading(false);
        }
    }

    // 🆕 Stock Research handler (LangGraph workflow with thinking UI)
    const performStockResearch = async (queryText) => {
        if(!queryText) {
            setPrevChats(prev => [...prev, {role: "assistant", content: "Type a stock query (e.g., 'Tell me about Tata Motors stock')"}]);
            return;
        }

        // ✅ Clear input IMMEDIATELY when sending
        setPrompt("");
        
        // Show user's query
        setPrevChats(prev => [...prev, {role: "user", content: queryText}]);
        
        // Define all 7 steps (Enhanced workflow with Technical Analysis!)
        const allSteps = [
            {step: "company_intro", status: "pending", label: "🏢 Company Introduction"},
            {step: "sector_analyst", status: "pending", label: "🏭 Sector Analysis"},
            {step: "company_researcher", status: "pending", label: "🕵️ Company Research"},
            {step: "policy_watchdog", status: "pending", label: "⚖️ Policy Analysis"},
            {step: "investor_sentiment", status: "pending", label: "📊 Investor Sentiment"},
            {step: "technical_analysis", status: "pending", label: "📈 Technical Analysis & Risk"},
            {step: "investment_suggestion", status: "pending", label: "💡 Investment Suggestion"}
        ];
        
        // Initialize thinking steps UI
        setThinkingSteps(allSteps);
        
        // Set intent for UI
        setSmartIntent("STOCK");

        try {
            setStockResearching(true);
            
            // 🆕 Simulate step progression while waiting for response
            // IMPORTANT: Don't complete the LAST step via timer - only complete it when API responds
            // This keeps the spinner and steps in sync!
            let stepIndex = 0;
            const maxAutoSteps = allSteps.length - 1; // Stop before last step
            const stepInterval = setInterval(() => {
                if(stepIndex < maxAutoSteps) {
                    setThinkingSteps(prev => prev.map((s, idx) => {
                        if(idx < stepIndex) return {...s, status: "complete"};
                        if(idx === stepIndex) return {...s, status: "in_progress"};
                        return s;
                    }));
                    stepIndex++;
                } else if(stepIndex === maxAutoSteps) {
                    // Keep last step as "in_progress" until API responds
                    setThinkingSteps(prev => prev.map((s, idx) => {
                        if(idx < maxAutoSteps) return {...s, status: "complete"};
                        if(idx === maxAutoSteps) return {...s, status: "in_progress"};
                        return s;
                    }));
                    stepIndex++; // Prevent re-running
                }
                // After this, the last step stays "in_progress" until API responds
            }, 5000); // Each step ~5 seconds
            
            // Show first step as in progress immediately
            setThinkingSteps(prev => prev.map((s, idx) => 
                idx === 0 ? {...s, status: "in_progress"} : s
            ));
            
            // ═══════════════════════════════════════════════════════════════
            // 🔗 CONNECTION: FRONTEND → BACKEND → AI SERVICE (LangGraph)
            // ═══════════════════════════════════════════════════════════════
            // STEP 1: Frontend sends stock query to Backend (Node.js)
            // STEP 2: Backend forwards to AI Service (Python FastAPI)
            // STEP 3: AI Service runs LangGraph 4-node workflow:
            //         → Sector Analyst → Company Researcher → Policy Watchdog → Final Advisor
            // 
            // 📌 Backend endpoint: Backend/routes/tools.js → POST /stock-research
            // 📌 AI endpoint: AI/agent_service.py → run_stock_research_workflow()
            // 📌 LangGraph: AI/stock_graph.py → stock_research_graph
            // ═══════════════════════════════════════════════════════════════
            const response = await fetch(`${API_URL}/api/stock-research`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    query: queryText,
                    thread_id: currThreadId  // 🆕 Save to chat history
                })
            });
            
            // Stop the step simulation
            clearInterval(stepInterval);
            
            const data = await response.json();

            if(!response.ok || data.error) {
                const msg = typeof data.error === "string" 
                    ? data.error 
                    : typeof data.detail === "string"
                        ? data.detail
                        : "Stock research failed. Please try again.";
                setPrevChats(prev => [...prev, {role: "assistant", content: msg}]);
                setThinkingSteps([]);
                setSmartIntent(null);
                return;
            }

            // Mark all steps as complete (they already ran on the server)
            setThinkingSteps(prev => prev.map(s => ({...s, status: "complete"})));
            
            // Small delay to show the completed steps
            await new Promise(resolve => setTimeout(resolve, 500));

            // Use ONLY final_recommendation - it already contains ALL sections combined properly
            // NO need to add individual sections (that causes duplication!)
            let fullResponse = data.final_recommendation || "No analysis available. Please try a different query.";

            setPrevChats(prev => [...prev, {role: "assistant", content: fullResponse}]);
            
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: "Stock research failed: network error"}]);
        } finally {
            setStockResearching(false);
            setThinkingSteps([]);
            setSmartIntent(null);
        }
    }

    /**
     * 🆕 TRAVEL PLANNER FUNCTION
     * --------------------------
     * Uses LangGraph 8-node workflow for comprehensive travel planning.
     * 
     * The 8 nodes:
     * 1. Destination Researcher  → Places, weather, safety
     * 2. Transport Finder        → Flights, trains, buses
     * 3. Accommodation Finder    → Hotels (central, secure)
     * 4. Activities Planner      → Sports, attractions
     * 5. Food & Shopping Guide   → Restaurants, markets
     * 6. Travel Requirements     → Visa, SIM, currency
     * 7. Emergency & Safety      → Hospitals, police
     * 8. Package Builder         → 3 packages (2 website + 1 DIY)
     */
    const performTravelPlanner = async (queryText) => {
        if(!queryText) {
            setPrevChats(prev => [...prev, {role: "assistant", content: "Type a travel query (e.g., 'Plan a trip to Goa from Mumbai')"}]);
            return;
        }

        // ✅ Clear input IMMEDIATELY when sending
        setPrompt("");
        
        // Show user's query
        setPrevChats(prev => [...prev, {role: "user", content: queryText}]);
        
        // Define all steps
        const allSteps = [
            {step: "destination_researcher", status: "pending", label: "📍 Destination Researcher"},
            {step: "transport_finder", status: "pending", label: "🚗 Transport Finder"},
            {step: "accommodation_finder", status: "pending", label: "🏨 Accommodation Finder"},
            {step: "activities_planner", status: "pending", label: "🏃 Activities Planner"},
            {step: "food_shopping_guide", status: "pending", label: "🍽️ Food & Shopping Guide"},
            {step: "travel_requirements", status: "pending", label: "🌍 Travel Requirements"},
            {step: "emergency_safety", status: "pending", label: "🆘 Emergency & Safety"},
            {step: "package_builder", status: "pending", label: "📦 Package Builder"}
        ];
        
        // Initialize thinking steps UI (8 nodes for travel planner)
        setThinkingSteps(allSteps);
        
        // Set the smart intent for UI display
        setSmartIntent("TRAVEL");

        try {
            setTravelPlanning(true);
            
            // 🆕 Simulate step progression while waiting for response
            // IMPORTANT: Don't complete the LAST step via timer - only complete it when API responds
            // This keeps the spinner and steps in sync!
            let stepIndex = 0;
            const maxAutoSteps = allSteps.length - 1; // Stop before last step (Package Builder)
            const stepInterval = setInterval(() => {
                if(stepIndex < maxAutoSteps) {
                    setThinkingSteps(prev => prev.map((s, idx) => {
                        if(idx < stepIndex) return {...s, status: "complete"};
                        if(idx === stepIndex) return {...s, status: "in_progress"};
                        return s;
                    }));
                    stepIndex++;
                } else if(stepIndex === maxAutoSteps) {
                    // Keep last step as "in_progress" until API responds
                    setThinkingSteps(prev => prev.map((s, idx) => {
                        if(idx < maxAutoSteps) return {...s, status: "complete"};
                        if(idx === maxAutoSteps) return {...s, status: "in_progress"};
                        return s;
                    }));
                    stepIndex++; // Prevent re-running
                }
                // After this, the last step stays "in_progress" until API responds
            }, 7000); // Each step ~7 seconds
            
            // Show first step as in progress immediately
            setThinkingSteps(prev => prev.map((s, idx) => 
                idx === 0 ? {...s, status: "in_progress"} : s
            ));
            
            // ═══════════════════════════════════════════════════════════════
            // 🔗 CONNECTION: FRONTEND → BACKEND → AI SERVICE (LangGraph)
            // ═══════════════════════════════════════════════════════════════
            // STEP 1: Frontend sends travel query to Backend (Node.js)
            // STEP 2: Backend forwards to AI Service (Python FastAPI)
            // STEP 3: AI Service runs LangGraph 8-node workflow:
            //         → Destination → Transport → Accommodation → Activities
            //         → Food/Shopping → Requirements → Emergency → Package Builder
            // 
            // 📌 Backend endpoint: Backend/routes/tools.js → POST /travel-planner
            // 📌 AI endpoint: AI/agent_service.py → (routes to travel_graph)
            // 📌 LangGraph: AI/travel_graph.py → run_travel_planner()
            // ═══════════════════════════════════════════════════════════════
            const response = await fetch(`${API_URL}/api/travel-planner`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    query: queryText,
                    thread_id: currThreadId  // 🆕 Save to chat history
                })
            });
            
            // Stop the step simulation
            clearInterval(stepInterval);
            
            const data = await response.json();

            if(!response.ok || data.error) {
                const msg = typeof data.error === "string" 
                    ? data.error 
                    : typeof data.detail === "string"
                        ? data.detail
                        : "Travel planning failed. Please try again.";
                setPrevChats(prev => [...prev, {role: "assistant", content: msg}]);
                setThinkingSteps([]);
                setSmartIntent(null);
                return;
            }

            // Mark all steps as complete
            setThinkingSteps(prev => prev.map(s => ({...s, status: "complete"})));
            
            // Small delay to show the completed steps
            await new Promise(resolve => setTimeout(resolve, 500));

            // Use the final_summary from the backend
            let fullResponse = data.final_summary || "Travel planning complete.";

            setPrevChats(prev => [...prev, {role: "assistant", content: fullResponse}]);
            setReply(fullResponse);
            
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: "Travel planning failed: network error"}]);
        } finally {
            setTravelPlanning(false);
            setThinkingSteps([]);
            setSmartIntent(null);
        }
    }

    // 🆕 Solo Trip Planner with Human-in-the-Loop
    const performSoloTrip = async (queryText) => {
        if(!queryText) {
            setPrevChats(prev => [...prev, {role: "assistant", content: "Type a solo trip query (e.g., 'Plan a solo trip from Delhi to Goa')"}]);
            return;
        }

        // Clear input immediately
        setPrompt("");
        
        // Show user's query
        setPrevChats(prev => [...prev, {role: "user", content: queryText}]);
        
        // Initial thinking steps (Phase 1: Auto research)
        const initialSteps = [
            {step: "destination_research", status: "pending", label: "📍 Destination Research"},
            {step: "transport_discovery", status: "pending", label: "🚗 Transport Options"}
        ];
        
        setThinkingSteps(initialSteps);
        setSmartIntent("SOLO_TRIP");

        try {
            setSoloTripPlanning(true);
            
            // Animate first step
            setThinkingSteps(prev => prev.map((s, idx) => 
                idx === 0 ? {...s, status: "in_progress"} : s
            ));
            
            // Start solo trip planning (will pause at preferences)
            // 📌 Pass currThreadId so it saves to chat history!
            const response = await fetch(`${API_URL}/api/solo-trip/start`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    query: queryText,
                    thread_id: currThreadId,  // 🆕 Save to this thread
                    user_id: userId || "default"  // 🆕 User isolation
                })
            });
            
            const data = await response.json();
            
            if(!response.ok || data.error) {
                throw new Error(data.error || data.detail || "Failed to start solo trip");
            }
            
            // Mark steps as complete
            setThinkingSteps(prev => prev.map(s => ({...s, status: "complete"})));
            
            // Check if we need human input (HITL interrupt)
            if(data.status === "awaiting_input") {
                // Save thread ID for resume (langgraph thread)
                setSoloTripThreadId(data.thread_id);
                
                // Save trip info for modal (including chat_thread_id for MongoDB)
                setSoloTripInfo({
                    origin: data.origin,
                    destination: data.destination,
                    distance_km: data.distance_km,
                    destination_info: data.destination_info,
                    transport_options: data.transport_options,
                    chat_thread_id: data.chat_thread_id  // 🆕 MongoDB thread ID
                });
                
                // Show info message
                setPrevChats(prev => [...prev, {
                    role: "assistant", 
                    content: `🎒 **Solo Trip Research Complete!**\n\n` +
                        `**Route:** ${data.origin} → ${data.destination}\n` +
                        `**Distance:** ${data.distance_km} km\n\n` +
                        `${data.destination_info || ''}\n\n` +
                        `---\n\n` +
                        `**Now I need your preferences to personalize the trip!**\n\n` +
                        `Please fill out the form to continue...`
                }]);
                
                // Clear thinking steps before showing modal
                setThinkingSteps([]);
                
                // Show the preferences modal
                setTimeout(() => {
                    setShowPreferencesModal(true);
                }, 500);
                
            } else if(data.status === "complete") {
                // Unlikely on start, but handle it
                setPrevChats(prev => [...prev, {role: "assistant", content: data.final_package || "Trip planned!"}]);
                setThinkingSteps([]);
            }
            
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: `Solo trip failed: ${err.message}`}]);
            setThinkingSteps([]);
        } finally {
            setSoloTripPlanning(false);
        }
    };
    
    // Resume Solo Trip with user preferences
    const handleSoloTripPreferences = async (preferences) => {
        setShowPreferencesModal(false);
        
        // Show remaining steps
        const remainingSteps = [
            {step: "personalized_transport", status: "pending", label: "🚗 Personalized Transport"},
            {step: "accommodation", status: "pending", label: "🏨 Accommodation"},
            {step: "activities", status: "pending", label: "🎯 Activities"},
            {step: "food_guide", status: "pending", label: "🍽️ Food Guide"},
            {step: "requirements", status: "pending", label: "📋 Requirements"},
            {step: "emergency", status: "pending", label: "🆘 Emergency Info"},
            {step: "package_builder", status: "pending", label: "📦 Package Builder"}
        ];
        
        setThinkingSteps(remainingSteps);
        setSmartIntent("SOLO_TRIP");
        setSoloTripPlanning(true);
        
        // Animate step progression
        let stepIndex = 0;
        const maxAutoSteps = remainingSteps.length - 1;
        const stepInterval = setInterval(() => {
            if(stepIndex < maxAutoSteps) {
                setThinkingSteps(prev => prev.map((s, idx) => {
                    if(idx < stepIndex) return {...s, status: "complete"};
                    if(idx === stepIndex) return {...s, status: "in_progress"};
                    return s;
                }));
                stepIndex++;
            } else if(stepIndex === maxAutoSteps) {
                setThinkingSteps(prev => prev.map((s, idx) => {
                    if(idx < maxAutoSteps) return {...s, status: "complete"};
                    if(idx === maxAutoSteps) return {...s, status: "in_progress"};
                    return s;
                }));
                stepIndex++;
            }
        }, 4000);
        
        // Start first step immediately
        setThinkingSteps(prev => prev.map((s, idx) => 
            idx === 0 ? {...s, status: "in_progress"} : s
        ));
        
        try {
            // Resume with preferences
            // 📌 Use chat_thread_id from start response (handles new chats!)
            const chatThreadId = soloTripInfo?.chat_thread_id || currThreadId;
            const response = await fetch(`${API_URL}/api/solo-trip/resume`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    thread_id: soloTripThreadId,
                    chat_thread_id: chatThreadId,  // 🆕 Use saved thread ID
                    preferences: preferences
                })
            });
            
            clearInterval(stepInterval);
            
            const data = await response.json();
            
            if(!response.ok || data.error) {
                throw new Error(data.error || data.detail || "Failed to resume solo trip");
            }
            
            // Mark all steps complete
            setThinkingSteps(prev => prev.map(s => ({...s, status: "complete"})));
            
            // Small delay to show completed steps
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Show final package
            setPrevChats(prev => [...prev, {
                role: "assistant", 
                content: data.final_package || "Solo trip planning complete!"
            }]);
            
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: `Solo trip resume failed: ${err.message}`}]);
        } finally {
            setSoloTripPlanning(false);
            setThinkingSteps([]);
            setSmartIntent(null);
            setSoloTripThreadId(null);
            setSoloTripInfo(null);
        }
    };

    // Voice capture + STT
    const handleVoiceToggle = async () => {
        if(isRecording) {
            if(recordTimeoutRef.current) {
                clearTimeout(recordTimeoutRef.current);
                recordTimeoutRef.current = null;
            }
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({audio: true});
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if(event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                if(recordTimeoutRef.current) {
                    clearTimeout(recordTimeoutRef.current);
                    recordTimeoutRef.current = null;
                }
                // If nothing was captured, bail early with user feedback.
                if(!audioChunksRef.current.length) {
                    setPrevChats(prev => [...prev, {role: "assistant", content: "No audio captured. Please try again."}]);
                    return;
                }
                stream.getTracks().forEach(t => t.stop());
                const blob = new Blob(audioChunksRef.current, {type: "audio/webm"});
                const formData = new FormData();
                formData.append("audio", blob, "input.webm");
                const browserLang = (navigator.language || "").split("-")[0];
                if(browserLang) {
                    formData.append("language", browserLang);
                }

                try {
                    // ═══════════════════════════════════════════════════════════════
                    // 🔗 CONNECTION: FRONTEND → BACKEND → AI SERVICE
                    // ═══════════════════════════════════════════════════════════════
                    // STEP 1: Frontend sends audio blob to Backend (Node.js)
                    // STEP 2: Backend forwards to AI Service (Python FastAPI)
                    // STEP 3: AI Service sends to OpenAI Whisper API → Returns text
                    // 
                    // 📌 Backend endpoint: Backend/routes/tools.js → POST /stt
                    // 📌 AI endpoint: AI/tools_service.py → transcribe_audio()
                    // ═══════════════════════════════════════════════════════════════
                    const response = await fetch(`${API_URL}/api/stt`, {method: "POST", body: formData});
                    const data = await response.json();
                    if(!response.ok) {
                        setPrevChats(prev => [...prev, {role: "assistant", content: `Transcription failed: ${data.error || "error"}`}]);
                        return;
                    }
                    const text = (data.text || "").trim();
                    if(!text) {
                        setPrevChats(prev => [...prev, {role: "assistant", content: "Didn't catch that. Please speak again."}]);
                        return;
                    }
                    setPrompt(text);
                    // Auto-send even short phrases; user can stop response if needed.
                    await getReply(text);
                } catch(err) {
                    console.log(err);
                    setPrevChats(prev => [...prev, {role: "assistant", content: "Transcription failed: network error"}]);
                }
            };

            mediaRecorder.start();
            setIsRecording(true);
            // Auto-stop after 10 seconds to avoid hanging recordings.
            recordTimeoutRef.current = setTimeout(() => {
                if(mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
                    mediaRecorderRef.current.stop();
                }
            }, 10000);
        } catch(err) {
            console.log(err);
            setPrevChats(prev => [...prev, {role: "assistant", content: "Mic permission denied or unavailable."}]);
        }
    }

    return (
        <div className="chatWindow">
            <div className="navbar">
                <span>SigmaGPT <i className="fa-solid fa-chevron-down"></i></span>
            </div>
            {ragMode && pdfName && (
                <div className="fileChip">
                    <i className="fa-solid fa-file-pdf"></i> {pdfName}
                    <span className="chipHint">Ask about this PDF</span>
                </div>
            )}
            
            {/* 🆕 Stock Mode Indicator */}
            {stockMode && !stockResearching && (
                <div className="fileChip stockChip">
                    <i className="fa-solid fa-chart-line"></i> Stock Research Mode
                    <span className="chipHint">Type a stock query (e.g., "Tata Motors stock")</span>
                </div>
            )}
            
            {/* 🆕 Travel Mode Indicator */}
            {travelMode && !travelPlanning && (
                <div className="fileChip travelChip">
                    <i className="fa-solid fa-plane"></i> Travel Planner Mode
                    <span className="chipHint">Type a travel query (e.g., "Plan trip to Goa from Mumbai")</span>
                </div>
            )}
            
            {/* 🆕 Solo Trip Mode Indicator */}
            {soloTripMode && !soloTripPlanning && (
                <div className="fileChip soloTripChip">
                    <i className="fa-solid fa-person-hiking"></i> Solo Trip Planner (HITL)
                    <span className="chipHint">Type a solo trip query (e.g., "Plan a solo trip from Delhi to Goa")</span>
                </div>
            )}
            
            <Chat></Chat>
            
            {/* 🆕 Smart AI Intent Display - Shows what the AI detected */}
            {loading && smartIntent && (
                <div className="smartIntentChip">
                    <span className="intentIcon">
                        {smartIntent === "STOCK" && "📈"}
                        {smartIntent === "TRAVEL" && "🧳"}
                        {smartIntent === "WEATHER" && "🌤️"}
                        {smartIntent === "NEWS" && "📰"}
                        {smartIntent === "CURRENT_INFO" && "🔍"}
                        {smartIntent === "GENERAL" && "💬"}
                        {smartIntent === "GENERAL_FALLBACK" && "🔄"}
                    </span>
                    <span className="intentText">
                        {smartIntent === "STOCK" && "Stock query detected - analyzing..."}
                        {smartIntent === "TRAVEL" && "Travel query detected - planning trip..."}
                        {smartIntent === "WEATHER" && "Weather query - fetching..."}
                        {smartIntent === "NEWS" && "News query - searching..."}
                        {smartIntent === "CURRENT_INFO" && "Searching for current info..."}
                        {smartIntent === "GENERAL" && "Processing with AI..."}
                        {smartIntent === "GENERAL_FALLBACK" && "Searching web for latest info..."}
                    </span>
                </div>
            )}
            
            {/* 🆕 Trip Preferences Modal - Human-in-the-Loop */}
            <TripPreferencesModal 
                isOpen={showPreferencesModal}
                tripInfo={soloTripInfo}
                onSubmit={handleSoloTripPreferences}
                onClose={() => setShowPreferencesModal(false)}
            />
            
            {/* 🆕 Thinking Steps UI - Shows BELOW chat messages during LangGraph execution */}
            {thinkingSteps.length > 0 && (
                <div className="thinkingSteps">
                    <div className="thinkingHeader">
                        <i className="fa-solid fa-brain"></i> 
                        {smartIntent === "STOCK" ? " LangGraph Stock Research" : 
                         smartIntent === "TRAVEL" ? " LangGraph Travel Planner" :
                         smartIntent === "SOLO_TRIP" ? " Solo Trip Planner (HITL)" : 
                         " Smart AI Workflow"}
                    </div>
                    {thinkingSteps.map((step, index) => (
                        <div 
                            key={step.step} 
                            className={`thinkingStep ${step.status}`}
                        >
                            <span className="stepIcon">
                                {step.status === "pending" && <i className="fa-regular fa-circle"></i>}
                                {step.status === "in_progress" && <i className="fa-solid fa-spinner fa-spin"></i>}
                                {step.status === "complete" && <i className="fa-solid fa-check-circle"></i>}
                            </span>
                            <span className="stepLabel">{step.label}</span>
                        </div>
                    ))}
                </div>
            )}

            <div className="chatInput">
                <div className="inputBox">
                    {/* Hidden file inputs wired to the + menu */}
                    <input
                        type="file"
                        accept="application/pdf"
                        ref={fileInputRef}
                        style={{display: "none"}}
                        onChange={handlePdfUpload}
                    />
                    <input
                        type="file"
                        accept="image/*"
                        ref={imageInputRef}
                        style={{display: "none"}}
                        onChange={handleImageUpload}
                    />
                    <div className="inputToolbar">
                        <button
                            className={`iconBtn ${showUploadMenu ? "active" : ""}`}
                            onClick={toggleUploadMenu}
                            disabled={uploading || imageUploading}
                            title="Upload file"
                            ref={uploadButtonRef}
                        >
                            {(uploading || imageUploading) ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-plus"></i>}
                        </button>
                        {showUploadMenu && (
                            <div className="uploadMenu" ref={uploadMenuRef}>
                                <button
                                    className="menuItem"
                                    onClick={handlePdfClick}
                                    disabled={uploading}
                                >
                                    <i className="fa-solid fa-file-pdf"></i> Upload PDF
                                </button>
                                <button
                                    className="menuItem"
                                    onClick={handleImageClick}
                                    disabled={imageUploading}
                                >
                                    <i className="fa-solid fa-image"></i> Upload Image (OCR)
                                </button>
                            </div>
                        )}
                        <button
                            className={`iconBtn ${searchMode ? "active" : ""}`}
                            onClick={toggleSearchMode}
                            disabled={searching}
                            title="Web search (click to arm, then type and send)"
                        >
                            {searching ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-globe"></i>}
                        </button>
                        {/* 🆕 Stock Research Button */}
                        <button
                            className={`iconBtn ${stockMode ? "active" : ""}`}
                            onClick={toggleStockMode}
                            disabled={stockResearching || travelPlanning}
                            title="Stock Research (LangGraph - click to arm, then type stock query)"
                        >
                            {stockResearching ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-chart-line"></i>}
                        </button>
                        {/* 🆕 Travel Planner Button */}
                        <button
                            className={`iconBtn ${travelMode ? "active" : ""}`}
                            onClick={toggleTravelMode}
                            disabled={travelPlanning || stockResearching || soloTripPlanning}
                            title="Travel Planner (LangGraph - click to arm, then type travel query)"
                        >
                            {travelPlanning ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-plane"></i>}
                        </button>
                        {/* 🆕 Solo Trip Button (Human-in-the-Loop) */}
                        <button
                            className={`iconBtn ${soloTripMode ? "active" : ""}`}
                            onClick={() => setSoloTripMode(!soloTripMode)}
                            disabled={travelPlanning || stockResearching || soloTripPlanning}
                            title="Solo Trip Planner with Human-in-the-Loop (EV charging, food preferences)"
                        >
                            {soloTripPlanning ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-person-hiking"></i>}
                        </button>
                    </div>
                    <input placeholder="Ask anything"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        onKeyDown={handleInputKeyDown}
                    >
                           
                    </input>
                    <div className="rightControls">
                        {loading && <ScaleLoader color="#fff" height={20} width={4} />}
                        <button
                            className={`iconBtn micBtn ${isRecording ? "active" : ""}`}
                            onClick={handleVoiceToggle}
                            title={isRecording ? "Stop recording" : "Voice input"}
                        >
                            {isRecording ? <i className="fa-solid fa-stop"></i> : <i className="fa-solid fa-microphone"></i>}
                        </button>
                        <button
                            type="button"
                            id="submit"
                            onClick={() => getReply()}
                            title={loading ? "Stop response" : "Send"}
                            className={loading ? "stop" : ""}
                        >
                            <i className={`fa-solid ${loading ? "fa-stop" : "fa-paper-plane"}`}></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ChatWindow;
