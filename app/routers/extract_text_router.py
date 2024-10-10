import json
import os
import re
from bs4 import BeautifulSoup
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
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

# code to break down leaning objectives and match documents

# Initialize the router
router = APIRouter(
    prefix="/extract-text",
    tags=["extract-text"],
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
files_folder = "files"

llm_prompt = (
            "Given the following text-content, extract and structure the information into JSON format with the following structure:\\n"
            "- **Main Topic:** The overarching subject of the content.\\n"
            "- **competencies:** Each distinct subtopic should be identified and listed under \"Subtopics.\" For each competency, include:\\n"
            "  - **competency:** The title or description of the competencies.\\n"
            "  - **parts:** A list of parts of the competencies or specific points covered under this competency.Rephrase parts to avoid words like Enumerate,list,mention\\n\\n"
            "    - **Rephrase the parts to make it more search-friendly by removing non-essential words such as 'enumerate,' 'list,' 'mention,' and any other similar words that don't contribute to the core meaning. Maintain the key information for better relevance in search queries.\\n\\n"
            "    - **Example part Input from text-content: 'Enumerate the side effects of scabicidal agents' Example Output: 'Side effects of scabicidal agents'\\n\\n"
            "    - **Example part Input from text-content: 'Mention the incubation period and various modes of transmission in scabies' Example Output: 'Incubation period and modes of transmission in scabies'\\n\\n"
            
            "Ensure the JSON structure follows this format:\\n\\n"
            "{{\\n"
            "  \"Main Topic\": \"Main topic extracted from the text\",\\n"
            "  \"competencies\": [\\n"
            "    {{\\n"
            "      \"competency\": \"First competency description\",\\n"
            "      \"parts\": [\\n"
            "        \"First part or point under the first competency.Rephrase to avoid words like Enumerate,list,mention\",\\n"
            "        \"Second part or point under under the first competency.Rephrase to avoid words like Enumerate,list,mention\"\\n"
            "      ]\\n"
            "    }},\\n"
            "    {{\\n"
            "      \"competency\": \"Second competency title\",\\n"
            "      \"Competencies\": [\\n"
            "        \"First part or point under the second competency.Rephrase to avoid words like Enumerate,list,mention\",\\n"
            "        \"Second part or point under the second competency.Rephrase to avoid words like Enumerate,list,mention\"\\n"
            "      ]\\n"
            "    }}\\n"
            "  ]\\n"
            "}}\\n\\n"
            "Please extract and structure the information accordingly.\\n\\n"
            "**text-content below:**\\n"
            "{{content}}"

        )


prompt2 = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            llm_prompt
        ),
        ("human", "text content :{content}"),
    ]
)


@router.post("/")
async def upload_pdfs_and_extract_text(
    files: List[UploadFile] = File(...),
):
    response = {
        "message": "PDF files processed successfully.",
        "uploaded_files": [],
        "extracted_content": [],
    }

    extracted_text_blocks = []

    for file in files:
        

        # Specify the directory where files will be saved
        file_path = os.path.join(files_folder, file.filename)
        os.makedirs(files_folder, exist_ok=True)  # Create the directory if it doesn't exist

        # Save the PDF file to the specified directory
        with open(file_path, "wb") as file_object:
            file_object.write(await file.read())

        # Extract text from PDF
        text_content = extract_text_from_pdf(file_path)

        # Add extracted text to the list
        extracted_text_blocks.append(text_content)

        # # Optionally delete the original PDF file
        # os.remove(file_path)

        # Keep track of the uploaded filenames
        response["uploaded_files"].append(file.filename)
        response["extracted_content"].append(text_content)

    # Combine all extracted text into a single content block (if needed)
    combined_text = "\n".join(extracted_text_blocks)

    # Call the dummy LLM method
    llm_response = get_response_from_LLM(combined_text, prompt2)
    
    # Include the LLM response in the final response
    response["llm_response"] = llm_response

    return response

def extract_text_from_pdf(file_path):
    document = fitz.open(file_path)
    text = ""
    for page in document:
        text += page.get_text()
    document.close()
    return text



def get_response_from_LLM(content,prompt_template):
    """
    Calls the LLM to extract structured information based on the content.
    """
   
     # Combine the prompt and the LLM into a chain
    chain = prompt_template | llm | StrOutputParser()
    
    result = chain.invoke({"content": content})
    
    
    # Convert the LLM result from JSON string to a dictionary
    llm_result_dict = json.loads(result)
    # Augment the LLM response
    augmented_result = augment_llm_result_with_details(llm_result_dict)

    return json.dumps(augmented_result, indent=2)


def augment_llm_result_with_details(llm_result):
    """
    Augments the LLM result by adding additional details such as relevant documents and search link.
    """
    for competency in llm_result.get('competencies', []):
        for index, part in enumerate(competency.get('parts', [])):
            # Get relevant documents and scores
            relevant_docs_with_scores, relevant_count = get_results(part)

          # Use doc_to_dict to convert each document and score into a consistent dictionary format
            relevant_docs = [doc_to_dict(doc, score) for score, doc in relevant_docs_with_scores]

            search_link = f"https://pubmed.ncbi.nlm.nih.gov/?term={part.replace(' ', '+')}"
            augmented_part = {
                "name": part,
                "relevant_docs": relevant_docs,
                "links": [search_link]
            }
            competency['parts'][index] = augmented_part

    return llm_result


def get_results(part, threshold=0.5):
    """
    Retrieves relevant documents and scores for a given part.
    """
    LC_chroma_client = get_LC_chroma_client()
    retriever = LC_chroma_client.as_retriever(search_kwargs={"k": 20})

    relevant_docs = retriever.invoke(part)
    cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    pairs = [[part, doc.page_content] for doc in relevant_docs]
    scores = cross_encoder.predict(pairs)

    def is_web_url(source):
        return bool(re.match(r'https?://', source))

    relevant_by_score = [
        (float(score), doc) for score, doc in zip(scores, relevant_docs)
        if score > threshold or (is_web_url(doc.metadata.get("source", "")) and score > -5)
    ]

    relevant_by_score.sort(key=lambda x: x[0], reverse=True)

    # Print scores for verification
    print(f"\nFor part '{part}':")
    for i, (score, doc) in enumerate(relevant_by_score, start=1):
        source_is_web_url = is_web_url(doc.metadata.get("source", ""))
        print(f"  Document {i}  score is {score:.4f} (Relevant - {'Web URL' if source_is_web_url else 'Score'})")
 
    return relevant_by_score, len(relevant_by_score)


def doc_to_dict(doc, score):
    """
    Converts a document object to a dictionary, including the score.
    """
    if isinstance(doc.page_content, str):
        soup = BeautifulSoup(doc.page_content, 'html.parser')
        plain_text = soup.get_text(strip=True)
    else:
        plain_text = doc.page_content

    return {
        "page_content": plain_text,
        "metadata": doc.metadata,
        "score": float(score)
    }


@router.get("/refresh-search")
async def recalculate_part_details(part_name: str, augmented_info: str = ""):
    """
    Recalculates the score and retrieves relevant documents for a part.
    """
    info_to_use = augmented_info if augmented_info.strip() else part_name
    relevant_docs_with_scores, relevant_count = get_results(info_to_use)

    relevant_docs = [doc_to_dict(doc, score) for score, doc in relevant_docs_with_scores]
    search_link = f"https://pubmed.ncbi.nlm.nih.gov/?term={part_name.replace(' ', '+')}"

    augmented_part = {
        "name": part_name,
        "augmented_info":augmented_info,
        "relevant_docs": relevant_docs,
        "links": [search_link]
    }

    return augmented_part