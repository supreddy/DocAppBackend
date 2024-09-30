import os
import re
import fitz  # PyMuPDF
import json
from fastapi import FastAPI, APIRouter, HTTPException


# Initialize the router
router = APIRouter(
    prefix="/get-toc",
    tags=["toc"],
    responses={404: {"description": "Not found"}},
)

# Function to extract the full TOC hierarchy from the PDF
def extract_full_toc_from_pdf(pdf_file: str):
    """
    Extracts the full Table of Contents (TOC) from a PDF file, including chapters and all subsections.

    :param pdf_file: Path to the PDF file.
    :return: TOC as a list of dictionaries containing chapters and all nested subsections.
    """
    if not os.path.exists(pdf_file):
        raise HTTPException(status_code=404, detail="PDF file not found.")

    doc = fitz.open(pdf_file)
    
    toc = doc.get_toc()  # Get the TOC from the PDF
    doc.close()

    toc_structure = []
    toc_hierarchy = {}

    for entry in toc:
        level, title, page = entry
        node = {
            'title': title.strip(),
            'page': page,
            'subsections': []
        }

        # Build the hierarchy based on the level
        if level == 1:
            # Top-level chapter
            toc_hierarchy[level] = node
            toc_structure.append(node)
        else:
            # Find the correct parent node based on the level
            parent = toc_hierarchy.get(level - 1)
            if parent:
                parent['subsections'].append(node)

        # Update the toc_hierarchy for the current level
        toc_hierarchy[level] = node

    return toc_structure


@router.get("/")
async def get_full_toc(pdf_file_path: str = os.path.expanduser("~/files/rooks 9th edition.pdf")):
    """
    API endpoint to extract and return the full Table of Contents (TOC) from a PDF file, including chapters and subsections.

    :param pdf_file_path: Path to the PDF file.
    :return: JSON structure of chapters and all nested subsections.
    """
    try:
        toc = extract_full_toc_from_pdf(pdf_file_path)
        return {
            "status": "success",
            "toc": toc
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
