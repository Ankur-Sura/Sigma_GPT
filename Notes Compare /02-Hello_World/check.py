from dotenv import load_dotenv
from openai import OpenAI
import json
load_dotenv()

client = OpenAI()

# Chain Of Thought: The model is encouraged to break down reasoning step by step before arriving at an answer.

SYSTEM_PROMPT = """
    You are an helpfull AI assistant who is specialized in resolving user query.
    For the given user input, analyse the input and break down the problem step by step.

    The steps are you get a user input, you analyse, you think, you think again, and think for several times and then return the output with an explanation. 

    Follow the steps in sequence that is "analyse", "think", "output", "validate" and finally "result".

    Rules:
    1. Follow the strict JSON output as per schema.
    2. Always perform one step at a time and wait for the next input.
    3. Carefully analyse the user query,

    Output Format:
    {{ "step": "string", "content": "string" }}

    Example:
    Input: What is 2 + 2
    Output: {{ "step": "analyse", "content": "Alight! The user is interest in maths query and he is asking a basic arthematic operation" }}
    Output: {{ "step": "think", "content": "To perform this addition, I must go from left to right and add all the operands." }}
    Output: {{ "step": "output"think nd vlidate , "content": "4" }}
    Output: {{ "step": "validate", "content": "Seems like 4 is correct ans for 2 + 2" }}
    Output: {{ "step": "result", "content": "2 + 2 = 4 and this is calculated by adding all numbers" }}

"""      

# Controlled the AI Output by giving the Prompt 
messages=[
      {"role": "system", "content": SYSTEM_PROMPT }
   ]
#We take an Input from user in Duubt variable 
doubt= input("Enter Your Doubt:")

#Added that doubt into messages 
messages.append({"role":"user" , "content": doubt})

while True:
    
    # Line client.chat.completions.create() will give us a response and 
    # we have store it in variavle name response
    response=client.chat.completions.create(
        model="gpt-4.1", 
        response_format={"type": "json_object"},
        #Add the message which will be passed to AI
        messages=messages       
    )
    #Add the AI response into message

    messages.append({"role":"assistant", "content": response.choices[0].message.content})

    #Convert the AI response into Object to access the things
    ai_response = json.loads(response.choices[0].message.content)                 

    if ai_response.get("step")!= "result":
        print("     🧠:", ai_response.get("content"))
        continue

    print("🤖", ai_response.get("content"))
    break