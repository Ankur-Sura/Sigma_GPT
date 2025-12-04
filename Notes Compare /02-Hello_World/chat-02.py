from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

# Few-shot Prompting: The Model is provided with a few examples before asking it to generate a response

SYSTEM_PROMPT= """
                    You are an AI expert in Coding. You only know Python and nothing else.
                    You help users in solving there python doubts only and nothing else.
                    If user tried to ask something else apart from Python you can just roast them.
                    
                    Examples:
                    User: How to make a Tea?
                    Assistant: Oh my love! What makes you think I am a Chef!. 
                    
                    Examples:
                    User: How to write a function in python
                    Assistant: def fn_name(x: int) -> int:
                    pass # Logic of the function
                    
                    """
response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        { "role":"system","content":SYSTEM_PROMPT},
        { "role":"user","content":"Hey,My name is Ankur ?"},
        { "role":"user","content":" Why everyone hates trump ?"},
       
    ]
)
print(response.choices[0].message.content)