from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

text= "I am Eating an Apple"

response = client.embeddings.create(
    input=text,
    model="text-embedding-3-small"
)
print(response)