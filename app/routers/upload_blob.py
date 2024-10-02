import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from fastapi import APIRouter, File, UploadFile, Form, HTTPException

from config import ACCOUNT_URL
from dotenv import load_dotenv

load_dotenv()
SHARED_ACCESS_KEY = os.getenv('SHARED_ACCESS_KEY')

# Initialize the router
router = APIRouter(
    prefix="/blob-upload",
    tags=["blobupload"],
    responses={404: {"description": "Not found"}},
)

# Create the BlobServiceClient object
blob_service_client = BlobServiceClient(ACCOUNT_URL, credential=SHARED_ACCESS_KEY)

# container_name should be for each client/customer
@router.post("/")
async def upload_blob_file(filepath : str, 
                           filename : str, 
                           container_name = "test"):
    response = {
        "message": "File uploaded successfully.",
        "uploaded_file": ""
    }

    container_client = blob_service_client.get_container_client(container=container_name)
    try:
        with open(file=filepath, mode="rb") as data:
            blob_client = container_client.upload_blob(name=filename, data=data, overwrite=True)
            print(blob_client.url)

            response["uploaded_file"].append(blob_client.url)
    except Exception as e:
        print ("blob error", e)
        raise HTTPException(status_code=500, detail=f"Error processing files to upload: {str(e)}")
    
    return response