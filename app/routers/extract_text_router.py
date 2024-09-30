import json
import os
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

prompt = (
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
            prompt
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




def get_response_from_LLM(content, prompt_template):

 
     # Combine the prompt and the LLM into a chain
    chain = prompt_template | llm | StrOutputParser()
    
    result = chain.invoke({"content": content})
    
    
    # Convert the LLM result from JSON string to a dictionary
    llm_result_dict = json.loads(result)

    # Augment the LLM result with additional details
    augmented_result = augment_llm_result_with_details(llm_result_dict)

    # Serialize the augmented result to a JSON-formatted string
    json_result = json.dumps(augmented_result, indent=2)

    # Return the JSON string
    return json_result

def augment_llm_result_with_details(llm_result):
    """
    Augments the LLM result by adding additional details to each part, such as
    the list of relevant documents (with scores greater than a configurable threshold) and a search link.

    :param llm_result: A dictionary containing the LLM's JSON response.
    :return: The augmented LLM result with additional details.
    """
    # Iterate over each competency in the 'competencies' list
    for competency in llm_result.get('competencies', []):
        for index, part in enumerate(competency.get('parts', [])):
            # Get relevant documents for the current part and count those with scores > threshold
            relevant_docs, relevant_count = get_results(part)

            # Convert any non-serializable objects in relevant_docs to dictionaries
            relevant_docs = [doc_to_dict(doc) for doc in relevant_docs]

            # Construct the search link
            search_link = f"https://pubmed.ncbi.nlm.nih.gov/?term={part.replace(' ', '+')}"

            # Augment the part with additional details
            augmented_part = {
                "name": part,
                "relevant_docs": relevant_docs,  # Use the list of relevant documents
                "links": [search_link]
            }

            # Replace the original part with the augmented part
            competency['parts'][index] = augmented_part

    return llm_result


def doc_to_dict(doc):
    """
    Converts a document object into a dictionary for JSON serialization, extracting plain text from HTML content.
    
    :param doc: The document object.
    :return: A dictionary representation of the document with plain text extracted from HTML content.
    """
    # Extract plain text from the HTML content
    soup = BeautifulSoup(doc.page_content, 'html.parser')
    plain_text = soup.get_text(strip=True)  # Extract and clean the text
    
    return {
       
        "page_content": plain_text,  # Replace HTML content with extracted plain text
        "metadata": doc.metadata,  # Include metadata in the dictionary
    }



def get_results(part,threshold=0.5):
    """
    Retrieves relevant documents for the given part using LC_chroma_client, scores them using a CrossEncoder,
    filters those with scores above 1, and prints the sorted results.

    :param part: The part of the competency to search for relevant documents.
    :return: A list of relevant documents with scores greater than 1, and the count of such documents.
    """
    # Initialize LC_chroma_client and the retriever
    LC_chroma_client = get_LC_chroma_client()  # Ensure get_LC_chroma_client is defined and returns a valid client
    retriever = LC_chroma_client.as_retriever(search_kwargs={"k": 10})
    
    # Retrieve relevant documents
    relevant_docs = retriever.get_relevant_documents(part)
    
    # Initialize the CrossEncoder for scoring
    cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    # Prepare pairs of (part, page_content) for scoring
    pairs = []
    for doc in relevant_docs:
        page_content = doc.page_content# Accessing the document's content
        pairs.append([part, page_content])
    
    # Score the pairs
    scores = cross_encoder.predict(pairs)
    
    # Filter documents with scores greater than 1
    relevant_by_score = [
        doc for score, doc in zip(scores, relevant_docs) if score > threshold
    ]
    
    # Print scores for verification
    print(f"\nFor part '{part}':")
    for i, (score, doc) in enumerate(zip(scores, relevant_docs), start=1):
        if score > threshold:
            print(f"  Document {i} score is {score:.4f} (Relevant)")
        else:
            print(f"  Document {i} score is {score:.4f} (Not Relevant)")
    
    # Return the filtered relevant documents and their count
    return relevant_by_score, len(relevant_by_score)


@router.get("/refresh-search")
async def recalculate_part_details(part_name: str):
    """
    Recalculates the score and finds relevant documents for a given part.
    
    :param part_name: The name of the part to process.
    :param threshold: The score threshold for considering a document relevant.
    :return: An augmented part object with relevant documents and search link.
    """
    # Get relevant documents for the current part and count those with scores > threshold
    relevant_docs, relevant_count = get_results(part_name)

    # Convert any non-serializable objects in relevant_docs to dictionaries
    relevant_docs = [doc_to_dict(doc) for doc in relevant_docs]

    # Construct the search link
    search_link = f"https://pubmed.ncbi.nlm.nih.gov/?term={part_name.replace(' ', '+')}"

    # Augment the part with additional details
    augmented_part = {
        "name": part_name,
        "relevant_docs": relevant_docs,  # Use the list of relevant documents
        "links": [search_link]
    }

    return augmented_part