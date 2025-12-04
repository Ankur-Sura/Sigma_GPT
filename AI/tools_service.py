"""
===================================================================================
            TOOLS_SERVICE.PY - Additional AI Tools (STT, OCR, Search)
===================================================================================

📚 WHAT ARE THESE TOOLS?
------------------------
This file contains helper tools that extend our AI capabilities:

1. STT (Speech-to-Text): Convert audio to text using OpenAI Whisper
2. OCR (Optical Character Recognition): Extract text from images
3. Search: Simple web search helper
4. 🆕 TAVILY SEARCH: AI-optimized web search (like ChatGPT uses Bing!)
5. 🆕 INDIAN STOCK NEWS: Specialized search for MoneyControl, Screener, ET
6. 🆕 WEATHER: Get current weather for any city
7. 🆕 DATE/TIME: Get current date and time

These are NOT agents - they're direct tool endpoints that the frontend can call.
PLUS: These tools can be used BY the agent in agent_service.py!

===================================================================================
                            ARCHITECTURE
===================================================================================

    Frontend (React)
         │
         ├── User records audio → calls /stt/transcribe → gets text
         │
         ├── User uploads image → calls /ocr/image → gets text
         │
         ├── User wants quick search → calls /search → gets results
         │
         └── User clicks "Web Search" toggle → Agent uses Tavily/DuckDuckGo
                    │
                    └── Agent can also use specialized tools:
                        - indian_stock_news (for share market)
                        - get_weather (for weather queries)
                        - get_current_datetime (for date/time)

===================================================================================
                    🆕 TAVILY VS DUCKDUCKGO (WHY WE USE BOTH)
===================================================================================

📌 TAVILY (Primary - AI Optimized)
----------------------------------
✔ Built specifically for AI agents (not humans)
✔ Returns CLEAN text, not just snippets
✔ Can read full page content
✔ Better for complex queries
✔ FREE: 1,000 searches/month

📌 DUCKDUCKGO (Backup - Unlimited Free)
----------------------------------------
✔ No API key needed
✔ Unlimited free searches
✔ Returns instant answers (Wikipedia, etc.)
✔ Good for simple factual queries

📌 OUR STRATEGY:
---------------
1. Try Tavily first (better quality)
2. If Tavily fails or quota exceeded → Fall back to DuckDuckGo
3. Always return something useful to the user!

🔗 THIS IS HOW CHATGPT'S "BROWSE WITH BING" WORKS:
    - ChatGPT uses Bing Search API (similar to Tavily)
    - It fetches pages, reads content, summarizes
    - We're doing the same thing!

===================================================================================
"""

# =============================================================================
#                           IMPORTS SECTION
# =============================================================================

# ----- Standard Library Imports -----
import io           # For handling byte streams (audio files)
import os           # For environment variables
import json         # For JSON parsing
import mimetypes    # For guessing file types
from io import BytesIO
from datetime import datetime  # For get_current_datetime tool
from typing import Optional, Dict, List, Any

# ----- Load Environment Variables FIRST -----
from dotenv import load_dotenv
load_dotenv()
"""
📖 Why load_dotenv() here?
--------------------------
We need to load environment variables BEFORE creating any clients.
Otherwise, OpenAI client will fail because OPENAI_API_KEY isn't set yet.

🔗 In your notes, you always had this at the top:
    from dotenv import load_dotenv
    load_dotenv()
"""

# ----- Third-Party Imports -----
import requests     # For HTTP requests (web search, weather)

# ----- Tavily Search (AI-Optimized Search like ChatGPT uses Bing) -----
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TavilyClient = None
    TAVILY_AVAILABLE = False
"""
📖 What is Tavily?
------------------
From the 'tavily-python' library (pip install tavily-python).

✔ Search engine built SPECIFICALLY for AI agents
✔ Returns clean, structured results
✔ Can extract full page content (not just snippets)
✔ Better than Google for AI applications
✔ FREE: 1,000 searches/month

🔗 THIS IS SIMILAR TO WHAT CHATGPT USES (Bing Search)!

📌 Why we check TAVILY_AVAILABLE:
- If user hasn't installed tavily-python, we fall back to DuckDuckGo
- Graceful degradation = app still works!
"""

# ----- Exa.ai Search (Secondary - AI-Powered) -----
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    Exa = None
    EXA_AVAILABLE = False
"""
📖 What is Exa.ai Search?
--------------------------
From the 'exa_py' library (pip install exa_py).

✔ AI-powered semantic search
✔ Better understanding of queries
✔ High-quality curated results
✔ Great for research & complex queries

📌 We use this as SECONDARY search after Tavily!
"""

# ----- DuckDuckGo Search (Tertiary Backup - Unlimited Free) -----
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS = None
    DDGS_AVAILABLE = False
"""
📖 What is DuckDuckGo Search?
-----------------------------
From the 'duckduckgo-search' library (pip install duckduckgo-search).

✔ No API key required!
✔ Unlimited free searches
✔ Privacy-focused
✔ Returns web results, news, images

📌 We use this as TERTIARY BACKUP when both Tavily and Exa fail.
"""

# ----- FastAPI Imports -----
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from typing import Optional

# ----- OpenAI Import (for Whisper STT) -----
from openai import OpenAI
"""
📖 What is Whisper?
-------------------
Whisper is OpenAI's speech-to-text model.

✔ Converts audio to text
✔ Supports many languages
✔ Very accurate
✔ Available through OpenAI API as whisper-1

📌 How it works:
    Audio File (mp3/wav/webm) → Whisper API → Text
"""

# ----- OCR Imports (Optional) -----
try:
    from PIL import Image, ImageOps, ImageFilter
    import numpy as np
except Exception:
    Image = None
    ImageOps = None
    ImageFilter = None
    np = None

# EasyOCR - Pure Python OCR (works on Render free tier!)
# 🆕 FULLY LAZY LOADING - Don't import at startup to avoid blocking server start
_easyocr_reader = None
_easyocr_available = None  # None = not checked yet

