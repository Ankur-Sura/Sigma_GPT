import os

# macOS + fork(): prevent Objective‑C fork safety crash when RQ spawns a worker
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Vector Embeddings
embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-large"
)

vector_db = QdrantVectorStore.from_existing_collection(
    url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    collection_name="learning_vectors",
    embedding=embedding_model
)

# Vector Similarity Search [query] in DB. Take the user’s question, log it, then ask the vector database for the most similar text chunks.”
def process_query(query: str):
    # Here i can apply Rate limiting like if num<60:sleep
    print("Searching Chunks", query)
    search_results = vector_db.similarity_search(
        query=query
    )

    context = "\n\n\n".join([f"Page Content: {result.page_content}\nPage Number: {result.metadata['page_label']}\nFile Location: {result.metadata['source']}" for result in search_results])
#Your code takes all search results → converts each to a readable block (text + page number + file path) → separates them with 3 blank lines → and stores everything in one big context string for the LLM.
    SYSTEM_PROMPT = f"""
    You are a helpfull AI Assistant who answers user query based on the available context
    retrieved from a PDF file along with page_contents and page number.

    You should only ans the user based on the following context and navigate the user
    to open the right page number to know more.

    Context:
    {context}
    """

    chat_completion = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        { "role": "system", "content": SYSTEM_PROMPT },
        { "role": "user", "content": query },
    ]
)

# Save to DB
    print(f"🤖: {query}", chat_completion.choices[0].message.content, "\n\n\n")
    return chat_completion.choices[0].message.content
