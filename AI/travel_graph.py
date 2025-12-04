"""
===================================================================================
                    🧳 SMART AI TRAVEL PLANNER - LangGraph Workflow
===================================================================================

📚 WHAT IS THIS FILE?
---------------------
This file implements a COMPREHENSIVE Travel Planner using LangGraph.
It creates personalized travel packages with ALL the features you requested!

🔗 THIS IS SIMILAR TO YOUR stock_graph.py!
Both use:
    - LangGraph StateGraph
    - Multiple nodes connected in sequence
    - State passed between nodes
    - Web search tools for real-time data

📌 WORKFLOW OVERVIEW (8 NODES):
------------------------------
    START
      ↓
    Node 1: DESTINATION RESEARCHER    → Places, weather, safety
      ↓
    Node 2: TRANSPORT FINDER          → Flights, trains, buses, car routes
      ↓
    Node 3: ACCOMMODATION FINDER      → Hotels (central, secure)
      ↓
    Node 4: ACTIVITIES PLANNER        → Sports, adventure, attractions
      ↓
    Node 5: FOOD & SHOPPING GUIDE     → Restaurants, markets
      ↓
    Node 6: TRAVEL REQUIREMENTS       → Visa, SIM, currency, vaccination
      ↓
    Node 7: EMERGENCY & SAFETY        → Hospitals, police, warnings
      ↓
    Node 8: PACKAGE BUILDER           → Creates 3 packages
      ↓
    END

📌 FOR YOUR INTERVIEW:
---------------------
"I built a Travel Planner using LangGraph with 8 specialized nodes.
Each node has a specific responsibility - destination research, transport,
hotels, activities, food, requirements, emergency info, and final package
building. This follows the same pattern as my Stock Research feature but
with more nodes for comprehensive travel planning."

===================================================================================
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

import json
import os
from typing import TypedDict, Optional, Annotated, List, Dict, Any
from datetime import datetime

# LangGraph imports (same as your Notes Compare/07-LangGraph/)
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# OpenAI for LLM calls
from openai import OpenAI

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import search tools from tools_service
from tools_service import smart_web_search, search_news, get_weather

"""
📖 IMPORTS EXPLAINED:
--------------------
1. TypedDict: For defining state structure (like your notes)
2. StateGraph: The main LangGraph class for building workflows
3. START, END: Special nodes for graph entry/exit
4. add_messages: Helper for managing message lists
5. OpenAI: For calling GPT models
6. smart_web_search: Our Tavily-powered search tool

🔗 In your notes (07-LangGraph/graph.py):
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    
SAME IMPORTS! You already know these! 🎉
"""

# Initialize OpenAI client
client = OpenAI()


# =============================================================================
#                           STATE DEFINITION
# =============================================================================

class TravelPlannerState(TypedDict):
    """
    📖 Travel Planner State
    =======================
    
    This defines WHAT DATA flows through our LangGraph workflow.
    Each node can READ and WRITE to this state.
    
    🔗 In your notes (07-LangGraph/graph.py):
        class State(TypedDict):
            messages: Annotated[list, add_messages]
    
    SAME PATTERN! We just have more fields for travel planning.
    
    📌 STATE FIELDS:
    ---------------
    - query: Original user question ("Plan trip to Goa")
    - source: Where user is traveling from
    - destination: Where user is traveling to
    - travel_dates: When they want to travel
    - preferences: User preferences (collected via Human-in-Loop)
    - destination_info: Output from Node 1
    - transport_info: Output from Node 2
    - accommodation_info: Output from Node 3
    - activities_info: Output from Node 4
    - food_shopping_info: Output from Node 5
    - requirements_info: Output from Node 6
    - emergency_info: Output from Node 7
    - packages: Final 3 packages from Node 8
    - error: Any error messages
    - messages: LangGraph message history
    """
    
    # User Input
    query: str                                    # "Plan a trip to Goa from Mumbai"
    source: Optional[str]                         # "Mumbai"
    destination: Optional[str]                    # "Goa"
    travel_dates: Optional[str]                   # "Dec 20-25, 2024"
    
    # User Preferences (Human-in-Loop)
    preferences: Optional[Dict[str, Any]]         # {vehicle: "EV", food: "veg", ...}
    """
    📖 Preferences Structure:
    {
        "vehicle_type": "petrol" | "diesel" | "ev" | "none",
        "food_preference": "veg" | "nonveg" | "both",
        "is_smoker": True | False,
        "budget": "budget" | "midrange" | "luxury",
        "interested_in_adventure": True | False,
        "travel_mode": "flight" | "train" | "bus" | "car"
    }
    """
    
    # Node Outputs (each node writes its findings here)
    destination_info: Optional[str]               # From Node 1: Places, weather, safety
    transport_info: Optional[str]                 # From Node 2: Flights, buses, fares
    accommodation_info: Optional[str]             # From Node 3: Hotels, locations
    activities_info: Optional[str]                # From Node 4: Sports, attractions
    food_shopping_info: Optional[str]             # From Node 5: Restaurants, markets
    requirements_info: Optional[str]              # From Node 6: Visa, SIM, currency
    emergency_info: Optional[str]                 # From Node 7: Hospitals, police
    
    # Final Output
    packages: Optional[Dict[str, Any]]            # 3 travel packages
    final_summary: Optional[str]                  # Complete summary
    
    # Error handling
    error: Optional[str]
    
    # LangGraph messages (for internal use)
    messages: Annotated[list, add_messages]


# =============================================================================
#                     HELPER FUNCTION: LLM CALL
# =============================================================================

def call_llm(prompt: str, system_prompt: str = None) -> str:
    """
    📖 Helper Function: Call OpenAI LLM
    -----------------------------------
    
    Makes a call to GPT-4o-mini and returns the response.
    
    Parameters:
    -----------
    prompt: The user message/question
    system_prompt: Instructions for the AI
    
    Returns:
    --------
    The AI's response as a string
    
    🔗 In your notes (03-Agents/main.py):
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages
        )
    
    SAME PATTERN!
    """
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling LLM: {str(e)}"


# =============================================================================
#                     NODE 1: DESTINATION RESEARCHER
# =============================================================================

def destination_researcher_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    📖 NODE 1: DESTINATION RESEARCHER
    =================================
    
    🎯 RESPONSIBILITY:
    - Research the destination
    - Find places to visit
    - Get weather information
    - Check safety & security
    - Learn about local customs
    
    📌 WHAT THIS NODE DOES:
    1. Searches for "places to visit in {destination}"
    2. Gets weather comparison
    3. Checks safety information
    4. Finds local customs & language info
    
    🔗 In your notes (07-LangGraph/graph.py):
        def chat_node(state: State):
            # Process state and return updated state
            return {"messages": [...]}
    
    SAME PATTERN! Each node takes state, processes it, returns updated state.
    
    📌 FOR INTERVIEW:
    "Node 1 is the Destination Researcher. It uses Tavily web search to find
    places to visit, weather information, and safety details about the destination.
    This gives the foundation for the entire travel plan."
    """
    
    print("\n" + "="*60)
    print("🔍 NODE 1: DESTINATION RESEARCHER")
    print("="*60)
    
    destination = state.get("destination", "unknown destination")
    source = state.get("source", "your location")
    
    print(f"📍 Researching: {destination}")
    print(f"📍 Traveling from: {source}")
    
    try:
        # Search 1: Places to visit
        places_query = f"top tourist places to visit in {destination} attractions sightseeing"
        places_results = smart_web_search(places_query, max_results=5)
        print(f"✅ Found places to visit")
        
        # Search 2: Weather information
        weather_query = f"weather in {destination} current temperature climate"
        weather_results = smart_web_search(weather_query, max_results=3)
        print(f"✅ Found weather info")
        
        # Search 3: Safety information
        safety_query = f"{destination} travel safety tourist safety crime rate travel advisory"
        safety_results = smart_web_search(safety_query, max_results=3)
        print(f"✅ Found safety info")
        
        # Search 4: Local customs
        customs_query = f"{destination} local customs culture language etiquette tips"
        customs_results = smart_web_search(customs_query, max_results=3)
        print(f"✅ Found local customs")
        
        # Use LLM to summarize all findings
        summary_prompt = f"""
        Based on the following search results, create a comprehensive destination guide for {destination}:
        
        PLACES TO VISIT:
        {json.dumps(places_results, indent=2) if isinstance(places_results, dict) else places_results}
        
        WEATHER:
        {json.dumps(weather_results, indent=2) if isinstance(weather_results, dict) else weather_results}
        
        SAFETY:
        {json.dumps(safety_results, indent=2) if isinstance(safety_results, dict) else safety_results}
        
        LOCAL CUSTOMS:
        {json.dumps(customs_results, indent=2) if isinstance(customs_results, dict) else customs_results}
        
        Please provide a structured summary with:
        1. 🏛️ Top 5-7 Places to Visit (with brief descriptions)
        2. 🌤️ Weather Overview (current conditions, best time to visit)
        3. 🛡️ Safety Information (any warnings, general safety level)
        4. 🎭 Local Customs (dress code, tipping, language, etiquette)
        5. 🕐 Time Zone (difference from major Indian cities)
        
        Keep it informative but concise.
        """
        
        destination_info = call_llm(summary_prompt)
        print(f"✅ Destination research complete!")
        
        return {
            **state,
            "destination_info": destination_info
        }
        
    except Exception as e:
        print(f"❌ Error in destination research: {e}")
        return {
            **state,
            "destination_info": f"Error researching destination: {str(e)}",
            "error": str(e)
        }