def get_easyocr_reader():
    """Lazy load EasyOCR only when first needed"""
    global _easyocr_reader, _easyocr_available
    
    # First time check
    if _easyocr_available is None:
        try:
            import easyocr
            _easyocr_available = True
            print("✅ EasyOCR module available")
        except Exception as e:
            print(f"⚠️ EasyOCR not available: {e}")
            _easyocr_available = False
            return None
    
    if not _easyocr_available:
        return None
    
    # Initialize reader on first use
    if _easyocr_reader is None:
        try:
            import easyocr
            print("🔤 Initializing EasyOCR (first use, may take 30-60 seconds)...")
            _easyocr_reader = easyocr.Reader(['en'], gpu=False)  # CPU mode for Render
            print("✅ EasyOCR initialized")
        except Exception as e:
            print(f"⚠️ EasyOCR initialization failed: {e}")
            _easyocr_available = False
            return None
    
    return _easyocr_reader

# For checking if easyocr is available without initializing
def is_easyocr_available():
    global _easyocr_available
    if _easyocr_available is None:
        try:
            import easyocr
            _easyocr_available = True
        except:
            _easyocr_available = False
    return _easyocr_available

# Tesseract - Fallback OCR (requires system install)
try:
    import pytesseract
except Exception:
    pytesseract = None

"""
📖 OCR Dependencies
-------------------
EasyOCR: Pure Python deep learning OCR - WORKS ON RENDER!
PIL (Pillow): Python Imaging Library for image processing
pytesseract: Fallback - requires Tesseract installed on system
numpy: For numerical operations on image arrays

📌 EasyOCR is the primary OCR engine (no system install needed)
📌 Tesseract is fallback (requires system install)
"""

# =============================================================================
#                     INITIALIZE ROUTER AND CLIENT
# =============================================================================

tools_router = APIRouter(
    prefix="",
    tags=["Tools"]
)
"""
📖 Creating API Router
----------------------
✔ Groups all tool-related routes
✔ Will be included in main app
"""

client = OpenAI()
"""
📖 OpenAI Client
----------------
✔ Used for Whisper STT
✔ Reads API key from environment
"""

# =============================================================================
#                     🆕 TAVILY SEARCH CONFIGURATION
# =============================================================================

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
"""
📖 Tavily API Key
-----------------
Get your FREE key from: https://tavily.com

✔ 1,000 searches/month on free tier
✔ Set in .env file: TAVILY_API_KEY=tvly-xxxxx

📌 If not set, we automatically fall back to DuckDuckGo!
"""

# Initialize Tavily client if available
_tavily_client = None
if TAVILY_AVAILABLE and TAVILY_API_KEY:
    try:
        _tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        print("✅ Tavily Search initialized (AI-optimized search ready!)")
    except Exception as e:
        print(f"⚠️ Tavily initialization failed: {e}")
        _tavily_client = None

if not _tavily_client:
    print("ℹ️ Tavily not available, will use Exa/DuckDuckGo fallback")


# =============================================================================
#                     🆕 EXA.AI CLIENT INITIALIZATION
# =============================================================================
"""
📖 Exa.ai - AI-Powered Search Engine
-------------------------------------
Exa provides semantic search - it understands the meaning of your query,
not just keyword matching. Great for:
- Research queries
- Complex questions
- Finding similar content

Get API key at: https://exa.ai/
Set in .env: EXA_API_KEY=your_key_here
"""

EXA_API_KEY = os.getenv("EXA_API_KEY", "")
_exa_client = None

if EXA_AVAILABLE and EXA_API_KEY:
    try:
        _exa_client = Exa(EXA_API_KEY)
        print("✅ Exa.ai Search initialized (AI-powered semantic search ready!)")
    except Exception as e:
        print(f"⚠️ Exa.ai initialization failed: {e}")
        _exa_client = None

if not _exa_client:
    print("ℹ️ Exa.ai not configured, DuckDuckGo will be tertiary fallback")


# =============================================================================
#                     🆕 INDIAN STOCK MARKET WEBSITES
# =============================================================================
"""
📚 TRUSTED INDIAN FINANCIAL WEBSITES
------------------------------------
When user asks about Indian stocks, we search ONLY these trusted sites.
This prevents random blog spam and ensures authentic financial data.

🔗 Why these specific sites?
----------------------------
1. MoneyControl.com - India's #1 financial portal
   - Real-time stock prices
   - Company news
   - Financial statements
   
2. Screener.in - Best for pure financial data
   - Quarterly results
   - Ratios (PE, ROE, etc.)
   - 10-year historical data
   
3. EconomicTimes - News + Market analysis
   - Market news
   - Expert opinions
   - Policy updates
   
4. LiveMint - Quality business journalism
   - In-depth analysis
   - Policy impact
   - Global context
"""

INDIAN_FINANCE_SITES = [
    "moneycontrol.com",
    "screener.in", 
    "economictimes.indiatimes.com",
    "livemint.com"
]

def _build_site_filter(sites: List[str]) -> str:
    """
    📖 Build Site Filter for Search
    --------------------------------
    Creates a search filter to limit results to specific websites.
    
    Example:
        _build_site_filter(["moneycontrol.com", "screener.in"])
        Returns: "site:moneycontrol.com OR site:screener.in"
    
    📌 This is standard search operator syntax used by Google, Bing, etc.
    """
    return " OR ".join([f"site:{site}" for site in sites])

# =============================================================================
#                     🆕 TAVILY SEARCH TOOL (Primary)
# =============================================================================

