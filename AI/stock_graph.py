"""
===================================================================================
            STOCK_GRAPH.PY - LangGraph Stock Research Workflow
===================================================================================

📚 WHAT IS THIS FILE?
---------------------
This file implements the SHARE MARKET RESEARCH WORKFLOW using LangGraph.

🔗 THIS IS EXACTLY LIKE YOUR NOTES (07-LangGraph/graph.py)!

YOUR NOTES:
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    graph_builder.add_edge(START, "chat_node")
    graph_builder.add_edge("chat_node", END)

THIS FILE (7-NODE VERSION WITH RISK SENTINEL!):
    graph_builder = StateGraph(StockResearchState)
    graph_builder.add_node("company_intro", company_intro_node)           
    graph_builder.add_node("sector_analyst", sector_analyst_node)
    graph_builder.add_node("company_researcher", company_researcher_node)
    graph_builder.add_node("policy_watchdog", policy_watchdog_node)
    graph_builder.add_node("investor_sentiment", investor_sentiment_node) 
    graph_builder.add_node("technical_analysis", technical_analysis_node)  # NEW! RISK SENTINEL
    graph_builder.add_node("investment_suggestion", investment_suggestion_node)
    
    Edges: START → company_intro → sector_analyst → company_researcher → 
           policy_watchdog → investor_sentiment → technical_analysis →
           investment_suggestion → END

===================================================================================
                     THE ENHANCED 7-NODE WORKFLOW (WITH RISK SENTINEL!)
===================================================================================

    User: "Tell me about Tata Motors stock"
                    │
                    ▼
    ┌─────────────────────────────────────┐
    │   NODE 1: COMPANY INTRO 🏢          │
    │  "What does this company do?"       │
    │  Overview, activities, locations    │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │   NODE 2: SECTOR ANALYST 🏭         │
    │  "What sector? How's it growing?"   │
    │  Uses intro for accurate sector ID  │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │   NODE 3: COMPANY RESEARCHER 🕵️     │
    │  "Get company financials & news"    │
    │  Tool: indian_stock_search()        │
    │  (MoneyControl, Screener only!)     │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │   NODE 4: POLICY WATCHDOG ⚖️        │
    │  "Any govt policies affecting it?"  │
    │  Tool: search_news("policy...")     │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │   NODE 5: INVESTOR SENTIMENT 📊     │
    │  "What are investors saying?"       │
    │  FII/DII, analyst ratings, buzz     │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │   NODE 6: TECHNICAL ANALYSIS 📈⚠️   │  ← NEW! RISK SENTINEL
    │  "Is it overbought? Any red flags?" │
    │  RSI, Moving Averages, Support      │
    │  ⚠️ STRICT RISK WARNINGS:           │
    │  - RSI > 70 → OVERBOUGHT ALERT      │
    │  - Negative news → AVOID NOW!       │
    │  - High volatility → SPECULATIVE    │
    └─────────────────┬───────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────┐
    │   NODE 7: INVESTMENT SUGGESTION 💡  │
    │  "Should I buy? How much?"          │
    │  RISK-AWARE recommendation          │
    │  Buy/sell/hold + quantity + horizon │
    │  + DISCLAIMER (not financial advice)│
    └─────────────────────────────────────┘

===================================================================================
"""

# =============================================================================
#                           IMPORTS SECTION
# =============================================================================

# ----- Standard Library Imports -----
import os
import json
from datetime import datetime
from typing import TypedDict, Annotated, List, Dict, Any, Optional

# ----- Load Environment Variables -----
from dotenv import load_dotenv
load_dotenv()

# ----- Configure LangChain Debug/Verbose Settings -----
# Use the correct LangChain API for configuring debug and verbose modes
try:
    from langchain.globals import set_debug, set_verbose
    set_debug(False)
    set_verbose(False)
except ImportError:
    # Fallback for older LangChain versions (< 0.2.0)
    try:
        import langchain
        if hasattr(langchain, 'globals'):
            langchain.globals.set_debug(False)
            langchain.globals.set_verbose(False)
    except (ImportError, AttributeError):
        # If all else fails, silently continue (debug/verbose are optional)
        pass
"""
📖 Why configure LangChain debug/verbose?
------------------------------------------
LangChain can output verbose debugging information which can clutter logs.
We explicitly disable debug and verbose modes for cleaner production logs.

📌 Correct API Usage:
- LangChain 0.2.0+: Use langchain.globals.set_debug() and set_verbose()
- Older versions: May use different APIs (handled in fallback)
"""

# ----- LangGraph Imports -----
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
"""
📖 LangGraph Imports Explained
------------------------------

StateGraph: The main graph builder class
    - Creates a graph of nodes (functions)
    - Connects them with edges (flow)
    
START: Special node representing the entry point
END: Special node representing the exit point

add_messages: A "reducer" function
    - Tells LangGraph how to combine messages
    - When you return {"messages": [new_msg]}, it APPENDS to existing messages
    
🔗 In your notes (07-LangGraph/graph.py):
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    
SAME IMPORTS!
"""

# ----- OpenAI Import -----
from openai import OpenAI
"""
📖 We use OpenAI directly (not LangChain) for simplicity
    - More control over the API calls
    - Easier to understand what's happening
    - Same as your notes (03-Agents/main.py)
"""

# ----- Import Tools from tools_service -----
from tools_service import (
    smart_web_search,
    indian_stock_search,
    search_news,
    get_current_datetime
)
"""
📖 Our Tools
------------
We import the tools we created in Stage 1.
Each node will use these tools to gather information.
"""

# =============================================================================
#                     INITIALIZE OPENAI CLIENT
# =============================================================================

client = OpenAI()
"""
📖 OpenAI Client
----------------
Reads OPENAI_API_KEY from environment automatically.

🔗 In your notes:
    client = OpenAI()
"""

# =============================================================================
#                     STATE DEFINITION
# =============================================================================

