from dotenv import load_dotenv

from pathlib import Path                                                # For Path we need to use this. Path helps build file paths safely.
from langchain_community.document_loaders import PyPDFLoader            # Here it is use for Langchain pdf loader . Comes directly from documentation
from langchain_text_splitters import RecursiveCharacterTextSplitter     # Langchain has Text Splitter 
from langchain_openai import OpenAIEmbeddings                           # To do Vector Embedding we use this 
from langchain_qdrant import QdrantVectorStore                          # For Qdrant Db usage

load_dotenv()

pdf_path = Path(__file__).parent / "nodejs.pdf"  # It is the current location of PDF file 

# Loading
loader = PyPDFLoader(file_path=pdf_path) #Now this will be loader and we provide path to it  
docs = loader.load()  #  Here we have read PDF File page by page 

# Chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,                    # All of this is from documentation of ext Splitter
    chunk_overlap=400                   #chunk overlap means taking context from previous chunk so that relation can be seen 
)

split_docs = text_splitter.split_documents(documents=docs) #Now we get document in splitted form with the help of Text splitter 

# Vector Embeddings
embedding_model = OpenAIEmbeddings(             # Here we have done Vector Embedding 
    model="text-embedding-3-large"
)

# Using [embedding_model] create embeddings of [split_docs] and store in DB
vector_store = QdrantVectorStore.from_documents(
    documents=split_docs,                         # We have provided Document here
    url="http://localhost:6333",                  # Database is running on this port
    collection_name="learning_vectors",           # Name giving, Just like Mongo has collection/table. Similary we have collection name
    embedding=embedding_model
)

print("Indexing of Documents Done...")