def tavily_search(query: str, max_results: int = 5, search_depth: str = "basic") -> Dict[str, Any]:
    """
    📖 Tavily AI Search - Primary Search Tool
    ==========================================
    
    Uses Tavily's AI-optimized search to find information.
    
    Parameters:
    -----------
    query: What to search for (e.g., "Latest AI news")
    max_results: Number of results to return (1-10)
    search_depth: "basic" (fast) or "advanced" (reads full pages)
    
    Returns:
    --------
    Dict with: query, results (list), source ("tavily"), fetched_at
    
    📌 WHY TAVILY IS BETTER FOR AI:
    ------------------------------
    1. Returns CLEAN text (no ads, no junk)
    2. Can read full page content (not just snippets)
    3. Structured JSON output
    4. Built for LLM consumption
    
    🔗 THIS IS SIMILAR TO CHATGPT'S BING BROWSING:
    - ChatGPT uses Bing API → We use Tavily API
    - Both fetch pages and extract relevant text
    - Both return structured results for AI to process
    
    📌 EXAMPLE:
    ----------
    User: "What's the latest news about OpenAI?"
    
    Tavily returns:
    {
        "results": [
            {
                "title": "OpenAI announces GPT-5",
                "content": "OpenAI has unveiled... (clean full text)",
                "url": "https://..."
            }
        ]
    }
    """
    if not _tavily_client:
        return {"error": "Tavily not configured", "fallback": True}
    
    try:
        # Call Tavily API
        response = _tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,  # "basic" or "advanced"
            include_answer=True,        # Get a direct answer if available
            include_raw_content=False   # Don't include raw HTML
        )
        """
        📖 Tavily search() parameters:
        ------------------------------
        - query: The search query
        - max_results: How many results (default 5)
        - search_depth: 
            "basic" = Fast, returns snippets
            "advanced" = Slower, reads full pages
        - include_answer: If True, Tavily tries to give a direct answer
        - include_raw_content: If True, includes raw HTML (we don't need this)
        
        🔗 From Tavily docs: https://docs.tavily.com
        """
        
        results = []
        for item in response.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),  # Tavily calls it "content"
                "url": item.get("url", ""),
                "score": item.get("score", 0)  # Relevance score
            })
        
        return {
            "query": query,
            "results": results,
            "answer": response.get("answer"),  # Direct answer if available
            "source": "tavily",
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        print(f"⚠️ Tavily search failed: {e}")
        return {"error": str(e), "fallback": True}


# =============================================================================
#                     🆕 EXA.AI SEARCH TOOL (Secondary)
# =============================================================================

def exa_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    📖 Exa.ai Search - AI-Powered Semantic Search
    ==============================================
    
    Uses Exa's semantic search for better understanding of complex queries.
    
    Parameters:
    -----------
    query: What to search for
    max_results: Number of results to return
    
    Returns:
    --------
    Dict with: query, results, source ("exa"), fetched_at
    
    📌 WHEN WE USE EXA:
    ------------------
    1. Tavily fails or quota exceeded
    2. For research-heavy queries
    3. When semantic understanding is needed
    
    📌 ADVANTAGES:
    -------------
    ✔ AI-powered semantic search
    ✔ Understands query intent
    ✔ High-quality curated results
    ✔ Great for research queries
    
    🔗 From: https://docs.exa.ai/
    """
    if not _exa_client:
        return {"error": "Exa.ai not configured", "fallback": True, "results": []}
    
    try:
        # Use Exa's search with auto-prompting for better results
        response = _exa_client.search(
            query,
            num_results=max_results,
            use_autoprompt=True  # Let Exa optimize the query
        )
        
        results = []
        for item in response.results:
            results.append({
                "title": item.title or "No Title",
                "url": item.url,
                "content": item.text[:500] if item.text else "No content available",
                "score": getattr(item, 'score', 0.0)
            })
        
        return {
            "query": query,
            "results": results,
            "source": "exa",
            "fetched_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"⚠️ Exa.ai search failed: {e}")
        return {"error": str(e), "fallback": True, "results": []}


# =============================================================================
#                     🆕 DUCKDUCKGO SEARCH TOOL (Tertiary Backup)
# =============================================================================

def duckduckgo_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    📖 DuckDuckGo Search - Backup Search Tool
    ==========================================
    
    Uses DuckDuckGo for web search when Tavily is unavailable.
    
    Parameters:
    -----------
    query: What to search for
    max_results: Number of results to return
    
    Returns:
    --------
    Dict with: query, results, source ("duckduckgo"), fetched_at
    
    📌 WHEN WE USE DUCKDUCKGO:
    -------------------------
    1. Tavily API key not configured
    2. Tavily quota exceeded (1000/month on free tier)
    3. Tavily API is down
    
    📌 ADVANTAGES:
    -------------
    ✔ No API key required
    ✔ Unlimited free searches
    ✔ Fast response
    
    📌 LIMITATIONS:
    --------------
    ✗ Only returns snippets (not full content)
    ✗ Less optimized for AI
    ✗ May hit rate limits if abused
    
    🔗 From: https://pypi.org/project/duckduckgo-search/
    """
    if not DDGS_AVAILABLE:
        return {"error": "DuckDuckGo search not available", "results": []}
    
    try:
        # Create DuckDuckGo Search instance
        ddgs = DDGS()
        """
        📖 DDGS() - DuckDuckGo Search Class
        -----------------------------------
        Creates a search client.
        
        Methods:
        - .text(query) - Web search
        - .news(query) - News search
        - .images(query) - Image search
        """
        
        # Perform text search
        raw_results = ddgs.text(query, max_results=max_results)
        """
        📖 ddgs.text() parameters:
        --------------------------
        - query: Search query
        - max_results: Number of results
        
        Returns list of dicts with: title, body, href
        """
        
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("body", ""),
                "url": item.get("href", "")
            })
        
        return {
            "query": query,
            "results": results,
            "source": "duckduckgo",
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        print(f"⚠️ DuckDuckGo search failed: {e}")
        return {"error": str(e), "results": []}


# =============================================================================
#                     🆕 UNIFIED WEB SEARCH (Smart Fallback)
# =============================================================================

def smart_web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    📖 Smart Web Search - Uses Best Available Tool
    ===============================================
    
    Tries Tavily → Exa.ai → DuckDuckGo (3-tier fallback).
    
    📌 THE FALLBACK STRATEGY:
    ------------------------
    1. Try Tavily (best quality, AI-optimized)
       ↓ If fails or not configured
    2. Try Exa.ai (semantic search, great for research)
       ↓ If fails or not configured
    3. Try DuckDuckGo (unlimited free)
       ↓ If fails
    4. Return error message
    
    🔗 THIS IS HOW PRODUCTION SYSTEMS WORK!
    - Always have a backup (and a backup for the backup!)
    - Never let the user see a failure if avoidable
    - Graceful degradation
    
    📌 FOR YOUR INTERVIEW:
    ----------------------
    "I implemented a 3-tier fallback strategy: Tavily for AI-optimized
    results, Exa.ai for semantic understanding, and DuckDuckGo as the
    unlimited free fallback. This ensures the user always gets results."
    """
    # Try Tavily first (Primary)
    if _tavily_client:
        result = tavily_search(query, max_results)
        if not result.get("fallback"):
            return result
        print("ℹ️ Tavily failed, trying Exa.ai...")
    
    # Try Exa.ai second (Secondary)
    if _exa_client:
        result = exa_search(query, max_results)
        if not result.get("fallback"):
            return result
        print("ℹ️ Exa.ai failed, falling back to DuckDuckGo...")
    
    # Fall back to DuckDuckGo (Tertiary)
    return duckduckgo_search(query, max_results)


# =============================================================================
#                     🆕 INDIAN STOCK NEWS SEARCH
# =============================================================================

def indian_stock_search(
    query: str, 
    max_results: int = 5,
    include_quarterly: bool = True
) -> Dict[str, Any]:
    """
    📖 Indian Stock Market Search - Specialized Tool
    ================================================
    
    Searches ONLY trusted Indian financial websites for stock information.
    
    Parameters:
    -----------
    query: Stock name or topic (e.g., "Tata Motors quarterly results")
    max_results: Number of results
    include_quarterly: If True, adds "quarterly results" to search
    
    Returns:
    --------
    Dict with results from MoneyControl, Screener, ET, LiveMint
    
    📌 WHY THIS IS SPECIAL:
    ----------------------
    Normal search: Returns random blogs, outdated articles, spam
    This search: Returns ONLY from trusted financial sources
    
    📌 HOW IT WORKS:
    ---------------
    1. Takes query like "Tata Motors"
    2. Builds filter: "site:moneycontrol.com OR site:screener.in ..."
    3. Combines: "Tata Motors site:moneycontrol.com OR site:screener.in"
    4. Searches → Gets results only from these sites
    
    📌 TRUSTED SITES:
    ----------------
    1. moneycontrol.com - Real-time prices, news
    2. screener.in - Financial statements, ratios
    3. economictimes.indiatimes.com - Market news
    4. livemint.com - Analysis, policy impact
    
    🔗 FOR YOUR INTERVIEW:
    ----------------------
    "To ensure users get authentic financial data, I implemented a
    specialized search tool that filters results to only trusted
    Indian financial websites like MoneyControl and Screener.in,
    preventing misinformation from random blogs."
    """
    # Build the specialized query with site filters
    site_filter = _build_site_filter(INDIAN_FINANCE_SITES)
    
    # Enhance query for better results
    enhanced_query = query
    if include_quarterly and "quarterly" not in query.lower():
        enhanced_query = f"{query} latest news financials"
    
    # Combine query with site filter
    full_query = f"{enhanced_query} {site_filter}"
    
    print(f"🔍 Indian Stock Search: {full_query}")
    
    # Use our smart search with the filtered query
    result = smart_web_search(full_query, max_results)
    result["specialized"] = True
    result["filter_sites"] = INDIAN_FINANCE_SITES
    result["original_query"] = query
    
    return result


# =============================================================================
#                     🆕 WEATHER TOOL
# =============================================================================

def get_weather(city: str) -> Dict[str, Any]:
    """
    📖 Weather Tool - Get Current Weather
    =====================================
    
    Gets current weather for any city using wttr.in (free, no API key).
    
    Parameters:
    -----------
    city: City name (e.g., "Mumbai", "New York", "London")
    
    Returns:
    --------
    Dict with: city, weather, temperature, feels_like, humidity
    
    📌 WHY wttr.in?
    --------------
    ✔ No API key required
    ✔ Free and unlimited
    ✔ Simple to use
    ✔ Returns both text and JSON
    
    🔗 In your notes (03-Agents/main.py), you had:
        def get_weather(city: str):
            url = f"https://wttr.in/{city}?format=%C+%t"
            response = requests.get(url)
            ...
    
    SAME PATTERN! We're just enhancing it.
    
    📌 FOR THE AGENT:
    ----------------
    When user asks "What's the weather in Delhi?",
    the agent calls this tool and gets structured data.
    """
    try:
        # Get detailed weather as JSON
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=10, headers={"User-Agent": "SigmaGPT"})
        
        if response.status_code != 200:
            # Fallback to simple format
            simple_url = f"https://wttr.in/{city}?format=%C+%t"
            simple_response = requests.get(simple_url, timeout=10)
            return {
                "city": city,
                "weather": simple_response.text.strip(),
                "source": "wttr.in"
            }
        
        data = response.json()
        current = data.get("current_condition", [{}])[0]
        
        return {
            "city": city,
            "weather": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
            "temperature_c": current.get("temp_C", "N/A"),
            "temperature_f": current.get("temp_F", "N/A"),
            "feels_like_c": current.get("FeelsLikeC", "N/A"),
            "humidity": current.get("humidity", "N/A") + "%",
            "wind_speed": current.get("windspeedKmph", "N/A") + " km/h",
            "source": "wttr.in",
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {"city": city, "error": str(e)}


# =============================================================================
#                     🆕 DATE/TIME TOOL
# =============================================================================

def get_current_datetime() -> Dict[str, Any]:
    """
    📖 Date/Time Tool - Get Current Date and Time
    ==============================================
    
    Returns the current date and time in various formats.
    
    📌 WHY THIS IS NEEDED:
    ---------------------
    LLMs don't know the current date!
    Their training data has a cutoff date.
    
    When user asks: "What day is it?" or "Is the market open today?"
    The agent needs to call this tool to get accurate info.
    
    📌 FOR POLICY CHECKS:
    --------------------
    In your stock research workflow, you want to check:
    "Any policy changes in the last 30 days affecting this company?"
    
    The agent needs to know today's date to search appropriately.
    
    Returns:
    --------
    {
        "date": "2024-11-30",
        "time": "14:30:00",
        "day": "Saturday",
        "formatted": "Saturday, November 30, 2024",
        "iso": "2024-11-30T14:30:00+05:30"
    }
    """
    now = datetime.now().astimezone()
    
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day": now.strftime("%A"),
        "month": now.strftime("%B"),
        "year": now.strftime("%Y"),
        "formatted": now.strftime("%A, %B %d, %Y"),
        "formatted_with_time": now.strftime("%A, %B %d, %Y at %I:%M %p"),
        "iso": now.isoformat(),
        "timezone": str(now.tzinfo) if now.tzinfo else "UTC"
    }


# =============================================================================
#                     🆕 NEWS SEARCH TOOL
# =============================================================================

def search_news(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    📖 News Search Tool - Get Latest News
    =====================================
    
    Searches for recent news articles on any topic.
    
    Parameters:
    -----------
    query: Topic to search (e.g., "AI technology", "Indian economy")
    max_results: Number of news articles to return
    
    📌 HOW IT DIFFERS FROM REGULAR SEARCH:
    -------------------------------------
    Regular search: Any webpage (blogs, old articles, Wikipedia)
    News search: Recent news articles from news sources
    
    📌 FOR STOCK RESEARCH:
    ---------------------
    In your workflow, you want to check:
    "Any news about government policies affecting this sector?"
    
    This tool focuses on NEWS specifically.
    """
    # Enhance query for news
    news_query = f"{query} latest news today"
    
    # 🆕 Try Tavily first (more reliable for news)
    if _tavily_client:
        try:
            response = _tavily_client.search(
                query=news_query,
                max_results=max_results,
                search_depth="basic",
                include_answer=True
            )
            
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "url": item.get("url", ""),
                    "date": "",  # Tavily doesn't provide date
                    "source": "tavily_news"
                })
            
            if results:
                return {
                    "query": query,
                    "results": results,
                    "type": "news",
                    "source": "tavily",
                    "answer": response.get("answer", ""),
                    "fetched_at": datetime.utcnow().isoformat() + "Z"
                }
                
        except Exception as e:
            print(f"⚠️ Tavily news search failed: {e}")
    
    # Try DuckDuckGo news as fallback
    if DDGS_AVAILABLE:
        try:
            ddgs = DDGS()
            raw_results = ddgs.news(query, max_results=max_results)
            
            results = []
            for item in raw_results:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("body", ""),
                    "url": item.get("url", ""),
                    "date": item.get("date", ""),
                    "source": item.get("source", "")
                })
            
            if results:
                return {
                    "query": query,
                    "results": results,
                    "type": "news",
                    "source": "duckduckgo_news",
                    "fetched_at": datetime.utcnow().isoformat() + "Z"
                }
            
        except Exception as e:
            print(f"⚠️ DuckDuckGo news search failed: {e}")
    
    # Last fallback: regular web search with news-focused query
    result = smart_web_search(news_query, max_results)
    
    # Return with news type indicator
    return {
        **result,
        "type": "news_fallback",
        "note": "Using web search as news sources were unavailable"
    }


