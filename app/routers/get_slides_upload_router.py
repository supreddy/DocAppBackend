import os
import asyncio
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from typing import List,Optional
from .get_slide_router import ContentRequest, get_llm_response
from .upload_to_storage_router import upload_to_azure, update_or_insert_subtopic
from pydantic import BaseModel
from app.helper import slides_generator
from app.helper import prompts
import json
router = APIRouter(
    prefix="/get-slide-upload",
    tags=["content"],
    responses={404: {"description": "Not found"}},
)

# Pydantic model for the request body (for LLM)
 

@router.post("/")
async def combined_api(
    subtopic_name: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),  # Make file upload optional
    description: Optional[str] = Form(None),         # Description is also optional
    text_content: List[str] = Form(...)
):
    try:
        # Define the file paths folder
        files_folder = os.path.expanduser("~/slide-uploads")
        
        # Task to generate slides
        slide_task = generate_slides(text_content, subtopic_name)
        
        # Task to upload files, only if files are provided
        if files:
            upload_task = upload_files_to_azure(files, files_folder, description, subtopic_name)
            content_result, upload_result = await asyncio.gather(slide_task, upload_task)
        else:
            content_result = await slide_task
            upload_result = {"azure_blob_urls": []}  # No uploaded images if files are empty

        # Generate presentation, adding content to the generator
        presentation_url = await slides_generator.create_presentation(json.loads(content_result))

        # If upload_result['azure_blob_urls'] is needed in the presentation, pass them here

        # Return the combined result with the presentation URL
        return {
            "content": content_result,
            "images": upload_result['azure_blob_urls'],  # May be empty if no files were uploaded
            "presentation_url": presentation_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_slides(text_content: List[str], subtopic_name: str):
    """
    Asynchronous function to generate slides by calling the LLM.
    """
    # Simulating the content preparation and LLM API call
    formatted_content = "\n".join(f"- {line}" for line in text_content)
    result = await get_llm_response(ContentRequest(subtopic=subtopic_name, text_content=text_content,isSummarySlide=False))
    return result


async def upload_files_to_azure(files: List[UploadFile], files_folder: str, description: str, subtopic_name: str):
    """
    Asynchronous function to upload files to Azure and update the database.
    """
    response = {
        "message": "Files uploaded and added to Azure successfully.",
        "uploaded_files": [],
        "azure_blob_urls": [],
        "description": description,
    }

    # Upload files to Azure
    for file in files:
        file_path = os.path.join(files_folder, file.filename)
        os.makedirs(files_folder, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        # Upload to Azure
        blob_url = upload_to_azure(file_path, file.filename)
        response["azure_blob_urls"].append(blob_url)

        # Clean up local file
        os.remove(file_path)

    # Update the database with file URLs
    update_or_insert_subtopic(subtopic_name, response["azure_blob_urls"])

    return response
