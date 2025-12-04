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
    Output: {{ "step": "output", "content": "4" }}
    Output: {{ "step": "validate", "content": "Seems like 4 is correct ans for 2 + 2" }}
    Output: {{ "step": "result", "content": "2 + 2 = 4 and this is calculated by adding all numbers" }}

"""                  
                    
response = client.chat.completions.create(
    model="gpt-4.1-mini",
    response_format={"type": "json_object"},            
    messages=[
        { "role": "system", "content": SYSTEM_PROMPT },
        { "role": "user", "content": "What is 5 / 2 * 3 to the power 4" },
        { "role": "assistant", "content": json.dumps({"step": "analyse", "content": "The user is asking to calculate the value of the expression 5 divided by 2, multiplied by 3 raised to the power of 4." })  },
        { "role": "assistant", "content": json.dumps({"step": "think", "content": "According to the order of operations (PEMDAS/BODMAS), I need to calculate the exponent first: 3 to the power 4. Then I perform the division 5/2. Finally, I multiply the results."})  },
        { "role": "assistant", "content": json.dumps({"step": "output", "content": "3 to the power 4 equals 81, 5 divided by 2 equals 2.5, and 2.5 multiplied by 81 equals 202.5"})  },
        { "role": "assistant", "content": json.dumps({"step": "validate", "content": "Double-checking the calculations: 3^4 = 81 is correct, 5/2 = 2.5 is correct, and 2.5 * 81 = 202.5 is also correct."})  },
        { "role": "assistant", "content": json.dumps({"step": "result", "content": "The value of the expression 5 / 2 * 3^4 is 202.5, computed by first calculating 3^4 = 81, then dividing 5 by 2 to get 2.5, and multiplying 2.5 by 81."})  }, 
    ]
)

print("\n\n🤖:", response.choices[0].message.content, "\n\n")

