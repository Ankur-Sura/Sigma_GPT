"""
===================================================================================
            SOLO_TRIP_GRAPH.PY - Human-in-the-Loop Solo Trip Planner
===================================================================================

📚 WHAT IS THIS FILE?
---------------------
This implements HUMAN-IN-THE-LOOP (HITL) for Solo Trip Planning using LangGraph.

🔗 BASED ON YOUR TEACHER'S CODE PATTERN:
----------------------------------------
1. interrupt() - Pauses graph, saves state to MongoDB
2. Command(resume={"data": response}) - Resumes with human input

📌 THE WORKFLOW (11 NODES):
---------------------------
START → destination_research → transport_discovery → 
        [INTERRUPT - Ask preferences] → 
        personalized_plan → accommodation → activities → 
        food_guide → shopping_guide → requirements → emergency → package_builder → END

===================================================================================
"""

# =============================================================================
#                           IMPORTS SECTION
# =============================================================================

import os
import json
from datetime import datetime
from typing import TypedDict, Annotated, List, Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt, Command
from langgraph.checkpoint.mongodb import MongoDBSaver

# NOTE: We don't use ToolNode/tools_condition here
# We use direct interrupt() calls for Human-in-the-Loop

# OpenAI
from openai import OpenAI

# Our tools
from tools_service import smart_web_search, search_news, get_current_datetime

# =============================================================================
#                           INITIALIZE
# =============================================================================

client = OpenAI()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")


def _sanitize_mongo_uri(uri: str) -> str:
    """
    📖 Sanitize MongoDB URI
    -----------------------
    Removes any whitespace and validates the URI format.
    pymongo is strict about URI format, so we clean it up.
    """
    if not uri:
        return uri
    # Remove leading/trailing whitespace
    uri = uri.strip()
    # Remove any quotes that might have been added
    if uri.startswith('"') and uri.endswith('"'):
        uri = uri[1:-1]
    if uri.startswith("'") and uri.endswith("'"):
        uri = uri[1:-1]
    return uri

# =============================================================================
#                           STATE DEFINITION
# =============================================================================

class SoloTripState(TypedDict):
    """
    📖 Solo Trip State with Human-in-the-Loop Support
    ==================================================
    """
    messages: Annotated[list, add_messages]
    
    # Trip basics
    query: str
    origin: str
    destination: str
    distance_km: Optional[int]
    
    # Research outputs
    destination_info: Optional[str]
    transport_options: Optional[str]
    
    # 🆕 HUMAN-IN-THE-LOOP fields
    awaiting_human_input: bool
    human_questions: Optional[List[Dict]]
    
    # User preferences (filled after HITL)
    travel_mode: Optional[str]  # "personal_vehicle" | "public" | "taxi" | "flight"
    vehicle_details: Optional[Dict]  # {make, model, fuel_type, ev_range, current_charge}
    food_preference: Optional[str]  # "veg" | "non_veg" | "vegan"
    budget_level: Optional[str]  # "budget" | "mid_range" | "premium"
    accommodation_type: Optional[str]  # "hotel" | "hostel" | "airbnb" | "camping"
    
    # Personalized plan outputs
    personalized_transport: Optional[str]
    charging_stops: Optional[List[Dict]]  # For EV: [{location, km_from_start, charger_type}]
    accommodation_plan: Optional[str]
    activities_plan: Optional[str]
    food_guide: Optional[str]
    shopping_guide: Optional[str]  # 🆕 Shopping at destination
    requirements: Optional[str]
    emergency_info: Optional[str]
    final_package: Optional[str]


# =============================================================================
#                     HUMAN-IN-THE-LOOP PATTERN
# =============================================================================
# 
# We use interrupt() directly in the node function (like your teacher's code!)
# 
# The pattern is:
# 1. Node calls interrupt(questions) → Graph pauses, state saved to MongoDB
# 2. API returns with status "awaiting_input"
# 3. User fills form, calls /resume endpoint
# 4. Command(resume={"data": answers}) resumes the graph
# 5. Node receives the answers and continues
#


# =============================================================================
#                     NODE 1: DESTINATION RESEARCH (AUTO)
# =============================================================================

