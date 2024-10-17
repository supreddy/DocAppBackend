import base64
import json
import httpx
from fastapi import APIRouter, HTTPException, Query
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI  # Example of LLM from Langchain

# Initialize the router
router = APIRouter(
    prefix="/process-image",
    tags=["Image Processing"],
    responses={404: {"description": "Not found"}},
)

model = ChatOpenAI(model="gpt-4o-mini")  # Assuming a vision-based model like GPT-4 Vision
# API to process the image and return the caption, title, and description
@router.get("/")
async def generate_caption_title_description(image_url: str = Query(...), topic: str = Query(...)):
    """
    Given an image URL and the overall topic, fetches the image, processes it, and returns the generated caption, title, and description.
    
    :param image_url: The URL of the image to be processed.
    :param topic: The overall topic or context for the image.
    :return: JSON object with the generated title, caption, and description.
    """
    try:
        # Fetch the image from the URL
        response = httpx.get(image_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch image from the URL.")

        # Encode the image as base64
        image_data = base64.b64encode(response.content).decode("utf-8")
        print("Image successfully fetched and base64 encoded.")
        topic=topic
        # Update the system message to include the topic
        prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", 
                            """
                            You are given an image encoded in base64 format. The image is used in a medical teaching context on the topic '{topic}'. Your task is to generate a JSON response with the following structure:

                            {{
                                "title": "<A suitable title for the image related to the topic of {topic}>",
                                "caption": "<A concise caption for the image>",
                                "description": "<A detailed description of the image with relevance to its use in medical teaching, and its connection to the topic of {topic}>"
                            }}

                            Instructions:
                            - Generate the response in plain JSON format.
                            - Do NOT include any code block formatting (such as backticks or ```json).
                            - Do NOT include any newline escape characters (\\n).
                            - Ensure the output is valid JSON with no extra characters or symbols.

                            Now, generate the title, caption, and description for the provided image.
                            """
                        ),
                        (
                            "user",
                            [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": "data:image/jpeg;base64,{image_data}"},
                                }
                            ],
                        ),
                    ]
                )

        # Create the chain with the prompt and model
        chain = prompt | model

        # Get the result by invoking the chain with the base64 image data
        response = chain.invoke({"image_data": image_data,"topic":topic})
        result = json.loads(response.content)
        print(response.content)
        # Extract and return the result
        return {
            "image_url": image_url,
            "generated_title": result["title"],
            "generated_caption": result["caption"],
            "generated_description": result["description"],
        
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
