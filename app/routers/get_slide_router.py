import json
import os
import webbrowser
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
from app.helper import slides_generator
from config import PDF_FILES_FOLDER

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
    image_urls: Optional[List[str]] = []  # Add this line

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
        print(json_result)
        
        # Parse the JSON result
        content_json = json.loads(json_result)
        
        # Generate presentation, adding content and images to the generator
        presentation_url = await slides_generator.create_presentation(content_json, request.image_urls)
    
        if is_summary_slide:
            return {
                "content": content_json,
                "images": request.image_urls,
                "presentation_url": presentation_url
            }   
        
        # For non-summary slides, return the full result including presentation URL
        return {
            "content": content_json,
            "images": request.image_urls,
            "presentation_url": presentation_url
        }
         
    except Exception as e:
        print(f"Error in get_llm_response: {str(e)}")  # Add this line for debugging
        raise HTTPException(status_code=500, detail=str(e))




 
  