def destination_research_node(state: SoloTripState) -> Dict[str, Any]:
    """
    📖 Node 1: Research the destination (runs automatically)
    """
    print("\n" + "="*60)
    print("📍 NODE 1: DESTINATION RESEARCH")
    print("="*60)
    
    query = state["query"]
    
    # Extract origin and destination
    extract_prompt = f"""
    Extract origin and destination from this trip query:
    "{query}"
    
    Return JSON: {{"origin": "city name", "destination": "city name"}}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": extract_prompt}]
    )
    
    locations = json.loads(response.choices[0].message.content)
    origin = locations.get("origin", "Unknown")
    destination = locations.get("destination", "Unknown")
    
    print(f"📍 Origin: {origin}")
    print(f"📍 Destination: {destination}")
    
    # Research destination
    dest_query = f"{destination} tourist information weather best time to visit"
    dest_results = smart_web_search(dest_query, max_results=3)
    
    # Get distance
    distance_query = f"distance from {origin} to {destination} by road km"
    distance_results = smart_web_search(distance_query, max_results=2)
    
    # Summarize
    summary_prompt = f"""
    Summarize destination info for a solo trip from {origin} to {destination}:
    
    Destination Info: {json.dumps(dest_results.get('results', []))}
    Distance Info: {json.dumps(distance_results.get('results', []))}
    
    Provide:
    1. Distance in km (approximate)
    2. Best time to visit
    3. Weather expectations
    4. Solo traveler tips for this destination
    
    Keep it concise (100-150 words).
    """
    
    summary = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": summary_prompt}]
    )
    
    destination_info = summary.choices[0].message.content
    
    # Try to extract distance using LLM
    distance_km = None
    try:
        import re
        # First try regex on search results
        for result in distance_results.get("results", []):
            text = result.get("content", "")
            # Match patterns like "759 km", "800km", "1,200 km"
            match = re.search(r'(\d{1,2},?\d{3}|\d{2,4})\s*km', text)
            if match:
                dist_str = match.group(1).replace(",", "")
                distance_km = int(dist_str)
                break
        
        # If still no distance, ask LLM to extract it
        if not distance_km:
            dist_prompt = f"""
            Extract the road distance in km from {origin} to {destination}.
            Search results: {json.dumps(distance_results.get('results', [])[:2])}
            
            Return ONLY a number (e.g., 750). If not found, estimate based on cities.
            """
            dist_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": dist_prompt}],
                max_tokens=20
            )
            try:
                dist_text = dist_response.choices[0].message.content.strip()
                distance_km = int(re.search(r'\d+', dist_text).group())
            except:
                distance_km = 500  # Default fallback
    except:
        distance_km = 500  # Default fallback
    
    print(f"✅ Destination research complete!")
    print(f"📏 Distance: {distance_km} km")
    
    return {
        "origin": origin,
        "destination": destination,
        "distance_km": distance_km,
        "destination_info": destination_info
    }


# =============================================================================
#                     NODE 2: TRANSPORT OPTIONS DISCOVERY (AUTO)
# =============================================================================

def transport_discovery_node(state: SoloTripState) -> Dict[str, Any]:
    """
    📖 Node 2: Discover all transport options (runs automatically)
    """
    print("\n" + "="*60)
    print("🚗 NODE 2: TRANSPORT OPTIONS DISCOVERY")
    print("="*60)
    
    origin = state.get("origin", "")
    destination = state.get("destination", "")
    distance = state.get("distance_km", 0)
    
    # Search for transport options
    transport_query = f"how to travel from {origin} to {destination} by road train flight bus"
    transport_results = smart_web_search(transport_query, max_results=3)
    
    summary_prompt = f"""
    List all transport options from {origin} to {destination} (Distance: {distance} km):
    
    Search Results: {json.dumps(transport_results.get('results', []))}
    
    Provide brief summary of:
    1. By Road (personal vehicle) - time, route
    2. By Train - major trains, time
    3. By Flight - if available
    4. By Bus - options
    
    Keep it brief (80-100 words).
    """
    
    summary = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": summary_prompt}]
    )
    
    transport_options = summary.choices[0].message.content
    
    print(f"✅ Transport options discovered!")
    
    return {
        "transport_options": transport_options
    }


# =============================================================================
#                     NODE 3: HUMAN PREFERENCES (INTERRUPT!)
# =============================================================================

def human_preferences_node(state: SoloTripState) -> Dict[str, Any]:
    """
    📖 Node 3: Ask user for preferences - THIS USES INTERRUPT!
    
    🛑 This node PAUSES the workflow and waits for human input!
    """
    print("\n" + "="*60)
    print("🛑 NODE 3: HUMAN PREFERENCES (INTERRUPT)")
    print("="*60)
    
    origin = state.get("origin", "")
    destination = state.get("destination", "")
    distance = state.get("distance_km", 0)
    
    # Create the interrupt question
    questions = {
        "type": "solo_trip_preferences",
        "message": f"Let's personalize your solo trip from {origin} to {destination} ({distance} km)!",
        "fields": [
            {
                "id": "travel_mode",
                "type": "select",
                "label": "🚗 How would you like to travel?",
                "options": [
                    {"value": "personal_vehicle", "label": "Personal Vehicle"},
                    {"value": "public_transport", "label": "Public Transport (Train/Bus)"},
                    {"value": "taxi", "label": "Taxi/Cab"},
                    {"value": "flight", "label": "Flight"}
                ],
                "required": True
            },
            {
                "id": "vehicle_make",
                "type": "text",
                "label": "🚙 Car Make (if personal vehicle)",
                "placeholder": "e.g., Tata, Mahindra, Hyundai",
                "showIf": {"travel_mode": "personal_vehicle"}
            },
            {
                "id": "vehicle_model",
                "type": "text", 
                "label": "🚙 Car Model",
                "placeholder": "e.g., Nexon EV, XUV700",
                "showIf": {"travel_mode": "personal_vehicle"}
            },
            {
                "id": "fuel_type",
                "type": "select",
                "label": "⛽ Fuel Type",
                "options": [
                    {"value": "petrol", "label": "Petrol"},
                    {"value": "diesel", "label": "Diesel"},
                    {"value": "cng", "label": "CNG"},
                    {"value": "ev", "label": "Electric (EV)"}
                ],
                "showIf": {"travel_mode": "personal_vehicle"}
            },
            {
                "id": "ev_range",
                "type": "number",
                "label": "🔋 EV Range (km per full charge)",
                "placeholder": "e.g., 350",
                "showIf": {"fuel_type": "ev"}
            },
            {
                "id": "current_charge",
                "type": "number",
                "label": "🔋 Current Battery (%)",
                "placeholder": "e.g., 100",
                "showIf": {"fuel_type": "ev"}
            },
            {
                "id": "food_preference",
                "type": "select",
                "label": "🍽️ Food Preference",
                "options": [
                    {"value": "veg", "label": "Vegetarian"},
                    {"value": "non_veg", "label": "Non-Vegetarian"},
                    {"value": "vegan", "label": "Vegan"},
                    {"value": "eggetarian", "label": "Eggetarian"}
                ],
                "required": True
            },
            {
                "id": "budget_level",
                "type": "select",
                "label": "💰 Budget Level",
                "options": [
                    {"value": "budget", "label": "Budget (₹500-1500/day)"},
                    {"value": "mid_range", "label": "Mid-Range (₹1500-4000/day)"},
                    {"value": "premium", "label": "Premium (₹4000+/day)"}
                ],
                "required": True
            },
            {
                "id": "accommodation_type",
                "type": "select",
                "label": "🏨 Accommodation Preference",
                "options": [
                    {"value": "hotel", "label": "Hotel"},
                    {"value": "hostel", "label": "Hostel"},
                    {"value": "airbnb", "label": "Airbnb/Homestay"},
                    {"value": "camping", "label": "Camping"},
                    {"value": "none", "label": "No Stay (Day Trip)"}
                ],
                "required": True
            }
        ]
    }
    
    print("🛑 Sending interrupt to get user preferences...")
    
    # 🛑 THIS PAUSES THE GRAPH AND SAVES STATE TO MONGODB!
    human_response = interrupt(questions)
    
    print(f"✅ Received human response: {human_response}")
    
    # Parse the response
    data = human_response.get("data", {})
    
    # Build vehicle details if personal vehicle
    vehicle_details = None
    if data.get("travel_mode") == "personal_vehicle":
        vehicle_details = {
            "make": data.get("vehicle_make", ""),
            "model": data.get("vehicle_model", ""),
            "fuel_type": data.get("fuel_type", "petrol"),
            "ev_range": data.get("ev_range"),
            "current_charge": data.get("current_charge")
        }
    
    return {
        "awaiting_human_input": False,
        "travel_mode": data.get("travel_mode"),
        "vehicle_details": vehicle_details,
        "food_preference": data.get("food_preference"),
        "budget_level": data.get("budget_level"),
        "accommodation_type": data.get("accommodation_type")
    }


# =============================================================================
#                     NODE 4: PERSONALIZED TRANSPORT PLAN
# =============================================================================

def personalized_transport_node(state: SoloTripState) -> Dict[str, Any]:
    """
    📖 Node 4: Create personalized transport plan based on user preferences
    """
    print("\n" + "="*60)
    print("🚗 NODE 4: PERSONALIZED TRANSPORT PLAN")
    print("="*60)
    
    origin = state.get("origin", "")
    destination = state.get("destination", "")
    # Handle None distance - default to 200 km if unknown
    distance = state.get("distance_km") or 200
    travel_mode = state.get("travel_mode", "personal_vehicle")
    vehicle_details = state.get("vehicle_details") or {}
    
    charging_stops = []
    
    # Special handling for EV
    if travel_mode == "personal_vehicle" and vehicle_details:
        fuel_type = vehicle_details.get("fuel_type", "petrol")
        
        if fuel_type == "ev":
            ev_range = vehicle_details.get("ev_range") or 300
            current_charge = vehicle_details.get("current_charge") or 100
            
            print(f"🔋 EV Mode: {vehicle_details.get('make')} {vehicle_details.get('model')}")
            print(f"🔋 Range: {ev_range} km, Current: {current_charge}%")
            
            # Calculate charging stops
            usable_range = (ev_range * current_charge / 100) * 0.8  # 80% buffer
            
            if distance > usable_range:
                # Search for EV charging stations
                ev_query = f"EV charging stations {origin} to {destination} highway"
                ev_results = smart_web_search(ev_query, max_results=3)
                
                # Calculate stops needed (ensure distance is a number)
                num_stops = int(float(distance) / (float(ev_range) * 0.7)) + 1
                
                charging_prompt = f"""
                Plan EV charging stops for {origin} to {destination} ({distance} km).
                
                EV Details:
                - Car: {vehicle_details.get('make')} {vehicle_details.get('model')}
                - Range: {ev_range} km
                - Current Charge: {current_charge}%
                
                Search Results: {json.dumps(ev_results.get('results', []))}
                
                Suggest {num_stops} charging stops with:
                - Location name
                - Approximate km from start
                - Charger type (DC Fast/AC)
                - Estimated charging time
                
                Format as JSON list.
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": charging_prompt}]
                )
                
                try:
                    charging_stops = json.loads(response.choices[0].message.content)
                except:
                    charging_stops = [{"note": "Charging stations along highway"}]
    
    # Create transport plan
    transport_prompt = f"""
    Create a personalized transport plan for solo trip from {origin} to {destination}.
    
    User Preferences:
    - Travel Mode: {travel_mode}
    - Vehicle: {json.dumps(vehicle_details) if vehicle_details else 'N/A'}
    - Distance: {distance} km
    
    Include:
    1. Best route
    2. Estimated time
    3. Rest stops every 2-3 hours
    4. {'EV charging stops' if vehicle_details and vehicle_details.get('fuel_type') == 'ev' else 'Fuel stops'}
    5. Safe night halt locations (if journey > 8 hours)
    6. Toll information
    7. Solo driver safety tips
    
    Keep it practical and detailed (200 words).
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": transport_prompt}]
    )
    
    personalized_transport = response.choices[0].message.content
    
    print(f"✅ Personalized transport plan ready!")
    if charging_stops:
        print(f"🔋 EV Charging stops: {len(charging_stops)}")
    
    return {
        "personalized_transport": personalized_transport,
        "charging_stops": charging_stops
    }


# =============================================================================
#                     NODE 5-9: REMAINING NODES (Similar to travel_graph.py)
# =============================================================================

def accommodation_node(state: SoloTripState) -> Dict[str, Any]:
    """Node 5: Accommodation based on preferences"""
    print("\n🏨 NODE 5: ACCOMMODATION")
    
    destination = state.get("destination", "")
    budget = state.get("budget_level", "mid_range")
    acc_type = state.get("accommodation_type", "hotel")
    
    acc_query = f"solo traveler {acc_type} {destination} {budget}"
    results = smart_web_search(acc_query, max_results=2)
    
    prompt = f"""
    Recommend accommodation for solo traveler in {destination}:
    - Type: {acc_type}
    - Budget: {budget}
    
    Search: {json.dumps(results.get('results', []))}
    
    Suggest 2-3 options with prices. Focus on solo-traveler friendly places.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"accommodation_plan": response.choices[0].message.content}


