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
# Pydantic model for request body
class ContentRequest(BaseModel):
    subtopic: str
    text_content: List[str]
    is_summary_slide: Optional[bool] = False  


# POST endpoint to process the content
@router.post("/")
async def get_llm_response(request: ContentRequest):
    try:
        formatted_content = "\n".join(f"- {line}" for line in request.text_content)
        is_summary_slide=request.is_summary_slide;
      
        prompt_text=prompts.create_slide_prompt2()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text)
                ,
                ("human", "content :{formatted_content} \n topic :{topic}"),
            ]
        )
        
        # This is just a placeholder for your actual logic
        chain = prompt | llm | StrOutputParser()
        json_result= chain.invoke({
            "formatted_content":formatted_content , "topic":request.subtopic
        })
        print(json_result)
        # # Call the create_presentation function from slides_generator
        # presentation_url = await slides_generator.create_presentation(json.loads(json_result))

        # # Output the presentation URL
        # print(presentation_url)
        # Return some dummy response
        
        # Generate presentation, adding content to the generator
        presentation_url = await slides_generator.create_presentation(json.loads(json_result))
    
        if is_summary_slide:
            return {
            "content": json_result,
            "images": [],  # May be empty if no files were uploaded
            "presentation_url": presentation_url
            }   
 
        
        
        return json_result
         
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




 
  
