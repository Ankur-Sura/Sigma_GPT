# Here we will categorise our Query and depending upon that we will use models
import warnings
# Suppress the Pydantic v1-on-Python-3.14 warning emitted by langchain-core
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*")

from typing import Literal
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from openai import OpenAI
from pydantic import BaseModel
from typing_extensions import TypedDict

load_dotenv()
client = OpenAI()

# For Validation we use Pydantic which is Pydantic Library. Now we will use Pydantic models to define expected LLM response structure so you don’t struggle with loose JSON.
class ClassifyMessageResponse(BaseModel):
    is_coding_question: bool

class CodeAccuracyResponse(BaseModel):
    accuracy_percentage: str

#Contraint or things which a state has are defined here 
class State(TypedDict):
    user_query: str
    llm_result: str | None     # This can be written in new way ----> Optional[str] which means this can be str or None.
    accuracy_percentage: str | None        # How much percentage it is 
    is_coding_question: bool | None        # Is the equery is related to Coding or not  

# This thing we are doing is to check whether query is related to Coding or not. 
def classify_message(state: State):
    print("⚠️ classify_message")
    query = state["user_query"]     # As state is a Dictionry so to access or modify value in it we use  Take the value stored under "user_query" in the state dictionary and put it into the variable query.

    SYSTEM_PROMPT = """
    You are an AI assistant. Your job is to detect if the user's query is
    related to coding question or not. 
    Return the response in specified JSON boolean only.
    """

    response = client.beta.chat.completions.parse(       # Here we want custom response format hence we need to use beta and also when we use beta then we need to use parse here
        model="gpt-4.1-nano",
        response_format=ClassifyMessageResponse,        # Just like earlier we say response should be in JSON format
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
    )

    is_coding_question = response.choices[0].message.parsed.is_coding_question
    state["is_coding_question"] = is_coding_question  # Here we have updated the state

    return state   # Then we have passed this state which tell us about whether query is related to Coding or Non-Coding.  

# Deciding the path which one to Choose based on State thing
def route_query(state: State) -> Literal["general_query", "coding_query"]:
    print("⚠️ route_query")
    is_coding = state["is_coding_question"]

    if is_coding:
        return "coding_query"

    return "general_query"

# When the query is more of a General 
def general_query(state: State):
    print("⚠️ general_query")
    query = state["user_query"]

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": query}
        ]
    )

    state["llm_result"] = response.choices[0].message.content

    return state

# When the query is related to Coding
def coding_query(state: State):
    print("⚠️ coding_query")
    query = state["user_query"]     # Take the value stored under "user_query" in the state dictionary and put it into the variable query.

    SYSTEM_PROMPT = """
        You are a Coding Expert Agent
    """

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]
    )

    state["llm_result"] = response.choices[0].message.content

    return state

def coding_validate_query(state: State):
    print("⚠️ coding_validate_query")
    query = state["user_query"]
    llm_code = state["llm_result"]

    SYSTEM_PROMPT = f"""
        You are expert in calculating accuracy of the code according to the question.
        Return the percentage of accuracy
        
        User Query: {query}
        Code: {llm_code}
    """

    response = client.beta.chat.completions.parse(
        model="gpt-4.1",
        response_format=CodeAccuracyResponse,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
    )

    state["accuracy_percentage"] = response.choices[0].message.parsed.accuracy_percentage 
    # ⚠️ Where does accuracy_percentage come from? It comes from CodeAccuracyResponse (Pydantic model),
    # ✅ The Pydantic model gives you an object whose fields (like accuracy_percentage) you can access with dot notation
    return state 
    
    # If this accuracy percentage is less than 95 percent then we can gain go to coding step and then check coding vlidation after coding again.
    # But an issue can arrise then we can use a counting to exit this loop Eg: if accuracy < 95 and count < 5 (This count can be defined in State). if count becomes 5 then it will exit this lopo and then end 
    # We call this as LLM as a Judge  

graph_builder = StateGraph(State)

# Define Nodes
graph_builder.add_node("classify_message", classify_message)
graph_builder.add_node("route_query", route_query)
graph_builder.add_node("general_query", general_query)
graph_builder.add_node("coding_query", coding_query)
graph_builder.add_node("coding_validate_query", coding_validate_query)

graph_builder.add_edge(START, "classify_message")
graph_builder.add_conditional_edges("classify_message", route_query) # Routing is always passed as a function rather than string 

graph_builder.add_edge("general_query", END)

graph_builder.add_edge("coding_query", "coding_validate_query")
graph_builder.add_edge("coding_validate_query", END)


#Let us make a Graph now
graph = graph_builder.compile()

def main():
    user = input("> ")

    _state: State = {
        "user_query": user,
        "accuracy_percentage": None,
        "is_coding_question": False,
        "llm_result": None,
    }
    
    for event in graph.stream(_state):   #graph.stream(_state) → “Do everything, but tell me what’s happening at every step.”
        print("Event", event)

    # response = graph.invoke(_state)  ----> graph.invoke(_state) → “Do everything and give me the final result once.”
    # print(response)
    
main()