class StockResearchState(TypedDict):
    """
    📖 Stock Research State (Enhanced with 7 Nodes!)
    =================================================
    
    This defines the DATA that flows through our graph.
    Each node can READ from and WRITE to this state.
    
    📌 ENHANCED WORKFLOW (7 NODES):
    ------------------------------
    1. User sends query → Initial state created
    2. Node 1: COMPANY INTRO → Company overview, activities, locations
    3. Node 2: SECTOR ANALYST → Sector trends and outlook
    4. Node 3: COMPANY RESEARCHER → Financials and news
    5. Node 4: POLICY WATCHDOG → Government policies impact
    6. Node 5: INVESTOR SENTIMENT → Market sentiment analysis
    7. Node 6: INVESTMENT SUGGESTION → Buy/sell recommendation
    
    📌 WHY ANNOTATED[list, add_messages]?
    ------------------------------------
    This tells LangGraph: "When I return messages, APPEND them, don't replace."
    """
    
    # ----- Core Fields -----
    messages: Annotated[list, add_messages]
    """List of conversation messages (user + assistant)"""
    
    query: str
    """The original user query (e.g., "Tell me about Tata Motors")"""
    
    company_name: str
    """Extracted company name (e.g., "Tata Motors")"""
    
    # ----- NEW: Company Introduction -----
    company_intro: Optional[str]
    """Output from Node 1: Company overview, activities, locations"""
    
    # ----- Research Findings -----
    sector_analysis: Optional[str]
    """Output from Node 2: Sector trends and outlook"""
    
    company_research: Optional[str]
    """Output from Node 3: Company financials and news"""
    
    policy_analysis: Optional[str]
    """Output from Node 4: Government policies impact"""
    
    # ----- NEW: Investor Sentiment -----
    investor_sentiment: Optional[str]
    """Output from Node 5: Market sentiment and investor outlook"""
    
    # ----- NEW: Technical Analysis & Risk Sentinel -----
    technical_analysis: Optional[str]
    """Output from Node 6: RSI, moving averages, support/resistance"""
    
    risk_warnings: Optional[List[str]]
    """List of risk warnings (overbought, negative news, speculative)"""
    
    is_overbought: Optional[bool]
    """Flag: RSI > 70"""
    
    is_oversold: Optional[bool]
    """Flag: RSI < 30"""
    
    has_negative_news: Optional[bool]
    """Flag: Negative news detected - AVOID!"""
    
    is_speculative: Optional[bool]
    """Flag: High volatility/speculative zone"""
    
    # ----- Final Output -----
    investment_suggestion: Optional[str]
    """Output from Node 7: Buy/sell recommendation with quantity"""
    
    final_recommendation: Optional[str]
    """Combined final analysis and recommendation"""
    
    # ----- Metadata -----
    current_date: Optional[str]
    """Today's date for context"""
    
    search_results: Optional[Dict[str, Any]]
    """Raw search results for reference"""


# =============================================================================
#                     NODE 1: COMPANY INTRODUCTION (NEW!)
# =============================================================================