# =============================================================================
#                     NODE 2: TRANSPORT FINDER
# =============================================================================

def transport_finder_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    📖 NODE 2: TRANSPORT FINDER
    ===========================
    
    🎯 RESPONSIBILITY:
    - Find flight options and prices
    - Find train options and prices
    - Find bus options and prices
    - Calculate car route with fuel costs
    - Show EV charging points (if applicable)
    - Include toll charges and taxes
    - 🆕 Find REST STOPS & WASHROOMS along the route!
    
    📌 WHAT THIS NODE DOES:
    1. Searches MakeMyTrip, IRCTC, RedBus for transport options
    2. Calculates car route with distance and fuel cost
    3. If EV selected, finds charging stations on route
    4. 🆕 Finds rest areas, petrol pumps with washrooms, food stops on highway
    
    📌 FOR INTERVIEW:
    "Node 2 is the Transport Finder. It searches travel websites like MakeMyTrip
    for flights, IRCTC for trains, and calculates car routes with fuel costs.
    I also added rest stop and washroom information for road trips, which is
    essential for comfortable long-distance travel."
    """
    
    print("\n" + "="*60)
    print("🚗 NODE 2: TRANSPORT FINDER")
    print("="*60)
    
    source = state.get("source", "Mumbai")
    destination = state.get("destination", "Goa")
    preferences = state.get("preferences", {})
    vehicle_type = preferences.get("vehicle_type", "petrol")
    travel_mode = preferences.get("travel_mode", "any")
    
    print(f"🚗 Finding transport: {source} → {destination}")
    print(f"🚗 Preferred mode: {travel_mode}")
    print(f"🚗 Vehicle type: {vehicle_type}")
    
    try:
        # Search 1: Flights
        flight_query = f"flights from {source} to {destination} price booking MakeMyTrip"
        flight_results = smart_web_search(flight_query, max_results=3)
        print(f"✅ Found flight options")
        
        # Search 2: Trains
        train_query = f"trains from {source} to {destination} IRCTC schedule fare"
        train_results = smart_web_search(train_query, max_results=3)
        print(f"✅ Found train options")
        
        # Search 3: Buses
        bus_query = f"bus from {source} to {destination} RedBus price timings"
        bus_results = smart_web_search(bus_query, max_results=3)
        print(f"✅ Found bus options")
        
        # Search 4: Car route
        car_query = f"road distance {source} to {destination} route highway toll"
        car_results = smart_web_search(car_query, max_results=3)
        print(f"✅ Found car route info")
        
        # Search 5: EV charging (if applicable)
        ev_info = ""
        if vehicle_type == "ev":
            ev_query = f"EV charging stations {source} to {destination} highway electric vehicle"
            ev_results = smart_web_search(ev_query, max_results=3)
            ev_info = f"\nEV CHARGING STATIONS:\n{json.dumps(ev_results, indent=2) if isinstance(ev_results, dict) else ev_results}"
            print(f"✅ Found EV charging stations")
        
        # 🆕 Search 6: Rest stops & Washrooms (for road trips)
        rest_stops_info = ""
        if travel_mode in ["car", "any", "bus"]:
            rest_query = f"rest stops washrooms petrol pumps restaurants highway {source} to {destination}"
            rest_results = smart_web_search(rest_query, max_results=3)
            rest_stops_info = f"\nREST STOPS & WASHROOMS:\n{json.dumps(rest_results, indent=2) if isinstance(rest_results, dict) else rest_results}"
            print(f"✅ Found rest stops and washroom info")
        
        # Use LLM to summarize
        summary_prompt = f"""
        Based on the following search results, create a transport guide from {source} to {destination}:
        
        User's vehicle preference: {vehicle_type}
        User's travel mode preference: {travel_mode}
        
        FLIGHTS:
        {json.dumps(flight_results, indent=2) if isinstance(flight_results, dict) else flight_results}
        
        TRAINS:
        {json.dumps(train_results, indent=2) if isinstance(train_results, dict) else train_results}
        
        BUSES:
        {json.dumps(bus_results, indent=2) if isinstance(bus_results, dict) else bus_results}
        
        CAR ROUTE:
        {json.dumps(car_results, indent=2) if isinstance(car_results, dict) else car_results}
        {ev_info}
        {rest_stops_info}
        
        Please provide a structured summary with:
        1. ✈️ Flight Options (airlines, approximate prices, duration)
        2. 🚂 Train Options (trains, classes, prices, duration)
        3. 🚌 Bus Options (operators, prices, duration, pickup points)
        4. 🚗 Car Route:
           - Distance and estimated time
           - Fuel cost (calculate for {vehicle_type}: petrol @₹100/L, diesel @₹90/L)
           - Assume mileage: Petrol 12km/L, Diesel 15km/L, EV 6km/kWh
           - Toll charges (estimate)
           - Total driving cost
        5. {"⚡ EV Charging Stations (locations on route, approximate distances)" if vehicle_type == "ev" else ""}
        6. 🚻 REST STOPS & WASHROOMS (Important for Road Trips!):
           - Major petrol pumps with clean washrooms (HP, IOCL, BP)
           - Highway restaurants/dhabas with facilities
           - Approximate distances from start (e.g., "100km from {source}")
           - Recommended food stops
        
        Include pickup points (airports, stations) and where the user will arrive.
        """
        
        transport_info = call_llm(summary_prompt)
        print(f"✅ Transport research complete!")
        
        return {
            **state,
            "transport_info": transport_info
        }
        
    except Exception as e:
        print(f"❌ Error in transport finder: {e}")
        return {
            **state,
            "transport_info": f"Error finding transport: {str(e)}",
            "error": str(e)
        }


# =============================================================================
#                     NODE 3: ACCOMMODATION FINDER
# =============================================================================

def accommodation_finder_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    📖 NODE 3: ACCOMMODATION FINDER
    ===============================
    
    🎯 RESPONSIBILITY:
    - Find hotels based on budget
    - Prioritize central locations
    - Check security and reviews
    - Show how to reach from transport drop-off
    - Local transport options from hotel
    
    📌 FOR INTERVIEW:
    "Node 3 finds accommodation. It searches for hotels that are centrally
    located, have good security, and match the user's budget. It also
    explains how to reach the hotel from the airport/station and what
    local transport is available from the hotel to attractions."
    """
    
    print("\n" + "="*60)
    print("🏨 NODE 3: ACCOMMODATION FINDER")
    print("="*60)
    
    destination = state.get("destination", "Goa")
    preferences = state.get("preferences", {})
    budget = preferences.get("budget", "midrange")
    
    print(f"🏨 Finding hotels in: {destination}")
    print(f"🏨 Budget: {budget}")
    
    try:
        # Search based on budget
        budget_term = {
            "budget": "budget cheap affordable hostel",
            "midrange": "3 star 4 star mid range",
            "luxury": "5 star luxury resort premium"
        }.get(budget, "")
        
        # Search 1: Hotels
        hotel_query = f"best hotels in {destination} {budget_term} central location booking.com"
        hotel_results = smart_web_search(hotel_query, max_results=5)
        print(f"✅ Found hotel options")
        
        # Search 2: Hotel reviews
        review_query = f"best rated hotels {destination} safe secure good reviews"
        review_results = smart_web_search(review_query, max_results=3)
        print(f"✅ Found hotel reviews")
        
        # Search 3: Local transport
        transport_query = f"local transport in {destination} taxi auto rickshaw rent scooter"
        transport_results = smart_web_search(transport_query, max_results=3)
        print(f"✅ Found local transport info")
        
        # Use LLM to summarize
        summary_prompt = f"""
        Based on the following search results, create an accommodation guide for {destination}:
        
        User's budget preference: {budget}
        
        HOTELS:
        {json.dumps(hotel_results, indent=2) if isinstance(hotel_results, dict) else hotel_results}
        
        REVIEWS:
        {json.dumps(review_results, indent=2) if isinstance(review_results, dict) else review_results}
        
        LOCAL TRANSPORT:
        {json.dumps(transport_results, indent=2) if isinstance(transport_results, dict) else transport_results}
        
        Please provide:
        1. 🏨 Top 3-5 Hotel Recommendations:
           - Name, location, approximate price per night
           - Why it's good (central location, security, reviews)
           - Star rating if available
        
        2. 🚕 How to Reach Hotels:
           - From airport: taxi/auto cost and time
           - From railway station: options and costs
           - From bus stand: options and costs
        
        3. 🛵 Local Transport from Hotel:
           - Scooter/bike rental (per day cost)
           - Taxi services available
           - Auto rickshaw availability
           - Any local apps for transport
        
        Prioritize hotels that are:
        - Centrally located (easy access to attractions)
        - Well-reviewed for safety and staff behavior
        - Good connectivity (near main roads/transport)
        """
        
        accommodation_info = call_llm(summary_prompt)
        print(f"✅ Accommodation research complete!")
        
        return {
            **state,
            "accommodation_info": accommodation_info
        }
        
    except Exception as e:
        print(f"❌ Error in accommodation finder: {e}")
        return {
            **state,
            "accommodation_info": f"Error finding accommodation: {str(e)}",
            "error": str(e)
        }


