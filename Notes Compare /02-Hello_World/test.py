from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        { "role":"user", "content": " Hey, My name is Ankur ?" }
    ]
)
print(response.choices[0].message.content)
