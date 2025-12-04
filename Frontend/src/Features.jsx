import { useState } from "react";
import "./Features.css";

const featureList = [
  // ========== CORE AI FEATURES ==========
  { 
    title: "Deep Retrieval Q&A", 
    desc: "Ask grounded questions on your PDFs with page-aware citations and chunked indexing using Qdrant vector DB." 
  },
  { 
    title: "Live Web Agent", 
    desc: "On-demand web search with Tavily AI-optimized search. Memory persists for your session to keep answers fresh." 
  },
  { 
    title: "Smart Intent Detection", 
    desc: "AI automatically detects your intent (stock research, travel planning, news, weather) and routes to specialized workflows." 
  },
  
  // ========== STOCK RESEARCH (7-NODE LANGGRAPH) ==========
  { 
    title: "Stock Research Workflow", 
    desc: "7-node LangGraph workflow: Company Intro → Sector Analysis → Financials → Policy → Sentiment → Technical Analysis → Investment Suggestion." 
  },
  { 
    title: "Risk Sentinel (RSI & News Shield)", 
    desc: "Technical analysis with RSI overbought/oversold detection. Scans for negative news (fraud, scam) and issues strict AVOID warnings." 
  },
  { 
    title: "Trusted Financial Sources", 
    desc: "Stock data only from MoneyControl, Screener.in, Economic Times, LiveMint - no random blogs or speculation." 
  },
  
  // ========== TRAVEL PLANNER (8-NODE LANGGRAPH) ==========
  { 
    title: "Travel Planner Workflow", 
    desc: "8-node LangGraph: Destination → Transport → Hotels → Activities → Food → Requirements → Emergency → 3 Package Options." 
  },
  { 
    title: "Solo Trip Planner (HITL)", 
    desc: "Human-in-the-Loop: AI pauses to ask preferences (EV/petrol, veg/non-veg, budget), then creates personalized itinerary with charging stops." 
  },
  
  // ========== MULTIMODAL INPUT ==========
  { 
    title: "Voice Input (Whisper STT)", 
    desc: "Hands-free prompts with OpenAI Whisper transcription. Built-in recorder with auto-stop (60s max). Auto-detects language." 
  },
  { 
    title: "Image OCR with ₹ Guard", 
    desc: "Upload screenshots or receipts. Smart extraction with Hindi+English support and Rupee symbol correction." 
  },
  { 
    title: "PDF Upload & RAG", 
    desc: "Smart extraction with OCR fallback for scanned pages. Auto-chunking for RAG with Qdrant storage." 
  },
  
  // ========== CHAT & MEMORY ==========
  { 
    title: "Threaded Chat History", 
    desc: "Organize conversations into threads. Rename, delete, revisit old chats anytime. Each thread maintains its own context." 
  },
  { 
    title: "LangGraph Checkpointer", 
    desc: "All tool results saved to MongoDB. Ask follow-up questions about previous searches seamlessly." 
  },
  
  // ========== OUTPUT & UX ==========
  { 
    title: "Markdown Smart Replies", 
    desc: "Readable answers with tables, code highlighting, bullet points, and animated typing effect." 
  },
  { 
    title: "Thinking Steps Animation", 
    desc: "See AI's progress through each node (Sector Analysis → Company Research → ...) with spinning icons." 
  },
  
  // ========== TOOLS ==========
  { 
    title: "Weather & News Search", 
    desc: "Get current weather for any city. Tavily-powered news search with DuckDuckGo fallback for latest headlines." 
  },
  { 
    title: "Calculator Tool", 
    desc: "Perform mathematical calculations directly in chat. Handles complex expressions." 
  },
  
  // ========== UI/UX ==========
  { 
    title: "Theme Flex & Responsive Design", 
    desc: "Switch between Black and Light Cream themes. Collapsible sidebar with hover effects and active thread highlighting." 
  },
];

function Features() {
  // First 3 cards expanded by default (one full row for symmetry)
  const [expandedCards, setExpandedCards] = useState([0, 1, 2]);

  const toggleCard = (index) => {
    setExpandedCards(prev => 
      prev.includes(index) 
        ? prev.filter(i => i !== index)  // Collapse
        : [...prev, index]                // Expand
    );
  };

  const expandAll = () => {
    setExpandedCards(featureList.map((_, idx) => idx));
  };

  const collapseAll = () => {
    setExpandedCards([]);
  };

  return (
    <div className="pageShell">
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Explore</p>
          <h1>Features</h1>
          <p className="lede">Everything Sigma GPT can do. Click to expand.</p>
        </div>
        <div className="headerActions">
          <button className="actionBtn" onClick={expandAll}>
            <i className="fa-solid fa-expand"></i> Expand All
          </button>
          <button className="actionBtn" onClick={collapseAll}>
            <i className="fa-solid fa-compress"></i> Collapse All
          </button>
        </div>
      </header>
      <div className="grid">
        {featureList.map((item, idx) => {
          const isExpanded = expandedCards.includes(idx);
          return (
            <div 
              className={`card ${isExpanded ? 'expanded' : 'collapsed'}`} 
              key={idx}
              onClick={() => toggleCard(idx)}
            >
              <div className="cardHeader">
                <div className="badge">{String(idx + 1).padStart(2, "0")}</div>
                <h3>{item.title}</h3>
                <span className="toggleIcon">
                  {isExpanded ? (
                    <i className="fa-solid fa-chevron-up"></i>
                  ) : (
                    <i className="fa-solid fa-chevron-down"></i>
                  )}
                </span>
              </div>
              <div className={`cardContent ${isExpanded ? 'show' : 'hide'}`}>
                <p>{item.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default Features;
