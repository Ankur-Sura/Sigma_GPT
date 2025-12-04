"""
===================================================================================
                AGENT_SERVICE.PY - AI Agent with Tools (Web Search)
===================================================================================

📚 WHAT IS AN AI AGENT?
-----------------------
An AI Agent is an LLM that can:
1. THINK about a problem (plan)
2. USE TOOLS to get information (action)
3. OBSERVE the results (observe)
4. GIVE A FINAL ANSWER (output)

This is different from a simple chatbot which just responds.
An agent can take actions in the real world!

📌 THE AGENT LOOP (from your notes):
-----------------------------------
    User Query: "What's the weather in New York?"
        ↓
    PLAN: "I need to get weather data. I should use the weather tool."
        ↓
    ACTION: Call get_weather("New York")
        ↓
    OBSERVE: "12 Degree Celsius"
        ↓
    OUTPUT: "The weather in New York is 12°C"

🔗 THIS IS EXACTLY WHAT YOU LEARNED IN:
    Notes Compare/03-Agents/main.py

===================================================================================
                            AGENT ARCHITECTURE
===================================================================================

    ┌─────────────────────────────────────────────────────────────┐
    │                         USER                                 │
    │              "What's the latest news about AI?"             │
    └───────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      AGENT LOOP                              │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ 1. PLAN: Analyze query, decide what tools to use     │  │
    │  └────────────────────────┬─────────────────────────────┘  │
    │                           ▼                                  │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ 2. ACTION: Call the tool (e.g., web_search)          │  │
    │  └────────────────────────┬─────────────────────────────┘  │
    │                           ▼                                  │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ 3. OBSERVE: Get and analyze tool results             │  │
    │  └────────────────────────┬─────────────────────────────┘  │
    │                           ▼                                  │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ 4. OUTPUT: Generate final answer for user            │  │
    │  └──────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────┘

===================================================================================
"""

# =============================================================================
#                           IMPORTS SECTION
# =============================================================================

# ----- Standard Library Imports -----
import json           # For parsing JSON responses from LLM
import os             # For environment variables
from datetime import datetime  # For getting current date/time
from typing import List, Dict, Any, Optional
from collections import defaultdict  # For conversation memory

# ----- Third-Party Imports -----
import requests       # For making HTTP requests (web search)
import redis          # For Redis-based memory (optional)

# ----- Import Tools from tools_service -----
from tools_service import (
    # Regular functions for DIRECT calls (existing code uses these)
    smart_web_search,
    indian_stock_search,
    get_weather,
    get_current_datetime,
    search_news,
    get_tools_description,
    AVAILABLE_TOOLS,
    # @tool wrapped versions for LANGGRAPH (matches your notes!)
    LANGGRAPH_TOOLS
)
"""
📖 Importing Tools from tools_service.py
-----------------------------------------
We import TWO types of tools:

1. REGULAR FUNCTIONS (for direct calls):
   - smart_web_search("query") → returns Dict
   - get_weather("Mumbai") → returns Dict
   - These are used throughout the existing code!

2. LANGGRAPH_TOOLS (for ToolNode):
   - @tool decorated wrappers
   - Used with ToolNode and tools_condition
   
🔗 In your notes (human-in-loop code):
    @tool
    def human_assistance(query: str) -> str:
        '''Request assistance from a human.'''
        ...
    tools = [human_assistance]

Same pattern! We have @tool decorated tools for LangGraph in LANGGRAPH_TOOLS.

📌 TOOLS AVAILABLE:
------------------
DIRECT CALLS: smart_web_search, indian_stock_search, get_weather, get_current_datetime, search_news
LANGGRAPH:    LANGGRAPH_TOOLS (for ToolNode)
"""

# ----- Tools List for ToolNode (matches your notes!) -----
tools = LANGGRAPH_TOOLS
"""
📖 Tools List for ToolNode
--------------------------
🔗 In your notes (human-in-loop code):
    tools = [human_assistance]
    tool_node = ToolNode(tools=tools)
    
Same pattern! LANGGRAPH_TOOLS contains @tool decorated functions.
"""

# ----- Import LangGraph Stock Research Workflow -----
from stock_graph import run_stock_research, stock_research_graph
"""
📖 Importing LangGraph Stock Research Workflow
----------------------------------------------
This is the STAGE 2 implementation using actual LangGraph nodes!

🔗 In your notes (07-LangGraph/graph.py):
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    ...
    graph = graph_builder.compile()

We import:
- run_stock_research: Function to run the full workflow
- stock_research_graph: The compiled LangGraph

📌 THE ENHANCED 7-NODE WORKFLOW:
--------------------------------
START → company_intro → sector_analyst → company_researcher → 
        policy_watchdog → investor_sentiment → technical_analysis →
        investment_suggestion → END
"""

# ----- MongoDB Import for LangGraph Checkpointer -----
from pymongo import MongoClient
"""
📖 What is pymongo?
-------------------
From the 'pymongo' library (pip install pymongo).

✔ Official Python driver for MongoDB
✔ We use it to save/load conversation state (checkpointing)
✔ This is how we persist memory across server restarts!
"""

# ----- LangGraph Imports (matches your notes!) -----
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt, Command
from typing import Annotated
from typing_extensions import TypedDict as LangGraphTypedDict
"""
📖 LangGraph Imports - MATCHES YOUR NOTES!
------------------------------------------

🔗 In your notes (human-in-loop code):
    from langgraph.prebuilt import ToolNode, tools_condition
    from langchain_core.tools import tool
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.mongodb import MongoDBSaver
    from langgraph.types import interrupt, Command
    
MongoDBSaver: 
    ✔ Saves/loads graph state to MongoDB
    ✔ Use with context manager: with MongoDBSaver.from_conn_string() as checkpointer
    
ToolNode:
    ✔ Automatically executes tools when LLM calls them
    ✔ Works with tools decorated with @tool
    
tools_condition:
    ✔ Conditional edge that checks if LLM wants to use a tool
    ✔ Routes to tool_node or END based on LLM's response
    
interrupt:
    ✔ Pauses graph execution for human input
    ✔ State is saved to MongoDB
    
Command:
    ✔ Used to resume graph with human response
    ✔ Command(resume={"data": human_response})
"""

# ----- FastAPI Imports -----
from fastapi import APIRouter, HTTPException

# ----- LangChain Imports (matches your notes!) -----
from langchain.chat_models import init_chat_model
"""
📖 What is init_chat_model?
---------------------------
From langchain.chat_models library.

✔ Creates a chat model in a provider-agnostic way
✔ Works with OpenAI, Anthropic, etc.
✔ Can bind tools with .bind_tools()

🔗 In your notes (human-in-loop code):
    llm = init_chat_model(model_provider="openai", model="gpt-4.1")
    llm_with_tools = llm.bind_tools(tools=tools)
"""

# ----- OpenAI Import (direct client for backward compatibility) -----
from openai import OpenAI
"""
📖 What is OpenAI client?
-------------------------
From the 'openai' library (pip install openai).

✔ Official Python client for OpenAI API
✔ We use it to call GPT models
✔ Automatically reads OPENAI_API_KEY from environment

🔗 In your notes (03-Agents/main.py):
    client = OpenAI()
"""

# =============================================================================
#                     INITIALIZE ROUTER AND CLIENT
# =============================================================================

agent_router = APIRouter(
    prefix="",           # No prefix
    tags=["Agent"]       # Groups in API docs
)
"""
📖 What is APIRouter?
---------------------
Creates a "sub-application" with its own routes.

✔ All agent routes go here
✔ Later we include this in the main app
✔ Keeps code organized
"""

client = OpenAI()
"""
📖 Creating OpenAI Client
-------------------------
✔ Reads OPENAI_API_KEY from environment automatically
✔ Used to call GPT models

🔗 In your notes (03-Agents/main.py):
    client = OpenAI()
"""

# ----- LangChain LLM (matches your notes!) -----
llm = init_chat_model(model_provider="openai", model="gpt-4o-mini")
"""
📖 Creating LangChain LLM
-------------------------
This creates a LangChain-compatible LLM that can:
✔ Bind tools with .bind_tools()
✔ Work with ToolNode
✔ Support streaming

🔗 In your notes (human-in-loop code):
    llm = init_chat_model(model_provider="openai", model="gpt-4.1")
    llm_with_tools = llm.bind_tools(tools=tools)

📌 We use gpt-4o-mini for cost efficiency. Change to gpt-4.1 if needed.
"""

# ----- Bind Tools to LLM (EXACTLY like your notes!) -----
llm_with_tools = llm.bind_tools(tools=tools)
"""
📖 LLM with Tools Bound
-----------------------
🔗 In your notes (human-in-loop code):
    llm_with_tools = llm.bind_tools(tools=tools)
    
This enables the LLM to:
✔ Know what tools are available
✔ Generate tool calls in its response
✔ Work with ToolNode for automatic execution
"""

# ----- Create ToolNode (EXACTLY like your notes!) -----
tool_node = ToolNode(tools=tools)
"""
📖 ToolNode for Automatic Tool Execution
----------------------------------------
🔗 In your notes (human-in-loop code):
    tool_node = ToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    
ToolNode:
✔ Automatically executes tools when LLM requests them
✔ Handles the tool call → result → back to LLM flow
✔ Works with tools_condition for routing
"""

# =============================================================================
#                     CONFIGURATION FROM ENVIRONMENT
# =============================================================================

# Google Search API Configuration (optional)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")  # Custom Search Engine ID
"""
📖 Google Search API
--------------------
✔ GOOGLE_API_KEY: Your Google Cloud API key
✔ GOOGLE_CX: Your Custom Search Engine ID

These are optional - if not set, we fall back to DuckDuckGo.

📌 How to get these:
1. Go to Google Cloud Console
2. Create a project and enable Custom Search API
3. Create an API key
4. Go to https://programmablesearchengine.google.com/
5. Create a search engine and get the CX ID
"""

# Memory Configuration
_MAX_TURNS = int(os.getenv("AGENT_MAX_TURNS", "12"))  # Max conversation turns to remember
_REDIS_TTL_SECONDS = int(os.getenv("AGENT_MEMORY_TTL_SECONDS", str(60 * 60 * 6)))  # 6 hours default

"""
📖 Why limit conversation turns?
--------------------------------
✔ LLMs have token limits
✔ Very long conversations use more tokens (costs more)
✔ We keep only the most recent 12 turns (24 messages)

📖 Redis TTL (Time To Live):
----------------------------
✔ Messages expire after 6 hours in Redis
✔ Prevents old conversations from taking up space forever
"""

# =============================================================================
#                     CONVERSATION MEMORY
# =============================================================================

# In-memory storage (simple Python dict)
_memory: Dict[str, List[Dict[str, str]]] = defaultdict(list)
"""
📖 What is this memory?
-----------------------
✔ Stores conversation history for each session
✔ Key = session_id, Value = list of messages
✔ defaultdict(list) means: if key doesn't exist, create empty list

Example:
    _memory = {
        "session-123": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ],
        "session-456": [...]
    }

📌 Why do we need memory?
-------------------------
Without memory, the agent forgets previous conversations.
With memory, we can have multi-turn conversations:
    User: "My name is Ankur"
    Agent: "Nice to meet you, Ankur!"
    User: "What's my name?"
    Agent: "Your name is Ankur!"  ← Remembers!
"""

_GLOBAL_KEY = "shared"  # Key for shared memory across all sessions
"""
📖 What is shared/global memory?
---------------------------------
✔ Some facts should be remembered across ALL conversations
✔ Example: User's name, preferences, important context
✔ We store these under a special "shared" key
"""

# =============================================================================
#                     REDIS-BASED MEMORY (Optional)
# =============================================================================

_redis_client: Optional[redis.Redis] = None
REDIS_URL = os.getenv("REDIS_URL")  # e.g., redis://localhost:6379/0

if REDIS_URL:
    try:
        _redis_client = redis.Redis.from_url(REDIS_URL)
        _redis_client.ping()  # Test connection
    except Exception:
        _redis_client = None  # Fall back to in-memory

"""
📖 Why use Redis for memory?
----------------------------
Problem with in-memory storage:
    - If the server restarts, ALL memory is lost!
    - Not good for production

Redis solves this:
    - Redis is a fast key-value database
    - Memory persists across server restarts
    - Can be shared across multiple server instances

🔗 In your notes (advanced_rag/queue/connection.py):
    from redis import Redis
    from rq import Queue
    queue = Queue(connection=Redis())
    
You already know Redis from your RQ (Redis Queue) notes!

📌 How it works:
    - If REDIS_URL is set, we try to connect to Redis
    - If connection fails or REDIS_URL is not set, we use simple Python dict
    - This is a "graceful fallback" pattern
"""

# =============================================================================
#                     TOOL: WEB SEARCH (DuckDuckGo Fallback)
# =============================================================================

