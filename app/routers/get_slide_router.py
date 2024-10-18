import json
import os
import logging
from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.output_parsers import StrOutputParser
from app.helper import prompts

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_transformers import (
    LongContextReorder,
)
from app.helper import slides_generator_alternate
from config import PDF_FILES_FOLDER

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# code to get slide json
# Define the directory where files are uploaded
UPLOAD_DIRECTORY = os.path.expanduser(PDF_FILES_FOLDER)

# Initialize the router
router = APIRouter(
    prefix="/get-slide",
    tags=["content"],
    responses={404: {"description": "Not found"}},
)


llm = ChatOpenAI(
    model="gpt-3.5-turbo-0125",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # api_key=apikey,  # if you prefer to pass api key in directly instaed of using env vars
    # base_url="...",
    # organization="...",
    # other params...
)


# Update the ContentRequest model
class ContentRequest(BaseModel):
    subtopic: str
    text_content: List[str]
    is_summary_slide: Optional[bool] = False

# POST endpoint to process the content
@router.post("/")
async def get_llm_response(request: ContentRequest):
    try:
        formatted_content = "\n".join(f"- {line}" for line in request.text_content)
        is_summary_slide = request.is_summary_slide
      
        prompt_text = prompts.create_slide_prompt2()
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_text),
            ("human", "content :{formatted_content} \n topic :{topic}"),
        ])
        
        chain = prompt | llm | StrOutputParser()
        json_result = chain.invoke({
            "formatted_content": formatted_content,
            "topic": request.subtopic
        })
        
        logger.debug(f"LLM Response: {json_result[:1000]}...")  # Log first 1000 characters
        
        # Parse the JSON result
        try:
            content_json = json.loads(json_result)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            logger.error(f"Raw JSON content: {json_result}")
            raise HTTPException(status_code=500, detail=f"Error parsing LLM response: {str(e)}")
        
        logger.debug(f"Parsed content_json: {content_json}")

        # Ensure the content has the correct structure
        if 'slides' not in content_json:
            logger.error(f"Invalid content structure: {content_json}")
            raise HTTPException(status_code=500, detail="Invalid content structure: 'slides' not found")

        # Generate presentation URL only for summary slide
        presentation_url = None
        if is_summary_slide:
            presentation_url = await slides_generator_alternate.create_presentation(content_json, request.image_urls or [])
        
        result = {
            "content": content_json,
            "images": request.image_urls if hasattr(request, 'image_urls') else [],
            "presentation_url": presentation_url
        }
        
        logger.debug(f"Final result: {result}")
        return result
    
    except HTTPException as he:
        logger.error(f"HTTP Exception in get_llm_response: {he.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_llm_response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

 
  