def company_intro_node(state: StockResearchState) -> Dict[str, Any]:
    """
    📖 Node 1: Company Introduction 🏢
    ==================================
    
    GOAL: Provide a comprehensive introduction to the company.
    
    WHAT IT DOES:
    1. Searches for company overview and history
    2. Lists key activities and business segments
    3. Shows manufacturing units and presence
    4. Provides a snapshot of what the company does
    
    📌 EXAMPLE OUTPUT:
    -----------------
    Bharat Electronics Limited (BEL) is an Indian state-owned aerospace 
    and defense electronics company...
    
    Key Activities:
    - Manufacturing: Advanced electronic products for defense
    - Diversification: Smart cities, e-governance, EVs
    
    Locations:
    - Bengaluru (HQ), Hyderabad, Pune, Chennai...
    """
    print("\n" + "="*60)
    print("🏢 NODE 1: COMPANY INTRODUCTION")
    print("="*60)
    
    company = state.get("company_name", state["query"])
    
    print(f"📌 Researching: {company}")
    
    try:
        # Search for company overview
        overview_query = f"{company} company overview history headquarters India"
        overview_results = smart_web_search(overview_query, max_results=3)
        print(f"✅ Found company overview")
        
        # Search for business segments
        business_query = f"{company} business segments products services key activities"
        business_results = smart_web_search(business_query, max_results=3)
        print(f"✅ Found business segments")
        
        # Search for locations
        location_query = f"{company} manufacturing plants offices locations India"
        location_results = smart_web_search(location_query, max_results=2)
        print(f"✅ Found company locations")
        
        # Use LLM to create a structured company introduction
        intro_prompt = f"""
        Based on the following search results, create a comprehensive COMPANY INTRODUCTION for {company}.
        
        COMPANY OVERVIEW:
        {json.dumps(overview_results.get("results", []), indent=2)}
        
        BUSINESS SEGMENTS:
        {json.dumps(business_results.get("results", []), indent=2)}
        
        LOCATIONS:
        {json.dumps(location_results.get("results", []), indent=2)}
        
        Please provide a structured introduction with:
        
        **🏢 About {company}**
        [2-3 sentence overview of the company - what it is, when founded, parent company if any]
        
        **📋 Key Activities & Business Segments**
        - [Business segment 1]: Brief description
        - [Business segment 2]: Brief description
        - [Add 3-5 key activities]
        
        **🏭 Manufacturing Units & Presence**
        - [Location 1]: What's there
        - [Location 2]: What's there
        - [List major locations across India]
        
        **📊 Quick Facts**
        - Industry: [sector]
        - Type: [Public/Private/PSU]
        - Employees: [if available]
        - Stock Exchange: NSE/BSE [ticker if available]
        
        Keep it informative and concise. This is an INTRODUCTION, not analysis.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": intro_prompt}]
        )
        
        company_intro = response.choices[0].message.content
        
        print(f"✅ Company introduction complete!")
        
        # NOTE: Don't add to messages here - only final node adds the combined message
        return {
            "company_intro": company_intro
        }
        
    except Exception as e:
        print(f"❌ Error in company introduction: {e}")
        return {
            "company_intro": f"Error getting company info: {str(e)}"
        }


# =============================================================================
#                     NODE 2: SECTOR ANALYST
# =============================================================================

def sector_analyst_node(state: StockResearchState) -> Dict[str, Any]:
    """
    📖 Node 2: Sector Analyst 🏭
    ============================
    
    GOAL: Understand the broader market context using company introduction.
    
    WHAT IT DOES:
    1. Reads company intro to identify the sector
    2. Searches for sector trends and growth
    3. Provides sector outlook
    
    📌 ENHANCED: Uses Company Introduction to identify sector!
    """
    print("\n" + "="*60)
    print("🏭 NODE 2: SECTOR ANALYST")
    print("="*60)
    
    query = state["query"]
    company = state.get("company_name", query)
    company_intro = state.get("company_intro", "")  # 🆕 Get from previous node
    
    # Get current date for context
    date_info = get_current_datetime()
    current_date = date_info.get("formatted", "")
    
    print(f"📌 Analyzing sector for: {company}")
    print(f"📅 Date: {current_date}")
    
    # 🆕 Use Company Introduction to identify sector (more accurate!)
    sector_prompt = f"""
    You are a financial sector analyst.
    
    Company: {company}
    
    COMPANY INTRODUCTION (from previous research):
    {company_intro}
    
    Based on the company introduction above:
    1. Identify the PRIMARY sector this company belongs to (e.g., Defense, Auto, IT, Pharma, Banking, FMCG, etc.)
    2. Create a search query to find sector trends in India
    
    Respond in JSON format:
    {{
        "sector": "the primary sector name",
        "sub_sectors": ["list of sub-sectors if any"],
        "search_query": "search query for sector trends India 2024"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": sector_prompt}]
        )
        
        sector_info = json.loads(response.choices[0].message.content)
        sector_name = sector_info.get("sector", "Unknown")
        sub_sectors = sector_info.get("sub_sectors", [])
        search_query = sector_info.get("search_query", f"{sector_name} sector trends India")
        
        print(f"🔍 Identified Sector: {sector_name}")
        if sub_sectors:
            print(f"🔍 Sub-sectors: {', '.join(sub_sectors)}")
        print(f"🔍 Search Query: {search_query}")
        
        # Search for sector information
        search_results = smart_web_search(search_query, max_results=3)
        
        # Summarize sector findings
        results_text = json.dumps(search_results.get("results", []), indent=2)
        
        summary_prompt = f"""
        You are a sector analyst. Based on the search results below, provide a sector analysis.
        
        Primary Sector: {sector_name}
        Sub-sectors: {', '.join(sub_sectors) if sub_sectors else 'N/A'}
        Company in question: {company}
        
        Search Results:
        {results_text}
        
        Provide a structured sector analysis:
        
        **Sector: {sector_name}**
        
        📈 **Growth Trends:**
        - [Current market size and growth rate]
        - [Key growth drivers]
        
        🌟 **Sector Outlook:**
        - [2-3 sentences on future prospects]
        - [Sentiment: Positive/Negative/Neutral with reason]
        
        Keep it informative and concise (150-200 words).
        """
        
        summary_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        
        sector_analysis = summary_response.choices[0].message.content
        
        print(f"✅ Sector Analysis Complete")
        
        # NOTE: Don't add to messages here - only final node adds the combined message
        # This prevents duplication in the output
        return {
            "sector_analysis": sector_analysis,
            "current_date": current_date
        }
        
    except Exception as e:
        print(f"❌ Error in sector analysis: {e}")
        return {
            "sector_analysis": f"Could not analyze sector: {str(e)}",
            "current_date": current_date
        }


# =============================================================================
#                     NODE 2: COMPANY RESEARCHER
# =============================================================================

def company_researcher_node(state: StockResearchState) -> Dict[str, Any]:
    """
    📖 Node 2: Company Researcher 🕵️
    =================================
    
    GOAL: Get specific company data from TRUSTED sources.
    
    WHAT IT DOES:
    1. Uses indian_stock_search() (NOT regular web search!)
    2. Searches MoneyControl, Screener, Economic Times ONLY
    3. Gets quarterly results, financials, recent news
    
    🔗 In your workflow:
        Step 2 - COMPANY CHECK:
        - Use "indian_stock_search" (NOT regular web_search!)
        - Check 3 sources for Quarterly results
    
    📌 WHY TRUSTED SOURCES ONLY?
    ---------------------------
    Random blogs = outdated info, speculation, clickbait
    MoneyControl/Screener = authentic financial data, verified news
    
    This makes your analysis RELIABLE!
    """
    print("\n" + "="*60)
    print("🕵️ NODE 2: COMPANY RESEARCHER")
    print("="*60)
    
    company = state.get("company_name", state["query"])
    
    print(f"📌 Researching company: {company}")
    print(f"🔍 Using TRUSTED sources: MoneyControl, Screener, ET")
    
    try:
        # Use indian_stock_search - filters to trusted sites only!
        search_results = indian_stock_search(
            query=f"{company} quarterly results news",
            max_results=5
        )
        
        print(f"📊 Found {len(search_results.get('results', []))} results from trusted sources")
        
        # Summarize company findings
        results_text = json.dumps(search_results.get("results", []), indent=2)
        
        summary_prompt = f"""
        You are a company research analyst. Based on the search results from trusted 
        Indian financial websites (MoneyControl, Screener, Economic Times), provide 
        a company analysis.
        
        Company: {company}
        
        Search Results (from trusted sources only):
        {results_text}
        
        Provide a summary covering:
        1. Recent financial performance (revenue, profit if mentioned)
        2. Key news or developments
        3. Stock price movement if mentioned
        
        Keep it to 3-4 sentences. Only use facts from the search results.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        
        company_research = response.choices[0].message.content
        
        print(f"✅ Company Research Complete")
        print(f"📊 Summary: {company_research[:100]}...")
        
        # NOTE: Don't add to messages here - only final node adds the combined message
        return {
            "company_research": f"**Company: {company}**\n\n{company_research}",
            "search_results": search_results
        }
        
    except Exception as e:
        print(f"❌ Error in company research: {e}")
        return {
            "company_research": f"Could not research company: {str(e)}"
        }


# =============================================================================
#                     NODE 3: POLICY WATCHDOG
# =============================================================================

def policy_watchdog_node(state: StockResearchState) -> Dict[str, Any]:
    """
    📖 Node 3: Policy Watchdog ⚖️
    =============================
    
    GOAL: Identify government policies that might impact the stock.
    
    WHAT IT DOES:
    1. Searches for recent policy news
    2. Looks for regulatory changes, sanctions, subsidies
    3. Assesses policy impact on the company/sector
    
    🔗 In your workflow:
        Step 4 - POLICY CHECK:
        - Any policy-related changes
        - USA sanctions, Indian govt policies
        - Which might impact the sector or company
    
    📌 WHY THIS MATTERS:
    -------------------
    Example: If govt announces new EV subsidies → Tata Motors stock goes UP
    Example: If US sanctions a company → Stock goes DOWN
    
    Policy awareness = Better investment decisions!
    """
    print("\n" + "="*60)
    print("⚖️ NODE 3: POLICY WATCHDOG")
    print("="*60)
    
    company = state.get("company_name", state["query"])
    sector_analysis = state.get("sector_analysis", "")
    
    # Extract sector from previous analysis
    sector = "general"
    if "Sector:" in sector_analysis:
        sector = sector_analysis.split("Sector:")[1].split("\n")[0].strip().strip("*")
    
    print(f"📌 Checking policies for: {company}")
    print(f"📌 Sector: {sector}")
    
    try:
        # Search for policy news
        policy_query = f"government policy {sector} India 2024"
        news_results = search_news(policy_query, max_results=3)
        
        print(f"📰 Found {len(news_results.get('results', []))} policy-related news")
        
        # Also check for specific company policy impacts
        company_policy_query = f"{company} government policy regulation news"
        company_news = smart_web_search(company_policy_query, max_results=2)
        
        # Combine results
        all_results = news_results.get("results", []) + company_news.get("results", [])
        results_text = json.dumps(all_results, indent=2)
        
        summary_prompt = f"""
        You are a policy analyst. Based on the news results, identify any 
        government policies or regulations that might impact this company.
        
        Company: {company}
        Sector: {sector}
        
        News Results:
        {results_text}
        
        Provide a brief analysis:
        1. Any recent policy changes affecting this sector?
        2. Any regulations or sanctions to be aware of?
        3. Any government incentives or subsidies?
        
        If no significant policy news found, say "No major policy changes identified."
        Keep it to 2-3 sentences.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        
        policy_analysis = response.choices[0].message.content
        
        print(f"✅ Policy Analysis Complete")
        print(f"📋 Summary: {policy_analysis[:100]}...")
        
        # NOTE: Don't add to messages here - only final node adds the combined message
        return {
            "policy_analysis": f"**Policy Impact:**\n\n{policy_analysis}"
        }
        
    except Exception as e:
        print(f"❌ Error in policy analysis: {e}")
        return {
            "policy_analysis": "No policy analysis available."
        }


# =============================================================================
#                     NODE 5: INVESTOR SENTIMENT (NEW!)
# =============================================================================

def investor_sentiment_node(state: StockResearchState) -> Dict[str, Any]:
    """
    📖 Node 5: Investor Sentiment 📊
    ================================
    
    GOAL: Analyze market sentiment and investor outlook.
    
    WHAT IT DOES:
    1. Searches for investor sentiment and ratings
    2. Checks analyst recommendations
    3. Analyzes FII/DII holdings
    4. Provides sentiment summary
    """
    print("\n" + "="*60)
    print("📊 NODE 5: INVESTOR SENTIMENT")
    print("="*60)
    
    company = state.get("company_name", state["query"])
    
    print(f"📌 Analyzing investor sentiment for: {company}")
    
    try:
        # Search for investor sentiment
        sentiment_query = f"{company} stock investor sentiment analyst rating buy sell hold"
        sentiment_results = smart_web_search(sentiment_query, max_results=3)
        print(f"✅ Found investor sentiment data")
        
        # Search for FII/DII holdings
        holdings_query = f"{company} FII DII shareholding pattern institutional investors"
        holdings_results = smart_web_search(holdings_query, max_results=2)
        print(f"✅ Found institutional holdings data")
        
        # Search for recent analyst calls (INDIAN sources - Rupees!)
        analyst_query = f"{company} stock target price analyst recommendation India NSE BSE rupees"
        analyst_results = smart_web_search(analyst_query, max_results=2)
        print(f"✅ Found analyst recommendations")
        
        # Use LLM to summarize sentiment
        sentiment_prompt = f"""
        Based on the following search results, provide an INVESTOR SENTIMENT analysis for {company}.
        
        IMPORTANT: This is an INDIAN stock. All prices MUST be in Indian Rupees (₹), NOT dollars ($).
        
        INVESTOR SENTIMENT DATA:
        {json.dumps(sentiment_results.get("results", []), indent=2)}
        
        INSTITUTIONAL HOLDINGS:
        {json.dumps(holdings_results.get("results", []), indent=2)}
        
        ANALYST RECOMMENDATIONS:
        {json.dumps(analyst_results.get("results", []), indent=2)}
        
        Provide a structured sentiment analysis:
        
        **📊 Investor Sentiment Analysis**
        
        🎯 **Overall Sentiment:** [Bullish 🟢 / Bearish 🔴 / Neutral 🟡]
        
        📈 **Analyst Ratings:**
        - Buy/Sell/Hold recommendations from Indian analysts
        - Target price range in ₹ (Rupees) - NOT dollars!
        
        🏛️ **Institutional Interest:**
        - FII (Foreign Institutional Investors) holdings trend
        - DII (Domestic Institutional Investors) holdings trend
        - Key changes in shareholding pattern
        
        💬 **Market Buzz:**
        - What are Indian investors/analysts saying?
        - Recent sentiment drivers in Indian market
        
        ⚡ **Sentiment Score:** [1-10] with brief justification
        
        CRITICAL: Use ₹ symbol for all prices. Example: "Target: ₹500 - ₹600" NOT "$500 - $600"
        
        Keep it concise and data-driven (150-200 words).
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": sentiment_prompt}]
        )
        
        investor_sentiment = response.choices[0].message.content
        
        print(f"✅ Investor Sentiment Analysis Complete")
        
        # NOTE: Don't add to messages here - only final node adds the combined message
        return {
            "investor_sentiment": investor_sentiment
        }
        
    except Exception as e:
        print(f"❌ Error in investor sentiment analysis: {e}")
        return {
            "investor_sentiment": "Investor sentiment data not available."
        }


# =============================================================================
#                     NODE 6: TECHNICAL ANALYSIS & RISK CHECK (NEW!)
# =============================================================================

def technical_analysis_node(state: StockResearchState) -> Dict[str, Any]:
    """
    📖 Node 6: Technical Analysis & Risk Sentinel 📈⚠️
    ==================================================
    
    GOAL: Provide technical indicators with BEGINNER-FRIENDLY explanations and STRICT risk warnings.
    
    WHAT IT DOES:
    1. Searches for RSI (14-day), P/E ratio, moving averages, support/resistance
    2. Checks if stock is OVERBOUGHT (RSI > 70) or OVERSOLD (RSI < 30)
    3. Evaluates P/E ratio (expensive vs undervalued)
    4. Detects NEGATIVE NEWS and issues strict warnings
    5. Flags "SPECULATIVE ZONE" if high volatility detected
    6. Explains each term so BEGINNERS can understand!
    
    📌 RULE-BASED WARNINGS (Not just LLM opinion!):
    - RSI > 70 → "⚠️ OVERBOUGHT - Wait for correction"
    - RSI < 30 → "🟢 OVERSOLD - Potential buying opportunity"
    - P/E > 40 → "💰 EXPENSIVE - Trading at high valuation"
    - Negative news → "🚨 AVOID NOW - Negative news found"
    - High volatility → "⚡ SPECULATIVE ZONE - High risk"
    
    📌 WHY THIS NODE?
    Users asked: "Warn me if the share is in speculative zone/overbought"
    And: "Explain these terms so beginners can understand"
    This node provides safety checks AND education!
    """
    print("\n" + "="*60)
    print("📈 NODE 6: TECHNICAL ANALYSIS & RISK SENTINEL")
    print("="*60)
    
    company = state.get("company_name", state["query"])
    company_research = state.get("company_research", "")
    investor_sentiment = state.get("investor_sentiment", "")
    
    print(f"📌 Technical analysis for: {company}")
    
    # Initialize risk flags
    risk_warnings = []
    is_overbought = False
    is_oversold = False
    has_negative_news = False
    is_speculative = False
    
    try:
        # Search for RSI and technical indicators
        rsi_query = f"{company} stock RSI technical analysis support resistance India"
        rsi_results = smart_web_search(rsi_query, max_results=3)
        print(f"✅ Found RSI/technical data")
        
        # Search for P/E ratio and valuation metrics
        pe_query = f"{company} stock P/E ratio EPS valuation India NSE BSE"
        pe_results = smart_web_search(pe_query, max_results=3)
        print(f"✅ Found P/E ratio data")
        
        # Search for volatility data
        volatility_query = f"{company} stock volatility 52 week high low beta India"
        volatility_results = smart_web_search(volatility_query, max_results=2)
        print(f"✅ Found volatility data")
        
        # Search for target price (INDIAN sources - in Rupees!)
        target_query = f"{company} stock target price analyst recommendation India NSE rupees"
        target_results = smart_web_search(target_query, max_results=2)
        print(f"✅ Found target price data")
        
        # Search for any negative news (CRITICAL!)
        negative_news_query = f"{company} stock fraud scam loss bankruptcy investigation SEBI warning"
        negative_news_results = search_news(negative_news_query, max_results=3)
        print(f"✅ Checked for negative news")
        
        # Use LLM to extract technical indicators and check for warnings
        analysis_prompt = f"""
        You are a technical analyst with STRICT risk management rules.
        This is for an INDIAN stock traded on NSE/BSE. All prices must be in ₹ (Rupees).
        
        Analyze the following data for {company} and provide:
        
        TECHNICAL DATA:
        {json.dumps(rsi_results.get("results", []), indent=2)}
        
        P/E RATIO & VALUATION:
        {json.dumps(pe_results.get("results", []), indent=2)}
        
        VOLATILITY DATA:
        {json.dumps(volatility_results.get("results", []), indent=2)}
        
        TARGET PRICE DATA:
        {json.dumps(target_results.get("results", []), indent=2)}
        
        NEGATIVE NEWS CHECK:
        {json.dumps(negative_news_results.get("results", []), indent=2)}
        
        PREVIOUS COMPANY RESEARCH:
        {company_research[:500] if company_research else "Not available"}
        
        Respond in JSON format:
        {{
            "current_price": <number in Rupees or null>,
            "rsi_value": <number or null if not found>,
            "rsi_status": "overbought" | "oversold" | "neutral" | "unknown",
            "pe_ratio": <number or null>,
            "pe_status": "expensive" | "fairly_valued" | "undervalued" | "unknown",
            "industry_pe": <number or null>,
            "eps": <number or null>,
            "moving_avg_50": <number in Rupees or null>,
            "moving_avg_200": <number in Rupees or null>,
            "support_level": <number in Rupees or null>,
            "resistance_level": <number in Rupees or null>,
            "target_price_low": <number in Rupees or null>,
            "target_price_high": <number in Rupees or null>,
            "target_price_avg": <number in Rupees or null>,
            "volatility": "high" | "moderate" | "low" | "unknown",
            "beta": <number or null>,
            "52_week_high": <number in Rupees or null>,
            "52_week_low": <number in Rupees or null>,
            "negative_news_found": true | false,
            "negative_news_summary": "<summary if any negative news found>",
            "speculative_zone": true | false,
            "technical_verdict": "bullish" | "bearish" | "neutral" | "avoid"
        }}
        
        IMPORTANT RULES:
        - All prices MUST be in Indian Rupees (₹), NOT dollars
        - If RSI > 70, set rsi_status = "overbought"
        - If RSI < 30, set rsi_status = "oversold"
        - If P/E > 40, set pe_status = "expensive"
        - If P/E < 15, set pe_status = "undervalued"
        - If any fraud/scam/loss/investigation news, set negative_news_found = true
        - If beta > 1.5 OR 52-week range is > 50% of current price, set speculative_zone = true
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        
        tech_data = json.loads(response.choices[0].message.content)
        
        # =====================================================================
        # RULE-BASED RISK FLAGS (NOT LLM OPINION!)
        # =====================================================================
        
        rsi_value = tech_data.get("rsi_value")
        rsi_status = tech_data.get("rsi_status", "unknown")
        pe_ratio = tech_data.get("pe_ratio")
        pe_status = tech_data.get("pe_status", "unknown")
        
        # Check RSI warnings
        if rsi_status == "overbought" or (rsi_value and rsi_value > 70):
            is_overbought = True
            risk_warnings.append("⚠️ **OVERBOUGHT (RSI > 70)** - Stock may be due for correction. Wait for pullback before buying.")
            print(f"🚨 RSI WARNING: Overbought detected!")
        
        if rsi_status == "oversold" or (rsi_value and rsi_value < 30):
            is_oversold = True
            risk_warnings.append("🟢 **OVERSOLD (RSI < 30)** - Stock may be undervalued. Potential buying opportunity.")
            print(f"✅ RSI: Oversold - potential opportunity")
        
        # Check P/E ratio warnings
        if pe_status == "expensive" or (pe_ratio and pe_ratio > 40):
            risk_warnings.append("💰 **EXPENSIVE VALUATION (P/E > 40)** - Stock is trading at high valuation. Price in a lot of growth.")
            print(f"💰 P/E WARNING: Expensive valuation!")
        
        # Check negative news (CRITICAL!)
        if tech_data.get("negative_news_found"):
            has_negative_news = True
            news_summary = tech_data.get("negative_news_summary", "Negative news detected")
            risk_warnings.append(f"🚨 **NEGATIVE NEWS ALERT** - {news_summary}")
            risk_warnings.append("⛔ **AVOID NOW** - Do not invest until situation clarifies!")
            print(f"🚨 NEGATIVE NEWS DETECTED!")
        
        # Check speculative zone
        if tech_data.get("speculative_zone") or tech_data.get("volatility") == "high":
            is_speculative = True
            risk_warnings.append("⚡ **SPECULATIVE ZONE** - High volatility/beta. Only for aggressive investors.")
            print(f"⚡ SPECULATIVE ZONE detected!")
        
        # Format price with ₹ symbol
        def format_rupee(val):
            if val is None or val == "N/A":
                return "N/A"
            try:
                return f"₹{float(val):,.2f}"
            except:
                return f"₹{val}"
        
        # Build technical analysis summary with BEGINNER-FRIENDLY explanations
        technical_summary = f"""
**📈 Technical Analysis for {company}**

---

**📊 Key Indicators (with Beginner Explanations)**

| Indicator | Value | What it Means |
|-----------|-------|---------------|
| **RSI (14-day)** | {rsi_value if rsi_value else 'N/A'} ({rsi_status.upper()}) | *RSI measures if stock is oversold (<30) or overbought (>70). Think of it like a "popularity meter" - if everyone is buying (>70), it might be too hot!* |
| **P/E Ratio** | {pe_ratio if pe_ratio else 'N/A'} ({pe_status.upper()}) | *Price-to-Earnings shows how many years of earnings you're paying for. P/E of 20 means you pay ₹20 for ₹1 of profit. Lower is usually cheaper.* |
| **Industry P/E** | {tech_data.get('industry_pe', 'N/A')} | *Compare company P/E to this. If company P/E > industry P/E, stock is relatively expensive.* |
| **EPS** | {format_rupee(tech_data.get('eps'))} | *Earnings Per Share - profit per share. Higher EPS = more profitable.* |

---

**📉 Moving Averages & Support/Resistance**

| Level | Price | Meaning |
|-------|-------|---------|
| **50-Day MA** | {format_rupee(tech_data.get('moving_avg_50'))} | *Short-term trend. If stock price > 50-day MA, short-term bullish.* |
| **200-Day MA** | {format_rupee(tech_data.get('moving_avg_200'))} | *Long-term trend. If stock price > 200-day MA, long-term bullish.* |
| **Support Level** | {format_rupee(tech_data.get('support_level'))} | *Price floor - stock tends to bounce up from here.* |
| **Resistance Level** | {format_rupee(tech_data.get('resistance_level'))} | *Price ceiling - stock struggles to go above this.* |

---

**🎯 Analyst Target Price (in ₹)**

| Target | Price |
|--------|-------|
| **Low Target** | {format_rupee(tech_data.get('target_price_low'))} |
| **Average Target** | {format_rupee(tech_data.get('target_price_avg'))} |
| **High Target** | {format_rupee(tech_data.get('target_price_high'))} |

*Analysts study companies and predict where stock price might go. These are their estimates.*

---

**⚡ Volatility & Risk Metrics**

| Metric | Value | Meaning |
|--------|-------|---------|
| **Volatility** | {tech_data.get('volatility', 'Unknown').upper()} | *How much price swings. HIGH = risky but potential for big gains.* |
| **Beta** | {tech_data.get('beta', 'N/A')} | *Beta=1 means moves like market. Beta>1 = more volatile than market. Beta<1 = less volatile.* |
| **52-Week Range** | {format_rupee(tech_data.get('52_week_low'))} - {format_rupee(tech_data.get('52_week_high'))} | *Lowest and highest price in last 1 year.* |

---

**🔮 Technical Verdict: {tech_data.get('technical_verdict', 'neutral').upper()}**
"""
        
        # Add risk warnings section if any
        if risk_warnings:
            technical_summary += "\n\n---\n\n**🚨 RISK WARNINGS**\n\n"
            for warning in risk_warnings:
                technical_summary += f"{warning}\n\n"
        else:
            technical_summary += "\n\n✅ **No major risk flags detected**"
        
        print(f"✅ Technical Analysis Complete")
        
        # NOTE: Don't add to messages here - only final node adds the combined message
        return {
            "technical_analysis": technical_summary,
            "risk_warnings": risk_warnings,
            "is_overbought": is_overbought,
            "is_oversold": is_oversold,
            "has_negative_news": has_negative_news,
            "is_speculative": is_speculative
        }
        
    except Exception as e:
        print(f"❌ Error in technical analysis: {e}")
        return {
            "technical_analysis": "Technical analysis not available.",
            "risk_warnings": [],
            "is_overbought": False,
            "is_oversold": False,
            "has_negative_news": False,
            "is_speculative": False
        }


# =============================================================================
#                     NODE 7: INVESTMENT SUGGESTION (ENHANCED!)
# =============================================================================

def investment_suggestion_node(state: StockResearchState) -> Dict[str, Any]:
    """
    📖 Node 7: Investment Suggestion 💡
    ===================================
    
    GOAL: Provide actionable investment recommendation WITH RISK AWARENESS.
    
    WHAT IT DOES:
    1. Combines all previous analysis INCLUDING technical + risk warnings
    2. Gives buy/sell/hold recommendation
    3. RESPECTS RISK FLAGS - If overbought/negative news → Warns strongly!
    4. Suggests quantity based on risk profile
    5. Recommends long-term vs short-term
    6. Adds important disclaimer
    
    📌 ENHANCED: Now uses risk flags from technical_analysis_node!
    - If has_negative_news → Strong AVOID recommendation
    - If is_overbought → Warn to wait for correction
    - If is_speculative → Only recommend for aggressive investors
    """
    print("\n" + "="*60)
    print("💡 NODE 7: INVESTMENT SUGGESTION")
    print("="*60)
    
    company = state.get("company_name", state["query"])
    company_intro = state.get("company_intro", "")
    sector_analysis = state.get("sector_analysis", "")
    company_research = state.get("company_research", "")
    policy_analysis = state.get("policy_analysis", "")
    investor_sentiment = state.get("investor_sentiment", "")
    technical_analysis = state.get("technical_analysis", "")
    current_date = state.get("current_date", "")
    
    # Get risk flags from technical analysis
    risk_warnings = state.get("risk_warnings", [])
    is_overbought = state.get("is_overbought", False)
    is_oversold = state.get("is_oversold", False)
    has_negative_news = state.get("has_negative_news", False)
    is_speculative = state.get("is_speculative", False)
    
    print(f"📌 Generating investment suggestion for: {company}")
    
    try:
        # Build risk context for the prompt
        risk_context = ""
        if has_negative_news:
            risk_context += "\n🚨 CRITICAL: NEGATIVE NEWS DETECTED - Must strongly warn against buying!\n"
        if is_overbought:
            risk_context += "\n⚠️ WARNING: Stock is OVERBOUGHT (RSI > 70) - Wait for correction!\n"
        if is_speculative:
            risk_context += "\n⚡ ALERT: SPECULATIVE ZONE - High volatility, only for aggressive investors!\n"
        if is_oversold:
            risk_context += "\n🟢 NOTE: Stock is OVERSOLD (RSI < 30) - Potential buying opportunity!\n"
        
        suggestion_prompt = f"""
        You are a senior investment advisor with STRICT RISK MANAGEMENT.
        
        Based on ALL the research below, provide a comprehensive INVESTMENT SUGGESTION for {company}.
        
        Company: {company}
        Date: {current_date}
        
        === RISK FLAGS (CRITICAL - MUST ADDRESS!) ===
        {risk_context if risk_context else "No major risk flags detected."}
        
        Risk Warnings: {risk_warnings if risk_warnings else "None"}
        
        === COMPANY INTRODUCTION ===
        {company_intro}
        
        === SECTOR ANALYSIS ===
        {sector_analysis}
        
        === COMPANY RESEARCH ===
        {company_research}
        
        === POLICY ANALYSIS ===
        {policy_analysis}
        
        === INVESTOR SENTIMENT ===
        {investor_sentiment}
        
        === TECHNICAL ANALYSIS ===
        {technical_analysis}
        
        ===========================
        
        **IMPORTANT RULES:**
        1. If NEGATIVE NEWS was detected → Recommend AVOID/DO NOT BUY
        2. If OVERBOUGHT → Recommend WAIT for correction before buying
        3. If SPECULATIVE ZONE → Only recommend for aggressive investors with stop-loss
        4. If OVERSOLD → Can recommend as potential opportunity
        
        Provide a DETAILED INVESTMENT SUGGESTION with:
        
        **💡 Investment Recommendation**
        
        🎯 **Action:** [BUY / SELL / HOLD / WAIT]
        
        📊 **Investment Horizon:**
        - **Short-term (< 6 months):** [Suitable? Yes/No with reason]
        - **Medium-term (6-18 months):** [Suitable? Yes/No with reason]
        - **Long-term (> 18 months):** [Suitable? Yes/No with reason]
        
        💰 **Suggested Investment Strategy:**
        - **For Conservative Investors:** [suggestion with quantity hint]
        - **For Moderate Risk Takers:** [suggestion with quantity hint]
        - **For Aggressive Investors:** [suggestion with quantity hint]
        
        📈 **Entry Strategy:**
        - Current Price Level: [good entry / wait for dip / expensive]
        - Suggested Entry Range: [if available from research]
        
        ⚠️ **Risk Factors to Watch:**
        - [Key risk 1]
        - [Key risk 2]
        - [Key risk 3]
        
        🎓 **Final Verdict:**
        [2-3 sentence clear conclusion on whether to invest and how]
        
        ---
        
        ⚠️ **IMPORTANT DISCLAIMER:**
        This analysis is for educational purposes only and NOT financial advice. 
        Stock market investments are subject to market risks. Please:
        - Do your own thorough research (DYOR)
        - Consult a SEBI-registered financial advisor
        - Never invest more than you can afford to lose
        - Don't treat investing like gambling
        
        💬 **Follow-up:** Would you like me to analyze any specific aspect in more detail?
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": suggestion_prompt}]
        )
        
        investment_suggestion = response.choices[0].message.content
        
        # Combine everything for final recommendation
        # ORDER: Company Intro → Sector → Research → Policy → Sentiment → Technical → Suggestion
        # NO DUPLICATES - each section appears ONCE
        final_recommendation = f"""
# 📊 Complete Stock Analysis: {company}

---

## 🏢 Company Introduction
*Who is this company? What do they do?*

{company_intro if company_intro else "Company information not available."}

---

## 🏭 Sector Analysis
*What industry are they in? How's the sector doing?*

{sector_analysis if sector_analysis else "Sector analysis not available."}

---

## 🕵️ Company Research
*Recent financials, news, and performance*

{company_research if company_research else "Company research not available."}

---

## ⚖️ Policy Analysis
*Government policies and regulations impacting the company*

{policy_analysis if policy_analysis else "No major policy impacts identified."}

---

## 📊 Investor Sentiment
*What are analysts and investors saying?*

{investor_sentiment if investor_sentiment else "Sentiment data not available."}

---

## 📈 Technical Analysis & Risk Check
*Key indicators, valuations, and risk warnings*

{technical_analysis if technical_analysis else "Technical analysis not available."}

---

## 💡 Investment Suggestion
*Based on ALL the above analysis, here's the recommendation:*

{investment_suggestion}
"""
        
        print(f"✅ Investment Suggestion Complete")
        print("="*60)
        
        return {
            "investment_suggestion": investment_suggestion,
            "final_recommendation": final_recommendation,
            "messages": [{
                "role": "assistant",
                "content": f"📈 **{company} Complete Stock Analysis**\n\n{final_recommendation}"
            }]
        }
        
    except Exception as e:
        print(f"❌ Error generating investment suggestion: {e}")
        error_response = f"""
        Sorry, I couldn't generate a complete suggestion due to an error.
        
        ⚠️ **Disclaimer**: This is not financial advice. Please do your own research.
        """
        return {
            "investment_suggestion": error_response,
            "final_recommendation": error_response,
            "messages": [{"role": "assistant", "content": error_response}]
        }


# =============================================================================
#                     NODE 7: FINAL ADVISOR (Summary)
# =============================================================================

def final_advisor_node(state: StockResearchState) -> Dict[str, Any]:
    """
    📖 Node 7: Final Advisor 🎓
    ===========================
    
    GOAL: This node now just passes through - all work done in investment_suggestion_node
    """
    print("\n" + "="*60)
    print("🎓 NODE 7: FINAL ADVISOR (Pass-through)")
    print("="*60)
    
    # All work already done in investment_suggestion_node
    # Just return state as-is
    return {
        "messages": state.get("messages", [])
    }


# =============================================================================
#                     BUILD THE GRAPH
# =============================================================================
"""
📖 Building the LangGraph
=========================

Now we connect all the nodes together!

🔗 In your notes (07-LangGraph/graph.py):
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    graph_builder.add_edge(START, "chat_node")
    graph_builder.add_edge("chat_node", END)

We do the same, but with 4 nodes in sequence!
"""

# Create the graph builder with our State
graph_builder = StateGraph(StockResearchState)
"""
📖 StateGraph(StockResearchState)
---------------------------------
Creates a new graph that uses StockResearchState as its data structure.
Every node will receive and return this state.
"""

# Add all 7 nodes (Enhanced workflow with Technical Analysis!)
graph_builder.add_node("company_intro", company_intro_node)             # Node 1
graph_builder.add_node("sector_analyst", sector_analyst_node)           # Node 2
graph_builder.add_node("company_researcher", company_researcher_node)   # Node 3
graph_builder.add_node("policy_watchdog", policy_watchdog_node)         # Node 4
graph_builder.add_node("investor_sentiment", investor_sentiment_node)   # Node 5
graph_builder.add_node("technical_analysis", technical_analysis_node)   # NEW! Node 6
graph_builder.add_node("investment_suggestion", investment_suggestion_node)  # Node 7
"""
📖 Enhanced Stock Research Workflow (7 Nodes!)
----------------------------------------------
1. Company Intro: What the company does, activities, locations
2. Sector Analyst: Uses intro to identify sector & trends
3. Company Researcher: Financials and news from trusted sources
4. Policy Watchdog: Government policies impact
5. Investor Sentiment: Market sentiment & analyst ratings
6. Technical Analysis: RSI, moving averages, RISK WARNINGS! ⚠️
7. Investment Suggestion: Buy/sell/hold with risk-aware recommendation
"""

# Add edges (the flow)
graph_builder.add_edge(START, "company_intro")
graph_builder.add_edge("company_intro", "sector_analyst")
graph_builder.add_edge("sector_analyst", "company_researcher")
graph_builder.add_edge("company_researcher", "policy_watchdog")
graph_builder.add_edge("policy_watchdog", "investor_sentiment")
graph_builder.add_edge("investor_sentiment", "technical_analysis")
graph_builder.add_edge("technical_analysis", "investment_suggestion")
graph_builder.add_edge("investment_suggestion", END)
"""
📖 Enhanced Flow (7 Nodes with Risk Sentinel!):
-----------------------------------------------
START → company_intro → sector_analyst → company_researcher → 
        policy_watchdog → investor_sentiment → technical_analysis → 
        investment_suggestion → END

This provides COMPREHENSIVE stock analysis with RISK PROTECTION:
1. First understand the company (intro)
2. Then analyze sector (using intro for accurate sector identification)
3. Research company financials from trusted sources
4. Check policy impacts
5. Analyze investor sentiment
6. 📈 TECHNICAL ANALYSIS + RISK WARNINGS (RSI, overbought, negative news!)
7. Finally give risk-aware investment suggestion
"""

# Compile the graph
stock_research_graph = graph_builder.compile()
"""
📖 compile()
------------
Finalizes the graph and makes it ready to run.
After this, you can call: graph.invoke(state)

🔗 In your notes:
    def compile_graph_with_checkpointer(checkpointer):
        graph_with_checkpointer = graph_builder.compile(checkpointer=checkpointer)
        return graph_with_checkpointer
"""


# =============================================================================
#                     RUN FUNCTION
# =============================================================================

def run_stock_research(query: str, company_name: Optional[str] = None) -> Dict[str, Any]:
    """
    📖 Run Stock Research
    =====================
    
    Main function to run the stock research workflow.
    
    Parameters:
    -----------
    query: The user's question (e.g., "Tell me about Tata Motors stock")
    company_name: Optional explicit company name
    
    Returns:
    --------
    Dict with final_recommendation and all intermediate findings
    
    📌 EXAMPLE USAGE:
    ----------------
    result = run_stock_research("Tell me about Reliance stock")
    print(result["final_recommendation"])
    """
    print("\n" + "="*60)
    print("🚀 STARTING LANGGRAPH STOCK RESEARCH WORKFLOW")
    print("="*60)
    print(f"📌 Query: {query}")
    
    # Extract company name from query if not provided
    if not company_name:
        # Use LLM to extract company name accurately
        extract_prompt = f"""
        Extract the INDIAN company or stock name from this query:
        "{query}"
        
        IMPORTANT: This is for INDIAN stocks only (NSE/BSE).
        Return the FULL INDIAN company name.
        
        Examples:
        - "Tell me about Reliance stock" → Reliance Industries Limited
        - "Suggest me the reliance share future" → Reliance Industries Limited
        - "Tata Motors analysis" → Tata Motors Limited
        - "How is HDFC Bank doing" → HDFC Bank Limited
        - "Infosys stock price" → Infosys Limited
        - "HAL stock" → Hindustan Aeronautics Limited  ← NOT Halliburton!
        - "BEL share" → Bharat Electronics Limited
        - "TCS analysis" → Tata Consultancy Services
        - "SBI stock" → State Bank of India
        - "ICICI Bank" → ICICI Bank Limited
        
        RULES:
        1. HAL = Hindustan Aeronautics Limited (NOT Halliburton)
        2. BEL = Bharat Electronics Limited
        3. SAIL = Steel Authority of India Limited
        4. ONGC = Oil and Natural Gas Corporation
        5. NTPC = NTPC Limited
        6. BHEL = Bharat Heavy Electricals Limited
        
        Return ONLY the full Indian company name, nothing else.
        If no specific company is mentioned, return "Unknown".
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": extract_prompt}],
                max_tokens=50
            )
            company_name = response.choices[0].message.content.strip()
            # Clean up quotes if any
            company_name = company_name.strip('"\'')
        except:
            # Fallback to simple extraction
            words = query.split()
            common_words = ["tell", "me", "about", "what", "is", "the", "stock", "share", 
                           "suggest", "how", "future", "price", "analysis", "give", 
                           "show", "check", "find", "get", "of", "for", "a", "an"]
            company_words = []
            for word in words:
                if word.lower() not in common_words and len(word) > 2:
                    company_words.append(word.capitalize())
            company_name = " ".join(company_words[:2]) if company_words else query
    
    print(f"📌 Company: {company_name}")
    
    # Create initial state (Enhanced with 7-node workflow + risk flags!)
    initial_state = {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "company_name": company_name,
        # Node outputs
        "company_intro": None,
        "sector_analysis": None,
        "company_research": None,
        "policy_analysis": None,
        "investor_sentiment": None,
        "technical_analysis": None,  # NEW!
        "investment_suggestion": None,
        "final_recommendation": None,
        # Risk flags from technical analysis
        "risk_warnings": [],
        "is_overbought": False,
        "is_oversold": False,
        "has_negative_news": False,
        "is_speculative": False,
        # Metadata
        "current_date": None,
        "search_results": None
    }
    
    # Run the graph
    try:
        final_state = stock_research_graph.invoke(initial_state)
        
        print("\n" + "="*60)
        print("✅ ENHANCED WORKFLOW COMPLETE! (7 Nodes with Risk Sentinel)")
        print("="*60)
        
        return {
            "query": query,
            "company_name": company_name,
            # Enhanced response with all 7 node outputs
            "company_intro": final_state.get("company_intro"),
            "sector_analysis": final_state.get("sector_analysis"),
            "company_research": final_state.get("company_research"),
            "policy_analysis": final_state.get("policy_analysis"),
            "investor_sentiment": final_state.get("investor_sentiment"),
            "technical_analysis": final_state.get("technical_analysis"),  # NEW!
            "investment_suggestion": final_state.get("investment_suggestion"),
            "final_recommendation": final_state.get("final_recommendation"),
            # Risk flags
            "risk_warnings": final_state.get("risk_warnings", []),
            "is_overbought": final_state.get("is_overbought", False),
            "has_negative_news": final_state.get("has_negative_news", False),
            "is_speculative": final_state.get("is_speculative", False),
            "messages": final_state.get("messages", [])
        }
        
    except Exception as e:
        print(f"❌ Workflow error: {e}")
        return {
            "error": str(e),
            "query": query,
            "company_name": company_name
        }


