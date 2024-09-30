from fastapi import APIRouter, HTTPException
from langchain.indexes import SQLRecordManager, index
from langchain.schema import Document  # Import the Document class

from typing import Optional
from config import DB_NAME as collection_name

from db.db import get_LC_chroma_client

# Initialize the router
router = APIRouter(
    prefix="/vector-store",
    tags=["vector-store"],
    responses={404: {"description": "Not found"}},
)
def create_langchain_documents(collection):
    # Initialize the list to hold Document objects
    documents = []

    # Iterate over the ids, documents, and their corresponding metadata
    for doc_id, doc, meta in zip(collection['ids'], collection['documents'], collection['metadatas']):
        # Create a metadata dictionary that includes the id and other metadata
         

        # Create a Document object
        document = Document(page_content=doc,id=doc_id, metadata=meta)

        # Append the Document to the list
        documents.append(document)

    return documents


# Function to initialize Chroma client
def get_chroma_client():
    # Assuming you have a function to set up and return your Chroma client
    chroma_client = get_LC_chroma_client()
    return chroma_client

@router.delete("/delete-record/{record_id}")
async def delete_record(record_id: str):
    """
    Deletes a record from the vector store using its ID.

    :param record_id: The ID of the record to delete.
    :return: A success message or an error if the record cannot be found.
    """
    try:
        # Get the Chroma client
        chroma_client = get_chroma_client()
        # Perform the deletion
        chroma_client.delete(ids=[record_id])

        collection = chroma_client.get();
        # Assuming collection is the object you've shown in the image
        langchain_documents = create_langchain_documents(collection)
        namespace = f"chromadb/{collection_name}"
        record_manager = SQLRecordManager(
            namespace, db_url="sqlite:///record_manager_cache.sql"
        )
 
        # Index the documents into the vector database
        response = index(
            langchain_documents,
            record_manager,
            chroma_client,
            cleanup="incremental",
            source_id_key="source",
        )
        print(response)
        # Create vector store
        
        return {"message": f"Record with ID {record_id} has been deleted successfully."}
    except ValueError as e:
        # Handle the case where the record is not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Handle any other exceptions
        raise HTTPException(status_code=500, detail=str(e))