def activities_node(state: SoloTripState) -> Dict[str, Any]:
    """Node 6: Solo-friendly activities"""
    print("\n🎯 NODE 6: ACTIVITIES")
    
    destination = state.get("destination", "")
    budget = state.get("budget_level", "mid_range")
    
    query = f"solo traveler things to do {destination}"
    results = smart_web_search(query, max_results=2)
    
    prompt = f"""
    Suggest solo-friendly activities in {destination}:
    Search: {json.dumps(results.get('results', []))}
    
    Focus on:
    - Activities good for solo travelers
    - Mix of adventure and relaxation
    - Budget: {budget}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"activities_plan": response.choices[0].message.content}


def food_guide_node(state: SoloTripState) -> Dict[str, Any]:
    """Node 7: Food guide based on preference + Local Dishes"""
    print("\n🍽️ NODE 7: FOOD GUIDE + LOCAL DISHES")
    
    destination = state.get("destination", "")
    food_pref = state.get("food_preference", "non_veg")
    budget = state.get("budget_level", "mid_range")
    
    # Search for restaurants
    restaurant_query = f"{food_pref} restaurants {destination} {budget}"
    restaurant_results = smart_web_search(restaurant_query, max_results=2)
    
    # Search for famous local dishes
    local_dishes_query = f"famous local food dishes cuisine {destination} must try"
    dishes_results = smart_web_search(local_dishes_query, max_results=2)
    
    prompt = f"""
    Create a comprehensive food guide for solo traveler in {destination}:
    
    User Preference: {food_pref}
    Budget: {budget}
    
    Restaurant Search: {json.dumps(restaurant_results.get('results', []))}
    Local Dishes Search: {json.dumps(dishes_results.get('results', []))}
    
    Provide:
    
    ## 🍛 MUST-TRY LOCAL DISHES
    - List 5-6 famous local dishes of {destination}
    - Brief description of each dish
    - Mark if vegetarian/non-vegetarian
    - Approximate price range
    
    ## 🍽️ RECOMMENDED RESTAURANTS
    - 3-4 restaurants matching {food_pref} preference
    - Address/area and price range
    - What to order at each
    
    ## 🌟 STREET FOOD SPOTS
    - Famous street food areas
    - Must-try street snacks
    - Hygiene tips for solo travelers
    
    ## 💡 SOLO DINING TIPS
    - Best times to visit restaurants solo
    - Counter seating or communal tables recommendations
    
    Make it practical and appetizing!
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"food_guide": response.choices[0].message.content}


