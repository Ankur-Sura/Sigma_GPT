from typing import TypedDict  # Built-in TypedDict for defining State
import warnings
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*") #Added to resolve issue by Cursor because the Pydantic v1 is not compatible with-on-Python 3.14
from openai import OpenAI  # We should use OpenAI
from dotenv import load_dotenv #To load .env file
from langgraph.graph import StateGraph, START, END  # Now we will make Graph and we will use variable start and end 

load_dotenv()

client = OpenAI()

# Here we will define a State ispssed on as input in each node(which are function here) and output of that Node is also  State
   # WE HAVE TO GIVE STATE TO A NODE
class State(TypedDict):     # Here : class is used so it mean we are defining blue print. Actual use/object making happens later
                                #	• State = name of the state schema
                                #	• (TypedDict) = says “this schema describes a dict with specific keys & types”.
    query: str
    llm_result: str | None          # It means llm_result can be string or none


def chat_bot(state: State):         # 1. Here we define a function named chat_bot

    query = state['query']         # 2. Now it will read query from State 

    llm_response = client.chat.completions.create(  # Now LLM will take query 
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": query}
        ]
    )

    result = llm_response.choices[0].message.content    # LLM will return a response
    state["llm_result"] = result     # Now we will add this result into state as new state is passed into the next function             

    return state            # It will return a State


graph_builder = StateGraph(State)       # To build a Graph we need this 

graph_builder.add_node("chat_bot", chat_bot) # It means we have a node named chat_bot and its has code chat_bot(right one)
graph_builder.add_edge(START, "chat_bot") # Make a edge which say take me from START to chat_bot
graph_builder.add_edge("chat_bot", END)  # Make a edge which say take me from chat_bot to END

graph = graph_builder.compile()  # Now we compile and and our Graph is made

#Now we will use this Graph
def main():
    user = input("> ")

    # Invoke the graph
    _state = {          #Here we have made a State named _state
        "query": user,
        "llm_result": None
    }

    graph_result = graph.invoke(_state)

    print("graph_result", graph_result)


main()
