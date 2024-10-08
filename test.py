import chromadb
import pandas as pd
import streamlit as st
import os
from config import DB_NAME
from langchain_community.vectorstores import Chroma
DB_IP = os.getenv('DB_IP')
DB_PORT = os.getenv('DB_PORT')
LOCALHOST_URL = os.getenv('LOCALHOST_URL')
LOCALHOST_PORT = os.getenv('LOCALHOST_PORT')


def get_data():
    # chroma_client = chromadb.HttpClient(host=DB_IP, port=DB_PORT)
    chroma_client = chromadb.HttpClient(host=LOCALHOST_URL, port=LOCALHOST_PORT)

    collection = chroma_client.get_collection(name='research-base')
    data = collection.get()
    return {
        'ids': data['ids'],
        'documents': data['documents'],
        'metadata': data['metadatas'],
        'embeddings': data['embeddings']
    }

def clear_db():
    persisten_client = chromadb.PersistentClient(path="chroma_db")
    persisten_client.reset()

    # Delete the record_manager_cache.sql file
    cache_file_path = os.path.join(os.path.dirname(__file__), 'record_manager_cache.sql')
    if os.path.exists(cache_file_path):
        os.remove(cache_file_path)

def main():
    st.title("Chroma Colleddddction Data")

    # Button to clear the database and delete the cache file
    if st.button('Clear Database'):
        clear_db()
        st.success("Database cleared and cache file deleted successfully!")

    else:
            # Fetch and display the data
        data = get_data()
        df = pd.DataFrame({
            'ID': data['ids'],
            'Document': data['documents'],
            'Metadata': data['metadata'],
            'Embeddings': data['embeddings']
        })
        
        st.write("Below is the data retrieved from the Chroma collection:")
        st.dataframe(df)

if __name__ == "__main__":
    main()