def shopping_guide_node(state: SoloTripState) -> Dict[str, Any]:
    """Node 8: Shopping guide at destination"""
    print("\n🛍️ NODE 8: SHOPPING GUIDE")
    
    destination = state.get("destination", "")
    budget = state.get("budget_level", "mid_range")
    
    # Search for shopping places
    shopping_query = f"shopping places markets souvenirs {destination} tourist"
    shopping_results = smart_web_search(shopping_query, max_results=3)
    
    # Search for local specialties to buy
    specialty_query = f"what to buy famous products handicrafts {destination}"
    specialty_results = smart_web_search(specialty_query, max_results=2)
    
    prompt = f"""
    Create a shopping guide for solo traveler in {destination}:
    
    Budget Level: {budget}
    
    Shopping Search: {json.dumps(shopping_results.get('results', []))}
    Specialty Search: {json.dumps(specialty_results.get('results', []))}
    
    Provide:
    
    ## 🎁 WHAT TO BUY IN {destination.upper()}
    - 5-6 famous local products/souvenirs
    - Why it's special to this region
    - Price range for each
    
    ## 🏪 BEST SHOPPING SPOTS
    - Local markets (with timings and best days)
    - Malls/Shopping complexes
    - Government emporiums (for authentic items)
    
    ## 💰 BARGAINING TIPS
    - Where to bargain vs fixed price shops
    - Expected discount percentages
    - Red flags to avoid scams
    
    ## 🧳 PACKING & SHIPPING
    - Items allowed/prohibited in luggage
    - Fragile item packing tips
    - Courier services for large items
    
    Make it practical for a solo shopper!
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"shopping_guide": response.choices[0].message.content}


def requirements_node(state: SoloTripState) -> Dict[str, Any]:
    """Node 9: Solo travel requirements"""
    print("\n📋 NODE 9: REQUIREMENTS")
    
    destination = state.get("destination", "")
    travel_mode = state.get("travel_mode", "")
    
    prompt = f"""
    Solo travel requirements for {destination}:
    - Travel mode: {travel_mode}
    
    Include:
    - Documents needed
    - Safety tips for solo travelers
    - Things to pack
    - Emergency contacts
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"requirements": response.choices[0].message.content}


