import json
import os
import webbrowser
from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing import List
from langchain_core.output_parsers import StrOutputParser

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_transformers import (
    LongContextReorder,
)
from app.helper import slides_generator
from config import PDF_FILES_FOLDER

# code to get slide json
# Define the directory where files are uploaded
UPLOAD_DIRECTORY = os.path.expanduser(PDF_FILES_FOLDER)


def create_slide_prompt() -> ChatPromptTemplate:
    # Join the list of strings into a single formatted string with bullet points
    
    
    # prompt_text = (
    #     "You are a helpful assistant specializing in creating engaging slides given a topic.\n"
    #     "\n"
    #     "Create a presentation slide based on the following content:\n"
    #     "\n"
    #     "Title: {{topic}}\n"
    #     "\n"
    #     "Content:\n"
    #     "{{formatted_content}}\n"
    #     "\n"
    #     "Design specifications:\n"
    #     "- Professional and clean font style.\n"
    #     "- Simple layout with clear headings and bullet points.\n"
    #     "\n"
    #     "Please stick strictly to the provided topic and content. If you cannot generate the slide with the given information, respond with: 'Cannot create slide, need more data.'\n"
    #     "\n"
    #     "Format the output in a JSON template structure compatible with Reveal.js, using placeholders for the content:\n"
    #     "\n"
    #     "{{\n"
    #     '    "title": "<Replace with slide title>",\n'
    #     '    "content": [\n'
    #     '        {{\n'
    #     '            "heading": "<Replace with section heading>",\n'
    #     '            "bullet_points": [\n'
    #     '                "<Replace with first bullet point>",\n'
    #     '                "<Replace with second bullet point>",\n'
    #     '                "<Replace with third bullet point>"\n'
    #     '            ]\n'
    #     '        }},\n'
    #     '        {{\n'
    #     '            "heading": "<Replace with next section heading>",\n'
    #     '            "bullet_points": [\n'
    #     '                "<Replace with first bullet point in this section>",\n'
    #     '                "<Replace with second bullet point in this section>"\n'
    #     '            ]\n'
    #     '        }}\n'
    #     "    ]\n"
    #     "}}\n"
    # )
    # return prompt_text
    prompt_text = (
                    "You are a helpful assistant specializing in creating engaging and challenging content for medical students.\n"
                    "\n"
                    "Create a comprehensive set of materials based on the following content:\n"
                    "\n"
                    "Title: {{topic}}\n"
                    "\n"
                    "Content:\n"
                    "{{formatted_content}}\n"
                    "\n"
                    "Design specifications:\n"
                    "- Professional and clean font style.\n"
                    "- Simple layout with clear headings and bullet points for slides.\n"
                    "- Challenging but engaging quiz questions that assess factual knowledge.\n"
                    "- Clinical case scenarios that test the application of knowledge.\n"
                    "- Questions based on Bloom's Taxonomy to test higher-order thinking (analysis, synthesis, and evaluation).\n"
                    "\n"
                    "The output should include four types of content:\n"
                    "1. **Slides**: Foundational knowledge organized with headings and bullet points. Stick to the topic while generating the slides even if content found is minimal. No Need to intro the genrenal and overall topic as these slides will be part of an overall deck but introduce the main theme of {{topic}}," 
                    "for example fir a topic 'Different clinical types of scabies' you dont need to introduce Scabies unless the topic itself has it for eg: Etiological agent of scabies, in which case have an introduction slide \n"
                    "2. **Quiz**: Challenging Jeopardy-style MCQs with indirect descriptions in the answers and plausible distractors.\n"
                    "3. **Case-based Questions**: Real-world clinical scenarios requiring application and analysis.\n"
                    "4. **Bloom's Levels**: Higher-order thinking questions to test analysis, evaluation, and synthesis of the material.\n"
                    "5. **Summary**: Summary of the main key points of the topic as a paragraph maximizing the semantic value.\n"
                    "\n"
                    "Each section should be nested under a specific key in a JSON structure:\n"
                    "- **Slides** key: Contains the content with headings and bullet points.Pay attention to the order of the slides, the more a heading is relevant to the topic the earlier the silde should appear \n"
                    "- **Quiz** key: Contains Jeopardy-style MCQs with indirect descriptions and challenging distractors.\n"
                    "- **Case-based** key: Contains clinical cases where students apply their knowledge to diagnose or treat patients.\n"
                    "- **Bloom's** key: Contains questions targeting higher levels of cognitive ability.\n"
                    "- **Summary** key: Contains a summary of the entire content in upto 300 words .\n"
                    "\n"
                    "Format the output in the following JSON structure:\n"
                    "\n"
                    '{{\n'
                    '    "slides": [\n'
                    '        {{\n'
                    '            "title": "<Replace with slide title>",\n'
                    '            "content": [\n'
                    '                {{\n'
                    '                    "heading": "<Replace with section heading>",\n'
                    '                    "bullet_points": [\n'
                    '                        "<Replace with first bullet point>",\n'
                    '                        "<Replace with second bullet point>",\n'
                    '                        "<Replace with third bullet point>"\n'
                    '                    ]\n'
                    '                }}\n'
                    '            ]\n'
                    '        }}\n'
                    '    ],\n'
                    '    "quiz": [\n'
                    '        {{\n'
                    '            "jeopardy_mcq": {{\n'
                    '                "answer": "<Provide an indirect description of the answer (e.g., characteristics or broader context)>",\n'
                    '                "options": [\n'
                    '                    "<Option A>",\n'
                    '                    "<Option B>",\n'
                    '                    "<Option C>",\n'
                    '                    "<Option D>"\n'
                    '                ],\n'
                    '                "correct_option": "<Indicate the correct option (e.g., \'A\', \'B\', \'C\', \'D\')>"\n'
                    '            }}\n'
                    '        }},\n'
                    '        {{\n'
                    '            "jeopardy_mcq": {{\n'
                    '                "answer": "<Provide an indirect description for the second MCQ>",\n'
                    '                "options": [\n'
                    '                    "<Option A>",\n'
                    '                    "<Option B>",\n'
                    '                    "<Option C>",\n'
                    '                    "<Option D>"\n'
                    '                ],\n'
                    '                "correct_option": "<Indicate the correct option for the second MCQ>"\n'
                    '            }}\n'
                    '        }}\n'
                    '    ],\n'
                    '    "case_based": [\n'
                    '        {{\n'
                    '            "case": {{\n'
                    '                "description": "<Describe the patient case>",\n'
                    '                "questions": [\n'
                    '                    {{\n'
                    '                        "question": "<First case question>",\n'
                    '                        "options": [\n'
                    '                            "<Option A>",\n'
                    '                            "<Option B>",\n'
                    '                            "<Option C>",\n'
                    '                            "<Option D>"\n'
                    '                        ],\n'
                    '                        "correct_option": "<Correct option for the first case question>"\n'
                    '                    }},\n'
                    '                    {{\n'
                    '                        "question": "<Second case question>",\n'
                    '                        "options": [\n'
                    '                            "<Option A>",\n'
                    '                            "<Option B>",\n'
                    '                            "<Option C>",\n'
                    '                            "<Option D>"\n'
                    '                        ],\n'
                    '                        "correct_option": "<Correct option for the second case question>"\n'
                    '                    }}\n'
                    '                ]\n'
                    '            }}\n'
                    '        }}\n'
                    '    ],\n'
                    '    "blooms": [\n'
                    '        {{\n'
                    '            "level": "Analysis",\n'
                    '            "question": "<Provide an analysis-level question requiring deeper understanding>"\n'
                    '        }},\n'
                    '        {{\n'
                    '            "level": "Evaluation",\n'
                    '            "question": "<Provide an evaluation-level question that tests judgment or decision-making>"\n'
                    '        }}\n'
                    '    ],\n'
                    '    "summary": {{\n'
                    '        "text": "<Summarize the main key points as a paragraph that maximizes semantic value>"\n'
                    '    }}\n'
                    '}}\n'
                )
    return prompt_text

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

filePath= os.path.expanduser("~/backend-MR/app/helper/credentials.json")
filePath2= os.path.expanduser("~/backend-MR/app/helper/input.json")
chrome_path = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))

# POST endpoint to process the content
@router.post("/")
async def get_llm_response(request: ContentRequest):
    try:
        formatted_content = "\n".join(f"- {line}" for line in request.text_content)
        prompt_text=create_slide_prompt()
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
        # Call the create_presentation function from slides_generator
        presentation_url = await slides_generator.create_presentation(json.loads(json_result))

        # Output the presentation URL
        print(presentation_url)
        # Return some dummy response
        return json_result
         
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




 
  
