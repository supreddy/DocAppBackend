from fastapi import APIRouter, HTTPException, Query
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

# Load OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize the router
router = APIRouter(
    prefix="/augment-subtopic",
    tags=["subtopic"],
    responses={404: {"description": "Not found"}},
)

# Set up the LLM
llm = ChatOpenAI(
    model="gpt-3.5-turbo-0125",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
# Define the prompt template
prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert in semantic search and natural language processing.",
        ),
        (
            "human",
            """
            The topic is '{topic}', and the subtopic is '{subtopic}'.
            
            Generate alternative ways to search for or find related content to {subtopic} within the context of {topic}. 
            
            Focus on producing **concise, high-value keyword phrases** that can be used for a similarity comparison.
            
            Consider different strategies, such as:
            - Using synonyms or semantically related terms.
            - Broadening the search to include related concepts or terms.
            - Narrowing the search to focus on specific details.
            - Leveraging timeframes, conditions, or processes associated with the subtopic.
            - Identifying conceptual or causal relationships tied to the subtopic.
            
            Return concise keyword variations or query terms that can enhance similarity comparison using cross-encoder or vector models.
            """
        ),
    ]
)




# Output parser to handle the LLM's response
chain = prompt_template | llm | StrOutputParser()

# GET endpoint to augment a subtopic
@router.get("/")
async def augment_subtopic(
    topic: str = Query(..., description="The main topic to discuss"),
    subtopic: str = Query(..., description="The subtopic to augment and explain")
):
    """
    API endpoint to augment a subtopic by providing detailed information.
    
    :param topic: The main topic to discuss.
    :param subtopic: The subtopic to augment and explain.
    :return: Detailed response about the subtopic in the context of the topic.
    """
    try:
        # Call the LLM with the prompt template and input values
        json_result = chain.invoke(
            {
                "topic": topic,
                "subtopic": subtopic,
            }
        )

        if json_result:
            # Return the response from the LLM
            return {"augmented_response": json_result}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate response from LLM.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
