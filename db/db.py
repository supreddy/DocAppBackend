# db.py
import chromadb
from chromadb import Settings
from langchain_community.vectorstores import Chroma

from langchain_openai import OpenAIEmbeddings
import os
from config import DB_NAME
from dotenv import load_dotenv

load_dotenv()

DB_IP = os.getenv('DB_IP')
DB_PORT = os.getenv('DB_PORT')

os.environ['ALLOW_RESET'] = 'True'
 

###this is a method that needs to be invoked
# def get_LC_chroma_client():
#     chroma_client = chromadb.HttpClient(host=DB_IP, port=DB_PORT)
#     embeddings = OpenAIEmbeddings(model= "text-embedding-3-large")

# # create a vector store  from client
#     langchain_chroma = Chroma(
#         client=chroma_client,
#         collection_name=DB_NAME,
#         embedding_function=embeddings,
#     )
#     return langchain_chroma

def get_LC_chroma_client():
    try:
        print("Initializing Chroma client...")
        
        # Print environment variables for debugging
        print(f"OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
        print(f"CHROMA_HOST: {os.getenv('DB_IP', 'Not set')}")
        print(f"CHROMA_PORT: {os.getenv('DB_PORT', 'Not set')}")

        # Initialize OpenAI embeddings
        embeddings = OpenAIEmbeddings(model= "text-embedding-3-large")

        # Initialize Chroma client
        chroma_client = chromadb.HttpClient(
            host=os.getenv("DB_IP", "172.208.27.84"),
            port=int(os.getenv("DB_PORT", "8000"))
        )

       # Initialize Langchain's Chroma integration
        langchain_chroma = Chroma(
            client=chroma_client,
            collection_name=DB_NAME,
            embedding_function=embeddings
        )

        print("Chroma client initialized successfully.")
        return langchain_chroma

    except Exception as e:
        print(f"Error in get_LC_chroma_client: {str(e)}")
        raise