# =============================================================================
#                     NODE 4: ACTIVITIES PLANNER
# =============================================================================

def activities_planner_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    📖 NODE 4: ACTIVITIES PLANNER
    ============================
    
    🎯 RESPONSIBILITY:
    - Find tourist attractions
    - Sports and adventure activities
    - Hidden gems / off-beat places
    - Entry fees and timings
    - How to reach from hotel
    
    📌 FOR INTERVIEW:
    "Node 4 plans activities. If the user expressed interest in adventure,
    it finds sports activities like water sports, trekking, etc. It also
    finds regular tourist spots, entry fees, and how to reach each place
    from the hotel."
    """
    
    print("\n" + "="*60)
    print("🏃 NODE 4: ACTIVITIES PLANNER")
    print("="*60)
    
    destination = state.get("destination", "Goa")
    preferences = state.get("preferences", {})
    interested_in_adventure = preferences.get("interested_in_adventure", True)
    
    print(f"🏃 Finding activities in: {destination}")
    print(f"🏃 Adventure interested: {interested_in_adventure}")
    
    try:
        # Search 1: Tourist attractions
        attractions_query = f"tourist attractions in {destination} sightseeing must visit"
        attractions_results = smart_web_search(attractions_query, max_results=5)
        print(f"✅ Found tourist attractions")
        
        # Search 2: Adventure activities (if interested)
        adventure_info = ""
        if interested_in_adventure:
            adventure_query = f"adventure sports activities in {destination} water sports trekking"
            adventure_results = smart_web_search(adventure_query, max_results=4)
            adventure_info = f"\nADVENTURE ACTIVITIES:\n{json.dumps(adventure_results, indent=2) if isinstance(adventure_results, dict) else adventure_results}"
            print(f"✅ Found adventure activities")
        
        # Search 3: Hidden gems
        hidden_query = f"hidden gems off beat places {destination} local secrets"
        hidden_results = smart_web_search(hidden_query, max_results=3)
        print(f"✅ Found hidden gems")
        
        # Search 4: Entry fees
        fees_query = f"entry fees ticket prices tourist places {destination}"
        fees_results = smart_web_search(fees_query, max_results=3)
        print(f"✅ Found entry fees info")
        
        # Use LLM to summarize
        summary_prompt = f"""
        Based on the following search results, create an activities guide for {destination}:
        
        User interested in adventure: {interested_in_adventure}
        
        TOURIST ATTRACTIONS:
        {json.dumps(attractions_results, indent=2) if isinstance(attractions_results, dict) else attractions_results}
        {adventure_info}
        
        HIDDEN GEMS:
        {json.dumps(hidden_results, indent=2) if isinstance(hidden_results, dict) else hidden_results}
        
        ENTRY FEES:
        {json.dumps(fees_results, indent=2) if isinstance(fees_results, dict) else fees_results}
        
        Please provide:
        1. 🏛️ Must-Visit Tourist Attractions (top 5-7):
           - Name and brief description
           - Entry fee (if any)
           - Best time to visit
           - How to reach (general directions)
        
        2. {"🏄 Adventure & Sports Activities:" if interested_in_adventure else ""}
           {"- Water sports (parasailing, jet ski, scuba, etc.)" if interested_in_adventure else ""}
           {"- Trekking/hiking options" if interested_in_adventure else ""}
           {"- Approximate costs for each" if interested_in_adventure else ""}
        
        3. 💎 Hidden Gems (off-beat places locals love)
        
        4. 💰 Estimated Activity Budget:
           - Entry fees total
           - Adventure activities total
           - Tips for saving money
        """
        
        activities_info = call_llm(summary_prompt)
        print(f"✅ Activities planning complete!")
        
        return {
            **state,
            "activities_info": activities_info
        }
        
    except Exception as e:
        print(f"❌ Error in activities planner: {e}")
        return {
            **state,
            "activities_info": f"Error planning activities: {str(e)}",
            "error": str(e)
        }


# =============================================================================
#                     NODE 5: FOOD & SHOPPING GUIDE
# =============================================================================

def food_shopping_guide_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    📖 NODE 5: FOOD & SHOPPING GUIDE
    ================================
    
    🎯 RESPONSIBILITY:
    - Find restaurants (filtered by veg/non-veg)
    - Local cuisine recommendations
    - Smoking-friendly places (if smoker)
    - Famous markets and shopping areas
    - Clothing/souvenir markets
    
    📌 FOR INTERVIEW:
    "Node 5 is the Food & Shopping Guide. It respects user preferences -
    if they selected vegetarian, it only shows veg restaurants. It also
    finds famous markets for shopping, especially if the destination is
    known for specific items like clothing."
    """
    
    print("\n" + "="*60)
    print("🍽️ NODE 5: FOOD & SHOPPING GUIDE")
    print("="*60)
    
    destination = state.get("destination", "Goa")
    preferences = state.get("preferences", {})
    food_preference = preferences.get("food_preference", "both")
    is_smoker = preferences.get("is_smoker", False)
    
    print(f"🍽️ Finding food & shopping in: {destination}")
    print(f"🍽️ Food preference: {food_preference}")
    print(f"🚬 Smoker: {is_smoker}")
    
    try:
        # Search 1: Restaurants based on preference
        food_term = {
            "veg": "vegetarian pure veg",
            "nonveg": "non vegetarian seafood meat",
            "both": "best restaurants"
        }.get(food_preference, "best restaurants")
        
        restaurant_query = f"best {food_term} restaurants in {destination} famous food"
        restaurant_results = smart_web_search(restaurant_query, max_results=5)
        print(f"✅ Found restaurants")
        
        # Search 2: Local cuisine
        cuisine_query = f"famous local food cuisine must try dishes {destination}"
        cuisine_results = smart_web_search(cuisine_query, max_results=3)
        print(f"✅ Found local cuisine")
        
        # Search 3: Shopping markets
        shopping_query = f"famous markets shopping places in {destination} clothing souvenirs"
        shopping_results = smart_web_search(shopping_query, max_results=4)
        print(f"✅ Found shopping places")
        
        # Search 4: Smoking areas (if smoker)
        smoking_info = ""
        if is_smoker:
            smoking_query = f"smoking allowed areas cafes bars {destination}"
            smoking_results = smart_web_search(smoking_query, max_results=2)
            smoking_info = f"\nSMOKING-FRIENDLY PLACES:\n{json.dumps(smoking_results, indent=2) if isinstance(smoking_results, dict) else smoking_results}"
            print(f"✅ Found smoking-friendly places")
        
        # Use LLM to summarize
        summary_prompt = f"""
        Based on the following search results, create a food & shopping guide for {destination}:
        
        User's food preference: {food_preference}
        User is smoker: {is_smoker}
        
        RESTAURANTS:
        {json.dumps(restaurant_results, indent=2) if isinstance(restaurant_results, dict) else restaurant_results}
        
        LOCAL CUISINE:
        {json.dumps(cuisine_results, indent=2) if isinstance(cuisine_results, dict) else cuisine_results}
        
        SHOPPING:
        {json.dumps(shopping_results, indent=2) if isinstance(shopping_results, dict) else shopping_results}
        {smoking_info}
        
        Please provide:
        1. 🍽️ Restaurant Recommendations (5-7 places):
           {"- ONLY vegetarian/pure veg restaurants" if food_preference == "veg" else ""}
           {"- Include seafood and non-veg specialties" if food_preference == "nonveg" else ""}
           - Name, type of cuisine, price range
           - Famous dishes to try
        
        2. 🥘 Must-Try Local Dishes:
           - Famous local cuisine
           - Where to find the best version
        
        3. 🛍️ Shopping Guide:
           - Famous markets (names, locations, what they're known for)
           - Best places for clothing
           - Souvenir recommendations
           - Bargaining tips
        
        4. {"🚬 Smoking-Friendly Places:" if is_smoker else ""}
           {"- Cafes, bars, areas where smoking is allowed" if is_smoker else ""}
        
        5. 💰 Estimated Food Budget:
           - Budget meal: ₹___
           - Mid-range meal: ₹___
           - Fine dining: ₹___
        """
        
        food_shopping_info = call_llm(summary_prompt)
        print(f"✅ Food & shopping guide complete!")
        
        return {
            **state,
            "food_shopping_info": food_shopping_info
        }
        
    except Exception as e:
        print(f"❌ Error in food & shopping guide: {e}")
        return {
            **state,
            "food_shopping_info": f"Error creating food guide: {str(e)}",
            "error": str(e)
        }


