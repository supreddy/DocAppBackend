import os
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import List
import fitz

from app.routers.get_LLM_result import process_files_with_instruction  # PyMuPDF

# Assuming process_files_with_instruction and extract_text_from_pdf are already defined

# Initialize the router
router = APIRouter(
    prefix="/upload",
    tags=["upload"],
    responses={404: {"description": "Not found"}},
)

files_folder = "files"

@router.post("/")
async def upload_pdfs(
    pdf_files: List[UploadFile] = File(...),
    description: str = Form(...)
):
    response = {
        "message": "PDF files uploaded successfully.",
        "uploaded_files": [],
        "description": description,
    }
    
    uploaded_filenames = []

    for pdf_file in pdf_files:
        if not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

        # Specify the directory where files will be saved
        file_path = os.path.join(files_folder, pdf_file.filename)
        os.makedirs(files_folder, exist_ok=True)  # Create the directory if it doesn't exist

        # Save the PDF file to the specified directory
        with open(file_path, "wb") as file_object:
            file_object.write(await pdf_file.read())

        # Extract text from PDF
        text_content = extract_text_from_pdf(file_path)

        # Remove the original extension and add .txt
        base_name = os.path.splitext(pdf_file.filename)[0]  # Get the filename without the extension
        processed_file_path = os.path.join(files_folder, f"{base_name}.txt")

        # Save the extracted text to a new file
        with open(processed_file_path, "w") as text_file:
            text_file.write(text_content)

        # Optionally delete the original PDF file
        os.remove(file_path)

        # Keep track of the uploaded filenames
        uploaded_filenames.append(processed_file_path)
        response["uploaded_files"].append(pdf_file.filename)

    # After uploading and processing the files, use the helper method to process them with the LLM
    try:
        transformed_text = process_files_with_instruction(uploaded_filenames, description)
        response["transformed_text"] = transformed_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files with LLM: {str(e)}")

    return response

def extract_text_from_pdf(file_path):
    document = fitz.open(file_path)
    text = ""
    for page in document:
        text += page.get_text()
    document.close()
    return text