# =============================================================================
#                     STT (SPEECH-TO-TEXT) ENDPOINT
# =============================================================================

@tools_router.post("/stt/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """
    📖 Speech-to-Text Endpoint
    --------------------------
    Converts audio to text using OpenAI Whisper.
    
    HTTP POST to: http://localhost:8000/stt/transcribe
    Body: multipart/form-data with audio file
    
    Parameters:
    -----------
    file: Audio file (webm, wav, mp3, m4a supported)
    language: Optional language hint (e.g., "en", "es")
    
    Returns:
    --------
    { "text": "The transcribed text..." }
    
    📌 HOW WHISPER WORKS:
    --------------------
    1. We receive audio file from frontend
    2. We send it to OpenAI's Whisper API
    3. Whisper processes and returns text
    4. We return text to frontend
    
    📌 WHY WE USE WHISPER:
    ---------------------
    - Very accurate (state-of-the-art)
    - Handles multiple languages
    - Handles background noise well
    - Easy to use via API
    
    EXAMPLE USE CASE:
    ----------------
    User records voice message → Frontend sends audio → 
    This endpoint → Whisper API → Text returned → 
    Frontend displays text in chat
    """
    try:
        # Read audio content from uploaded file
        content = await file.read()
        
        if not content:
            raise HTTPException(
                status_code=400,
                detail="No audio content provided for transcription."
            )
        
        # Determine content type
        content_type = file.content_type or "audio/webm"
        
        # Handle generic content type
        if content_type == "application/octet-stream":
            content_type = "audio/webm"  # Default to webm
        
        # Get file extension for Whisper
        ext = mimetypes.guess_extension(content_type) or ".webm"
        
        # Create file-like object for OpenAI
        audio_file = io.BytesIO(content)
        audio_file.name = file.filename or f"input{ext}"
        """
        📖 Why set .name?
        -----------------
        Whisper API needs to know the file type.
        Setting .name helps it understand the format.
        """
        
        # Extract language hint (e.g., "en-US" → "en")
        language_hint = (language or "").split("-")[0].lower() or None
        """
        📖 What is language_hint?
        -------------------------
        Optional hint to help Whisper.
        
        If user is speaking English, we pass "en".
        This improves accuracy.
        
        We take just the first part: "en-US" → "en"
        """
        
        # Call OpenAI Whisper API
        result = client.audio.transcriptions.create(
            model="whisper-1",       # Whisper model
            file=audio_file,         # Audio data
            language=language_hint   # Optional language hint
        )
        """
        📖 client.audio.transcriptions.create()
        ---------------------------------------
        This is OpenAI's Whisper API call.
        
        Parameters:
        - model: "whisper-1" (the Whisper model name)
        - file: The audio file to transcribe
        - language: Optional language code
        
        Returns:
        - result.text: The transcribed text
        
        📌 This is from OpenAI documentation:
        https://platform.openai.com/docs/guides/speech-to-text
        """
        
        text = (result.text or "").strip()
        
        if not text:
            raise HTTPException(
                status_code=502,
                detail="Transcription returned empty text. Please try again."
            )
        
        return {"text": text}
        
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {err}")


# =============================================================================
#                     OCR (IMAGE TO TEXT) ENDPOINT
# =============================================================================

def fix_currency_symbols(text: str) -> str:
    """
    📖 Fix Currency Symbols in OCR Output (CONSERVATIVE VERSION)
    ------------------------------------------------------------
    Post-processes OCR text to fix common symbol recognition errors.
    
    PROBLEM:
    --------
    The Rupee symbol (₹) is often misread as "2" (they look similar!)
    
    SOLUTION:
    ---------
    Only replace "2" with "₹" in CLEAR CURRENCY CONTEXTS to avoid false positives.
    
    📌 SAFE PATTERNS (only these are replaced):
    - Currency keywords + 2XXX.XX (e.g., "Up to 2396.85" → "Up to ₹396.85")
    - "2" + number with decimal AND commas (e.g., "21,234.56" → "₹1,234.56")
    - Rs./INR followed by number
    
    📌 NOT REPLACED (to avoid false positives):
    - Plain numbers like "2024", "2500" (could be years, quantities, etc.)
    """
    import re
    
    # ==========================================================================
    # PATTERN 1: Currency keywords followed by "2" + digits
    # ==========================================================================
    # Only match when preceded by currency-related words
    # This catches: "Up to 2396.85", "limit 2500", "amount 21000"
    currency_keywords = r'(?:Up to|Upto|Limit|Amount|Price|Cost|Total|Balance|Pay|Paid|Fee|Charge|₹)\s*'
    
    # Match: keyword + 2 + 3+ digits with optional decimal
    text = re.sub(
        rf'({currency_keywords})2(\d{{2,}}(?:\.\d{{1,2}})?)\b',
        r'\1₹\2',
        text,
        flags=re.IGNORECASE
    )
    
    # ==========================================================================
    # PATTERN 2: "2" + number with BOTH comma AND decimal (very likely currency)
    # ==========================================================================
    # E.g., "21,234.56" → "₹1,234.56" (Indian format with decimal = currency)
    text = re.sub(
        r'\b2(\d{1,2},\d{2,3}(?:,\d{2,3})*\.\d{1,2})\b',
        r'₹\1',
        text
    )
    
    # ==========================================================================
    # PATTERN 3: Rs./Rs/RS followed by number → ₹
    # ==========================================================================
    text = re.sub(
        r'\bRs\.?\s*(\d)',
        r'₹\1',
        text,
        flags=re.IGNORECASE
    )
    
    # ==========================================================================
    # PATTERN 4: INR followed by number → ₹
    # ==========================================================================
    text = re.sub(
        r'\bINR\s*(\d)',
        r'₹\1',
        text,
        flags=re.IGNORECASE
    )
    
    # ==========================================================================
    # PATTERN 5: "2" followed by space then comma-formatted number
    # ==========================================================================
    # E.g., "2 1,234" → "₹1,234" (space indicates it was ₹ symbol)
    text = re.sub(
        r'\b2\s+(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?)\b',
        r'₹\1',
        text
    )
    
    return text


def preprocess_for_ocr(content: bytes) -> "Image.Image":
    """
    📖 Preprocess Image for OCR (IMPROVED!)
    ---------------------------------------
    Enhances image quality for better OCR results.
    
    Steps:
    1. Convert to grayscale
    2. Auto-contrast (improve brightness/contrast)
    3. Invert if dark background (make text dark on light)
    4. Upscale small images (increased target size)
    5. Sharpen image for clearer text edges
    6. Light denoise
    7. Adaptive binarization (better threshold calculation)
    
    📌 WHY PREPROCESS?
    ------------------
    OCR works best on:
    - Clear, high-contrast images
    - Black text on white background
    - Large enough text (300+ DPI equivalent)
    
    Screenshots often have:
    - Dark themes (light text on dark)
    - Low resolution
    - Noise
    - Compression artifacts
    
    Preprocessing fixes these issues!
    
    📌 IMPROVEMENTS MADE:
    --------------------
    1. Increased upscale target from 1200 to 2000 for sharper text
    2. Added sharpening step before OCR
    3. Better adaptive thresholding using Otsu-like method
    4. Smaller median filter (3→3) to preserve text edges
    """
    # Open image
    img = Image.open(BytesIO(content)).convert("RGB")
    
    # Convert to grayscale with auto-contrast
    gray = ImageOps.autocontrast(img.convert("L"))
    
    # Check if dark background (light text on dark)
    arr = np.array(gray)
    if arr.mean() < 128:
        # Dark background - invert colors
        gray = ImageOps.invert(gray)
        arr = np.array(gray)
    
    # Upscale small images (INCREASED target for better accuracy)
    min_target = 2000  # Increased from 1200 for sharper text
    min_dim = min(gray.size)
    if min_dim < min_target:
        scale = min_target / float(min_dim)
        new_size = (int(gray.width * scale), int(gray.height * scale))
        gray = gray.resize(new_size, Image.Resampling.LANCZOS)
        arr = np.array(gray)
    
    # Sharpen image for clearer text edges (NEW!)
    gray = gray.filter(ImageFilter.SHARPEN)
    
    # Light denoise (small kernel to preserve text)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    arr = np.array(gray)
    
    # Adaptive Binarization using Otsu-like method (IMPROVED!)
    # Calculate optimal threshold using histogram
    hist, _ = np.histogram(arr.flatten(), bins=256, range=(0, 256))
    total = arr.size
    sum_total = np.sum(np.arange(256) * hist)
    
    sum_bg = 0
    weight_bg = 0
    max_variance = 0
    threshold = 128  # Default threshold
    
    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > max_variance:
            max_variance = variance
            threshold = t
    
    # Apply threshold
    bw = gray.point(lambda x: 255 if x > threshold else 0)
    
    return bw


@tools_router.post("/ocr/image")
async def ocr_image(
    image: UploadFile = File(None),
    file: UploadFile = File(None)
):
    """
    📖 OCR Image Endpoint
    ---------------------
    Extracts text from an uploaded image.
    
    HTTP POST to: http://localhost:8000/ocr/image
    Body: multipart/form-data with image file
    
    Parameters:
    -----------
    image: Image file (png, jpg, webp, bmp, tiff)
    file: Alternative parameter name for image
    
    Returns:
    --------
    { "text": "Extracted text from the image..." }
    
    📌 HOW OCR WORKS:
    ----------------
    1. Receive image from frontend
    2. Preprocess (enhance for OCR)
    3. Run Tesseract OCR engine
    4. Return extracted text
    
    📌 WHAT IS TESSERACT?
    --------------------
    Tesseract is an open-source OCR engine developed by Google.
    - Free and open source
    - Supports 100+ languages
    - Very accurate
    - pytesseract is the Python wrapper
    
    EXAMPLE USE CASE:
    ----------------
    User uploads screenshot of code → This endpoint →
    Tesseract extracts text → Returns code as text →
    User can ask questions about the code
    """
    # Accept either 'image' or 'file' parameter
    upload = image or file
    
    if not upload:
        raise HTTPException(status_code=400, detail="No image provided")
    
    # Validate file type
    if upload.content_type and not upload.content_type.lower().startswith(("image/", "application/octet-stream")):
        raise HTTPException(status_code=400, detail="Only image files are supported")
    
    # Check if OCR dependencies are installed
    if not Image:
        raise HTTPException(
            status_code=503,
            detail="OCR service is currently unavailable. Image processing library not installed."
        )
    
    # Check if we have ANY OCR engine available
    easyocr_available = is_easyocr_available()
    tesseract_available = pytesseract is not None
    
    if not easyocr_available and not tesseract_available:
        raise HTTPException(
            status_code=503,
            detail="OCR service is currently unavailable. No OCR engine installed."
        )
    
    try:
        # Read image content
        content = await upload.read()
        
        # Preprocess image for better OCR
        prepped = preprocess_for_ocr(content)
        
        text = ""
        ocr_engine_used = "none"
        
        # 🆕 TRY EASYOCR FIRST (pure Python, works on Render!)
        if easyocr_available:
            try:
                print("🔤 Attempting EasyOCR...")
                reader = get_easyocr_reader()
                if reader:
                    # Convert PIL Image to numpy array for EasyOCR
                    import numpy as np
                    img_array = np.array(prepped)
                    
                    # Run EasyOCR
                    results = reader.readtext(img_array)
                    
                    # Extract text from results
                    text_parts = [result[1] for result in results]
                    text = "\n".join(text_parts).strip()
                    ocr_engine_used = "EasyOCR"
                    print(f"✅ EasyOCR extracted {len(text)} characters")
            except Exception as easy_err:
                print(f"⚠️ EasyOCR failed: {easy_err}")
                text = ""
        
        # FALLBACK TO TESSERACT if EasyOCR failed or not available
        if not text and tesseract_available:
            try:
                print("🔤 Attempting Tesseract OCR...")
                config = "--psm 3 --oem 3"
                
                # Try with Hindi support first (includes ₹ Rupee symbol)
                try:
                    available_langs = pytesseract.get_languages()
                    if 'hin' in available_langs:
                        text = (pytesseract.image_to_string(prepped, lang="eng+hin", config=config) or "").strip()
                    else:
                        text = (pytesseract.image_to_string(prepped, lang="eng", config=config) or "").strip()
                except Exception:
                    text = (pytesseract.image_to_string(prepped, lang="eng", config=config) or "").strip()
                
                ocr_engine_used = "Tesseract"
                print(f"✅ Tesseract extracted {len(text)} characters")
            except Exception as tess_err:
                print(f"⚠️ Tesseract failed: {tess_err}")
                if not text:
                    raise tess_err
        
        # 🆕 Post-processing: Fix common OCR mistakes for currency symbols
        text = fix_currency_symbols(text)
        
        if not text:
            raise HTTPException(status_code=422, detail="No text detected in the image.")
        
        return {"text": text}
        
    except HTTPException:
        raise
    except Exception as err:
        # Provide helpful error message for common Tesseract issues
        error_msg = str(err)
        if "tesseract" in error_msg.lower() or "not found" in error_msg.lower() or "not installed" in error_msg.lower():
            detail = "OCR service unavailable: Tesseract OCR engine is not installed on the server. This feature requires system-level installation that is not available in this environment. Please use text-based PDFs or contact support for OCR capabilities."
        else:
            detail = f"OCR failed: {error_msg}"
        raise HTTPException(status_code=503, detail=detail)


# =============================================================================
#                     SIMPLE SEARCH ENDPOINT
# =============================================================================

@tools_router.get("/search")
def search_web(query: str = Query(..., description="Search query text")):
    """
    📖 Simple Search Endpoint
    -------------------------
    Basic web search using DuckDuckGo Instant Answer API.
    
    HTTP GET to: http://localhost:8000/search?query=python tutorials
    
    Parameters:
    -----------
    query: The search query
    
    Returns:
    --------
    { "query": "...", "results": [...] }
    
    📌 DIFFERENCE FROM AGENT SEARCH:
    --------------------------------
    - /search: Simple, direct search results
    - /agent/web-search: AI agent that thinks, plans, and answers
    
    This is for quick lookups without the full agent overhead.
    
    📌 WHY DUCKDUCKGO?
    -----------------
    - No API key required!
    - Free to use
    - Returns "instant answers" (Wikipedia summaries, etc.)
    - Good for quick facts
    
    🔗 Similar to search_routes.py in your original code.
    """
    try:
        # Make request to DuckDuckGo
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,           # Search query
                "format": "json",     # Response format
                "no_html": 1,         # No HTML in response
                "skip_disambig": 1    # Skip disambiguation
            },
            headers={"User-Agent": "Mozilla/5.0 SigmaGPT"},
            timeout=10
        )
        
        # DuckDuckGo can return 202 (accepted), treat as valid
        if resp.status_code not in (200, 202):
            raise HTTPException(status_code=resp.status_code, detail="Search API failed")
        
        data = resp.json()
        results = []
        
        # Extract abstract (main answer)
        abstract = data.get("AbstractText")
        if abstract:
            results.append({
                "title": data.get("Heading") or "Result",
                "snippet": abstract
            })
        
        # Extract related topics
        for topic in data.get("RelatedTopics", []):
            text = topic.get("Text")
            url = topic.get("FirstURL")
            if text and url:
                results.append({
                    "title": text[:80],
                    "snippet": text,
                    "url": url
                })
        
        # Fallback message if no results
        if not results:
            results.append({
                "title": "No result",
                "snippet": "No results found",
                "url": None
            })
        
        return {"query": query, "results": results[:5]}
        
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Search failed: {err}")


# =============================================================================
#                     🆕 SMART SEARCH ENDPOINT (Tavily + DuckDuckGo)
# =============================================================================

@tools_router.post("/tools/smart-search")
async def smart_search_endpoint(payload: Dict[str, Any]):
    """
    📖 Smart Web Search Endpoint
    ============================
    
    HTTP POST to: http://localhost:8000/tools/smart-search
    Body: { "query": "Latest AI news", "max_results": 5 }
    
    Uses Tavily (AI-optimized) with DuckDuckGo fallback.
    
    🔗 THIS IS WHAT THE AGENT USES FOR WEB SEARCH!
    
    Returns structured results the AI can easily process.
    """
    query = payload.get("query")
    max_results = payload.get("max_results", 5)
    
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' parameter")
    
    result = smart_web_search(query, max_results)
    return result


@tools_router.post("/tools/indian-stocks")
async def indian_stocks_endpoint(payload: Dict[str, Any]):
    """
    📖 Indian Stock News Endpoint
    =============================
    
    HTTP POST to: http://localhost:8000/tools/indian-stocks
    Body: { "query": "Tata Motors", "max_results": 5 }
    
    Searches ONLY trusted Indian financial sites:
    - MoneyControl
    - Screener.in
    - Economic Times
    - LiveMint
    
    📌 USE CASE:
    -----------
    User asks: "Why is HDFC Bank falling?"
    → This endpoint searches only trusted finance sites
    → Returns authentic news and data, not blog spam
    """
    query = payload.get("query")
    max_results = payload.get("max_results", 5)
    
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' parameter")
    
    result = indian_stock_search(query, max_results)
    return result


@tools_router.get("/tools/weather/{city}")
async def weather_endpoint(city: str):
    """
    📖 Weather Endpoint
    ===================
    
    HTTP GET to: http://localhost:8000/tools/weather/Mumbai
    
    Returns current weather for the specified city.
    
    🔗 In your notes (03-Agents/main.py):
        def get_weather(city: str):
            url = f"https://wttr.in/{city}?format=%C+%t"
    
    SAME PATTERN! Just as an API endpoint.
    """
    result = get_weather(city)
    return result


@tools_router.get("/tools/datetime")
async def datetime_endpoint():
    """
    📖 Date/Time Endpoint
    =====================
    
    HTTP GET to: http://localhost:8000/tools/datetime
    
    Returns current date and time in multiple formats.
    
    📌 WHY THIS EXISTS:
    ------------------
    LLMs don't know the current date!
    This tool provides accurate date/time for:
    - "What day is today?"
    - "Is the market open?" (weekday check)
    - Policy date searches
    """
    result = get_current_datetime()
    return result


@tools_router.post("/tools/news")
async def news_endpoint(payload: Dict[str, Any]):
    """
    📖 News Search Endpoint
    =======================
    
    HTTP POST to: http://localhost:8000/tools/news
    Body: { "query": "AI technology", "max_results": 5 }
    
    Searches for recent news articles specifically.
    
    📌 DIFFERENCE FROM /search:
    --------------------------
    /search → Any webpage
    /tools/news → Recent news articles only
    """
    query = payload.get("query")
    max_results = payload.get("max_results", 5)
    
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' parameter")
    
    result = search_news(query, max_results)
    return result


# =============================================================================
#                     🆕 TOOL REGISTRY (For Agent Use)
# =============================================================================
"""
📚 TOOL REGISTRY
----------------
This is a dictionary of all available tools that the AGENT can use.

🔗 In your notes (03-Agents/main.py):
    available_tools = {
        "get_weather": get_weather,
        "run_command": run_command
    }

SAME PATTERN! We register tools here so the agent knows what's available.

📌 HOW THE AGENT USES THIS:
--------------------------
1. Agent receives user query
2. Agent decides which tool to use
3. Agent calls AVAILABLE_TOOLS[tool_name](input)
4. Agent gets result and continues

📌 FOR YOUR INTERVIEW:
----------------------
"I implemented a tool registry pattern where all available tools
are registered in a dictionary. This makes it easy to add new tools
and allows the agent to dynamically discover and use them."
"""

AVAILABLE_TOOLS = {
    "web_search": smart_web_search,
    "indian_stock_search": indian_stock_search,
    "get_weather": get_weather,
    "get_current_datetime": get_current_datetime,
    "search_news": search_news,
}


def get_tools_description() -> str:
    """
    📖 Get Tools Description for System Prompt
    ==========================================
    
    Returns a formatted string describing all available tools.
    This is injected into the agent's system prompt.
    
    📌 WHY THIS IS IMPORTANT:
    -------------------------
    The LLM needs to know:
    1. What tools are available
    2. What each tool does
    3. What parameters each tool takes
    
    This function generates that description automatically!
    """
    return """
Available Tools:
----------------

1. "web_search" 
   - Description: Search the internet for any information
   - Input: {"query": "search query string"}
   - Use when: User asks about current events, facts, general knowledge
   - Example: {"query": "latest OpenAI announcements 2024"}

2. "indian_stock_search"
   - Description: Search Indian financial websites (MoneyControl, Screener, ET)
   - Input: {"query": "company name or stock topic"}
   - Use when: User asks about Indian stocks, companies, market news
   - Example: {"query": "Tata Motors quarterly results"}
   - Note: Results come ONLY from trusted financial sites!

3. "get_weather"
   - Description: Get current weather for any city
   - Input: {"city": "city name"}
   - Use when: User asks about weather
   - Example: {"city": "Mumbai"}

4. "get_current_datetime"
   - Description: Get current date and time
   - Input: {} (no input needed)
   - Use when: User asks about today's date, day, time
   - Example: {}

5. "search_news"
   - Description: Search for recent news articles
   - Input: {"query": "news topic"}
   - Use when: User specifically asks for NEWS about something
   - Example: {"query": "government policy changes India"}

Remember:
- For Indian stock/finance questions → Use "indian_stock_search"
- For general web info → Use "web_search"
- For news specifically → Use "search_news"
- For weather → Use "get_weather"
- For date/time → Use "get_current_datetime"
"""


"""
===================================================================================
                        SUMMARY: TOOLS SERVICE
===================================================================================

This file provides utility endpoints for various AI tools.

ENDPOINTS:
----------
ORIGINAL:
1. POST /stt/transcribe        - Convert audio to text (Whisper)
2. POST /ocr/image             - Extract text from images (Tesseract)
3. GET  /search                - Simple web search (DuckDuckGo instant answers)

🆕 NEW (AI Agent Tools):
4. POST /tools/smart-search    - AI-optimized search (Tavily + DuckDuckGo fallback)
5. POST /tools/indian-stocks   - Indian finance sites only (MoneyControl, Screener)
6. GET  /tools/weather/{city}  - Current weather for any city
7. GET  /tools/datetime        - Current date and time
8. POST /tools/news            - Recent news articles

TOOL FUNCTIONS (For Agent Use):
-------------------------------
- smart_web_search()      → Primary search with fallback
- indian_stock_search()   → Filtered to trusted finance sites
- get_weather()           → Weather data
- get_current_datetime()  → Date/time info
- search_news()           → News-focused search

KEY CONCEPTS:
-------------
1. Whisper: OpenAI's speech-to-text model
2. Tesseract: Open-source OCR engine
3. Tavily: AI-optimized search (like ChatGPT's Bing)
4. DuckDuckGo: Free backup search
5. Site Filtering: Limiting search to trusted sources
6. Tool Registry: Dict of tools the agent can call

DEPENDENCIES:
-------------
- openai: For Whisper STT
- Pillow (PIL): For image processing
- pytesseract: For OCR (requires Tesseract installed)
- numpy: For image array operations
- requests: For HTTP requests
- tavily-python: For AI-optimized search (optional)
- duckduckgo-search: For backup search (optional)

📌 SYSTEM REQUIREMENTS:
----------------------
For OCR to work, you need Tesseract installed on your system:

macOS:
    brew install tesseract

Ubuntu/Debian:
    sudo apt-get install tesseract-ocr

Windows:
    Download from: https://github.com/UB-Mannheim/tesseract/wiki

📌 ENVIRONMENT VARIABLES:
------------------------
TAVILY_API_KEY - Your Tavily API key (get free at tavily.com)
                 If not set, DuckDuckGo is used as fallback.

===================================================================================
"""

