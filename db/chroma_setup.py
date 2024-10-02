import chromadb
from  dotenv import load_dotenv

import os
from config import DB_NAME
from dotenv import load_dotenv

load_dotenv()

DB_IP = os.getenv('DB_IP')
DB_PORT = os.getenv('DB_PORT')
LOCALHOST_URL = os.getenv('LOCALHOST_URL')
LOCALHOST_PORT = os.getenv('LOCALHOST_PORT')
 

async def setup_chroma(is_reset=False):
    try:    
        # persisten_client= chromadb.PersistentClient(path="chroma_db") # type: ignore
        # chroma_client = chromadb.HttpClient(host=DB_IP, port=DB_PORT)
        chroma_client = chromadb.HttpClient(host=LOCALHOST_URL, port=LOCALHOST_PORT)
        collection = chroma_client.get_or_create_collection(name=DB_NAME)
        print("collection created with docs:",collection.count())




    except Exception as e:
        print("An error occurred:", str(e))
    
 