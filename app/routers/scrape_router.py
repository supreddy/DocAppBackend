import json
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import AsyncGenerator

from starlette.responses import StreamingResponse

from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# code to summarize links

from langchain_core.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant specializing in medical artciles and journals that translates summarizes medical abstract from their provided text. use no more 20 words use bullet points if neccesary",
        ),
        ("human", "{text_to_summarize}"),
    ]
)

llm = ChatOpenAI(
    model="gpt-3.5-turbo-0125",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # api_key = "",  # if you prefer to pass api key in directly instaed of using env vars
    # base_url="...",
    # organization="...",
    # other params...
)
chain = prompt | llm | StrOutputParser()
# Define the request body model
class CrawlRequest(BaseModel):
    url: str = Field(..., description="URL to crawl and extract text from")

# Define the request body model
class PageSummary(BaseModel): 
    title: str = Field(..., description="Title of the page.") 
    summary: str = Field(..., description="Summary of the page.") 
    brief_summary: str = Field(..., description="Brief summary of the page.") 
    keywords: list = Field(..., description="Keywords assigned to the page.")
    
# Initialize the router
router = APIRouter(
    prefix="/scrape",
    tags=["scrape"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def crawl_url(url: str) -> StreamingResponse:
    """
    FastAPI POST endpoint to crawl a given URL and return its text content.
    """
    # Initialize and warm up the web crawler
    crawler = initialize_crawler()

    # Create a generator that yields the text content as it's being scraped
    text_data_generator = stream_text_content(crawler, url)
    
    # Return a StreamingResponse, streaming the text content as JSON
    return StreamingResponse(text_data_generator, media_type="application/json")

@router.get("/summarize")
async def summarize_url(url: str) -> JSONResponse:
    """
    FastAPI GET endpoint to scrape and summarize content from a specific div
    with the class 'abstract-content selected'.
    """
    # Initialize and warm up the web crawler
    crawler = initialize_crawler()

    # Fetch the content of the specific div
    content = fetch_specific_content(crawler, url)
    
    if content:
        return JSONResponse(content)
    else:
        raise HTTPException(status_code=404, detail="Content not found")


@router.get("/summarize-lite")
async def summarize_url_lite(url: str) -> JSONResponse:
    """
    FastAPI GET endpoint to scrape and summarize content from a specific div
    or element on a webpage.
    """
    html_content = requests.get(url)
    soup = BeautifulSoup(html_content.content, "html.parser")

    if "pubmed.ncbi.nlm.nih.gov" in url:
        # Extract content only from the element with id 'abstract'
        content_element = soup.find(id="abstract")
        if content_element:
            content = str(content_element)  # Convert the element to a string containing HTML
        else:
            raise HTTPException(status_code=404, detail="Abstract content not found")
    else:
        # Extract all text content if the URL is not from PubMed
        content = soup.get_text(strip=True)
    
    # Use the extracted content to generate a summary using the chain
    json_result = chain.invoke(
        {
            "text_to_summarize": content,
        }
    )
    
    if json_result:
        # Return the summary within a JSON object
        return JSONResponse({"summary": json_result, "actual_text": content})
    else:
        raise HTTPException(status_code=404, detail="Content not found")







def initialize_crawler():
    """
    Initializes and warms up the WebCrawler.
    """
    crawler = WebCrawler()
    crawler.warmup()  # Prepares the crawler for scraping by loading necessary models or settings
    return crawler

async def stream_text_content(crawler, url: str) -> AsyncGenerator[str, None]:
    """
    Generator function to scrape and stream text content from the given URL.
    """
    # Fetch the HTML content of the page
    response = fetch_html_content(crawler, url)
    
    if response:
        yield json.dumps(response) + "\n"
    else:
        # If HTML content couldn't be fetched, yield an error message
        yield json.dumps({"error": "Failed to retrieve content"}) + "\n"

def fetch_html_content(crawler, url: str) -> str:
    """
    Fetches HTML content from a specified URL using the WebCrawler.
    """
    result = crawler.run(
        url=url,
        word_count_threshold=1, 
        extraction_strategy=LLMExtractionStrategy(
            provider="openai/gpt-3.5-turbo-0125", 
            api_token=api_key, 
            schema=PageSummary.model_json_schema(), 
            extraction_type="schema", 
            apply_chunking=False, 
            instruction=(
                "From the crawled content, extract the following details: "
                "1. Title of the page "
                "2. Summary of the page, which is a detailed summary "
                "3. Brief summary of the page, which is a paragraph text "
                "4. Keywords assigned to the page, which is a list of keywords. "
                'The extracted JSON format should look like this: '
                '{ "title": "Page Title", "summary": "Detailed summary of the page.", '
                '"brief_summary": "Brief summary in a paragraph.", "keywords": ["keyword1", "keyword2", "keyword3"] }'
            )
        ),
        bypass_cache=True,
    )
    return json.loads(result.extracted_content) if result else None  # Return the HTML content if the result is valid

def fetch_specific_content(crawler, url: str) -> dict:
    """
    Fetches content from a specified div with the class 'abstract-content selected' using the WebCrawler.
    """
    result = crawler.run(
        url=url,
        css_selector="div.abstract-content.selected", 
        only_text=True,# Use the CSS selector to target the specific div
        bypass_cache=True,
    )
    
    if result and result.extracted_content:
        # Parsing the HTML content
        soup = BeautifulSoup(result.extracted_content, "html.parser")
        content = soup.get_text(strip=True)  # Extract text content from the div
        json_result= chain.invoke(
                {
                    "text_to_summarize": content,
                }
            )
        
        return json_result
    else:
        return None