def emergency_node(state: SoloTripState) -> Dict[str, Any]:
    """Node 10: Emergency info"""
    print("\n🆘 NODE 10: EMERGENCY INFO")
    
    origin = state.get("origin", "")
    destination = state.get("destination", "")
    
    query = f"emergency contacts hospitals {destination} highway {origin}"
    results = smart_web_search(query, max_results=2)
    
    prompt = f"""
    Emergency information for solo trip {origin} to {destination}:
    
    Search: {json.dumps(results.get('results', []))}
    
    Provide:
    - Emergency numbers
    - Hospitals along route
    - Police stations
    - Roadside assistance
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"emergency_info": response.choices[0].message.content}


def package_builder_node(state: SoloTripState) -> Dict[str, Any]:
    """Node 11: Final package"""
    print("\n📦 NODE 11: PACKAGE BUILDER")
    
    origin = state.get("origin", "")
    destination = state.get("destination", "")
    distance = state.get("distance_km") or 500  # Default to 500 if None
    
    # Compile all information
    final_package = f"""
# 🎒 Solo Trip Package: {origin} → {destination}

**Distance:** {distance} km (approx)
**Travel Mode:** {state.get('travel_mode', 'N/A')}
**Budget Level:** {state.get('budget_level', 'N/A')}

---

