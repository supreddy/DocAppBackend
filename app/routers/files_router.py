# SERVES THE FILES TO LOAD LIST OF FILES IN THE UI

from dotenv import load_dotenv
load_dotenv()
from fastapi import APIRouter
from config import SERVER_URL, PDF_FILES_FOLDER
import os
from urllib.parse import quote
files_router = APIRouter()

router = APIRouter(
    prefix="/files",  # Customize the prefix according to your API context
    tags=["source"],  # Customize the tag for grouping API routes
    responses={404: {"description": "Not found"}},  # Custom responses, if needed
)

@router.get("/")
async def get_files():
    files_folder = PDF_FILES_FOLDER  # Path to the 'files' folder
    server_url = SERVER_URL
    try:
        # Read files from the 'files' folder
        files = os.listdir(files_folder)

        # Create a list of file objects
        file_objects = []
        for file_name in files :
            file_path = os.path.join(files_folder, file_name)
            file_stats = os.stat(file_path)
            if file_name not in ('urls.txt', 'processed_files.txt'):
                file_objects.append({
                    "name": file_name,
                    "size": file_stats.st_size,
                    "path": f"{server_url}/{quote(file_path)}"
                })

        # Send the list of file objects as JSON
        return {"files": file_objects}
    except Exception as e:
        # Handle any errors
        return {"error": str(e)}
    
@router.delete("/delete")
async def remove_file(filename: str):
    files_folder = "files"  # Path to the 'files' folder
    try:
        # Construct the file path
        file_path = os.path.join(files_folder, filename)

        # Check if the file exists
        if os.path.exists(file_path):
            # Remove the file
            os.remove(file_path)
            return {"message": f"File '{filename}' deleted successfully."}
        else:
            return {"message": f"File '{filename}' not found."}, 404
    except Exception as e:
        return {"error": str(e)}, 500