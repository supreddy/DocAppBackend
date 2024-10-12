import os
import asyncio
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from typing import List
from .get_slide_router import create_slide_prompt, get_llm_response
from .upload_to_storage_router import upload_to_azure, update_or_insert_subtopic
from pydantic import BaseModel
from app.helper import slides_generator
import json
router = APIRouter(
    prefix="/get-slide-upload",
    tags=["content"],
    responses={404: {"description": "Not found"}},
)

# Pydantic model for the request body (for LLM)
class SlideRequest(BaseModel):
    subtopic: str
    text_content: List[str]

@router.post("/")
async def combined_api(
    subtopic_name: str = Form(...),
    files: List[UploadFile] = File(...),
    description: str = Form(...),
    text_content: List[str] = Form(...)
):
    try:
        # Define the file paths folder
        files_folder = os.path.expanduser("~/slide-uploads")
        
        # Run both operations in parallel using asyncio.gather()
        slide_task = generate_slides(text_content, subtopic_name)
        upload_task = upload_files_to_azure(files, files_folder, description, subtopic_name)
        
        # Wait for both tasks to completeD
        content_result, upload_result = await asyncio.gather(slide_task, upload_task)

     

        presentation_url = await slides_generator.create_presentation(json.loads(content_result))
        # to do pass  upload_result['azure_blob_urls'] to the function create_presentation above to use in creating the ppt

        # Output the presentation URL
        print(presentation_url)
        # Return some dummy response
        # Combine results into a single response
        return {
            "content": content_result,
            "images": upload_result['azure_blob_urls']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_slides(text_content: List[str], subtopic_name: str):
    """
    Asynchronous function to generate slides by calling the LLM.
    """
    # Simulating the content preparation and LLM API call
    formatted_content = "\n".join(f"- {line}" for line in text_content)
    result = await get_llm_response(SlideRequest(subtopic=subtopic_name, text_content=text_content))
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