# =============================================================================
#                     NODE 6: TRAVEL REQUIREMENTS
# =============================================================================

def travel_requirements_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    📖 NODE 6: TRAVEL REQUIREMENTS
    ==============================
    
    🎯 RESPONSIBILITY:
    - Visa requirements (for international)
    - SIM card options
    - Currency exchange
    - Vaccination requirements
    - Travel insurance
    - Power adapter needs
    - Useful apps
    
    📌 FOR INTERVIEW:
    "Node 6 handles travel requirements. For international trips, it checks
    visa rules, SIM card options, currency exchange rates, and vaccination
    requirements. It also suggests useful apps and power adapter needs."
    """
    
    print("\n" + "="*60)
    print("🌍 NODE 6: TRAVEL REQUIREMENTS")
    print("="*60)
    
    destination = state.get("destination", "Goa")
    source = state.get("source", "Mumbai")
    
    # Check if international (simple heuristic)
    international_destinations = ["dubai", "singapore", "thailand", "bali", "maldives", 
                                   "europe", "usa", "uk", "australia", "japan", "korea"]
    is_international = any(intl in destination.lower() for intl in international_destinations)
    
    print(f"🌍 Checking requirements for: {destination}")
    print(f"🌍 International trip: {is_international}")
    
    try:
        results = {}
        
        if is_international:
            # Search 1: Visa requirements
            visa_query = f"visa requirements for Indian passport {destination} visa on arrival"
            visa_results = smart_web_search(visa_query, max_results=3)
            results["visa"] = visa_results
            print(f"✅ Found visa info")
            
            # Search 2: SIM card
            sim_query = f"best SIM card for tourists in {destination} prepaid internet"
            sim_results = smart_web_search(sim_query, max_results=2)
            results["sim"] = sim_results
            print(f"✅ Found SIM card info")
            
            # Search 3: Currency
            currency_query = f"currency exchange rate INR to {destination} currency where to exchange"
            currency_results = smart_web_search(currency_query, max_results=2)
            results["currency"] = currency_results
            print(f"✅ Found currency info")
            
            # Search 4: Vaccination
            vaccination_query = f"vaccination requirements {destination} from India health"
            vaccination_results = smart_web_search(vaccination_query, max_results=2)
            results["vaccination"] = vaccination_results
            print(f"✅ Found vaccination info")
        
        # Search: Travel tips (for both domestic and international)
        tips_query = f"travel tips {destination} what to pack useful apps"
        tips_results = smart_web_search(tips_query, max_results=3)
        results["tips"] = tips_results
        print(f"✅ Found travel tips")
        
        # Use LLM to summarize
        summary_prompt = f"""
        Based on the following search results, create a travel requirements guide for {destination}:
        
        Traveling from: {source}
        International trip: {is_international}
        
        SEARCH RESULTS:
        {json.dumps(results, indent=2)}
        
        Please provide:
        {'''
        1. 📋 Visa Requirements:
           - Visa on arrival available? Yes/No
           - Documents needed
           - Fees and validity
           - Processing time
        
        2. 📱 SIM Card Options:
           - Best tourist SIM providers
           - Where to buy (airport, shops)
           - Approximate cost and data
        
        3. 💱 Currency:
           - Local currency name
           - Current exchange rate (approximate)
           - Where to exchange (airport, banks, money changers)
           - Cards accepted?
        
        4. 💉 Vaccination:
           - Required vaccinations (if any)
           - Recommended vaccinations
           - COVID requirements (if any)
        
        5. 🔌 Power Adapter:
           - Plug type needed
           - Voltage information
        ''' if is_international else '''
        1. 📋 Documents Needed:
           - ID proof requirements
           - Any permits needed
        '''}
        
        6. 📱 Useful Apps:
           - Maps/Navigation
           - Local transport
           - Language/Translation
           - Food delivery
        
        7. 🧳 Packing Tips:
           - What to pack based on weather
           - Items to avoid
        
        8. 🏦 Additional Charges:
           - Any tourist taxes
           - Entry fees for special areas
        """
        
        requirements_info = call_llm(summary_prompt)
        print(f"✅ Travel requirements complete!")
        
        return {
            **state,
            "requirements_info": requirements_info
        }
        
    except Exception as e:
        print(f"❌ Error in travel requirements: {e}")
        return {
            **state,
            "requirements_info": f"Error checking requirements: {str(e)}",
            "error": str(e)
        }


# =============================================================================
#                     NODE 7: EMERGENCY & SAFETY
# =============================================================================

def emergency_safety_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    📖 NODE 7: EMERGENCY & SAFETY
    ============================
    
    🎯 RESPONSIBILITY:
    - Find nearest hospitals
    - 24-hour pharmacies
    - Police station contacts
    - Embassy contacts (international)
    - Travel advisories
    - Areas to avoid
    - Scam warnings
    
    📌 FOR INTERVIEW:
    "Node 7 handles emergency and safety information. It finds hospitals,
    pharmacies, and police contacts at the destination. For international
    trips, it also finds the Indian embassy. It warns about any areas to
    avoid and common tourist scams."
    """
    
    print("\n" + "="*60)
    print("🆘 NODE 7: EMERGENCY & SAFETY")
    print("="*60)
    
    destination = state.get("destination", "Goa")
    
    # Check if international
    international_destinations = ["dubai", "singapore", "thailand", "bali", "maldives", 
                                   "europe", "usa", "uk", "australia", "japan", "korea"]
    is_international = any(intl in destination.lower() for intl in international_destinations)
    
    print(f"🆘 Finding emergency info for: {destination}")
    
    try:
        # Search 1: Hospitals
        hospital_query = f"best hospitals in {destination} 24 hours emergency"
        hospital_results = smart_web_search(hospital_query, max_results=3)
        print(f"✅ Found hospitals")
        
        # Search 2: Pharmacies
        pharmacy_query = f"24 hour pharmacy medical store {destination}"
        pharmacy_results = smart_web_search(pharmacy_query, max_results=2)
        print(f"✅ Found pharmacies")
        
        # Search 3: Safety warnings
        safety_query = f"tourist scams {destination} areas to avoid safety tips"
        safety_results = smart_web_search(safety_query, max_results=3)
        print(f"✅ Found safety info")
        
        # Search 4: Embassy (if international)
        embassy_info = ""
        if is_international:
            embassy_query = f"Indian embassy consulate in {destination} contact address"
            embassy_results = smart_web_search(embassy_query, max_results=2)
            embassy_info = f"\nEMBASSY:\n{json.dumps(embassy_results, indent=2) if isinstance(embassy_results, dict) else embassy_results}"
            print(f"✅ Found embassy info")
        
        # Use LLM to summarize
        summary_prompt = f"""
        Based on the following search results, create an emergency & safety guide for {destination}:
        
        International trip: {is_international}
        
        HOSPITALS:
        {json.dumps(hospital_results, indent=2) if isinstance(hospital_results, dict) else hospital_results}
        
        PHARMACIES:
        {json.dumps(pharmacy_results, indent=2) if isinstance(pharmacy_results, dict) else pharmacy_results}
        
        SAFETY:
        {json.dumps(safety_results, indent=2) if isinstance(safety_results, dict) else safety_results}
        {embassy_info}
        
        Please provide:
        1. 🏥 Emergency Contacts:
           - Hospitals (names, addresses, phone numbers)
           - 24-hour pharmacies
           - Police helpline
           - Tourist helpline
           {f"- Indian Embassy/Consulate (address, phone, emergency number)" if is_international else ""}
        
        2. ⚠️ Safety Warnings:
           - Areas to avoid (especially at night)
           - Common tourist scams
           - General safety tips
        
        3. 🚨 Emergency Numbers:
           - Police: ___
           - Ambulance: ___
           - Fire: ___
           - Tourist helpline: ___
        
        4. 💊 Medical Tips:
           - Carry basic medicines
           - Travel insurance recommendation
        """
        
        emergency_info = call_llm(summary_prompt)
        print(f"✅ Emergency & safety info complete!")
        
        return {
            **state,
            "emergency_info": emergency_info
        }
        
    except Exception as e:
        print(f"❌ Error in emergency & safety: {e}")
        return {
            **state,
            "emergency_info": f"Error getting emergency info: {str(e)}",
            "error": str(e)
        }


