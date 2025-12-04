import google.generativeai as genai
import os
# The client gets the API key from the environment variable `GEMINI_API_KEY`.
genai.configure(api_key="AIzaSyDPwZFgXpEW9mC7AOdHqRafGhrrYnFne0Y")

model = genai.GenerativeModel("gemini-2.5-flash")

# Start a chat session - This keeps track of the conversation
chat = model.start_chat(history=[])

# First question
print("You: What is my name?")
response1 = chat.send_message("What is my name?")
print("Gemini:", response1.text)

# Second message - telling your name
print("\nYou: My name is Ankur. What will be my name?")
response2 = chat.send_message("My name is Ankur. What will be my name?")
print("Gemini:", response2.text)