def fallback_ddg(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    📖 DuckDuckGo Search Fallback
    -----------------------------
    Uses DuckDuckGo's Instant Answer API for web search.
    
    ✔ No API key required!
    ✔ Free and simple
    ✔ Used when Google Search is not configured
    
    📌 How DuckDuckGo Instant Answer works:
    - It's not a full search engine API
    - Returns "instant answers" (Wikipedia summaries, definitions, etc.)
    - Good for quick facts, not comprehensive search
    
    Parameters:
    -----------
    query: The search query (e.g., "What is Python?")
    max_results: Maximum number of results to return
    
    Returns:
    --------
    List of dicts with: title, snippet, url
    
    🔗 In your notes (03-Agents/main.py), you had:
        def get_weather(city: str):
            url = f"https://wttr.in/{city}?format=%C+%t"
            response = requests.get(url)
            ...
            
    Same pattern! Make HTTP request → Parse response → Return result
    """
    try:
        # Make HTTP GET request to DuckDuckGo API
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,           # The search query
                "format": "json",     # Response format
                "no_html": 1,         # Don't include HTML in response
                "skip_disambig": 1    # Skip disambiguation pages
            },
            headers={"User-Agent": "SigmaGPT"},  # Identify ourselves
            timeout=10  # Don't wait more than 10 seconds
        )
        
        # Check if request was successful
        if resp.status_code not in (200, 202):
            return []
        
        # Parse JSON response
        data = resp.json()
        results = []
        
        # Extract abstract (main answer) if available
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading"),
                "snippet": data.get("AbstractText"),
                "url": data.get("AbstractURL")
            })
        
        # Extract related topics
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                results.append({
                    "title": topic.get("Text")[:80],
                    "snippet": topic.get("Text"),
                    "url": topic.get("FirstURL")
                })
            if len(results) >= max_results:
                break
        
        return results[:max_results]
        
    except Exception:
        return []


def web_search(query: str, max_results: int = 3) -> str:
    """
    📖 Web Search Tool
    ------------------
    Main web search function that the agent uses.
    
    ✔ First tries Google Custom Search (if configured)
    ✔ Falls back to DuckDuckGo if Google fails or is not set up
    
    Parameters:
    -----------
    query: What to search for
    max_results: Maximum number of results
    
    Returns:
    --------
    JSON string with search results (for the agent to parse)
    
    📌 This is a TOOL that the agent can CALL:
    
    🔗 In your notes (03-Agents/main.py), you defined tools:
        def get_weather(city: str):
            ...
        def run_command(cmd: str):
            ...
        
        available_tools = {
            "get_weather": get_weather,
            "run_command": run_command
        }
        
    Same pattern! web_search is our tool.
    """
    try:
        results = []
        
        # Try Google Search first (if configured)
        if GOOGLE_API_KEY and GOOGLE_CX:
            resp = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": GOOGLE_API_KEY,
                    "cx": GOOGLE_CX,
                    "q": query,
                    "num": max_results
                },
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items") or []
                for item in items[:max_results]:
                    results.append({
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                        "url": item.get("link")
                    })
        
        # Fallback to DuckDuckGo if Google didn't return results
        if not results:
            results = fallback_ddg(query, max_results=max_results)
        
        # If still no results
        if not results:
            return json.dumps({"error": "No results found. Please try again later."})
        
        # Return results as JSON string
        return json.dumps({
            "query": query,
            "results": results,
            "fetched_at": datetime.utcnow().isoformat() + "Z"  # When results were fetched
        })
        
    except Exception:
        return json.dumps({"error": "Search is temporarily unavailable."})


# =============================================================================
#                     MEMORY HELPER FUNCTIONS
# =============================================================================

def _clamp_history(session_id: str):
    """
    📖 Clamp History
    ----------------
    Limits conversation history to _MAX_TURNS * 2 messages.
    
    Why * 2? Because each turn has:
    - 1 user message
    - 1 assistant message
    
    So 12 turns = 24 messages max.
    """
    history = _memory[session_id]
    if len(history) > _MAX_TURNS * 2:
        _memory[session_id] = history[-_MAX_TURNS * 2:]


def _load_history(session_id: str) -> List[Dict[str, str]]:
    """
    📖 Load Conversation History
    ----------------------------
    Gets the conversation history for a session.
    
    ✔ Tries Redis first (if available)
    ✔ Falls back to in-memory storage
    
    Returns: List of message dicts like:
        [{"role": "user", "content": "Hello"}, ...]
    """
    if _redis_client:
        try:
            # Get all messages from Redis list
            data = _redis_client.lrange(f"agent:history:{session_id}", 0, -1)
            history = [json.loads(item) for item in data] if data else []
            return history[-_MAX_TURNS * 2:]  # Return only last N messages
        except Exception:
            pass
    
    return _memory.get(session_id, [])


def _save_history(session_id: str, history: List[Dict[str, str]]):
    """
    📖 Save Conversation History
    ----------------------------
    Saves the conversation history.
    
    ✔ Saves to both Redis AND in-memory
    ✔ Caps history to max turns
    ✔ Sets expiration in Redis (TTL)
    """
    capped = history[-_MAX_TURNS * 2:]  # Only keep last N messages
    _memory[session_id] = capped
    
    if _redis_client:
        try:
            key = f"agent:history:{session_id}"
            _redis_client.delete(key)  # Clear old history
            if capped:
                # Push all messages to Redis list
                _redis_client.rpush(key, *[json.dumps(item) for item in capped])
                _redis_client.expire(key, _REDIS_TTL_SECONDS)  # Set expiration
        except Exception:
            pass


def _load_shared_history() -> List[Dict[str, str]]:
    """Load the global shared memory."""
    return _load_history(_GLOBAL_KEY)


def _save_shared_history(history: List[Dict[str, str]]):
    """Save to global shared memory."""
    _save_history(_GLOBAL_KEY, history)


def _reset_history(session_id: str):
    """
    📖 Reset/Clear History
    ----------------------
    Clears all conversation history for a session.
    Useful when user wants to start fresh.
    """
    _memory.pop(session_id, None)
    if _redis_client:
        try:
            _redis_client.delete(f"agent:history:{session_id}")
        except Exception:
            pass


# =============================================================================
#                     LANGGRAPH-STYLE MONGODB CHECKPOINTER
# =============================================================================
"""
📚 WHAT IS A CHECKPOINTER?
--------------------------
A checkpointer SAVES and LOADS the state of a conversation.

Think of it like a "save game" feature:
- When you close the game (server restarts), your progress is saved
- When you open the game again, you continue from where you left off

🔗 In your notes (07-LangGraph/graph.py), you used:
    from langgraph.checkpoint.mongodb import MongoDBSaver
    
    # Sanitize URI to ensure proper format
    sanitized_uri = _sanitize_mongo_uri(MONGODB_URI)
    with MongoDBSaver.from_conn_string(sanitized_uri) as mongo_checkpointer:
        graph_with_mongo = compile_graph_with_checkpointer(mongo_checkpointer)
        
We're implementing the SAME concept here!

📌 HOW IT WORKS:
---------------
    User sends message with thread_id="abc123"
        ↓
    Checkpointer loads previous state from MongoDB
        ↓
    Agent processes message with full history
        ↓
    Checkpointer saves new state to MongoDB
        ↓
    Next time user opens thread "abc123", history is restored!
"""

# MongoDB Configuration for Checkpointer
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "sigma_gpt")
MONGODB_COLLECTION = "langgraph_checkpoints"
MONGODB_GLOBAL_MEMORY_COLLECTION = "global_user_memory"

# MongoDB client (lazy initialization)
_mongo_client: Optional[MongoClient] = None
_mongo_db = None
_checkpoints_collection = None
_global_memory_collection = None


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


def _get_mongo_collection():
    """
    📖 Get MongoDB Collection (Lazy Initialization)
    ------------------------------------------------
    Creates MongoDB connection only when first needed.
    
    ✔ Connects to MongoDB using MONGODB_URI from environment
    ✔ Uses database specified by MONGODB_DB
    ✔ Returns the checkpoints collection
    
    📌 Why lazy initialization?
    - Don't connect until we actually need to save/load
    - Avoids errors if MongoDB isn't running but not used
    """
    global _mongo_client, _mongo_db, _checkpoints_collection
    
    if _checkpoints_collection is None:
        try:
            # Sanitize URI to ensure proper format
            sanitized_uri = _sanitize_mongo_uri(MONGODB_URI)
            _mongo_client = MongoClient(sanitized_uri, serverSelectionTimeoutMS=5000)
            # Test connection immediately
            _mongo_client.admin.command('ping')
            _mongo_db = _mongo_client[MONGODB_DB]
            _checkpoints_collection = _mongo_db[MONGODB_COLLECTION]
            
            # Create index on thread_id for fast lookups
            _checkpoints_collection.create_index("thread_id", unique=True)
            print(f"✅ Connected to MongoDB checkpointer: {MONGODB_DB}.{MONGODB_COLLECTION}")
        except Exception as e:
            print(f"⚠️ MongoDB checkpointer not available: {e}")
            print(f"   Raw URI from env: {MONGODB_URI[:80]}..." if len(MONGODB_URI) > 80 else f"   Raw URI from env: {MONGODB_URI}")
            print(f"   URI length: {len(MONGODB_URI)} characters (should be ~130-140)")
            if len(MONGODB_URI) < 130:
                print(f"   ⚠️  URI appears incomplete - missing query parameters!")
                print(f"   Expected: ...sigma_gpt?retryWrites=true&w=majority&appName=Cluster0")
            print(f"   Check Render Dashboard → Environment → MONGODB_URI")
            return None
    
    return _checkpoints_collection


def _get_global_memory_collection():
    """
    📖 Get Global Memory Collection
    --------------------------------
    Returns the MongoDB collection for storing global user memory.
    
    ✔ Stores user preferences that persist across ALL threads
    ✔ Like ChatGPT's memory feature!
    """
    global _mongo_client, _mongo_db, _global_memory_collection
    
    if _global_memory_collection is None:
        try:
            if _mongo_client is None:
                # Sanitize URI to ensure proper format
                sanitized_uri = _sanitize_mongo_uri(MONGODB_URI)
                _mongo_client = MongoClient(sanitized_uri, serverSelectionTimeoutMS=5000)
                # Test connection immediately
                _mongo_client.admin.command('ping')
                _mongo_db = _mongo_client[MONGODB_DB]
            
            _global_memory_collection = _mongo_db[MONGODB_GLOBAL_MEMORY_COLLECTION]
            _global_memory_collection.create_index("user_id", unique=True)
            print(f"✅ Connected to Global Memory: {MONGODB_DB}.{MONGODB_GLOBAL_MEMORY_COLLECTION}")
        except Exception as e:
            print(f"⚠️ Global memory not available: {e}")
            print(f"   Raw URI from env: {MONGODB_URI[:80]}..." if len(MONGODB_URI) > 80 else f"   Raw URI from env: {MONGODB_URI}")
            print(f"   URI length: {len(MONGODB_URI)} characters (should be ~130-140)")
            if len(MONGODB_URI) < 130:
                print(f"   ⚠️  URI appears incomplete - missing query parameters!")
                print(f"   Expected: ...sigma_gpt?retryWrites=true&w=majority&appName=Cluster0")
            print(f"   Check Render Dashboard → Environment → MONGODB_URI")
            return None
    
    return _global_memory_collection


# =============================================================================
#                     GLOBAL MEMORY (Like ChatGPT's Memory Feature!)
# =============================================================================
"""
📚 WHAT IS GLOBAL MEMORY?
-------------------------
Global memory stores information about the USER that persists across ALL threads.

🔗 THIS IS EXACTLY WHAT CHATGPT DOES!
When you tell ChatGPT "My name is Ankur", it remembers in ALL future chats.

GLOBAL MEMORY STORES:
---------------------
1. User's name
2. Preferences (how they want notes formatted)
3. Important facts they've shared
4. Their interests and expertise

HOW IT WORKS:
-------------
    User says: "My name is Ankur and I prefer detailed explanations"
        ↓
    AI extracts: name="Ankur", preference="detailed explanations"
        ↓
    Saved to global_user_memory collection
        ↓
    Next chat (ANY thread): AI knows user is Ankur who likes detailed explanations!

DIFFERENCE FROM THREAD MEMORY:
------------------------------
    Thread Memory: "We discussed Python decorators" (only in that thread)
    Global Memory: "User's name is Ankur" (available in ALL threads)
"""


class GlobalMemoryManager:
    """
    📖 Global Memory Manager
    ========================
    
    Manages user preferences and facts that persist across ALL conversations.
    
    🔗 THIS IS LIKE CHATGPT'S MEMORY FEATURE!
    
    STRUCTURE:
    ----------
    {
        "user_id": "default",  # Can support multiple users
        "name": "Ankur",
        "preferences": {
            "note_style": "detailed with examples",
            "language": "English",
            "expertise_level": "beginner"
        },
        "facts": [
            "Loves Python programming",
            "Learning AI/ML",
            "Preparing for interviews"
        ],
        "updated_at": datetime
    }
    """
    
    def __init__(self):
        self.collection = _get_global_memory_collection()
    
    def load(self, user_id: str = "default") -> Dict[str, Any]:
        """
        📖 Load Global Memory
        ---------------------
        Gets user's global preferences and facts.
        
        Returns default empty structure if not found.
        """
        if self.collection is None:
            return self._default_memory(user_id)
        
        try:
            doc = self.collection.find_one({"user_id": user_id})
            if doc:
                doc.pop("_id", None)
                print(f"📥 Loaded global memory for user: {user_id}")
                return doc
            return self._default_memory(user_id)
        except Exception as e:
            print(f"⚠️ Error loading global memory: {e}")
            return self._default_memory(user_id)
    
    def _default_memory(self, user_id: str) -> Dict[str, Any]:
        """Return empty default memory structure."""
        return {
            "user_id": user_id,
            "name": None,
            "preferences": {
                "note_style": None,
                "language": "English",
                "expertise_level": None
            },
            "facts": [],
            "updated_at": None
        }
    
    def save(self, user_id: str, memory: Dict[str, Any]) -> bool:
        """
        📖 Save Global Memory
        ---------------------
        Saves user's global preferences and facts.
        """
        if self.collection is None:
            return False
        
        try:
            memory["user_id"] = user_id
            memory["updated_at"] = datetime.utcnow()
            
            self.collection.update_one(
                {"user_id": user_id},
                {"$set": memory},
                upsert=True
            )
            print(f"📤 Saved global memory for user: {user_id}")
            return True
        except Exception as e:
            print(f"⚠️ Error saving global memory: {e}")
            return False
    
    def update_from_conversation(self, user_id: str, message: str, ai_response: str) -> bool:
        """
        📖 Extract and Update Global Memory from Conversation
        -----------------------------------------------------
        
        Automatically extracts important user info from messages.
        
        🔗 THIS IS HOW CHATGPT LEARNS ABOUT YOU!
        
        When you say "My name is Ankur", ChatGPT extracts:
            - name: "Ankur"
        
        When you say "I prefer detailed explanations with examples", ChatGPT extracts:
            - preferences.note_style: "detailed with examples"
        
        This function does the same thing!
        """
        memory = self.load(user_id)
        updated = False
        
        message_lower = message.lower()
        
        # Extract name
        # Patterns: "my name is X", "I'm X", "I am X", "call me X"
        name_patterns = [
            "my name is ", "i'm ", "i am ", "call me ", "this is "
        ]
        for pattern in name_patterns:
            if pattern in message_lower:
                idx = message_lower.find(pattern) + len(pattern)
                # Get the next word(s) as name
                remaining = message[idx:].strip()
                # Take first 1-3 words as name
                name_parts = remaining.split()[:3]
                # Clean up - remove punctuation
                potential_name = " ".join(name_parts).rstrip(".,!?")
                if potential_name and len(potential_name) > 1:
                    memory["name"] = potential_name.title()
                    updated = True
                    print(f"🧠 Learned user name: {memory['name']}")
                break
        
        # Extract note style preferences
        style_keywords = {
            "detailed": "detailed with examples",
            "brief": "brief and concise",
            "simple": "simple and easy to understand",
            "technical": "technical with code examples",
            "beginner": "beginner-friendly",
            "step by step": "step-by-step explanations",
            "with examples": "with practical examples",
            "like a teacher": "classroom-style teaching",
            "interview": "interview-focused explanations"
        }
        
        for keyword, style in style_keywords.items():
            if keyword in message_lower and ("prefer" in message_lower or "want" in message_lower or "like" in message_lower or "explain" in message_lower):
                memory["preferences"]["note_style"] = style
                updated = True
                print(f"🧠 Learned note style preference: {style}")
                break
        
        # Extract expertise level
        level_keywords = {
            "beginner": "beginner",
            "intermediate": "intermediate", 
            "advanced": "advanced",
            "expert": "expert",
            "new to": "beginner",
            "learning": "beginner",
            "experienced": "intermediate"
        }
        
        for keyword, level in level_keywords.items():
            if keyword in message_lower:
                memory["preferences"]["expertise_level"] = level
                updated = True
                print(f"🧠 Learned expertise level: {level}")
                break
        
        # Extract facts (things user tells about themselves)
        fact_patterns = [
            "i love ", "i like ", "i work ", "i am learning ",
            "i'm learning ", "i'm studying ", "i study ",
            "i'm preparing ", "i am preparing ", "my goal is "
        ]
        
        for pattern in fact_patterns:
            if pattern in message_lower:
                idx = message_lower.find(pattern)
                # Get the rest of the sentence
                remaining = message[idx:].split(".")[0].split(",")[0]
                if remaining and len(remaining) > 10:
                    # Avoid duplicates
                    if remaining not in memory["facts"]:
                        memory["facts"].append(remaining)
                        # Keep only last 10 facts
                        memory["facts"] = memory["facts"][-10:]
                        updated = True
                        print(f"🧠 Learned new fact: {remaining}")
                break
        
        if updated:
            self.save(user_id, memory)
        
        return updated
    
    def get_context_prompt(self, user_id: str = "default") -> str:
        """
        📖 Get Context Prompt for LLM
        -----------------------------
        
        Generates a prompt that injects global memory into the conversation.
        
        This is added to EVERY chat so the AI knows:
        - User's name
        - How they want notes
        - Their interests and level
        """
        memory = self.load(user_id)
        
        parts = []
        
        if memory.get("name"):
            parts.append(f"The user's name is {memory['name']}.")
        
        prefs = memory.get("preferences", {})
        if prefs.get("note_style"):
            parts.append(f"The user prefers {prefs['note_style']} style explanations.")
        
        if prefs.get("expertise_level"):
            parts.append(f"The user's expertise level is {prefs['expertise_level']}.")
        
        facts = memory.get("facts", [])
        if facts:
            facts_str = "; ".join(facts[-5:])  # Last 5 facts
            parts.append(f"Known facts about the user: {facts_str}")
        
        if parts:
            return "USER CONTEXT (from global memory):\n" + "\n".join(parts)
        
        return ""


# Global memory manager instance
_global_memory = GlobalMemoryManager()
"""
📖 Why a global instance?
-------------------------
✔ One manager for all requests
✔ Efficiently manages user preferences
✔ Like ChatGPT's memory system!
"""


class MongoDBCheckpointer:
    """
    📖 MongoDB Checkpointer Class
    =============================
    
    This class saves and loads conversation state to/from MongoDB.
    
    🔗 THIS IS SIMILAR TO YOUR NOTES (07-LangGraph/graph.py):
        from langgraph.checkpoint.mongodb import MongoDBSaver
        
    We implement the same functionality manually to avoid dependency conflicts.
    
    STATE STRUCTURE:
    ----------------
    {
        "thread_id": "abc123",           # Unique conversation ID
        "messages": [...],                # List of {role, content} messages
        "metadata": {...},                # Any extra info (pdf_id, etc.)
        "updated_at": datetime            # When last updated
    }
    
    METHODS:
    --------
    - load(thread_id) → Load state from MongoDB
    - save(thread_id, state) → Save state to MongoDB
    - delete(thread_id) → Delete state from MongoDB
    """
    
    def __init__(self):
        """Initialize the checkpointer."""
        self.collection = _get_mongo_collection()
    
    def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        📖 Load State from MongoDB
        --------------------------
        Retrieves saved conversation state for a thread.
        
        Parameters:
        -----------
        thread_id: The unique identifier for the conversation
        
        Returns:
        --------
        The saved state dict, or None if not found
        
        🔗 In your notes, this happens automatically when you call:
            graph_with_mongo.invoke({"messages": [...]}, config)
            
        LangGraph's checkpointer loads the previous state behind the scenes!
        """
        if self.collection is None:
            return None
        
        try:
            doc = self.collection.find_one({"thread_id": thread_id})
            if doc:
                # Remove MongoDB's _id field before returning
                doc.pop("_id", None)
                print(f"📥 Loaded checkpoint for thread: {thread_id}")
                return doc
            return None
        except Exception as e:
            print(f"⚠️ Error loading checkpoint: {e}")
            return None
    
    def save(self, thread_id: str, state: Dict[str, Any]) -> bool:
        """
        📖 Save State to MongoDB
        ------------------------
        Persists conversation state for a thread.
        
        Parameters:
        -----------
        thread_id: The unique identifier for the conversation
        state: The state dict to save (messages, metadata, etc.)
        
        Returns:
        --------
        True if saved successfully, False otherwise
        
        🔗 In your notes, this happens automatically after:
            result = graph_with_mongo.invoke(...)
            
        LangGraph's checkpointer saves the new state behind the scenes!
        """
        if self.collection is None:
            return False
        
        try:
            # Add thread_id and timestamp to state
            doc = {
                "thread_id": thread_id,
                "messages": state.get("messages", []),
                "metadata": state.get("metadata", {}),
                "updated_at": datetime.utcnow()
            }
            
            # Upsert: Update if exists, insert if not
            self.collection.update_one(
                {"thread_id": thread_id},
                {"$set": doc},
                upsert=True
            )
            print(f"📤 Saved checkpoint for thread: {thread_id}")
            return True
        except Exception as e:
            print(f"⚠️ Error saving checkpoint: {e}")
            return False
    
    def delete(self, thread_id: str) -> bool:
        """
        📖 Delete State from MongoDB
        ----------------------------
        Removes saved conversation state for a thread.
        
        Parameters:
        -----------
        thread_id: The unique identifier for the conversation
        
        Returns:
        --------
        True if deleted successfully, False otherwise
        """
        if self.collection is None:
            return False
        
        try:
            self.collection.delete_one({"thread_id": thread_id})
            print(f"🗑️ Deleted checkpoint for thread: {thread_id}")
            return True
        except Exception as e:
            print(f"⚠️ Error deleting checkpoint: {e}")
            return False


# Global checkpointer instance
_checkpointer = MongoDBCheckpointer()
"""
📖 Why a global instance?
-------------------------
✔ We create ONE checkpointer that's reused for all requests
✔ This maintains the MongoDB connection efficiently
✔ Similar to how you'd use MongoDBSaver in your notes
"""


# =============================================================================
#                     GLOBAL MEMORY (Like ChatGPT's Memory Feature)
# =============================================================================
"""
📚 WHAT IS GLOBAL MEMORY?
-------------------------
Global Memory remembers things about YOU across ALL conversations.

🔗 THIS IS EXACTLY WHAT CHATGPT DOES!
When you tell ChatGPT "My name is Ankur", it remembers in ALL future chats.

📌 DIFFERENCE FROM THREAD MEMORY:
---------------------------------
Thread Memory: Remembers within ONE conversation
Global Memory: Remembers across ALL conversations

Example:
    Thread 1: "My name is Ankur" → Saved to GLOBAL memory
    Thread 2: "What's my name?" → Reads GLOBAL memory → "Ankur!"
    Thread 3: New chat → Still knows you're Ankur!

📌 WHAT WE STORE IN GLOBAL MEMORY:
----------------------------------
1. User's name
2. Preferences (how they like responses)
3. Note-taking style
4. Important facts about the user
5. Anything the user explicitly asks to remember

📌 HOW IT WORKS:
---------------
    User says something
        ↓
    AI detects if it's something to remember
        ↓
    If yes → Save to Global Memory (MongoDB)
        ↓
    In EVERY future chat → Load Global Memory first
        ↓
    AI knows user's preferences everywhere!
"""

# MongoDB collection for global user memory
GLOBAL_MEMORY_COLLECTION = "global_user_memory"
_global_memory_collection = None


def _get_global_memory_collection():
    """
    📖 Get Global Memory Collection
    -------------------------------
    Returns the MongoDB collection for storing user-wide memory.
    """
    global _global_memory_collection
    
    if _global_memory_collection is None:
        try:
            # Sanitize URI to ensure proper format
            sanitized_uri = _sanitize_mongo_uri(MONGODB_URI)
            client = MongoClient(sanitized_uri, serverSelectionTimeoutMS=5000)
            # Test connection immediately
            client.admin.command('ping')
            db = client[MONGODB_DB]
            _global_memory_collection = db[GLOBAL_MEMORY_COLLECTION]
            _global_memory_collection.create_index("user_id", unique=True)
            print(f"✅ Connected to Global Memory: {MONGODB_DB}.{GLOBAL_MEMORY_COLLECTION}")
        except Exception as e:
            print(f"⚠️ Global Memory not available: {e}")
            return None
    
    return _global_memory_collection


class GlobalMemory:
    """
    📖 Global Memory Class (Like ChatGPT's Memory)
    ==============================================
    
    Stores and retrieves user preferences that persist across ALL threads.
    
    🔗 THIS IS WHAT CHATGPT DOES!
    When you say "Remember that I prefer concise answers", 
    ChatGPT saves it and uses it in ALL future conversations.
    
    MEMORY STRUCTURE:
    -----------------
    {
        "user_id": "default",           # User identifier
        "name": "Ankur",                 # User's name
        "preferences": {
            "note_style": "detailed with examples",
            "response_length": "comprehensive",
            "tone": "friendly teacher"
        },
        "facts": [                       # Things to remember
            "Loves Python programming",
            "Learning AI/ML",
            "Preparing for interviews"
        ],
        "updated_at": datetime
    }
    """
    
    def __init__(self):
        self.collection = _get_global_memory_collection()
    
    def load(self, user_id: str = "default") -> Dict[str, Any]:
        """
        📖 Load Global Memory for User
        ------------------------------
        Gets all saved preferences and facts about the user.
        
        This is called at the START of every chat to give the AI
        context about who you are and how you like things.
        """
        if self.collection is None:
            return self._default_memory(user_id)
        
        try:
            doc = self.collection.find_one({"user_id": user_id})
            if doc:
                doc.pop("_id", None)
                print(f"🧠 Loaded global memory for user: {user_id}")
                return doc
            return self._default_memory(user_id)
        except Exception as e:
            print(f"⚠️ Error loading global memory: {e}")
            return self._default_memory(user_id)
    
    def _default_memory(self, user_id: str) -> Dict[str, Any]:
        """Default empty memory structure."""
        return {
            "user_id": user_id,
            "name": None,
            "preferences": {
                "note_style": None,
                "response_length": None,
                "tone": None
            },
            "facts": [],
            "updated_at": None
        }
    
    def save(self, user_id: str, memory: Dict[str, Any]) -> bool:
        """
        📖 Save Global Memory for User
        ------------------------------
        Persists user preferences and facts to MongoDB.
        """
        if self.collection is None:
            return False
        
        try:
            memory["user_id"] = user_id
            memory["updated_at"] = datetime.utcnow()
            
            self.collection.update_one(
                {"user_id": user_id},
                {"$set": memory},
                upsert=True
            )
            print(f"🧠 Saved global memory for user: {user_id}")
            return True
        except Exception as e:
            print(f"⚠️ Error saving global memory: {e}")
            return False
    
    def update_name(self, user_id: str, name: str) -> bool:
        """Update user's name in global memory."""
        memory = self.load(user_id)
        memory["name"] = name
        return self.save(user_id, memory)
    
    def add_fact(self, user_id: str, fact: str) -> bool:
        """Add a fact about the user to remember."""
        memory = self.load(user_id)
        if fact not in memory["facts"]:
            memory["facts"].append(fact)
            # Keep only last 20 facts to avoid bloat
            memory["facts"] = memory["facts"][-20:]
        return self.save(user_id, memory)
    
    def update_preference(self, user_id: str, key: str, value: str) -> bool:
        """Update a user preference."""
        memory = self.load(user_id)
        memory["preferences"][key] = value
        return self.save(user_id, memory)
    
    def clear(self, user_id: str) -> bool:
        """Clear all memory for a user."""
        if self.collection is None:
            return False
        try:
            self.collection.delete_one({"user_id": user_id})
            print(f"🗑️ Cleared global memory for user: {user_id}")
            return True
        except Exception:
            return False


# Global memory instance
_global_memory = GlobalMemory()


def _build_global_context(user_id: str = "default") -> str:
    """
    📖 Build Global Context String
    ------------------------------
    Creates a context string from global memory to inject into prompts.
    
    This is added to EVERY chat so the AI knows:
    - Who you are
    - How you like responses
    - Important facts about you
    
    🔗 This is exactly what ChatGPT does behind the scenes!
    """
    memory = _global_memory.load(user_id)
    
    context_parts = []
    
    # Add name if known
    if memory.get("name"):
        context_parts.append(f"The user's name is {memory['name']}.")
    
    # Add preferences
    prefs = memory.get("preferences", {})
    if prefs.get("note_style"):
        context_parts.append(f"The user prefers notes in this style: {prefs['note_style']}.")
    if prefs.get("response_length"):
        context_parts.append(f"The user prefers {prefs['response_length']} responses.")
    if prefs.get("tone"):
        context_parts.append(f"Use a {prefs['tone']} tone.")
    
    # Add facts
    facts = memory.get("facts", [])
    if facts:
        context_parts.append("Things to remember about this user:")
        for fact in facts:
            context_parts.append(f"  - {fact}")
    
    if not context_parts:
        return ""
    
    return "\n".join(context_parts)


# =============================================================================
#                     LANGGRAPH-STYLE CHAT WITH CHECKPOINTER
# =============================================================================

def run_chat_with_memory(
    query: str,
    thread_id: str,
    user_id: str = "default",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    📖 LangGraph-Style Chat with MongoDB Checkpointing + Global Memory
    ==================================================================
    
    This function implements the SAME pattern as your notes (07-LangGraph/graph.py)!
    PLUS: Global Memory like ChatGPT's "Memory" feature!
    
    🔗 YOUR NOTES:
        config = {"configurable": {"thread_id": "1"}}
        
        # Sanitize URI to ensure proper format
    sanitized_uri = _sanitize_mongo_uri(MONGODB_URI)
    with MongoDBSaver.from_conn_string(sanitized_uri) as mongo_checkpointer:
            graph_with_mongo = compile_graph_with_checkpointer(mongo_checkpointer)
            result = graph_with_mongo.invoke({"messages": [...]}, config)
    
    🔗 THIS FUNCTION DOES THE SAME THING + GLOBAL MEMORY:
        1. Load GLOBAL memory (name, preferences) ← Like ChatGPT!
        2. Load thread state (like checkpointer.load)
        3. Add new message
        4. Call LLM with global context + thread history
        5. Detect if user shared something to remember globally
        6. Save to global memory if needed ← Like ChatGPT!
        7. Save thread state (like checkpointer.save)
    
    Parameters:
    -----------
    query: The user's message
    thread_id: Unique conversation ID
    user_id: User identifier for global memory (default: "default")
    metadata: Optional extra data
    
    Returns:
    --------
    Dict with: answer, thread_id, message_count, memory_updated
    """
    
    # Step 1: Load GLOBAL memory (name, preferences)
    # -----------------------------------------------
    # 🔗 THIS IS WHAT CHATGPT DOES!
    # Before every chat, it loads what it knows about you.
    
    global_context = _build_global_context(user_id)
    global_memory = _global_memory.load(user_id)
    
    if global_context:
        print(f"🧠 Loaded global memory for user: {user_id}")
    
    # Step 2: Load previous thread state from MongoDB
    # -------------------------------------------------
    state = _checkpointer.load(thread_id) or {
        "messages": [],
        "metadata": metadata or {}
    }
    
    print(f"🧵 Thread {thread_id}: Loaded {len(state['messages'])} previous messages")
    
    # Step 3: Add user's message to state
    # ------------------------------------
    state["messages"].append({
        "role": "user",
        "content": query
    })
    
    # Step 4: Build messages for LLM (with GLOBAL context + thread history)
    # ----------------------------------------------------------------------
    # The system prompt now includes:
    # 1. Global memory (who the user is, preferences)
    # 2. Instructions on how to detect things to remember
    
    system_prompt = f"""
You are a helpful AI assistant with memory capabilities, just like ChatGPT.

📌 GLOBAL MEMORY (Things you know about this user across ALL conversations):
{global_context if global_context else "No information saved yet about this user."}

📌 YOUR CAPABILITIES:
1. You remember the user's name, preferences, and important facts
2. You can detect when the user shares something worth remembering
3. You adapt your responses based on their preferences

📌 MEMORY DETECTION RULES:
When the user says things like:
- "My name is X" → Remember their name
- "I prefer X style notes" → Remember their preference
- "Remember that I like X" → Save as a fact
- "I am learning X" → Save as a fact
- "I work at X" → Save as a fact

When you detect something to remember, include this EXACT format at the END of your response:
[MEMORY_UPDATE]
type: name OR preference OR fact
key: (for preferences: note_style, response_length, tone)
value: the value to save
[/MEMORY_UPDATE]

Only include memory updates when the user explicitly shares personal information.
Do NOT include memory updates for normal questions.

📌 RESPONSE STYLE:
- Be helpful, friendly, and conversational
- Use the user's name if you know it
- Adapt to their preferences if known
- Remember context from this conversation
"""
    
    messages_for_llm = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add conversation history (limit to last 20 messages for token efficiency)
    history = state["messages"][-20:]
    messages_for_llm.extend(history)
    
    # Step 5: Call LLM
    # -----------------
    memory_updated = False
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for_llm
        )
        
        assistant_reply = response.choices[0].message.content
        
        # Step 6: Check for memory updates in the response
        # -------------------------------------------------
        # 🔗 THIS IS WHAT CHATGPT DOES!
        # It detects when you share something and saves it.
        
        if "[MEMORY_UPDATE]" in assistant_reply:
            memory_updated = _process_memory_update(assistant_reply, user_id)
            # Remove the memory update tag from visible response
            assistant_reply = assistant_reply.split("[MEMORY_UPDATE]")[0].strip()
        
    except Exception as e:
        assistant_reply = f"Sorry, I encountered an error: {str(e)}"
    
    # Step 7: Add assistant's response to state
    # ------------------------------------------
    state["messages"].append({
        "role": "assistant",
        "content": assistant_reply
    })
    
    # Update metadata if provided
    if metadata:
        state["metadata"].update(metadata)
    
    # Step 8: Save updated state to MongoDB
    # --------------------------------------
    _checkpointer.save(thread_id, state)
    
    print(f"🧵 Thread {thread_id}: Now has {len(state['messages'])} messages")
    
    return {
        "answer": assistant_reply,
        "thread_id": thread_id,
        "message_count": len(state["messages"]),
        "memory_updated": memory_updated
    }


def _process_memory_update(response: str, user_id: str) -> bool:
    """
    📖 Process Memory Update from AI Response
    -----------------------------------------
    Parses the AI's response for memory update instructions and saves them.
    
    🔗 THIS IS WHAT CHATGPT DOES!
    When you say "My name is Ankur", ChatGPT extracts and saves it.
    
    Format expected:
    [MEMORY_UPDATE]
    type: name OR preference OR fact
    key: (optional, for preferences)
    value: the value to save
    [/MEMORY_UPDATE]
    """
    try:
        # Extract the memory update block
        start = response.find("[MEMORY_UPDATE]")
        end = response.find("[/MEMORY_UPDATE]")
        
        if start == -1 or end == -1:
            return False
        
        block = response[start + len("[MEMORY_UPDATE]"):end].strip()
        lines = block.split("\n")
        
        update_type = None
        key = None
        value = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("type:"):
                update_type = line.split(":", 1)[1].strip().lower()
            elif line.startswith("key:"):
                key = line.split(":", 1)[1].strip().lower()
            elif line.startswith("value:"):
                value = line.split(":", 1)[1].strip()
        
        if not update_type or not value:
            return False
        
        # Save to global memory based on type
        if update_type == "name":
            _global_memory.update_name(user_id, value)
            print(f"🧠 Saved name: {value}")
            return True
        
        elif update_type == "preference" and key:
            _global_memory.update_preference(user_id, key, value)
            print(f"🧠 Saved preference {key}: {value}")
            return True
        
        elif update_type == "fact":
            _global_memory.add_fact(user_id, value)
            print(f"🧠 Saved fact: {value}")
            return True
        
        return False
        
    except Exception as e:
        print(f"⚠️ Error processing memory update: {e}")
        return False


# =============================================================================
#                     THE AGENT: RUN AGENT FUNCTION
# =============================================================================

def run_agent(query: str, session_id: str = "default") -> Dict[str, Any]:
    """
    📖 Run Agent - THE MAIN AGENT LOGIC
    ===================================
    
    This function runs the AI agent that can:
    1. PLAN - Think about what to do
    2. ACTION - Call a tool (web_search)
    3. OBSERVE - See the tool results
    4. OUTPUT - Give final answer
    
    🔗 THIS IS EXACTLY YOUR NOTES (03-Agents/main.py)!
    
    Let me map your notes code to this function:
    
    YOUR NOTES                          THIS FUNCTION
    ----------                          --------------
    while True:                         while True:
        response = client.chat...           response = client.chat...
        parsed_response = json...           parsed = json.loads(...)
        
        if step == "plan":                  if step == "plan":
            print(plan content)                 steps.append(...)
            continue                            continue
            
        if step == "action":                if step == "action":
            tool_name = ...                     tool_name = parsed.get("function")
            tool_input = ...                    tool_input = parsed.get("input")
            output = available_tools[...]       observation = web_search(...)
            messages.append(observe)            messages.append(observe)
            continue                            continue
            
        if step == "output":                if step == "output":
            print(final answer)                 return {"answer": ...}
            break
    
    Parameters:
    -----------
    query: User's question (e.g., "What's the weather in NYC?")
    session_id: Conversation session identifier
    
    Returns:
    --------
    Dict with: answer, steps (for debugging), session_id
    """
    
    # Get current date/time for the agent to use
    date_str = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    
    # =============================================================================
    # SYSTEM PROMPT - Instructions for the Agent
    # =============================================================================
    
    # Get dynamic tools description from tools_service
    tools_description = get_tools_description()
    
    SYSTEM_PROMPT = f"""
        You are a helpful AI Assistant specialized in resolving user queries.
        You work in start → plan → action → observe → output mode.
        
        Today is {date_str}.
        
        For the given user query and available tools, plan the step-by-step execution.
        If the user asks for live information or presses a "Web Search" button,
        you MUST call the appropriate tool.
        
        Rules:
        1. Follow the strict JSON output format below.
        2. Always perform one step at a time and wait for next input.
        3. Carefully analyze the user query.
        4. Show your thinking process in the "content" field during plan steps.
        
        Output JSON Format:
        {{
            "step": "string",              // one of: plan, action, observe, output
            "content": "string",           // explanation for plan/output steps
            "function": "string or null",  // name of function if the step is action
            "input": "object or null"      // input parameters for the function (as JSON object)
        }}
        
        {tools_description}
        
        ═══════════════════════════════════════════════════════════════════════════
        📈 SPECIAL: INDIAN STOCK MARKET RESEARCH WORKFLOW
        ═══════════════════════════════════════════════════════════════════════════
        
        When user asks about INDIAN STOCKS (Tata, Reliance, HDFC, Infosys, etc.):
        
        STEP 1 - SECTOR CHECK:
        - First, understand which sector the company belongs to
        - Search for sector trends: "EV sector growth India 2024"
        
        STEP 2 - COMPANY CHECK:
        - Use "indian_stock_search" (NOT regular web_search!)
        - Search for company news: "Tata Motors latest news quarterly results"
        - This searches ONLY: MoneyControl, Screener.in, Economic Times
        
        STEP 3 - POLICY CHECK:
        - Search for government policies that might affect the company
        - Example: "government policy EV sector India 2024"
        
        STEP 4 - FINAL OUTPUT:
        - Summarize findings from all searches
        - Give your assessment (bullish/bearish with reasons)
        - ALWAYS add this disclaimer at the end:
          "⚠️ This is not financial advice. Please do your own research before investing."
        
        STEP 5 - ENGAGEMENT (Optional):
        - After giving analysis, ask: "Are you planning to invest in this stock?"
        
        ═══════════════════════════════════════════════════════════════════════════
        
        Example Flow for Stock Query:
        User: "Tell me about Tata Motors stock"
        
        Output: {{"step": "plan", "content": "🔍 User is asking about Tata Motors stock. This is an Indian company in the auto sector. I'll do a comprehensive analysis: 1) Check sector trends, 2) Get company news from trusted sources, 3) Check for policy impacts."}}
        
        Output: {{"step": "action", "function": "indian_stock_search", "input": {{"query": "Tata Motors stock news quarterly results 2024"}}}}
        [You receive MoneyControl/Screener results]
        
        Output: {{"step": "observe", "content": "📊 Found news about Q3 results and EV segment growth..."}}
        
        Output: {{"step": "action", "function": "search_news", "input": {{"query": "auto sector India government policy 2024"}}}}
        [You receive policy news]
        
        Output: {{"step": "observe", "content": "📋 Found policy about EV subsidies..."}}
        
        Output: {{"step": "output", "content": "📈 **Tata Motors Analysis**\\n\\n**Sector:** Auto/EV - Growing...\\n\\n**Company:** Strong Q3...\\n\\n**Policy:** Government supporting EV...\\n\\n**Assessment:** Moderately bullish...\\n\\n⚠️ This is not financial advice. Please do your own research before investing.\\n\\nAre you planning to invest in this stock?"}}
        
        ═══════════════════════════════════════════════════════════════════════════
        
        Example Flow for General Query:
        User: "What is the latest news about AI?"
        Output: {{"step": "plan", "content": "User wants latest AI news. I should search the web."}}
        Output: {{"step": "action", "function": "web_search", "input": {{"query": "latest AI news 2024"}}}}
        [You receive search results]
        Output: {{"step": "observe", "content": "I got search results about AI developments"}}
        Output: {{"step": "output", "content": "Here are the latest AI news..."}}
        
        Example Flow for Weather Query:
        User: "What's the weather in Mumbai?"
        Output: {{"step": "plan", "content": "User wants weather info. I'll use the weather tool."}}
        Output: {{"step": "action", "function": "get_weather", "input": {{"city": "Mumbai"}}}}
        [You receive weather data]
        Output: {{"step": "output", "content": "The current weather in Mumbai is..."}}
    """
    """
    📖 What is this System Prompt?
    ------------------------------
    This tells the agent:
    1. WHO it is (helpful AI assistant)
    2. HOW to behave (plan → action → observe → output)
    3. WHAT tools it has (web_search)
    4. WHAT format to use (JSON output)
    
    🔗 In your notes (03-Agents/main.py):
        SYSTEM_PROMPT = '''You are an helpful AI Assistant...
            You work on start, plan, action, observe, mode.
            ...
            Available Tools:
                - "get_weather": ...
                - "run_command": ...
        '''
    
    Same pattern!
    """
    
    # =============================================================================
    # BUILD INITIAL MESSAGES
    # =============================================================================
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # Load conversation history for context
    shared_history = _load_shared_history()
    session_history = _load_history(session_id)
    combined = [*shared_history, *session_history]
    
    if combined:
        messages.extend(combined)
    
    # Add current user query
    messages.append({"role": "user", "content": query})
    
    """
    📖 Why do we add history?
    -------------------------
    So the agent remembers previous conversations!
    
    Without history:
        User: "My name is Ankur"
        Agent: "Nice to meet you!"
        User: "What's my name?"
        Agent: "I don't know your name."  ← No memory!
    
    With history:
        User: "My name is Ankur"
        Agent: "Nice to meet you!"
        User: "What's my name?"  
        Agent: "Your name is Ankur!"  ← Remembers from history!
    
    🔗 In your notes (03-Agents/main.py):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        while True:
            messages.append({"role": "user", "content": query})
            ...
            messages.append({"role": "assistant", "content": response})
    """
    
    # Track agent steps (for debugging/UI)
    steps: List[Dict[str, Any]] = []
    
    # =============================================================================
    # THE AGENT LOOP
    # =============================================================================
    
    while True:
        """
        📖 The Agent Loop
        -----------------
        This loop continues until the agent outputs a final answer.
        
        Each iteration:
        1. Send messages to GPT
        2. Parse the JSON response
        3. Handle based on "step" type:
            - plan: Continue planning
            - action: Execute a tool
            - output: Return final answer
        
        🔗 In your notes (03-Agents/main.py):
            while True:  # Outer loop for multiple queries
                while True:  # Inner loop for agent steps
                    response = client.chat.completions.create(...)
                    ...
        """
        
        # Call OpenAI GPT
        response = client.chat.completions.create(
            model="gpt-4o-mini",         # Using cost-effective model
            response_format={"type": "json_object"},  # Force JSON output
            messages=messages
        )
        """
        📖 What is response_format={"type": "json_object"}?
        ---------------------------------------------------
        This tells GPT to ONLY output valid JSON.
        
        Without this, GPT might output:
            "I'll search for that. {"step": "action"..."
            
        With this, GPT outputs ONLY:
            {"step": "action", "function": "web_search", ...}
        
        This is crucial for parsing the response!
        
        🔗 In your notes (03-Agents/main.py):
            response = client.chat.completions.create(
                model="gpt-4.1",
                response_format={"type": "json_object"},  ← Same!
                messages=messages
            )
        """
        
        # Extract and parse response
        content = response.choices[0].message.content
        messages.append({"role": "assistant", "content": content})
        
        parsed = json.loads(content)
        """
        📖 Parsing JSON Response
        ------------------------
        GPT returns a string like:
            '{"step": "plan", "content": "I need to search..."}'
            
        json.loads() converts this to a Python dict:
            {"step": "plan", "content": "I need to search..."}
        
        🔗 In your notes (03-Agents/main.py):
            parsed_response = json.loads(response.choices[0].message.content)
        """
        
        step = parsed.get("step")
        
        # Track step for debugging/UI
        if step:
            steps.append({"step": step, "payload": parsed})
        
        # ---------------------------------------------------------------------
        # HANDLE: PLAN STEP
        # ---------------------------------------------------------------------
        if step == "plan":
            """
            📖 Plan Step
            ------------
            Agent is thinking/planning.
            We just continue to let it process more.
            
            🔗 In your notes (03-Agents/main.py):
                if parsed_response.get("step") == "plan":
                    print(f"🧠: {parsed_response.get('content')}")
                    continue
            """
            continue
        
        # ---------------------------------------------------------------------
        # HANDLE: ACTION STEP (Tool Execution)
        # ---------------------------------------------------------------------
        if step == "action":
            """
            📖 Action Step
            --------------
            Agent wants to use a tool.
            We execute the tool and add results as observation.
            
            🔗 In your notes (03-Agents/main.py):
                if parsed_response.get("step") == "action":
                    tool_name = parsed_response.get("function")
                    tool_input = parsed_response.get("input")
                    
                    print(f"🛠️: Calling Tool:{tool_name} with input {tool_input}")
                    
                    if available_tools.get(tool_name):
                        output = available_tools[tool_name](tool_input)
                        messages.append({
                            "role": "user",
                            "content": json.dumps({"step": "observe", "output": output})
                        })
                        continue
            
            📌 NEW: We now have multiple tools!
            ----------------------------------
            - web_search: General search (Tavily + DuckDuckGo)
            - indian_stock_search: Indian finance sites only
            - get_weather: Weather data
            - get_current_datetime: Date/time info
            - search_news: News articles
            """
            
            tool_name = parsed.get("function")
            tool_input = parsed.get("input")
            
            print(f"🛠️ Agent calling tool: {tool_name}")
            print(f"📥 Input: {tool_input}")
            
            # Execute the requested tool
            observation = {"error": f"Tool '{tool_name}' not found"}
            
            try:
                if tool_name == "web_search":
                    # Smart web search (Tavily + DuckDuckGo fallback)
                    query_str = tool_input.get("query") if isinstance(tool_input, dict) else tool_input or query
                    observation = smart_web_search(query_str)
                    print(f"🔍 Web search completed: {len(observation.get('results', []))} results")
                    
                elif tool_name == "indian_stock_search":
                    # Indian stock market search (MoneyControl, Screener, etc.)
                    query_str = tool_input.get("query") if isinstance(tool_input, dict) else tool_input
                    observation = indian_stock_search(query_str)
                    print(f"📈 Indian stock search completed: {len(observation.get('results', []))} results")
                    
                elif tool_name == "get_weather":
                    # Weather lookup
                    city = tool_input.get("city") if isinstance(tool_input, dict) else tool_input
                    observation = get_weather(city)
                    print(f"🌤️ Weather fetched for: {city}")
                    
                elif tool_name == "get_current_datetime":
                    # Current date/time
                    observation = get_current_datetime()
                    print(f"📅 Date/time fetched: {observation.get('formatted')}")
                    
                elif tool_name == "search_news":
                    # News search
                    query_str = tool_input.get("query") if isinstance(tool_input, dict) else tool_input
                    observation = search_news(query_str)
                    print(f"📰 News search completed: {len(observation.get('results', []))} results")
                    
                else:
                    observation = {"error": f"Unknown tool: {tool_name}"}
                    print(f"❌ Unknown tool requested: {tool_name}")
                    
            except Exception as e:
                observation = {"error": f"Tool execution failed: {str(e)}"}
                print(f"❌ Tool error: {e}")
            
            # Add observation to messages
            messages.append({
                "role": "user",
                "content": json.dumps({"step": "observe", "output": observation})
            })
            """
            📖 Why add observation as user message?
            ---------------------------------------
            After calling a tool, the agent needs to "see" the results.
            We add the tool output as a user message so the agent
            can process it in the next iteration.
            
            This simulates the observe step:
            1. Agent requests action (call tool)
            2. We execute the tool
            3. We tell agent "here are the results" (observe)
            4. Agent processes results and continues
            
            🔗 In your notes (03-Agents/main.py):
                messages.append({
                    "role": "user",
                    "content": json.dumps({"step": "observe", "output": output})
                })
            """
            continue
        
        # ---------------------------------------------------------------------
        # HANDLE: OUTPUT STEP (Final Answer)
        # ---------------------------------------------------------------------
        if step == "output":
            """
            📖 Output Step
            --------------
            Agent has the final answer. We save to memory and return.
            
            🔗 In your notes (03-Agents/main.py):
                if parsed_response.get("step") == "output":
                    print(f"🤖: {parsed_response.get('content')}")
                    break
            """
            
            answer = parsed.get("content")
            
            # Save to session memory
            session_history = _load_history(session_id)
            session_history.extend([
                {"role": "user", "content": query},
                {"role": "assistant", "content": answer}
            ])
            _save_history(session_id, session_history)
            
            # Save to shared memory (for cross-session recall)
            shared_history = _load_shared_history()
            shared_history.extend([
                {"role": "user", "content": query},
                {"role": "assistant", "content": answer}
            ])
            _save_shared_history(shared_history)
            
            return {
                "answer": answer,
                "steps": steps,  # All steps for debugging/UI
                "session_id": session_id
            }
        
        # ---------------------------------------------------------------------
        # SAFETY: Prevent Infinite Loops
        # ---------------------------------------------------------------------
        if len(steps) > 8:
            """
            📖 Safety Limit
            ---------------
            If agent takes more than 8 steps, something might be wrong.
            Stop to prevent infinite loops.
            """
            return {
                "answer": "Stopped: too many steps.",
                "steps": steps,
                "session_id": session_id
            }


# =============================================================================
#                     API ENDPOINTS
# =============================================================================

@agent_router.post("/agent/web-search")
def agent_web_search(payload: Dict[str, str]):
    """
    📖 Agent Web Search Endpoint
    ----------------------------
    HTTP POST to: http://localhost:8000/agent/web-search
    Body: { "query": "What's the weather?", "session_id": "optional" }
    
    This endpoint:
    1. Takes a user query
    2. Runs the agent with web search capability
    3. Returns the answer with agent steps
    
    📌 This is called by your Frontend when user clicks "Web Search"
    """
    query = payload.get("query")
    session_id = payload.get("session_id") or "default"
    
    if not query:
        raise HTTPException(status_code=400, detail="missing query")
    
    try:
        result = run_agent(query, session_id=session_id)
        return result
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Agent search failed: {err}")


@agent_router.post("/agent/reset-memory")
def reset_agent_memory(payload: Dict[str, str]):
    """
    📖 Reset Memory Endpoint
    ------------------------
    HTTP POST to: http://localhost:8000/agent/reset-memory
    Body: { "session_id": "optional" }
    
    Clears conversation memory for the specified session.
    Useful when user wants to start a fresh conversation.
    """
    session_id = payload.get("session_id") or "default"
    _reset_history(session_id)
    return {"status": "cleared", "session_id": session_id}


# =============================================================================
#                     🆕 LANGGRAPH STOCK RESEARCH ENDPOINT
# =============================================================================

# =============================================================================
#                     🆕 LANGGRAPH TRAVEL PLANNER ENDPOINT
# =============================================================================

@agent_router.post("/agent/travel-planner")
def langgraph_travel_planner(payload: Dict[str, Any]):
    """
    📖 LangGraph Travel Planner Endpoint
    ====================================
    
    HTTP POST to: http://localhost:8000/agent/travel-planner
    Body: { 
        "query": "Plan a trip to Goa from Mumbai",
        "source": "Mumbai",        // optional
        "destination": "Goa",      // optional
        "preferences": {           // optional (Human-in-Loop)
            "vehicle_type": "petrol",
            "food_preference": "veg",
            "is_smoker": false,
            "budget": "midrange",
            "interested_in_adventure": true,
            "travel_mode": "car"
        }
    }
    
    🧳 THIS USES LANGGRAPH! (8-Node Workflow)
    
    📌 THE WORKFLOW:
    ---------------
    START → destination_researcher → transport_finder → accommodation_finder →
    activities_planner → food_shopping_guide → travel_requirements →
    emergency_safety → package_builder → END
    
    📌 OUTPUT:
    ---------
    3 Travel Packages:
    1. Website Package 1 (MakeMyTrip)
    2. Website Package 2 (Yatra)
    3. DIY Solo Plan (Personalized)
    
    📌 FOR INTERVIEW:
    ----------------
    "I built a Travel Planner using LangGraph with 8 specialized nodes.
    Each node handles a specific aspect - destination research, transport,
    hotels, activities, food, requirements, emergency info, and final
    package building. It creates 3 travel packages including a personalized
    DIY plan based on user preferences."
    """
    query = payload.get("query")
    source = payload.get("source")
    destination = payload.get("destination")
    preferences = payload.get("preferences")
    
    if not query:
        raise HTTPException(status_code=400, detail="missing query")
    
    try:
        print("\n" + "="*60)
        print("🧳 LANGGRAPH TRAVEL PLANNER REQUESTED")
        print("="*60)
        print(f"Query: {query}")
        print(f"Source: {source or 'auto-detect'}")
        print(f"Destination: {destination or 'auto-detect'}")
        print(f"Preferences: {preferences or 'defaults'}")
        
        # Import and run travel planner
        from travel_graph import run_travel_planner
        result = run_travel_planner(query, source, destination, preferences)
        
        return {
            "success": True,
            "query": query,
            "workflow": "langgraph_travel",
            "nodes_executed": [
                "destination_researcher",
                "transport_finder",
                "accommodation_finder",
                "activities_planner",
                "food_shopping_guide",
                "travel_requirements",
                "emergency_safety",
                "package_builder"
            ],
            "source": result.get("source"),
            "destination": result.get("destination"),
            "destination_info": result.get("destination_info"),
            "transport_info": result.get("transport_info"),
            "accommodation_info": result.get("accommodation_info"),
            "activities_info": result.get("activities_info"),
            "food_shopping_info": result.get("food_shopping_info"),
            "requirements_info": result.get("requirements_info"),
            "emergency_info": result.get("emergency_info"),
            "packages": result.get("packages"),
            "final_summary": result.get("final_summary"),
            "error": result.get("error")
        }
        
    except Exception as err:
        print(f"❌ LangGraph travel planner failed: {err}")
        raise HTTPException(status_code=500, detail=f"Travel planner failed: {err}")


# =============================================================================
#                     SOLO TRIP PLANNER WITH HUMAN-IN-THE-LOOP
# =============================================================================

from solo_trip_graph import start_solo_trip, resume_solo_trip

@agent_router.post("/agent/solo-trip/start")
def start_solo_trip_endpoint(payload: Dict[str, Any]):
    """
    📖 Start Solo Trip Planning with Human-in-the-Loop
    ===================================================
    
    HTTP POST to: http://localhost:8000/agent/solo-trip/start
    Body: { 
        "query": "Plan a solo trip from Delhi to Goa",
        "thread_id": "optional_custom_id"
    }
    
    This endpoint:
    1. Runs initial research (destination, transport options)
    2. PAUSES at human_preferences node (interrupt)
    3. Returns questions for user to answer
    
    Frontend shows a modal with the questions.
    User fills and submits → calls /agent/solo-trip/resume
    """
    query = payload.get("query", "")
    thread_id = payload.get("thread_id", f"solo_trip_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    print("\n" + "="*60)
    print("🎒 STARTING SOLO TRIP PLANNER (HITL)")
    print("="*60)
    print(f"Query: {query}")
    print(f"Thread ID: {thread_id}")
    
    try:
        result = start_solo_trip(query, thread_id)
        
        return {
            "success": True,
            "status": result.get("status"),
            "thread_id": thread_id,
            "message": result.get("message"),
            # If interrupted, send the questions
            "questions": result.get("interrupt_data", {}).get("human_questions") if result.get("status") == "awaiting_input" else None,
            # Initial research data - extract from state properly
            "origin": (result.get("interrupt_data", {}) or {}).get("origin") if result.get("status") == "awaiting_input" else None,
            "destination": (result.get("interrupt_data", {}) or {}).get("destination") if result.get("status") == "awaiting_input" else None,
            "distance_km": (result.get("interrupt_data", {}) or {}).get("distance_km") if result.get("status") == "awaiting_input" else None,
            "destination_info": result.get("interrupt_data", {}).get("destination_info") if result.get("status") == "awaiting_input" else None,
            "transport_options": result.get("interrupt_data", {}).get("transport_options") if result.get("status") == "awaiting_input" else None,
            # If already complete (unlikely on start)
            "final_package": result.get("result", {}).get("final_package") if result.get("status") == "complete" else None
        }
        
    except Exception as err:
        print(f"❌ Solo trip start failed: {err}")
        raise HTTPException(status_code=500, detail=f"Solo trip failed: {err}")


@agent_router.post("/agent/solo-trip/resume")
def resume_solo_trip_endpoint(payload: Dict[str, Any]):
    """
    📖 Resume Solo Trip Planning with User Preferences
    ===================================================
    
    HTTP POST to: http://localhost:8000/agent/solo-trip/resume
    Body: { 
        "thread_id": "solo_trip_xxx",
        "preferences": {
            "travel_mode": "personal_vehicle",
            "vehicle_make": "Tata",
            "vehicle_model": "Nexon EV",
            "fuel_type": "ev",
            "ev_range": 350,
            "current_charge": 100,
            "food_preference": "veg",
            "budget_level": "mid_range",
            "accommodation_type": "hotel"
        }
    }
    
    This endpoint:
    1. Resumes the paused graph with user preferences
    2. Runs remaining nodes (personalized transport, accommodation, etc.)
    3. Returns the complete solo trip package
    """
    thread_id = payload.get("thread_id", "")
    preferences = payload.get("preferences", {})
    
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")
    
    if not preferences:
        raise HTTPException(status_code=400, detail="preferences are required")
    
    print("\n" + "="*60)
    print("🎒 RESUMING SOLO TRIP PLANNER")
    print("="*60)
    print(f"Thread ID: {thread_id}")
    print(f"Preferences: {preferences}")
    
    try:
        result = resume_solo_trip(thread_id, preferences)
        
        return {
            "success": True,
            "status": result.get("status"),
            "thread_id": thread_id,
            "final_package": result.get("final_package")
        }
        
    except Exception as err:
        print(f"❌ Solo trip resume failed: {err}")
        raise HTTPException(status_code=500, detail=f"Solo trip resume failed: {err}")


@agent_router.post("/agent/stock-research")
def langgraph_stock_research(payload: Dict[str, Any]):
    """
    📖 LangGraph Stock Research Endpoint
    ====================================
    
    HTTP POST to: http://localhost:8000/agent/stock-research
    Body: { 
        "query": "Tell me about Tata Motors stock",
        "company_name": "Tata Motors"  // optional
    }
    
    🔗 THIS USES LANGGRAPH! (Stage 2)
    
    Unlike /agent/web-search which uses a prompt-based workflow,
    this endpoint uses actual LangGraph nodes:
    
    START → sector_analyst → company_researcher → policy_watchdog → final_advisor → END
    
    📌 THE DIFFERENCE:
    ------------------
    /agent/web-search:
        - Uses system prompt to guide behavior
        - Agent decides steps dynamically
        - More flexible, less predictable
    
    /agent/stock-research:
        - Uses LangGraph StateGraph
        - Fixed 4-node workflow
        - Predictable, thorough analysis
        - Each node has specific responsibility
    
    📌 NODES:
    ---------
    1. sector_analyst     → Analyzes sector trends
    2. company_researcher → Gets data from MoneyControl, Screener
    3. policy_watchdog    → Checks government policies
    4. final_advisor      → Combines and recommends
    
    📌 FOR YOUR INTERVIEW:
    ----------------------
    "I implemented two approaches: a flexible agent-based workflow for
    general queries, and a structured LangGraph workflow for stock
    research that ensures thorough analysis across sector, company,
    and policy dimensions."
    """
    query = payload.get("query")
    company_name = payload.get("company_name")
    
    if not query:
        raise HTTPException(status_code=400, detail="missing query")
    
    try:
        print("\n" + "="*60)
        print("📈 LANGGRAPH STOCK RESEARCH REQUESTED")
        print("="*60)
        print(f"Query: {query}")
        print(f"Company: {company_name or 'auto-detect'}")
        
        # Run the LangGraph workflow
        result = run_stock_research(query, company_name)
        
        return {
            "success": True,
            "query": query,
            "company_name": result.get("company_name"),
            "workflow": "langgraph",
            "nodes_executed": [
                "company_intro",           # Node 1: Company Introduction
                "sector_analyst",          # Node 2: Sector Analysis
                "company_researcher",      # Node 3: Company Research
                "policy_watchdog",         # Node 4: Policy Analysis
                "investor_sentiment",      # Node 5: Investor Sentiment
                "technical_analysis",      # Node 6: Technical Analysis & Risk
                "investment_suggestion"    # Node 7: Investment Suggestion
            ],
            # All 7 node outputs
            "company_intro": result.get("company_intro"),
            "sector_analysis": result.get("sector_analysis"),
            "company_research": result.get("company_research"),
            "policy_analysis": result.get("policy_analysis"),
            "investor_sentiment": result.get("investor_sentiment"),
            "technical_analysis": result.get("technical_analysis"),
            "investment_suggestion": result.get("investment_suggestion"),
            "final_recommendation": result.get("final_recommendation"),
            # Risk flags
            "risk_warnings": result.get("risk_warnings", []),
            "has_negative_news": result.get("has_negative_news", False),
            "is_overbought": result.get("is_overbought", False),
            "is_speculative": result.get("is_speculative", False),
            "error": result.get("error")
        }
        
    except Exception as err:
        print(f"❌ LangGraph stock research failed: {err}")
        raise HTTPException(status_code=500, detail=f"Stock research failed: {err}")


# =============================================================================
#                     LANGGRAPH-STYLE CHAT ENDPOINTS
# =============================================================================

@agent_router.post("/chat/with-memory")
def chat_with_memory_endpoint(payload: Dict[str, Any]):
    """
    📖 LangGraph-Style Chat with MongoDB Checkpointing + Global Memory
    ===================================================================
    
    HTTP POST to: http://localhost:8000/chat/with-memory
    Body: { 
        "query": "Hello, my name is Ankur",
        "thread_id": "abc123",
        "user_id": "optional",                # For global memory (default: "default")
        "metadata": {"pdf_id": "optional"}    # optional
    }
    
    🔗 THIS IS ALIGNED WITH YOUR NOTES (07-LangGraph/graph.py)!
    🔗 PLUS: Global Memory like ChatGPT's "Memory" feature!
    
    📌 KEY FEATURES:
    ----------------
    1. ✅ Thread Memory - Persists conversation to MongoDB
    2. ✅ Global Memory - Remembers name/preferences across ALL threads (like ChatGPT!)
    3. ✅ Auto-detects when user shares info worth remembering
    4. ✅ Uses thread_id for conversation isolation
    5. ✅ Uses user_id for cross-thread memory
    
    📌 EXAMPLE:
    -----------
    Thread 1: "My name is Ankur" → Saved to GLOBAL memory
    Thread 2: "What's my name?" → Knows "Ankur" from global memory!
    
    📌 COMPARISON:
    --------------
    /agent/web-search → Uses tools, for web search
    /chat/with-memory → MongoDB persistence + Global Memory (like ChatGPT!)
    """
    query = payload.get("query")
    thread_id = payload.get("thread_id")
    user_id = payload.get("user_id", "default")
    metadata = payload.get("metadata")
    
    if not query:
        raise HTTPException(status_code=400, detail="missing query")
    
    if not thread_id:
        raise HTTPException(status_code=400, detail="missing thread_id")
    
    try:
        result = run_chat_with_memory(
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            metadata=metadata
        )
        return result
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Chat failed: {err}")


@agent_router.get("/chat/history/{thread_id}")
def get_chat_history(thread_id: str):
    """
    📖 Get Chat History from MongoDB
    ================================
    
    HTTP GET to: http://localhost:8000/chat/history/{thread_id}
    
    Returns the saved conversation history for a thread.
    
    🔗 This is useful for:
    - Loading previous messages when user opens an old thread
    - Debugging what's in the checkpointed state
    
    Returns:
    --------
    {
        "thread_id": "abc123",
        "messages": [...],
        "metadata": {...},
        "message_count": 10
    }
    """
    state = _checkpointer.load(thread_id)
    
    if not state:
        return {
            "thread_id": thread_id,
            "messages": [],
            "metadata": {},
            "message_count": 0
        }
    
    return {
        "thread_id": thread_id,
        "messages": state.get("messages", []),
        "metadata": state.get("metadata", {}),
        "message_count": len(state.get("messages", []))
    }


@agent_router.delete("/chat/history/{thread_id}")
def delete_chat_history(thread_id: str):
    """
    📖 Delete Chat History from MongoDB
    ===================================
    
    HTTP DELETE to: http://localhost:8000/chat/history/{thread_id}
    
    Deletes the saved conversation history for a thread.
    
    🔗 This is useful for:
    - Clearing a conversation completely
    - Starting fresh in a thread
    """
    success = _checkpointer.delete(thread_id)
    
    return {
        "thread_id": thread_id,
        "deleted": success
    }


# =============================================================================
#                     GLOBAL MEMORY ENDPOINTS (Like ChatGPT!)
# =============================================================================

@agent_router.get("/memory/{user_id}")
def get_global_memory(user_id: str = "default"):
    """
    📖 Get Global Memory (Like ChatGPT's Memory)
    ============================================
    
    HTTP GET to: http://localhost:8000/memory/default
    
    Returns everything the AI remembers about you across ALL conversations.
    
    🔗 THIS IS LIKE CHATGPT's "Manage Memory" FEATURE!
    
    Returns:
    --------
    {
        "user_id": "default",
        "name": "Ankur",
        "preferences": {
            "note_style": "detailed with examples",
            "response_length": "comprehensive"
        },
        "facts": [
            "Loves Python programming",
            "Learning AI/ML"
        ]
    }
    """
    memory = _global_memory.load(user_id)
    return memory


@agent_router.post("/memory/{user_id}")
def update_global_memory(user_id: str, payload: Dict[str, Any]):
    """
    📖 Update Global Memory Manually
    ================================
    
    HTTP POST to: http://localhost:8000/memory/default
    Body: {
        "name": "Ankur",
        "preferences": {"note_style": "concise"},
        "facts": ["Loves Python"]
    }
    
    Allows you to manually set memory without chatting.
    
    🔗 Like ChatGPT's "Add memory" feature!
    """
    memory = _global_memory.load(user_id)
    
    if "name" in payload:
        memory["name"] = payload["name"]
    
    if "preferences" in payload:
        memory["preferences"].update(payload["preferences"])
    
    if "facts" in payload:
        for fact in payload["facts"]:
            if fact not in memory["facts"]:
                memory["facts"].append(fact)
    
    success = _global_memory.save(user_id, memory)
    
    return {
        "user_id": user_id,
        "updated": success,
        "memory": memory
    }


@agent_router.delete("/memory/{user_id}")
def clear_global_memory(user_id: str = "default"):
    """
    📖 Clear Global Memory
    ======================
    
    HTTP DELETE to: http://localhost:8000/memory/default
    
    Deletes all saved memory for a user.
    
    🔗 Like ChatGPT's "Clear memory" feature!
    
    ⚠️ This will make the AI forget everything about you!
    """
    success = _global_memory.clear(user_id)
    
    return {
        "user_id": user_id,
        "cleared": success
    }


# =============================================================================
#                     🆕 SMART AI - AUTOMATIC TOOL DETECTION
# =============================================================================
"""
📚 WHAT IS SMART AI?
--------------------
Smart AI automatically detects when the user's query needs tools.

BEFORE (Manual):
- User must click "Web Search" button to enable search
- User must click "Stock Research" button for stocks

NOW (Smart AI):
- User just types naturally
- AI automatically decides if tools are needed
- Falls back to web search if AI doesn't have current info

📌 HOW IT WORKS:
---------------
1. Analyze user query
2. Detect INTENT:
   - STOCK → indian_stock_search
   - WEATHER → get_weather
   - NEWS → search_news
   - CURRENT_INFO → smart_web_search (latest events, prices, etc.)
   - GENERAL → No tools needed, use LLM knowledge
3. If LLM says "I don't know" or "my knowledge is outdated" → Auto web search
4. Return response

📌 KEYWORDS THAT TRIGGER TOOLS:
------------------------------
- Stock/Shares: "stock", "share price", "Tata", "Reliance", "HDFC", "NSE", "BSE"
- Weather: "weather", "temperature", "rain", "forecast"
- News: "news", "latest", "current events", "today's", "happening"
- Current Info: "now", "today", "current", "latest", "2024", "right now"

📌 FOR INTERVIEWS:
-----------------
"I implemented Smart AI that automatically detects query intent and routes
to appropriate tools. This eliminates the need for manual button clicks
while still maintaining explicit override options for power users."
"""


def detect_intent(query: str) -> str:
    """
    📖 Detect Intent from User Query
    ---------------------------------
    Analyzes the query and returns the most likely intent.
    
    Returns one of:
    - "STOCK" → Indian stock market query
    - "WEATHER" → Weather information
    - "NEWS" → News/current events
    - "CURRENT_INFO" → Needs current/live information
    - "GENERAL" → Can be answered from LLM knowledge
    
    📌 This is keyword-based for SPEED.
    We could use an LLM for more accuracy, but this adds latency.
    """
    query_lower = query.lower()
    
    # Stock market keywords (Indian focus)
    stock_keywords = [
        "stock", "share", "shares", "nse", "bse", "sensex", "nifty",
        "tata", "reliance", "hdfc", "infosys", "icici", "sbi", 
        "wipro", "hcl", "bajaj", "adani", "mahindra", "maruti",
        "stock price", "share price", "quarterly result", "q1", "q2", "q3", "q4",
        "market cap", "dividend", "earnings", "investment", "portfolio",
        "bullish", "bearish", "buy", "sell", "hold"
    ]
    
    # Weather keywords
    weather_keywords = [
        "weather", "temperature", "rain", "sunny", "cloudy", 
        "forecast", "humidity", "climate", "cold", "hot"
    ]
    
    # News keywords
    news_keywords = [
        "news", "headline", "breaking", "update", "announcement",
        "happened", "event", "incident"
    ]
    
    # Current/live info keywords
    current_info_keywords = [
        "today", "now", "current", "latest", "recent", "right now",
        "this week", "this month", "2024", "2025", "live",
        "real-time", "at the moment", "happening",
        
        # 🆕 Sports (always need real-time data)
        "score", "match", "cricket", "football", "ipl", "world cup",
        "t20", "odi", "test match", "fifa", "premier league",
        "champions league", "playing", "won", "lost", "result",
        
        # 🆕 More Football/Soccer Leagues
        "epl", "la liga", "bundesliga", "serie a", "ucl",
        "euro", "asian cup", "copa america", "ligue 1",
        "eredivisie", "mls", "indian super league", "isl",
        
        # 🆕 Cricket Tournaments
        "bcci", "asia cup", "bbl", "psl", "cpl", "hundred",
        "ranji", "vijay hazare", "syed mushtaq ali",
        
        # 🆕 Other Sports
        "nba", "nfl", "mlb", "nhl", "tennis", "wimbledon",
        "us open", "australian open", "french open", "formula 1",
        "f1", "motogp", "olympics", "commonwealth games",
        "badminton", "hockey", "kabaddi", "pro kabaddi", "pkl",
        
        # 🆕 General Sports Terms
        "standings", "fixtures", "schedule", "lineup", "squad",
        "injury", "transfer", "goal", "wicket", "runs", "points table"
    ]
    
    # 🆕 Travel keywords
    travel_keywords = [
        "travel", "trip", "tour", "vacation", "holiday", "journey",
        "flight", "hotel", "booking", "resort", "package",
        "visit", "explore", "destination", "itinerary",
        "makemytrip", "yatra", "goibibo", "booking.com", "airbnb",
        "visa", "passport", "airport", "railway", "bus stand"
    ]
    
    # Check for travel intent FIRST (before current_info)
    for keyword in travel_keywords:
        if keyword in query_lower:
            return "TRAVEL"
    
    # Check for stock intent (highest priority for Indian stocks)
    for keyword in stock_keywords:
        if keyword in query_lower:
            return "STOCK"
    
    # Check for weather intent
    for keyword in weather_keywords:
        if keyword in query_lower:
            return "WEATHER"
    
    # Check for news intent
    for keyword in news_keywords:
        if keyword in query_lower:
            return "NEWS"
    
    # Check for current info (needs web search)
    for keyword in current_info_keywords:
        if keyword in query_lower:
            return "CURRENT_INFO"
    
    # Default: General knowledge query
    return "GENERAL"


def run_smart_chat(
    query: str,
    thread_id: str,
    user_id: str = "default",
    force_tool: str = None  # "search", "stock", etc. - for manual override
) -> Dict[str, Any]:
    """
    📖 Smart AI Chat - Automatic Tool Detection
    ============================================
    
    This is the MAIN entry point for Smart AI.
    
    🔗 HOW IT WORKS:
    1. If force_tool is set → Use that tool (manual override)
    2. Detect intent from query → Route to appropriate handler
    3. 🆕 If intent is GENERAL but query is ambiguous (like "again", "check")
       → Look at thread history for context!
    4. If intent is GENERAL → Try LLM first
    5. If LLM says "I don't know" → Fallback to web search
    
    Parameters:
    -----------
    query: User's message
    thread_id: Conversation thread ID
    user_id: User ID for global memory
    force_tool: Manual override ("search", "stock", "weather", "news")
    
    Returns:
    --------
    {
        "answer": "The response",
        "intent": "STOCK",
        "tool_used": "indian_stock_search",
        "auto_detected": True,
        "steps": [...] // For showing thinking UI
    }
    """
    
    print("\n" + "="*60)
    print("🧠 SMART AI PROCESSING")
    print("="*60)
    print(f"Query: {query}")
    print(f"Thread: {thread_id}")
    
    # Step 1: Check for manual override
    # ---------------------------------
    if force_tool:
        print(f"⚡ Manual override: {force_tool}")
        if force_tool == "search":
            result = run_agent(query, session_id=thread_id)
            return {
                **result,
                "intent": "MANUAL_SEARCH",
                "tool_used": "smart_web_search",
                "auto_detected": False
            }
        elif force_tool == "stock":
            # Use LangGraph stock workflow (with smart routing)
            from stock_graph import run_stock_research
            result = run_stock_research(query)
            
            # Handle both company and sector analysis results
            if result.get("type") == "sector_analysis":
                return {
                    "answer": result.get("final_recommendation", "Analysis complete."),
                    "intent": "MANUAL_STOCK_SECTOR",
                    "tool_used": "sector_analysis",
                    "auto_detected": False,
                    "sector": result.get("sector"),
                    "sector_analysis": result.get("sector_analysis"),
                    "final_recommendation": result.get("final_recommendation"),
                    "steps": result.get("steps", [])
                }
            else:
                return {
                    "answer": result.get("final_recommendation", "Analysis complete."),
                    "intent": "MANUAL_STOCK",
                    "tool_used": "langgraph_stock_workflow",
                    "auto_detected": False,
                    "sector_analysis": result.get("sector_analysis"),
                    "company_research": result.get("company_research"),
                    "policy_analysis": result.get("policy_analysis"),
                    "final_recommendation": result.get("final_recommendation"),
                    "steps": [
                        {"step": "sector_analyst", "status": "complete"},
                        {"step": "company_researcher", "status": "complete"},
                        {"step": "policy_watchdog", "status": "complete"},
                        {"step": "final_advisor", "status": "complete"}
                    ]
                }
    
    # Step 2: Detect intent automatically
    # -----------------------------------
    intent = detect_intent(query)
    print(f"🎯 Initial Intent: {intent}")
    
    # 🆕 Step 2.5: Context-Aware Intent Detection
    # -------------------------------------------
    # If query is ambiguous or a follow-up question, 
    # we need to consider thread history for context.
    
    # Patterns that suggest follow-up questions
    followup_patterns = [
        "again", "check", "same", "more", "another", "update", "refresh", 
        "latest", "what about", "how about", "tell me more", "explain",
        "which one", "why", "can you", "please", "also", "and",
        "that", "this", "it", "they", "those", "these",
        "compare", "difference", "better", "best", "cheapest", "expensive"
    ]
    
    query_lower = query.lower()
    query_words = len(query.split())
    
    # Check if this looks like a follow-up question
    is_followup = (
        query_words <= 8 and  # Short query
        any(pattern in query_lower for pattern in followup_patterns)
    )
    
    # Also check if query starts with question words without context
    starts_with_question = query_lower.startswith(("what", "which", "why", "how", "where", "when", "who", "is it", "are they", "can you"))
    is_contextual = is_followup or (starts_with_question and query_words <= 6)
    
    if is_contextual and intent == "GENERAL":
        print("🔍 Query appears to be a follow-up, checking thread history...")
        
        # Load thread history
        thread_state = _checkpointer.load(thread_id)
        if thread_state and thread_state.get("messages"):
            # Look at last few messages for context
            recent_messages = thread_state["messages"][-6:]  # Last 3 exchanges
            history_text = " ".join([
                msg.get("content", "") for msg in recent_messages
            ]).lower()
            
            # Check what topics were discussed - SPECIFIC TOPICS FIRST
            if any(kw in history_text for kw in ["cricket", "score", "match", "ipl", "odi", "t20", "test match", "runs", "wickets", "batting", "bowling", "india vs", "vs india"]):
                print("🏏 Thread context: Cricket - upgrading to CURRENT_INFO")
                intent = "CURRENT_INFO"
                query = f"latest cricket score India {query}"
            
            elif any(kw in history_text for kw in ["stock", "share", "nifty", "sensex", "share price", "market", "bse", "nse"]):
                print("📈 Thread context: Stocks - upgrading to STOCK")
                intent = "STOCK"
            
            elif any(kw in history_text for kw in ["weather", "temperature", "rain", "forecast", "humidity", "climate"]):
                print("🌤️ Thread context: Weather - upgrading to WEATHER")
                intent = "WEATHER"
            
            elif any(kw in history_text for kw in ["news", "headline", "breaking", "announced", "reported"]):
                print("📰 Thread context: News - upgrading to NEWS")
                intent = "NEWS"
            
            elif any(kw in history_text for kw in ["travel", "trip", "flight", "hotel", "goa", "mumbai", "destination", "package", "booking"]):
                print("🧳 Thread context: Travel - upgrading to TRAVEL")
                intent = "TRAVEL"
            
            # 🆕 GENERAL WEB SEARCH CONTEXT - If previous messages had web search results
            # Check if there was a web search in recent history
            elif len(history_text) > 500:  # Substantial content in history
                print("🌐 Thread has substantial context - will use thread history for answer")
                # Keep intent as GENERAL but the run_chat_with_memory will 
                # include thread history so LLM can answer from context
                # This is the KEY: LLM gets full thread history!
                pass
        
        print(f"🎯 Final Intent (after context check): {intent}")
    
    # 🆕 IMPORTANT: For ALL intents, thread history is passed to LLM
    # The run_chat_with_memory function loads thread history and includes it
    # So even if intent is GENERAL, follow-up questions will have context!
    
    # Step 3: Route based on intent
    # -----------------------------
    
    if intent == "STOCK":
        print("📈 Routing to Stock Research (with Smart Routing)")
        from stock_graph import run_stock_research
        result = run_stock_research(query)
        final_answer = result.get("final_recommendation", "Analysis complete.")
        
        # 🆕 SAVE TO CHECKPOINTER so follow-ups have context!
        _save_to_thread_checkpointer(thread_id, query, final_answer)
        
        # Handle both company and sector analysis results
        if result.get("type") == "sector_analysis":
            return {
                "answer": final_answer,
                "intent": "STOCK_SECTOR",
                "tool_used": "sector_analysis",
                "auto_detected": True,
                "sector": result.get("sector"),
                "sector_analysis": result.get("sector_analysis"),
                "final_recommendation": final_answer,
                "steps": result.get("steps", [])
            }
        else:
            return {
                "answer": final_answer,
                "intent": "STOCK",
                "tool_used": "langgraph_stock_workflow",
                "auto_detected": True,
                "sector_analysis": result.get("sector_analysis"),
                "company_research": result.get("company_research"),
                "policy_analysis": result.get("policy_analysis"),
                "final_recommendation": final_answer,
                "steps": [
                    {"step": "sector_analyst", "status": "complete"},
                    {"step": "company_researcher", "status": "complete"},
                    {"step": "policy_watchdog", "status": "complete"},
                    {"step": "final_advisor", "status": "complete"}
                ]
            }
    
    elif intent == "TRAVEL":
        print("🧳 Routing to Travel Planner (LangGraph)")
        from travel_graph import run_travel_planner
        result = run_travel_planner(query)
        final_answer = result.get("final_summary", "Travel planning complete.")
        
        # 🆕 SAVE TO CHECKPOINTER so follow-ups have context!
        _save_to_thread_checkpointer(thread_id, query, final_answer)
        
        return {
            "answer": final_answer,
            "intent": "TRAVEL",
            "tool_used": "langgraph_travel_workflow",
            "auto_detected": True,
            "destination_info": result.get("destination_info"),
            "transport_info": result.get("transport_info"),
            "accommodation_info": result.get("accommodation_info"),
            "activities_info": result.get("activities_info"),
            "food_shopping_info": result.get("food_shopping_info"),
            "requirements_info": result.get("requirements_info"),
            "emergency_info": result.get("emergency_info"),
            "packages": result.get("packages"),
            "final_summary": result.get("final_summary"),
            "steps": [
                {"step": "destination_researcher", "status": "complete"},
                {"step": "transport_finder", "status": "complete"},
                {"step": "accommodation_finder", "status": "complete"},
                {"step": "activities_planner", "status": "complete"},
                {"step": "food_shopping_guide", "status": "complete"},
                {"step": "travel_requirements", "status": "complete"},
                {"step": "emergency_safety", "status": "complete"},
                {"step": "package_builder", "status": "complete"}
            ]
        }
    
    elif intent == "WEATHER":
        print("🌤️ Routing to Weather Tool")
        # Extract city from query
        city = _extract_city(query)
        if city:
            weather_data = get_weather(city)
            # Use pre-formatted output from the function
            if weather_data.get("error"):
                answer = f"**🌤️ Weather in {city}:**\n\n❌ Unable to fetch weather: {weather_data.get('error')}"
            else:
                # Use the pre-formatted output from get_weather()
                answer = weather_data.get("formatted", f"Weather in {city}: {weather_data.get('weather', 'N/A')}")
        else:
            # Use agent to figure out the city
            result = run_agent(query, session_id=thread_id)
            final_answer = result.get("answer", "")
            
            # 🆕 SAVE TO CHECKPOINTER
            _save_to_thread_checkpointer(thread_id, query, final_answer)
            
            return {
                **result,
                "intent": "WEATHER",
                "tool_used": "get_weather",
                "auto_detected": True
            }
        
        # 🆕 SAVE TO CHECKPOINTER
        _save_to_thread_checkpointer(thread_id, query, answer)
        
        return {
            "answer": answer,
            "intent": "WEATHER",
            "tool_used": "get_weather",
            "auto_detected": True,
            "steps": [{"step": "get_weather", "status": "complete", "city": city}]
        }
    
    elif intent == "NEWS":
        print("📰 Routing to News Search")
        result = run_agent(query, session_id=thread_id)
        final_answer = result.get("answer", "")
        
        # 🆕 SAVE TO CHECKPOINTER
        _save_to_thread_checkpointer(thread_id, query, final_answer)
        
        return {
            **result,
            "intent": "NEWS",
            "tool_used": "search_news",
            "auto_detected": True
        }
    
    elif intent == "CURRENT_INFO":
        print("🔍 Routing to Web Search (needs current info)")
        result = run_agent(query, session_id=thread_id)
        final_answer = result.get("answer", "")
        
        # 🆕 SAVE TO CHECKPOINTER
        _save_to_thread_checkpointer(thread_id, query, final_answer)
        
        return {
            **result,
            "intent": "CURRENT_INFO",
            "tool_used": "smart_web_search",
            "auto_detected": True
        }
    
    else:  # GENERAL
        print("💬 Trying LLM knowledge first...")
        
        # Try normal chat first
        chat_result = run_chat_with_memory(
            query=query,
            thread_id=thread_id,
            user_id=user_id
        )
        
        answer = chat_result.get("answer", "")
        
        # Check if LLM admitted it doesn't know or has outdated info
        # 🆕 Added more fallback trigger phrases
        fallback_phrases = [
            "i don't have", "i cannot provide", "my knowledge",
            "i'm unable to", "i am unable to", "as of my",
            "i don't know", "i'm not sure", "outside my knowledge",
            "real-time", "current data", "up-to-date",
            "i cannot access", "i can't access",
            # 🆕 More fallback triggers
            "i recommend checking", "check a website", "visit a website",
            "sports news", "official website", "sports app",
            "i can't browse", "i cannot browse", "no access to internet",
            "knowledge cutoff", "training data", "october 2023",
            "i suggest checking", "please check", "for the latest"
        ]
        
        needs_fallback = any(phrase in answer.lower() for phrase in fallback_phrases)
        
        if needs_fallback:
            print("🔄 LLM doesn't have info - falling back to web search")
            result = run_agent(query, session_id=thread_id)
            final_answer = result.get("answer", "")
            
            # 🆕 SAVE TO CHECKPOINTER so follow-ups have context!
            _save_to_thread_checkpointer(thread_id, query, final_answer)
            
            return {
                **result,
                "intent": "GENERAL_FALLBACK",
                "tool_used": "smart_web_search",
                "auto_detected": True,
                "fallback_reason": "LLM knowledge outdated or unavailable"
            }
        
        # run_chat_with_memory already saves to checkpointer
        return {
            **chat_result,
            "intent": "GENERAL",
            "tool_used": None,
            "auto_detected": True
        }


def _save_to_thread_checkpointer(thread_id: str, query: str, answer: str):
    """
    ═══════════════════════════════════════════════════════════════════════════
    📖 Save Query & Answer to Thread Checkpointer
    ═══════════════════════════════════════════════════════════════════════════
    
    🎯 PURPOSE:
    -----------
    This function saves the user's query AND the AI's response to MongoDB,
    so that follow-up questions can access the previous conversation context.
    
    🔗 WHY THIS IS NEEDED:
    ----------------------
    Before this fix, different tools had different save behaviors:
    
    | Function              | Saves to Checkpointer? |
    |-----------------------|------------------------|
    | run_chat_with_memory  | ✅ YES (built-in)      |
    | run_agent (web search)| ❌ NO                  |
    | run_stock_research    | ❌ NO                  |
    | run_travel_planner    | ❌ NO                  |
    | get_weather           | ❌ NO                  |
    | search_news           | ❌ NO                  |
    
    This meant: If you did a web search for "best laptops 2024" and then
    asked "which one is cheapest?", the AI couldn't remember the laptop list!
    
    🛠️ HOW IT WORKS:
    -----------------
    1. Load existing thread state from MongoDB (or create empty state)
    2. Append the user's query as a "user" message
    3. Append the AI's answer as an "assistant" message
    4. Save the updated state back to MongoDB
    
    📊 DATA STRUCTURE IN MONGODB:
    -----------------------------
    {
        "thread_id": "abc123",
        "messages": [
            {"role": "user", "content": "Best laptops 2024"},
            {"role": "assistant", "content": "MacBook Air M4, Lenovo Yoga..."},
            {"role": "user", "content": "Which one is cheapest?"},
            {"role": "assistant", "content": "The Lenovo Yoga 7i..."}
        ],
        "metadata": {}
    }
    
    🔗 CONNECTION TO YOUR NOTES (07-LangGraph/graph.py):
    ----------------------------------------------------
    This is similar to LangGraph's checkpointing concept!
    
    YOUR NOTES:
        # Sanitize URI to ensure proper format
    sanitized_uri = _sanitize_mongo_uri(MONGODB_URI)
    with MongoDBSaver.from_conn_string(sanitized_uri) as mongo_checkpointer:
            graph_with_mongo = compile_graph_with_checkpointer(mongo_checkpointer)
            result = graph_with_mongo.invoke({"messages": [...]}, config)
    
    THIS CODE:
        state = _checkpointer.load(thread_id)  # Like checkpointer.get_state()
        state["messages"].append(...)           # Add new messages
        _checkpointer.save(thread_id, state)   # Like checkpointer.put()
    
    📌 WHERE THIS IS CALLED:
    ------------------------
    - After STOCK intent → Saves stock analysis results
    - After TRAVEL intent → Saves travel planning results
    - After WEATHER intent → Saves weather data
    - After NEWS intent → Saves news articles
    - After CURRENT_INFO intent → Saves web search results
    - After GENERAL_FALLBACK → Saves fallback web search results
    
    📌 FOR YOUR INTERVIEW:
    ----------------------
    "I implemented context persistence for conversational continuity.
    When a user asks a follow-up question like 'tell me more' or
    'which one is cheapest', the system loads the previous messages
    from MongoDB and includes them in the prompt. This allows the
    LLM to reference earlier results without the user repeating context.
    
    The key insight was that while the main chat function already saved
    to the checkpointer, the tool functions (web search, stock research)
    did not. I fixed this by adding a _save_to_thread_checkpointer()
    helper that's called after every tool execution."
    
    Parameters:
    -----------
    thread_id: str
        Unique identifier for this conversation thread
        Example: "abc123", "user1_chat_5"
    
    query: str
        The user's question that was just asked
        Example: "Which one is cheapest?"
    
    answer: str
        The AI's response to that question
        Example: "The Lenovo Yoga 7i is the most affordable..."
    
    Returns:
    --------
    None (but logs success/failure to console)
    """
    try:
        # ================================================================
        # Step 1: Load existing thread state from MongoDB
        # ================================================================
        # _checkpointer is a MongoDBCheckpointer instance (defined above)
        # It connects to MongoDB and stores thread states
        
        state = _checkpointer.load(thread_id)
        
        # If no state exists for this thread, create a new empty state
        if state is None:
            state = {
                "messages": [],   # Will hold all user + assistant messages
                "metadata": {}    # Optional: store extra info (timestamps, etc.)
            }
        
        # ================================================================
        # Step 2: Append the new query and answer to messages
        # ================================================================
        # Messages follow the OpenAI format: {"role": "...", "content": "..."}
        # role can be: "user", "assistant", or "system"
        
        state["messages"].append({
            "role": "user",
            "content": query
        })
        
        state["messages"].append({
            "role": "assistant", 
            "content": answer
        })
        
        # ================================================================
        # Step 3: Save updated state back to MongoDB
        # ================================================================
        # This persists the conversation so future requests can load it
        
        _checkpointer.save(thread_id, state)
        
        print(f"💾 Saved to checkpointer: Thread {thread_id} now has {len(state['messages'])} messages")
        
    except Exception as e:
        # Don't crash the whole request if checkpointing fails
        # Just log the error and continue
        print(f"⚠️ Failed to save to checkpointer: {e}")


def _extract_city(query: str) -> str:
    """
    📖 Extract City Name from Weather Query
    ---------------------------------------
    Simple extraction of city names from weather queries.
    
    Examples:
    - "What's the weather in Mumbai?" → "Mumbai"
    - "Temperature in New York" → "New York"
    """
    query_lower = query.lower()
    
    # Common patterns
    patterns = [" in ", " at ", " for "]
    
    for pattern in patterns:
        if pattern in query_lower:
            idx = query_lower.find(pattern) + len(pattern)
            remaining = query[idx:].strip()
            # Take first 1-3 words as city
            words = remaining.split()[:3]
            city = " ".join(words).rstrip("?,.")
            if city:
                return city.title()
    
    # Common Indian cities (fallback)
    indian_cities = [
        "mumbai", "delhi", "bangalore", "chennai", "kolkata",
        "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow"
    ]
    
    for city in indian_cities:
        if city in query_lower:
            return city.title()
    
    return None


# =============================================================================
#                     🆕 SMART AI API ENDPOINT
# =============================================================================

@agent_router.post("/agent/smart-chat")
def smart_chat_endpoint(payload: Dict[str, Any]):
    """
    📖 Smart AI Chat Endpoint
    =========================
    
    HTTP POST to: http://localhost:8000/agent/smart-chat
    Body: {
        "query": "What is the stock price of Tata Motors?",
        "thread_id": "abc123",
        "user_id": "default",
        "force_tool": null  // Optional: "search", "stock", "weather", "news"
    }
    
    🧠 THIS IS THE MAIN SMART AI ENDPOINT!
    
    Features:
    ---------
    1. ✅ Auto-detects if query needs tools
    2. ✅ Routes to appropriate tool automatically
    3. ✅ Falls back to web search if LLM doesn't know
    4. ✅ Supports manual override with force_tool
    5. ✅ Returns intent and tool_used for UI
    
    📌 FOR FRONTEND:
    ----------------
    - Show "🧠 Smart AI analyzing..." when request starts
    - Show detected intent: "📈 Stock query detected"
    - Show tool being used: "🔍 Searching MoneyControl, Screener..."
    - Show final answer
    
    📌 FOR INTERVIEWS:
    -----------------
    "Smart AI uses intent detection to automatically route queries
    to the appropriate tool. If the LLM admits it doesn't have current
    information, we automatically fall back to web search. This provides
    a seamless experience without requiring manual button clicks."
    """
    query = payload.get("query")
    thread_id = payload.get("thread_id", "default")
    user_id = payload.get("user_id", "default")
    force_tool = payload.get("force_tool")
    
    if not query:
        raise HTTPException(status_code=400, detail="missing query")
    
    try:
        result = run_smart_chat(
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            force_tool=force_tool
        )
        return result
    except Exception as err:
        print(f"❌ Smart AI error: {err}")
        raise HTTPException(status_code=500, detail=f"Smart AI failed: {err}")


"""
===================================================================================
                        SUMMARY: AGENT SERVICE
===================================================================================

This file implements:
1. AI Agent with plan → action → observe → output pattern
2. LangGraph-style chat with MongoDB checkpointing (from your notes!)
3. Global Memory like ChatGPT's "Memory" feature!
4. 🆕 Multiple Tools: Web Search, Indian Stocks, Weather, News, DateTime

ENDPOINTS:
----------
AGENT:
1. POST /agent/web-search    - Run agent with web search capability
2. POST /agent/reset-memory  - Clear agent session memory

CHAT WITH MEMORY (LangGraph-style):
3. POST /chat/with-memory    - Chat with thread + global memory
4. GET  /chat/history/{id}   - Get thread conversation history
5. DELETE /chat/history/{id} - Delete thread history

GLOBAL MEMORY (Like ChatGPT!):
6. GET    /memory/{user_id}  - Get what AI remembers about you
7. POST   /memory/{user_id}  - Manually update your memory
8. DELETE /memory/{user_id}  - Clear all memory about you

🆕 AVAILABLE TOOLS:
-------------------
1. web_search          - General web search (Tavily + DuckDuckGo fallback)
2. indian_stock_search - Indian finance sites ONLY (MoneyControl, Screener, ET)
3. get_weather         - Current weather for any city
4. get_current_datetime- Current date and time
5. search_news         - Recent news articles

🆕 INDIAN STOCK RESEARCH WORKFLOW:
----------------------------------
When user asks about Indian stocks, the agent:
1. SECTOR CHECK  → Searches sector trends
2. COMPANY CHECK → Uses indian_stock_search (trusted sites only!)
3. POLICY CHECK  → Searches for government policy impacts
4. OUTPUT        → Gives analysis with disclaimer
5. ENGAGEMENT    → Asks "Are you planning to invest?"

KEY CONCEPTS:
-------------
1. Agent Loop: Continuous loop until agent outputs final answer
2. Tools: Functions the agent can call (from tools_service.py)
3. Memory: Conversation history (in-memory + optional Redis)
4. System Prompt: Instructions telling agent how to behave
5. Tool Registry: Dictionary mapping tool names to functions

🔗 MAPPED TO YOUR NOTES:
------------------------
Notes Compare/03-Agents/main.py:
    - available_tools dict → AVAILABLE_TOOLS in tools_service.py
    - while True loop → while True in run_agent
    - parsed_response handling → step handling
    - json.loads() → json.loads()

THE AGENT FLOW:
--------------
    User Query: "Tell me about Tata Motors stock"
        ↓
    PLAN: "I'll analyze this Indian stock step by step"
        ↓
    ACTION: indian_stock_search("Tata Motors news")
        ↓
    OBSERVE: "Found Q3 results, EV segment growing..."
        ↓
    ACTION: search_news("auto sector policy India")
        ↓
    OBSERVE: "Found EV subsidy policy..."
        ↓
    OUTPUT: "Analysis + Disclaimer + Engagement question"
        ↓
    Return to User

📌 ENVIRONMENT VARIABLES:
------------------------
TAVILY_API_KEY - For AI-optimized search (get free at tavily.com)
OPENAI_API_KEY - For GPT models
MONGODB_URI    - For checkpointing and global memory

===================================================================================
"""

