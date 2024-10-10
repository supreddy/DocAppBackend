import json
import os
import re
from bs4 import BeautifulSoup
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
import fitz  # PyMuPDF
from langchain.chains.retrieval import create_retrieval_chain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import CrossEncoder
from langchain_community.document_transformers import (
    LongContextReorder,
)
from db.db import get_LC_chroma_client
import asyncio

router = APIRouter(
    prefix="/extract-text-stream",
    tags=["extract-text-stream"],
    responses={404: {"description": "Not found"}},
)

llm = ChatOpenAI(
    model="gpt-3.5-turbo-0125",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    streaming=True,
)

files_folder = "files"

prompt = (
    "Given the following text-content, extract and structure the information into JSON format with the following structure:\n"
    # ... (rest of the prompt remains the same)
)

prompt2 = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            prompt
        ),
        ("human", "text content :{content}"),
    ]
)

async def process_file(file):
    file_path = os.path.join(files_folder, file.filename)
    os.makedirs(files_folder, exist_ok=True)

    with open(file_path, "wb") as file_object:
        file_object.write(await file.read())

    text_content = extract_text_from_pdf(file_path)
    
    return file.filename, text_content

async def stream_response(files):
    response = {
        "message": "Processing PDF files...",
        "uploaded_files": [],
        "extracted_content": [],
    }
    yield json.dumps(response) + "\n"

    extracted_text_blocks = []

    for file in files:
        filename, text_content = await process_file(file)
        extracted_text_blocks.append(text_content)
        response["uploaded_files"].append(filename)
        response["extracted_content"].append(text_content)
        yield json.dumps(response) + "\n"

    combined_text = "\n".join(extracted_text_blocks)
    
    yield json.dumps({"status": "Analyzing content with LLM..."}) + "\n"

    async for competency in get_response_from_LLM_stream(combined_text, prompt2):
        yield json.dumps({"competency": competency}) + "\n"

@router.post("/")
async def upload_pdfs_and_extract_text(
    files: List[UploadFile] = File(...),
):
    return StreamingResponse(stream_response(files), media_type="application/json")

def extract_text_from_pdf(file_path):
    document = fitz.open(file_path)
    text = ""
    for page in document:
        text += page.get_text()
    document.close()
    return text

async def get_response_from_LLM_stream(content, prompt_template):
    chain = prompt_template | llm | StrOutputParser()
    
    buffer = ""
    current_competency = {}
    async for chunk in chain.astream({"content": content}):
        buffer += chunk
        if '"competency":' in buffer:
            if current_competency:
                yield await augment_competency(current_competency)
                current_competency = {}
            buffer = '{"competency":' + buffer.split('"competency":')[-1]
        
        if buffer.endswith("},") or buffer.endswith("}}"):
            try:
                current_competency = json.loads(buffer.rstrip(","))
                buffer = ""
            except json.JSONDecodeError:
                continue

    if current_competency:
        yield await augment_competency(current_competency)

async def augment_competency(competency):
    for index, part in enumerate(competency.get('parts', [])):
        relevant_docs, relevant_count = await get_results(part)
        relevant_docs = [doc_to_dict(doc) for doc in relevant_docs]
        search_link = f"https://pubmed.ncbi.nlm.nih.gov/?term={part.replace(' ', '+')}"
        augmented_part = {
            "name": part,
            "relevant_docs": relevant_docs,
            "links": [search_link]
        }
        competency['parts'][index] = augmented_part
    return competency

def doc_to_dict(doc):
    soup = BeautifulSoup(doc.page_content, 'html.parser')
    plain_text = soup.get_text(strip=True)
    return {
        "page_content": plain_text,
        "metadata": doc.metadata,
    }

async def get_results(part, threshold=0.5):
    LC_chroma_client = get_LC_chroma_client()
    retriever = LC_chroma_client.as_retriever(search_kwargs={"k": 20})
    
    relevant_docs = await retriever.ainvoke(part)
    
    cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    pairs = [[part, doc.page_content] for doc in relevant_docs]
    
    scores = cross_encoder.predict(pairs)
    
    def is_web_url(source):
        return bool(re.match(r'https?://', source))

    relevant_by_score = [
        (score, doc) for score, doc in zip(scores, relevant_docs)
        if score > threshold or (is_web_url(doc.metadata.get("source", "")) and score > 0)
    ]
    
    relevant_by_score.sort(key=lambda x: x[0], reverse=True)
    
    return [doc for score, doc in relevant_by_score], len(relevant_by_score)

@router.get("/refresh-search")
async def recalculate_part_details(part_name: str):
    relevant_docs, relevant_count = await get_results(part_name)
    relevant_docs = [doc_to_dict(doc) for doc in relevant_docs]
    search_link = f"https://pubmed.ncbi.nlm.nih.gov/?term={part_name.replace(' ', '+')}"
    augmented_part = {
        "name": part_name,
        "relevant_docs": relevant_docs,
        "links": [search_link]
    }
    return augmented_part