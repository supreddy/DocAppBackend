import logging
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from typing import List, Optional, Union
from pydantic import BaseModel
from .get_slide_router import ContentRequest, get_llm_response
from .upload_to_storage_router import upload_to_azure, update_or_insert_subtopic
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["content"])

class FormData(BaseModel):
    subtopic_name: str
    files: Optional[List[UploadFile]] = None
    description: Optional[str] = None
    text_content: List[str]

@router.post("/get-slide-upload")
@router.post("/get-slide-upload/")
async def combined_api(
    request: Request,
    subtopic_name: str = Form(...),
    files: UploadFile = File(...),
    description: Optional[str] = Form(None),
    text_content: Union[str, List[str]] = Form(...)
):
    try:
        logger.debug(f"Received request: {request.method} {request.url}")
        logger.debug(f"Received subtopic_name: {subtopic_name}")
        logger.debug(f"Received description: {description}")
        logger.debug(f"Received file: {files.filename}")
        logger.debug(f"Received text_content: {text_content}")
        
        # Ensure text_content is always a list
        if isinstance(text_content, str):
            text_content = [text_content]

        # Define the file paths folder
        files_folder = os.path.expanduser("~/slide-uploads")
        
        # Upload file to Azure
        upload_result = await upload_files_to_azure([files], files_folder, description, subtopic_name)
        image_urls = upload_result['azure_blob_urls']
        logger.debug(f"Uploaded image URLs: {image_urls}")
        
        # Generate slides with the image URLs
        content_result = await generate_slides(text_content, subtopic_name, image_urls)

        # Combine the results
        combined_result = {
            **content_result,
            "uploaded_files": upload_result['uploaded_files'],
            "azure_blob_urls": image_urls
        }

        logger.debug(f"Combined result: {combined_result}")

        return JSONResponse(content=combined_result)
    
    except Exception as e:
        logger.exception(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def upload_files_to_azure(files: List[UploadFile], files_folder: str, description: str, subtopic_name: str):
    logger.debug(f"Uploading {len(files)} files for subtopic: {subtopic_name}")
    response = {
        "message": "Files uploaded and added to Azure successfully.",
        "uploaded_files": [],
        "azure_blob_urls": [],
        "description": description,
    }

    if not files:
        logger.debug("No files to upload")
        return response

    for file in files:
        logger.debug(f"Processing file: {file.filename}")
        file_path = os.path.join(files_folder, file.filename)
        os.makedirs(files_folder, exist_ok=True)
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            logger.debug(f"File saved locally: {file_path}")

            blob_url = upload_to_azure(file_path, file.filename)
            response["azure_blob_urls"].append(blob_url)
            response["uploaded_files"].append(file.filename)
            logger.debug(f"Uploaded file {file.filename} to Azure: {blob_url}")

            os.remove(file_path)
            logger.debug(f"Removed local file: {file_path}")
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")

    update_or_insert_subtopic(subtopic_name, response["azure_blob_urls"])
    logger.debug(f"Updated subtopic {subtopic_name} with {len(response['azure_blob_urls'])} URLs")

    return response

async def generate_slides(text_content: List[str], subtopic_name: str, image_urls: List[str]):
    logger.debug(f"Generating slides for subtopic: {subtopic_name} with {len(image_urls)} images")
    logger.debug(f"Image URLs for slide generation: {image_urls}")
    
    request = ContentRequest(
        subtopic=subtopic_name,
        text_content=text_content,
        is_summary_slide=False,
        image_urls=image_urls
    )
    
    result = await get_llm_response(request)
    
    # Log a summary of the result
    if isinstance(result, dict):
        logger.debug(f"Slides generated. Content keys: {list(result.get('content', {}).keys())}")
        logger.debug(f"Presentation URL: {result.get('presentation_url', 'Not available')}")
    else:
        logger.debug(f"Unexpected result type: {type(result)}")
    
    return result