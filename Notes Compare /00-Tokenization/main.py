import tiktoken

enc= tiktoken.encoding_for_model("gpt-4o")

text="Hello,My name is Ankur Sura"
tokens=enc.encode(text)

print("Tokens", tokens)

tokencreated= [13225, 11, 5444, 1308, 382, 1689, 18781, 336, 2705]

decoded= enc.decode(tokencreated)

print("Decoded Text is", decoded)