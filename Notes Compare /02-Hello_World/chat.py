from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

#Zero Shot Prompting:The model is given a direct question or task

SYSTEM_PROMPT= """
                    You are an AI expert in Coding. You only know Python and nothing else.
                    You help users in solving there python doubts only and nothing else.
                    If user tried to ask something else apart from Python you can just roast them.
                    """
response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        { "role":"system","content":SYSTEM_PROMPT},
        { "role":"user","content":"Hey,My name is Ankur?"},
        { "role":"user","content": "How to make a tea?"}
    ]
)
print(response.choices[0].message.content)