# =============================================================================
#                     NODE 8: PACKAGE BUILDER
# =============================================================================

def package_builder_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    📖 NODE 8: PACKAGE BUILDER
    ==========================
    
    🎯 RESPONSIBILITY:
    - Combine all information
    - Search for website packages (MakeMyTrip, Yatra)
    - Create 3 travel packages:
      1. Website Package 1
      2. Website Package 2 (alternative)
      3. DIY Solo Plan (personalized)
    
    📌 FOR INTERVIEW:
    "Node 8 is the Package Builder - the final node. It takes all the
    information gathered by previous nodes and creates 3 travel packages.
    Two are from travel websites, and one is a personalized DIY plan
    based on the user's preferences with detailed cost breakdown."
    """
    
    print("\n" + "="*60)
    print("📦 NODE 8: PACKAGE BUILDER")
    print("="*60)
    
    source = state.get("source", "Mumbai")
    destination = state.get("destination", "Goa")
    preferences = state.get("preferences", {})
    
    print(f"📦 Building packages: {source} → {destination}")
    
    try:
        # Search 1: MakeMyTrip packages
        mmt_query = f"MakeMyTrip holiday package {source} to {destination} flight hotel"
        mmt_results = smart_web_search(mmt_query, max_results=3)
        print(f"✅ Found MakeMyTrip packages")
        
        # Search 2: Yatra packages
        yatra_query = f"Yatra travel package {source} to {destination} best deals"
        yatra_results = smart_web_search(yatra_query, max_results=3)
        print(f"✅ Found Yatra packages")
        
        # Gather all previous node outputs
        all_info = f"""
        DESTINATION INFO:
        {state.get('destination_info', 'Not available')}
        
        TRANSPORT INFO:
        {state.get('transport_info', 'Not available')}
        
        ACCOMMODATION INFO:
        {state.get('accommodation_info', 'Not available')}
        
        ACTIVITIES INFO:
        {state.get('activities_info', 'Not available')}
        
        FOOD & SHOPPING INFO:
        {state.get('food_shopping_info', 'Not available')}
        
        TRAVEL REQUIREMENTS:
        {state.get('requirements_info', 'Not available')}
        
        EMERGENCY INFO:
        {state.get('emergency_info', 'Not available')}
        """
        
        # Extract actual URLs from search results for clickable links
        mmt_urls = []
        yatra_urls = []
        
        if isinstance(mmt_results, dict):
            for r in mmt_results.get("results", []):
                url = r.get("url", "")
                if url and "makemytrip" in url.lower():
                    mmt_urls.append(url)
        
        if isinstance(yatra_results, dict):
            for r in yatra_results.get("results", []):
                url = r.get("url", "")
                if url and "yatra" in url.lower():
                    yatra_urls.append(url)
        
        # Use LLM to create final packages
        summary_prompt = f"""
        You are a travel agent creating 3 travel packages for a trip from {source} to {destination}.
        
        USER PREFERENCES:
        {json.dumps(preferences, indent=2)}
        
        WEBSITE PACKAGES FOUND (with actual URLs!):
        
        📌 MakeMyTrip Results:
        {json.dumps(mmt_results, indent=2) if isinstance(mmt_results, dict) else mmt_results}
        Actual URLs found: {mmt_urls if mmt_urls else ['https://www.makemytrip.com/holidays/']}
        
        📌 Yatra Results:
        {json.dumps(yatra_results, indent=2) if isinstance(yatra_results, dict) else yatra_results}
        Actual URLs found: {yatra_urls if yatra_urls else ['https://www.yatra.com/holidays/']}
        
        ALL RESEARCH:
        {all_info}
        
        ═══════════════════════════════════════════════════════════════
        🗺️ FIRST: TRIP OVERVIEW (Show this at the TOP!)
        ═══════════════════════════════════════════════════════════════
        
        Start with a brief, friendly overview:
        
        **🧳 Your Trip to {destination}**
        
        📍 **Route:** {source} → {destination}
        📅 **Duration:** [X days based on typical trip]
        🌤️ **Weather:** [Brief weather summary from destination info]
        ⭐ **Highlights:** [Top 3-4 must-visit places from activities info]
        
        💡 **Quick Tip:** [One useful tip for this destination]
        
        ---
        
        Then show the 3 packages:
        
        ═══════════════════════════════════════════════════════════════
        📦 PACKAGE 1: WEBSITE PACKAGE (MakeMyTrip)
        ═══════════════════════════════════════════════════════════════
        
        📊 **Source:** MakeMyTrip.com (Searched: "{mmt_query}")
        
        - **Details:** [Package name, inclusions from search results]
        - **Includes:** Flight + Hotel at [specific hotel name]
        - **Total Price:** ₹[price] for [X Days/Y Nights]
        
        📅 **DAILY ITINERARY:**
        - **Day 1:** Arrival, Check-in, Evening exploration
        - **Day 2:** [Main attraction/activity from activities info]
        - **Day 3:** [Second major activity/beach/site]
        - **Day 4:** Shopping, local cuisine, Departure
        
        🔗 **Booking Link:** [Book on MakeMyTrip]({mmt_urls[0] if mmt_urls else 'https://www.makemytrip.com/holidays/'})
        
        *URL: {mmt_urls[0] if mmt_urls else 'https://www.makemytrip.com/holidays/'}*
        
        ✅ **WHY RANK #1:** [Explain: Best value for money / Most inclusions / Trusted brand / Best reviews]
        
        ---
        
        ═══════════════════════════════════════════════════════════════
        📦 PACKAGE 2: WEBSITE PACKAGE (Yatra)
        ═══════════════════════════════════════════════════════════════
        
        📊 **Source:** Yatra.com (Searched: "{yatra_query}")
        
        - **Details:** [Package name from search results]
        - **Includes:** Flight + Accommodation (various options)
        - **Total Price:** ₹[price] for [X Days/Y Nights] (varies based on selection)
        
        📅 **DAILY ITINERARY:**
        - **Day 1:** Arrival and check-in
        - **Day 2:** [Major sightseeing]
        - **Day 3:** [Adventure activities]
        - **Day 4-5:** [Beach/relaxation/local exploration]
        
        🔗 **Booking Link:** [Book on Yatra]({yatra_urls[0] if yatra_urls else 'https://www.yatra.com/holidays/'})
        
        *URL: {yatra_urls[0] if yatra_urls else 'https://www.yatra.com/holidays/'}*
        
        🔄 **WHY RANK #2:** [Explain: Good alternative / Different hotel options / More flexibility / Slightly higher price but more customization]
        
        📊 **COMPARISON WITH PACKAGE 1:**
        | Feature | MakeMyTrip | Yatra |
        |---------|------------|-------|
        | Price | ₹X | ₹Y |
        | Hotel Rating | ⭐⭐⭐⭐ | ⭐⭐⭐ |
        | Inclusions | Flight+Hotel+Breakfast | Flight+Hotel |
        | Flexibility | Fixed | Customizable |
        
        ---
        
        ═══════════════════════════════════════════════════════════════
        📦 PACKAGE 3: DIY SOLO PLAN (Personalized for User)
        ═══════════════════════════════════════════════════════════════
        Based on user preferences: {json.dumps(preferences, indent=2)}
        
        Include:
        🚗 TRANSPORT:
        - Recommended mode (based on preference: {preferences.get('travel_mode', 'any')})
        - Detailed cost breakdown
        - If car: fuel cost, tolls, route
        - If EV: charging stations on route
        - 🚻 **REST STOPS & WASHROOMS on the way** (petrol pumps, dhabas with facilities)
        
        🏨 HOTEL:
        - Recommended hotel (from accommodation info)
        - How to reach from drop point
        - Price per night × days = total
        
        🍽️ FOOD:
        - Daily food budget (based on {preferences.get('food_preference', 'both')} preference)
        - Recommended restaurants
        
        🏃 ACTIVITIES & PLACES TO VISIT:
        - 📍 **Must-Visit Places:** (from destination info)
        - Adventure activities (if interested)
        - Entry fees
        - How to reach each place
        
        🛍️ SHOPPING:
        - Budget for shopping
        - Best markets to visit
        
        💰 **TOTAL COST BREAKDOWN:**
        
        Use ONLY this markdown table format (no ASCII art, no box drawings):
        
        | Category | Cost |
        |----------|------|
        | Transport | ₹X,XXX |
        | Hotel (X nights) | ₹X,XXX |
        | Food (X days) | ₹X,XXX |
        | Activities | ₹X,XXX |
        | Local Transport | ₹X,XXX |
        | Shopping | ₹X,XXX |
        | Miscellaneous | ₹X,XXX |
        | **TOTAL** | **₹XX,XXX** |
        
        ⚠️ IMPORTANT: Use markdown tables (pipes and dashes), NOT ASCII box drawings!
        
        ═══════════════════════════════════════════════════════════════
        
        📋 **PACKING CHECKLIST:**
        - [ ] ID Proof / Passport
        - [ ] Comfortable shoes
        - [ ] Weather-appropriate clothing
        - [ ] Medicines
        - [ ] Phone charger / Power bank
        - [ ] Cash + Cards
        
        🆘 **EMERGENCY CONTACTS:**
        - Include key emergency numbers from research
        
        ⚠️ **SAFETY REMINDERS:**
        - Key safety tips from emergency info
        
        End with:
        "⚠️ Prices are estimates based on current search results. 
        Please verify before booking. Have a safe and enjoyable trip! 🧳✈️"
        """
        
        final_summary = call_llm(summary_prompt)
        print(f"✅ Package building complete!")
        
        # Create structured packages dict
        packages = {
            "package_1": "Website Package (MakeMyTrip)",
            "package_2": "Website Package (Yatra)",
            "package_3": "DIY Solo Plan",
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            **state,
            "packages": packages,
            "final_summary": final_summary
        }
        
    except Exception as e:
        print(f"❌ Error in package builder: {e}")
        return {
            **state,
            "packages": None,
            "final_summary": f"Error building packages: {str(e)}",
            "error": str(e)
        }


# =============================================================================
#                     BUILD THE LANGGRAPH
# =============================================================================

def build_travel_graph():
    """
    📖 Build the Travel Planner LangGraph
    =====================================
    
    This function creates and compiles the LangGraph workflow.
    
    🔗 In your notes (07-LangGraph/graph.py):
        graph_builder = StateGraph(State)
        graph_builder.add_node("chat_node", chat_node)
        graph_builder.add_edge(START, "chat_node")
        graph_builder.add_edge("chat_node", END)
        graph = graph_builder.compile()
    
    SAME PATTERN! We just have more nodes.
    
    📌 WORKFLOW:
    START → destination → transport → accommodation → activities → 
    food_shopping → requirements → emergency → package_builder → END
    """
    
    print("🔧 Building Travel Planner LangGraph...")
    
    # Create the graph builder
    graph_builder = StateGraph(TravelPlannerState)
    """
    📖 What is StateGraph?
    ----------------------
    StateGraph is the main class from LangGraph for building workflows.
    It takes a TypedDict that defines the state structure.
    
    🔗 In your notes:
        graph_builder = StateGraph(State)
    """
    
    # Add all 8 nodes
    graph_builder.add_node("destination_researcher", destination_researcher_node)
    graph_builder.add_node("transport_finder", transport_finder_node)
    graph_builder.add_node("accommodation_finder", accommodation_finder_node)
    graph_builder.add_node("activities_planner", activities_planner_node)
    graph_builder.add_node("food_shopping_guide", food_shopping_guide_node)
    graph_builder.add_node("travel_requirements", travel_requirements_node)
    graph_builder.add_node("emergency_safety", emergency_safety_node)
    graph_builder.add_node("package_builder", package_builder_node)
    """
    📖 What is add_node?
    --------------------
    add_node(name, function) adds a node to the graph.
    Each node is a function that takes state and returns updated state.
    
    🔗 In your notes:
        graph_builder.add_node("chat_node", chat_node)
    """
    
    # Add edges (connections between nodes)
    graph_builder.add_edge(START, "destination_researcher")
    graph_builder.add_edge("destination_researcher", "transport_finder")
    graph_builder.add_edge("transport_finder", "accommodation_finder")
    graph_builder.add_edge("accommodation_finder", "activities_planner")
    graph_builder.add_edge("activities_planner", "food_shopping_guide")
    graph_builder.add_edge("food_shopping_guide", "travel_requirements")
    graph_builder.add_edge("travel_requirements", "emergency_safety")
    graph_builder.add_edge("emergency_safety", "package_builder")
    graph_builder.add_edge("package_builder", END)
    """
    📖 What is add_edge?
    --------------------
    add_edge(from_node, to_node) connects two nodes.
    This defines the flow of execution.
    
    🔗 In your notes:
        graph_builder.add_edge(START, "chat_node")
        graph_builder.add_edge("chat_node", END)
    
    Our graph has a LINEAR flow:
    START → node1 → node2 → ... → node8 → END
    """
    
    # Compile the graph
    travel_graph = graph_builder.compile()
    """
    📖 What is compile()?
    ---------------------
    compile() finalizes the graph and makes it ready to run.
    After compilation, you can call graph.invoke() to execute it.
    
    🔗 In your notes:
        graph = graph_builder.compile()
    """
    
    print("✅ Travel Planner LangGraph built successfully!")
    
    return travel_graph


# Create the compiled graph
travel_planner_graph = build_travel_graph()


# =============================================================================
#                     RUN TRAVEL PLANNER
# =============================================================================

def run_travel_planner(
    query: str,
    source: str = None,
    destination: str = None,
    preferences: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    📖 Run the Travel Planner
    =========================
    
    Main function to execute the travel planner workflow.
    
    Parameters:
    -----------
    query: User's travel query ("Plan a trip to Goa from Mumbai")
    source: Starting location (extracted from query if not provided)
    destination: Destination (extracted from query if not provided)
    preferences: User preferences dict (from Human-in-Loop)
    
    Returns:
    --------
    Dict with all travel information and 3 packages
    
    📌 FOR INTERVIEW:
    "I call run_travel_planner() with the query and optional preferences.
    It invokes the LangGraph workflow which runs all 8 nodes in sequence.
    Each node writes its findings to the state, and the final node
    combines everything into travel packages."
    """
    
    print("\n" + "="*70)
    print("🧳 SMART AI TRAVEL PLANNER STARTED")
    print("="*70)
    print(f"Query: {query}")
    
    # Extract source and destination from query if not provided
    if not source or not destination:
        # Use LLM to extract
        extract_prompt = f"""
        Extract the source (from) and destination (to) from this travel query:
        "{query}"
        
        Return ONLY a JSON object like:
        {{"source": "Mumbai", "destination": "Goa"}}
        
        If source is not mentioned, use "your location".
        If destination is not clear, return "unknown".
        """
        
        try:
            extraction = call_llm(extract_prompt)
            # Try to parse JSON
            import re
            json_match = re.search(r'\{[^}]+\}', extraction)
            if json_match:
                extracted = json.loads(json_match.group())
                source = source or extracted.get("source", "your location")
                destination = destination or extracted.get("destination", "unknown")
        except:
            source = source or "your location"
            destination = destination or "unknown destination"
    
    print(f"📍 From: {source}")
    print(f"📍 To: {destination}")
    print(f"⚙️ Preferences: {preferences}")
    
    # Default preferences if not provided
    if not preferences:
        preferences = {
            "vehicle_type": "petrol",
            "food_preference": "both",
            "is_smoker": False,
            "budget": "midrange",
            "interested_in_adventure": True,
            "travel_mode": "any"
        }
    
    # Create initial state
    initial_state = {
        "query": query,
        "source": source,
        "destination": destination,
        "preferences": preferences,
        "messages": []
    }
    
    try:
        # Run the graph
        print("\n🚀 Starting LangGraph workflow...")
        result = travel_planner_graph.invoke(initial_state)
        
        print("\n" + "="*70)
        print("✅ TRAVEL PLANNER COMPLETED!")
        print("="*70)
        
        return {
            "success": True,
            "query": query,
            "source": source,
            "destination": destination,
            "preferences": preferences,
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
        
    except Exception as e:
        print(f"❌ Travel planner failed: {e}")
        return {
            "success": False,
            "query": query,
            "error": str(e)
        }


# =============================================================================
#                     SUMMARY & CHEAT SHEET
# =============================================================================
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🎯 INTERVIEW CHEAT SHEET - TRAVEL PLANNER                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

📌 WHAT IS IT?
--------------
"A comprehensive Travel Planner built using LangGraph with 8 specialized nodes.
Each node has a specific responsibility, and they execute in sequence to create
personalized travel packages."

📌 TECHNOLOGY USED:
------------------
- LangGraph (StateGraph, nodes, edges)
- OpenAI GPT-4o-mini
- Tavily Web Search (for real-time data)
- Python TypedDict (for state management)

📌 THE 8 NODES:
--------------
1. DESTINATION RESEARCHER  → Places, weather, safety, customs
2. TRANSPORT FINDER        → Flights, trains, buses, car routes, EV charging
3. ACCOMMODATION FINDER    → Hotels (central, secure, good reviews)
4. ACTIVITIES PLANNER      → Sports, adventure, attractions, entry fees
5. FOOD & SHOPPING GUIDE   → Restaurants (veg/non-veg), markets
6. TRAVEL REQUIREMENTS     → Visa, SIM, currency, vaccination
7. EMERGENCY & SAFETY      → Hospitals, police, embassy, scam warnings
8. PACKAGE BUILDER         → Creates 3 packages (2 website + 1 DIY)

📌 HUMAN-IN-LOOP FEATURES:
-------------------------
The system asks:
- Vehicle preference: EV / Petrol / Diesel
- Food preference: Veg / Non-veg
- Smoker: Yes / No
- Budget: Budget / Mid-range / Luxury
- Adventure interested: Yes / No
- Travel mode: Flight / Train / Bus / Car

📌 OUTPUT - 3 PACKAGES:
----------------------
1. Website Package 1 (MakeMyTrip)  → Pre-made bundle
2. Website Package 2 (Yatra)       → Alternative option
3. DIY Solo Plan                   → Personalized with cost breakdown

📌 HOW IT WORKS (FLOW):
----------------------
User Query → Extract Source/Destination → Run 8 Nodes in Sequence → 
Each Node Searches Web + Uses LLM → Package Builder Combines All → 
Output 3 Packages

📌 CODE PATTERN (same as Stock Research):
----------------------------------------
```python
# Define State
class TravelPlannerState(TypedDict):
    query: str
    destination_info: str
    # ... more fields

# Define Nodes
def destination_researcher_node(state):
    # Search + LLM summarize
    return {**state, "destination_info": info}

# Build Graph
graph_builder = StateGraph(TravelPlannerState)
graph_builder.add_node("destination_researcher", destination_researcher_node)
graph_builder.add_edge(START, "destination_researcher")
# ... more nodes and edges
graph = graph_builder.compile()

# Run
result = graph.invoke(initial_state)
```

📌 INTERVIEW QUESTIONS & ANSWERS:
--------------------------------

Q: "Why 8 nodes instead of one big function?"
A: "Separation of concerns. Each node has a single responsibility, making the 
   code maintainable and debuggable. If hotel search fails, I know exactly 
   where to look."

Q: "How does state flow between nodes?"
A: "LangGraph passes the state dict to each node. Each node reads what it needs,
   adds its findings, and passes it to the next node. Like a relay race."

Q: "Why use web search instead of APIs?"
A: "Flexibility. Web search (Tavily) can find current prices from any travel
   site without needing individual API integrations. Real travel APIs often
   require partnerships and fees."

Q: "How do you handle user preferences?"
A: "Human-in-Loop pattern. Before running the graph, I collect preferences
   (vehicle type, food, budget) and include them in the initial state.
   Each node respects these preferences when searching and summarizing."

Q: "What if a node fails?"
A: "Each node has try-catch. If it fails, it writes an error to state and
   continues. The Package Builder still creates packages with available info
   and notes what couldn't be found."

╚══════════════════════════════════════════════════════════════════════════════╝
"""

