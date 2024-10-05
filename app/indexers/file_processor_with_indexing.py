import os
import asyncio
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
import numpy as np
from langchain_community.embeddings import CohereEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from config import DB_NAME as collection_name
from langchain.indexes import SQLRecordManager, index
from langchain.schema import Document  # Import the Document schema
from config import DB_NAME
from db.db import get_LC_chroma_client
from typing import Optional
 

# embeddings = CohereEmbeddings(model="embed-english-light-v3.0")
embeddings = OpenAIEmbeddings(model= "text-embedding-3-large")
namespace = f"chromadb/{collection_name}"
record_manager = SQLRecordManager(
    namespace, db_url="sqlite:///record_manager_cache.sql"
)
record_manager.create_schema()

# Initialize list to store documents
documents = []
splitter =  RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=1000,
                length_function=len,
                keep_separator=True
            )

async def process_files(folder_path="../../files", processed_files_path="../../files/processed_files.txt"):
    try:
        # Read the list of processed files
        processed_files = read_processed_files(processed_files_path)
        
        files = os.listdir(folder_path)

        for file in files:
            file_path = os.path.join(folder_path, file)
            
            # Skip processing if the file has already been processed
            if file in processed_files:
                print(f"Skipping {file_path}. Already processed.")
                continue
            
            file_type = get_file_type(file_path)

            if file_type == "txt" and ("urls.txt" and "processed_files.txt") not in file:
                get_text_loader(file_path,file)
            elif file_type == "pdf":
                get_pdf_loader(file_path,file)
            else:
                print(f"Unsupported file type for {file_path}")

        # Update the list of processed files
        update_processed_files(processed_files_path, files)
        
        docs_to_index = []
        for array in documents:
            docs_to_index.extend(array)
      
        print("Document count:", len(docs_to_index))
        print("Adding docs...")

        langchain_chroma = get_LC_chroma_client()

        response = index(
            docs_to_index,
            record_manager,
            langchain_chroma,
            cleanup="incremental",
            source_id_key="source",
        )

        print(response)
        # Create vector store
        return response
       
    except Exception as e:
        print('Error processing files:', e)
        

def process_text_and_index(text: str, source_id: str = "manual_text_input", file_name: str = "", metadata: dict = None) -> Optional[dict]:
    """
    Process a large block of text, split it into chunks, and index the content to the vector database.
    
    :param text: The block of text to be processed and indexed.
    :param source_id: An identifier for the source of the text.
    :param file_name: The name of the file being processed.
    :param metadata: Additional metadata to be included with each chunk.
    :return: Response from the indexing operation or None if an error occurred.
    """
    print(f"Processing text for indexing. Source ID: {source_id}, File Name: {file_name}")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        length_function=len,
        add_start_index=True,
    )
    
    try:
        # Prepare metadata
        base_metadata = {
            "source": source_id,
            "file_name": file_name
        }
        if metadata:
            base_metadata.update(metadata)
        
        # Split the text into chunks
        chunks = splitter.create_documents([text], metadatas=[base_metadata])
        
        # Add chunk-specific metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
            chunk.metadata["total_chunks"] = len(chunks)
        
        print(f"Document count after splitting: {len(chunks)}")
        
        # Initialize Chroma client
        try:
            langchain_chroma = get_LC_chroma_client()
            print(f"Chroma client initialized successfully.")
        except Exception as e:
            print(f"Error initializing Chroma client: {e}")
            return None
        
        # Initialize record manager
        record_manager = SQLRecordManager(
            f"chromadb/{langchain_chroma._collection.name}",
            db_url="sqlite:///record_manager_cache.sql"
        )
        record_manager.create_schema()
        
        # Index the documents into the vector database
        try:
            response = index(
                chunks,
                record_manager,
                langchain_chroma,
                cleanup="incremental",
                source_id_key="source",
            )
            print("Indexing response:", response) 
            print("Text successfully indexed.")
            return response
        except Exception as e:
            print(f"Error during indexing: {e}")
            return None
    except Exception as e:
        print(f"Error processing text: {e}")
        return None
    


def read_processed_files(file_path):
    try:
        with open(file_path, "r") as file:
            processed_files = [line.strip() for line in file]
        return processed_files
    except FileNotFoundError:
        print(f"no file {file_path}. Starting fresh.")
        return []

def update_processed_files(file_path, processed_files):
    try:
        with open(file_path, "w") as file:
            for file_name in processed_files:
                file.write(file_name + "\n")
        print(f"updated {file_path}")
    except Exception as e:
        print(f"Error updating processed files at {file_path}: {e}")

# Function to determine the file type based on extension
def get_file_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return ext[1:]  # Removing the dot from the extension

# Function for handling txt files
def get_text_loader(file_path,file):
    print(f"spilting file: {file}")
    text_loader = TextLoader(file_path)
    docs_text =  text_loader.load()
    docs =  splitter.split_documents(docs_text)
    documents.append(docs)

# Function for handling pdf files
def get_pdf_loader(file_path,file):
    print(f"spilting file: {file}")
    pdf_loader = PyPDFLoader(file_path)
    docs_pdf =  pdf_loader.load()
    docs =  splitter.split_documents(docs_pdf)
    documents.append(docs)