# =============================================================================
#                     MAIN (FOR TESTING)
# =============================================================================

if __name__ == "__main__":
    """
    📖 Test the workflow directly
    -----------------------------
    Run: python3 stock_graph.py
    """
    print("🧪 Testing Stock Research Workflow...")
    
    result = run_stock_research("Tell me about Tata Motors stock")
    
    print("\n" + "="*60)
    print("📊 FINAL RESULT")
    print("="*60)
    print(result.get("final_recommendation", "No recommendation"))


"""
===================================================================================
                        SUMMARY: STOCK_GRAPH.PY (7-NODE VERSION WITH RISK SENTINEL!)
===================================================================================

This file implements the SHARE MARKET RESEARCH WORKFLOW using LangGraph.

🔗 EXACTLY LIKE YOUR NOTES (07-LangGraph/graph.py)!

📌 ENHANCED WORKFLOW (7 NODES WITH RISK PROTECTION!):
-----------------------------------------------------
1. company_intro_node        → Company overview, activities, locations
2. sector_analyst_node       → Sector trends (uses intro for accurate sector ID!)
3. company_researcher_node   → Financials from trusted sources
4. policy_watchdog_node      → Government policies impact
5. investor_sentiment_node   → Market sentiment, analyst ratings, FII/DII
6. technical_analysis_node   → RSI, Moving Averages, RISK WARNINGS! ⚠️ (NEW!)
7. investment_suggestion_node → RISK-AWARE buy/sell/hold recommendation

GRAPH FLOW:
-----------
    START → company_intro → sector_analyst → company_researcher → 
            policy_watchdog → investor_sentiment → technical_analysis →
            investment_suggestion → END

STATE (StockResearchState):
---------------------------
- messages: Conversation history
- query: User's original question
- company_name: The company being researched
- company_intro: Output from Node 1
- sector_analysis: Output from Node 2
- company_research: Output from Node 3
- policy_analysis: Output from Node 4
- investor_sentiment: Output from Node 5
- technical_analysis: Output from Node 6 (NEW!)
- investment_suggestion: Output from Node 7
- final_recommendation: Combined final report
- risk_warnings: List of risk alerts (NEW!)
- is_overbought: RSI > 70 flag (NEW!)
- has_negative_news: Negative news flag (NEW!)
- is_speculative: High volatility flag (NEW!)

📌 RISK SENTINEL FEATURE (NODE 6):
----------------------------------
This node provides STRICT RULE-BASED warnings:
- RSI > 70 → ⚠️ "OVERBOUGHT - Wait for correction"
- RSI < 30 → 🟢 "OVERSOLD - Potential opportunity"
- Negative news → 🚨 "AVOID NOW - Do not invest!"
- High volatility → ⚡ "SPECULATIVE ZONE - Only for aggressive"

KEY PATTERNS (From Your Notes):
-------------------------------
1. StateGraph(State) - Create graph with typed state
2. add_node(name, func) - Register nodes
3. add_edge(from, to) - Define flow
4. compile() - Finalize graph
5. invoke(state) - Run the graph

FOR YOUR INTERVIEW:
-------------------
"I implemented a comprehensive 7-node stock research workflow using LangGraph.

The flow is:
1. Company Introduction - First understand what the company does
2. Sector Analysis - Uses the intro to accurately identify sector trends
3. Company Research - Gets financials from MoneyControl, Screener.in
4. Policy Watchdog - Checks government policy impacts
5. Investor Sentiment - Analyzes FII/DII holdings and analyst ratings
6. Technical Analysis - RSI, moving averages, and STRICT RISK WARNINGS
   (overbought alerts, negative news detection, speculative zone flags)
7. Investment Suggestion - RISK-AWARE buy/sell/hold with quantity and timeframe

The Technical Analysis node acts as a 'Risk Sentinel' - it flags stocks that
are overbought (RSI > 70), have negative news, or are in speculative zones.
This ensures users don't blindly follow recommendations without understanding
the risks."

===================================================================================
"""