## 📍 Destination Overview
{state.get('destination_info', 'N/A')}

---

## 🚗 Your Personalized Transport Plan
{state.get('personalized_transport', 'N/A')}

{f"### 🔋 EV Charging Stops" + chr(10) + json.dumps(state.get('charging_stops', []), indent=2) if state.get('charging_stops') else ''}

---

## 🏨 Accommodation
{state.get('accommodation_plan', 'N/A')}

---

## 🎯 Activities
{state.get('activities_plan', 'N/A')}

---

## 🍽️ Food Guide ({state.get('food_preference', 'N/A')})
{state.get('food_guide', 'N/A')}

---

## 🛍️ Shopping Guide
{state.get('shopping_guide', 'N/A')}

---

## 📋 Requirements & Checklist
{state.get('requirements', 'N/A')}

---

## 🆘 Emergency Information
{state.get('emergency_info', 'N/A')}

---

**Happy Solo Travels! Stay safe! 🚗✨**
"""
    
    print("✅ Solo trip package complete!")
    
    return {
        "final_package": final_package,
        "messages": [{"role": "assistant", "content": final_package}]
    }


# =============================================================================
#                     BUILD THE GRAPH
# =============================================================================

def build_solo_trip_graph():
    """Build the Solo Trip Graph with Human-in-the-Loop"""
    
    graph_builder = StateGraph(SoloTripState)
    
    # Add all nodes (11 total)
    graph_builder.add_node("destination_research", destination_research_node)
    graph_builder.add_node("transport_discovery", transport_discovery_node)
    graph_builder.add_node("human_preferences", human_preferences_node)  # 🛑 INTERRUPT NODE
    graph_builder.add_node("personalized_transport", personalized_transport_node)
    graph_builder.add_node("accommodation", accommodation_node)
    graph_builder.add_node("activities", activities_node)
    graph_builder.add_node("food_guide", food_guide_node)
    graph_builder.add_node("shopping_guide", shopping_guide_node)  # 🆕 SHOPPING
    graph_builder.add_node("requirements", requirements_node)
    graph_builder.add_node("emergency", emergency_node)
    graph_builder.add_node("package_builder", package_builder_node)
    
    # Add edges (11 nodes)
    graph_builder.add_edge(START, "destination_research")
    graph_builder.add_edge("destination_research", "transport_discovery")
    graph_builder.add_edge("transport_discovery", "human_preferences")  # 🛑 GOES TO INTERRUPT
    graph_builder.add_edge("human_preferences", "personalized_transport")  # RESUMES AFTER HUMAN INPUT
    graph_builder.add_edge("personalized_transport", "accommodation")
    graph_builder.add_edge("accommodation", "activities")
    graph_builder.add_edge("activities", "food_guide")
    graph_builder.add_edge("food_guide", "shopping_guide")  # 🆕 SHOPPING
    graph_builder.add_edge("shopping_guide", "requirements")
    graph_builder.add_edge("requirements", "emergency")
    graph_builder.add_edge("emergency", "package_builder")
    graph_builder.add_edge("package_builder", END)
    
    return graph_builder


# Compile without checkpointer (for testing)
solo_trip_graph_builder = build_solo_trip_graph()
solo_trip_graph = solo_trip_graph_builder.compile()


def create_solo_trip_graph_with_checkpointer(checkpointer):
    """Create graph with MongoDB checkpointer for HITL"""
    return solo_trip_graph_builder.compile(checkpointer=checkpointer)


# =============================================================================
#                     RUN FUNCTIONS
# =============================================================================

def start_solo_trip(query: str, thread_id: str = "solo_trip_1") -> Dict[str, Any]:
    """
    Start a solo trip planning session.
    This will run until it hits the INTERRUPT for human preferences.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # Sanitize URI to ensure proper format
    sanitized_uri = _sanitize_mongo_uri(MONGODB_URI)
    with MongoDBSaver.from_conn_string(sanitized_uri) as checkpointer:
        graph = create_solo_trip_graph_with_checkpointer(checkpointer)
        
        initial_state = {
            "messages": [{"role": "user", "content": query}],
            "query": query,
            "awaiting_human_input": False
        }
        
        result = None
        for event in graph.stream(initial_state, config, stream_mode="values"):
            result = event
            
        # Check if we're at interrupt
        state = graph.get_state(config)
        
        if state.next:  # If there's a next node, we're interrupted
            return {
                "status": "awaiting_input",
                "thread_id": thread_id,
                "interrupt_data": result,
                "message": "Please provide your travel preferences to continue."
            }
        else:
            return {
                "status": "complete",
                "thread_id": thread_id,
                "result": result
            }


