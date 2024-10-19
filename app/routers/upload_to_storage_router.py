import os
import re
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import List
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import shutil
from config import PDF_FILES_FOLDER ,ACCOUNT_URL 
from app.indexers.db_handler import init_db, update_or_insert_subtopic  # Import the modularized SQL functions

# Load environment variables for Azure
load_dotenv()
SHARED_ACCESS_KEY = os.getenv('SHARED_ACCESS_KEY')

# Initialize the router
router = APIRouter(
    prefix="/upload-store",
    tags=["upload"],
    responses={404: {"description": "Not found"}},
)

# Azure Blob Storage Configuration
blob_service_client = BlobServiceClient(account_url=ACCOUNT_URL, credential=SHARED_ACCESS_KEY)
container_name = "test"

# Folder to store files locally (temporarily)
files_folder = PDF_FILES_FOLDER +"slide-uploads"

# Initialize the database
init_db()

@router.post("/")
async def upload_files(
    subtopic_name: str = Form(...),  # Subtopic name associated with files
    files: List[UploadFile] = File(...),
    description: str = Form(...)
):
    """
    API to upload files locally and to Azure Blob Storage, then store blob URLs in the database.

    :param subtopic_name: The subtopic name associated with the files.
    :param files: List of files to be uploaded.
    :param description: A description of the uploaded files.
    :return: A response with the file details and Azure Blob URLs.
    """
    response = {
        "message": "Files uploaded and added to Azure successfully.",
        "uploaded_files": [],
        "azure_blob_urls": [],
        "description": description,
    }

    uploaded_filenames = []

    for file in files:
        # Save file locally
        file_path = os.path.join(files_folder, file.filename)
        os.makedirs(files_folder, exist_ok=True)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        uploaded_filenames.append(file_path)
        response["uploaded_files"].append(file.filename)

        # Upload to Azure Blob Storage
        try:
            blob_url = upload_to_azure(file_path, file.filename)
            response["azure_blob_urls"].append(blob_url)
            # Remove local file after upload
            os.remove(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading file to Azure Blob: {str(e)}")

    # After uploading to Azure, update the database
    update_or_insert_subtopic(subtopic_name, response["azure_blob_urls"])

    return response

# Define a function similar to the JavaScript version to extract the file name
def get_file_name(url):
    match = re.search(r'[^/]*\.(\w+)($|\?)', url)
    return match.group(0).split('?')[0] if match else None

def upload_to_azure(filepath: str, filename: str):
    """
    Upload a file to Azure Blob Storage.

    :param filepath: The local path of the file.
    :param filename: The name of the file in Azure Blob Storage.
    :return: The URL of the uploaded blob.
    """
    container_client = blob_service_client.get_container_client(container_name)
    filename =get_file_name(filename)
    try:
        with open(filepath, "rb") as data:
            blob_client = container_client.upload_blob(name=filename, data=data, overwrite=True)
            return f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{filename}"
    except Exception as e:
        print("Blob error:", e)
        raise HTTPException(status_code=500, detail=f"Error uploading to Azure Blob: {str(e)}")
