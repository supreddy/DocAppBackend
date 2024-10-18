from asyncio.log import logger
import os
import asyncio
import aiohttp  # We will use aiohttp to download the images from URLs asynchronously
from fastapi import APIRouter, HTTPException, File, Request, UploadFile, Form
from typing import List, Optional, Union
from .get_slide_router import ContentRequest, get_llm_response
from .upload_to_storage_router import upload_to_azure, update_or_insert_subtopic
from app.helper import slides_generator_alternate
import json

router = APIRouter(
    prefix="/get-slide-upload",
    tags=["content"],
    responses={404: {"description": "Not found"}},
)

# Pydantic model for the request body (for LLM)

def ensure_list(item):
    if item is None:
        return []
    return item if isinstance(item, list) else [item]

@router.post("/")
async def combined_api(
    request: Request,
    subtopic_name: str = Form(...),
    files: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    description: Optional[str] = Form(None),
    text_content: Optional[Union[str, List[str]]] = Form(None),
    image_urls: Optional[Union[str, List[str]]] = Form(None)
):
    try:
        logger.debug(f"Received request: {request.method} {request.url}")
        logger.debug(f"Received subtopic_name: {subtopic_name}")
        logger.debug(f"Received description: {description}")

        # Handle files
        files_list = ensure_list(files)
        logger.debug(f"Received files: {[f.filename for f in files_list]}")

        # Handle text_content
        if text_content is None:
            raise HTTPException(status_code=422, detail="text_content is required")
        text_content_list = ensure_list(text_content)
        logger.debug(f"Received text_content: {text_content_list}")

        # Handle image_urls
        image_urls_list = ensure_list(image_urls)
        logger.debug(f"Received image_urls: {image_urls_list}")

        # Define the file paths folder
        files_folder = os.path.expanduser("~/slide-uploads")

        # Task to generate slides
        slide_task = generate_slides(text_content_list, subtopic_name)

        # Initialize empty result for uploaded files
        upload_result = {"azure_blob_urls": []}

        # Task to handle file uploads, image URLs, or both
        if files_list or image_urls_list:
            upload_task = handle_file_and_url_uploads(files_list, image_urls_list, files_folder, description, subtopic_name)
            content_result, upload_result = await asyncio.gather(slide_task, upload_task)
        else:
            content_result = await slide_task

        # Generate presentation, adding content to the generator
        try:
            content_json = json.loads(content_result) if isinstance(content_result, str) else content_result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse content_result as JSON: {content_result}")
            raise HTTPException(status_code=500, detail="Failed to parse slide content")

        presentation_url = await slides_generator_alternate.create_presentation(content_input=content_json, image_urls=image_urls_list)

        # Return the combined result with the presentation URL
        result = {
            "content": content_json,
            "images": upload_result['azure_blob_urls'],
            "presentation_url": presentation_url
        }
        logger.debug(f"Combined result: {result}")
        return result

    except HTTPException as he:
        logger.error(f"HTTP error: {he.detail}")
        raise
    except Exception as e:
        logger.exception(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    



async def generate_slides(text_content: List[str], subtopic_name: str):
    """
    Asynchronous function to generate slides by calling the LLM.
    """
    logger.debug(f"Generating slides for subtopic: {subtopic_name}")
    logger.debug(f"Text content for slide generation: {text_content}")

    result = await get_llm_response(ContentRequest(subtopic=subtopic_name, text_content=text_content, isSummarySlide=False))

    # Log a summary of the result
    if isinstance(result, dict):
        logger.debug(f"Slides generated. Content keys: {list(result.keys())}")
    elif isinstance(result, str):
        logger.debug(f"Slides generated. Result length: {len(result)}")
    else:
        logger.debug(f"Unexpected result type: {type(result)}")

    return result



async def handle_file_and_url_uploads(files: List[UploadFile], image_urls: List[str], files_folder: str, description: str, subtopic_name: str):
    """
    Asynchronous function to upload files or download and upload images from URLs to Azure.
    """
    response = {
        "message": "Files and URLs processed successfully.",
        "uploaded_files": [],
        "azure_blob_urls": [],
        "description": description,
    }

    # Create a folder for local storage
    os.makedirs(files_folder, exist_ok=True)

    # If files are provided, upload them to Azure
    for file in files:
        file_path = os.path.join(files_folder, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Upload to Azure
        blob_url = upload_to_azure(file_path, file.filename)
        response["azure_blob_urls"].append(blob_url)

        # Clean up local file
        os.remove(file_path)

    # If image URLs are provided, download and upload them to Azure
    for url in image_urls:
        image_filename = os.path.basename(url)
        image_path = os.path.join(files_folder, image_filename)
        
        # Download the image from the URL
        await download_image_from_url(url, image_path)

        # Upload the downloaded image to Azure
        blob_url = upload_to_azure(image_path, image_filename)
        response["azure_blob_urls"].append(blob_url)

        # Clean up local file
        os.remove(image_path)

    # Update the database with the file/URL upload information
    update_or_insert_subtopic(subtopic_name, response["azure_blob_urls"])
    logger.debug(f"Updated subtopic {subtopic_name} with {len(response['azure_blob_urls'])} URLs")

    return response



async def download_image_from_url(url: str, image_path: str):
    """
    Asynchronous function to download an image from a URL and save it locally.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(image_path, "wb") as f:
                    f.write(await response.read())
            else:
                raise HTTPException(status_code=response.status, detail=f"Failed to download image from {url}")