def resume_solo_trip(thread_id: str, human_response: Dict) -> Dict[str, Any]:
    """
    Resume the solo trip planning with human input.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # Sanitize URI to ensure proper format
    sanitized_uri = _sanitize_mongo_uri(MONGODB_URI)
    with MongoDBSaver.from_conn_string(sanitized_uri) as checkpointer:
        graph = create_solo_trip_graph_with_checkpointer(checkpointer)
        
        # Resume with human response
        resume_command = Command(resume={"data": human_response})
        
        result = None
        for event in graph.stream(resume_command, config, stream_mode="values"):
            result = event
            
        return {
            "status": "complete",
            "thread_id": thread_id,
            "final_package": result.get("final_package") if result else None
        }


# =============================================================================
#                     MAIN (FOR TESTING)
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing Solo Trip Graph with Human-in-the-Loop...")
    print("="*60)
    
    # Start the trip
    result = start_solo_trip("Plan a solo trip from Delhi to Goa")
    
    print("\n" + "="*60)
    print(f"Status: {result['status']}")
    
    if result['status'] == 'awaiting_input':
        print("🛑 Graph is waiting for human input!")
        print("Call resume_solo_trip() with preferences to continue.")
    else:
        print("✅ Trip planning complete!")
        print(result.get('final_package', ''))

