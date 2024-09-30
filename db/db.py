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
def get_LC_chroma_client():
    chroma_client = chromadb.HttpClient(host=DB_IP, port=DB_PORT)
    embeddings = OpenAIEmbeddings(model= "text-embedding-3-large")

# create a vector store  from client
    langchain_chroma = Chroma(
        client=chroma_client,
        collection_name=DB_NAME,
        embedding_function=embeddings,
    )
    return langchain_chroma


