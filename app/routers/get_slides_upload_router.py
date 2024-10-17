from asyncio.log import logger
import os
import asyncio
import aiohttp  # We will use aiohttp to download the images from URLs asynchronously
from fastapi import APIRouter, HTTPException, File, Request, UploadFile, Form
from typing import List, Optional
from .get_slide_router import ContentRequest, get_llm_response
from .upload_to_storage_router import upload_to_azure, update_or_insert_subtopic
from pydantic import BaseModel
from app.helper import slides_generator_alternate
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
    request: Request,
    subtopic_name: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),  # Make file upload optional
    description: Optional[str] = Form(None),         # Description is also optional
    text_content: List[str] = Form(...),
    image_urls: Optional[List[str]] = Form(None)     # New parameter for image URLs
):
    try:
        logger.debug(f"Received request: {request.method} {request.url}")
        logger.debug(f"Received subtopic_name: {subtopic_name}")
        logger.debug(f"Received description: {description}")
        # logger.debug(f"Received file: {files.filename}")
        logger.debug(f"Received text_content: {text_content}")
        
        # Ensure text_content is always a list
        if isinstance(text_content, str):
            text_content = [text_content]

        # Define the file paths folder
        files_folder = os.path.expanduser("~/slide-uploads")

        # Task to generate slides
        slide_task = generate_slides(text_content, subtopic_name)

        # Initialize empty result for uploaded files
        upload_result = {"azure_blob_urls": []}

        # Task to handle file uploads, image URLs, or both
        if files or image_urls:
            upload_task = handle_file_and_url_uploads(files, image_urls, files_folder, description, subtopic_name)
            content_result, upload_result = await asyncio.gather(slide_task, upload_task)
        else:
            content_result = await slide_task

        # Generate presentation, adding content to the generator
        presentation_url = await slides_generator_alternate.create_presentation(content_input=json.loads(content_result), image_urls= image_urls)
        # Return the combined result with the presentation URL
        return {
            "content": content_result,
            "images": upload_result['azure_blob_urls'],  # May be empty if no files/URLs were uploaded
            "presentation_url": presentation_url
        }

        # logger.debug(f"Combined result: {combined_result}")

        # return JSONResponse(content=combined_result)
    
    except Exception as e:
        logger.exception(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_slides(text_content: List[str], subtopic_name: str):
    """
    Asynchronous function to generate slides by calling the LLM.
    """
    # Simulating the content preparation and LLM API call
    formatted_content = "\n".join(f"- {line}" for line in text_content)
    result = await get_llm_response(ContentRequest(subtopic=subtopic_name, text_content=text_content,isSummarySlide=False))
    return result

# async def generate_slides(text_content: List[str], subtopic_name: str, image_urls: List[str]):
#     logger.debug(f"Generating slides for subtopic: {subtopic_name} with {len(image_urls)} images")
#     logger.debug(f"Image URLs for slide generation: {image_urls}")
    
#     request = ContentRequest(
#         subtopic=subtopic_name,
#         text_content=text_content,
#         is_summary_slide=False
#     )
    
#     result = await get_llm_response(request)
    
#     # Log a summary of the result
#     if isinstance(result, dict):
#         logger.debug(f"Slides generated. Content keys: {list(result.get('content', {}).keys())}")
#         logger.debug(f"Presentation URL: {result.get('presentation_url', 'Not available')}")
#     else:
#         logger.debug(f"Unexpected result type: {type(result)}")
    
#     return result



async def handle_file_and_url_uploads(files: Optional[List[UploadFile]], image_urls: Optional[List[str]], files_folder: str, description: str, subtopic_name: str):
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
    if files:
        for file in files:
            file_path = os.path.join(files_folder, file.filename)
            with open(file_path, "wb") as f:
                f.write(file.file.read())

            # Upload to Azure
            blob_url = upload_to_azure(file_path, file.filename)
            response["azure_blob_urls"].append(blob_url)

            # Clean up local file
            os.remove(file_path)

    # If image URLs are provided, download and upload them to Azure
    if image_urls:
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
