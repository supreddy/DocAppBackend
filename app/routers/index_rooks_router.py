from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import fitz  # PyMuPDF
import json
import re
import os
from app.indexers.file_processor_with_indexing import process_text_and_index  # Importing the indexing function
from pydantic import BaseModel
from typing import List, Optional, Union

from app.indexers.file_processor_with_indexing import process_text_and_index
from app.indexers.update_indexed_files import add_or_update_file, get_all_files, init_db
from config import PDF_FILES_FOLDER
 

# Initialize the router
router = APIRouter(
    prefix="/process-pdf",
    tags=["PDF Processing"],
    responses={404: {"description": "Not found"}},
)

BOOK_NAME =  "rooks 9th edition.pdf"

 
# Class to represent a TOC entry with hierarchical structure
class TOCNode:
    """
    Class to represent a node in the Table of Contents (TOC) hierarchy.

    Attributes:
        title (str): The title of the TOC entry (e.g., chapter title).
        from_page (int): The page where the TOC entry starts.
        to_page (int): The page where the TOC entry ends (None until calculated).
        subsections (list): List of child nodes (subsections).
    """
    def __init__(self, title, from_page):
        self.title = title
        self.from_page = from_page  # Starting page
        self.to_page = None  # Ending page, to be filled later
        self.subsections = []  # List of subsections (children nodes)

    def add_subsection(self, subsection):
        """Add a subsection (child node) to this TOC node."""
        self.subsections.append(subsection)

    def set_to_page(self, to_page):
        """Set the ending page of this TOC node."""
        self.to_page = to_page

    def to_dict(self):
        """Convert the node to a dictionary for JSON serialization."""
        return {
            "title": self.title,
            "from_page": self.from_page,
            "to_page": self.to_page,
            "subsections": [subsection.to_dict() for subsection in self.subsections]
        }

def get_toc_json_from_pdf(pdf_file):
    """
    Extract the Table of Contents (TOC) from a PDF file and return it as JSON.

    :param pdf_file: Path to the PDF file.
    :return: JSON string of the TOC.
    """
    doc = fitz.open(pdf_file)
    toc = doc.get_toc()

    if not toc:
        return None

    root = []
    last_node_at_level = {}

    # Process the table of contents, creating nodes for each entry
    for entry in toc:
        level, title, page_num = entry
        new_node = TOCNode(title, page_num)

        if level == 1:
            root.append(new_node)
            last_node_at_level[level] = new_node
        else:
            parent_node = last_node_at_level.get(level - 1)
            if parent_node:
                parent_node.add_subsection(new_node)
                last_node_at_level[level] = new_node

    # Set the 'to' pages for each TOC entry
    set_to_pages(root, doc.page_count)

    toc_json = [node.to_dict() for node in root]
    return json.dumps(toc_json, indent=4)

def set_to_pages(toc_root, total_pages):
    """
    Set the "to" page for each TOC node (i.e., the ending page for each TOC entry).

    :param toc_root: Root of the TOC hierarchy (list of TOCNode).
    :param total_pages: Total number of pages in the document.
    """
    def calculate_to_pages(node, next_page):
        if node.subsections:
            last_subsection = node.subsections[-1]
            calculate_to_pages(last_subsection, next_page)
            node.set_to_page(last_subsection.to_page)
        else:
            node.set_to_page(next_page - 1)

        for i in range(len(node.subsections) - 1, -1, -1):
            current_subsection = node.subsections[i]
            next_subsection_page = node.subsections[i + 1].from_page if i + 1 < len(node.subsections) else node.to_page + 1
            calculate_to_pages(current_subsection, next_subsection_page)

    for i in range(len(toc_root)):
        next_part_page = toc_root[i + 1].from_page if i + 1 < len(toc_root) else total_pages + 1
        calculate_to_pages(toc_root[i], next_part_page)




def extract_chapter_names_from_toc(pdf_file: str, chapter_numbers: List[int] = None) -> List[str]:
    """
    Extract chapter names from the PDF's Table of Contents based on chapter numbers.
    If no chapter numbers are provided, extract all chapter names.

    :param pdf_file: Path to the PDF file.
    :param chapter_numbers: List of chapter numbers. If None or empty, extract all chapters.
    :return: List of chapter names corresponding to the chapter numbers or all chapters.
    """
    doc = fitz.open(pdf_file)  # Open the PDF file
    toc = doc.get_toc()  # Get the TOC as a list of tuples (level, title, page_num)
    
    chapter_names = []
    chapter_regex = re.compile(r'^CHAPTER\s+(\d+).*')

    if chapter_numbers is None or len(chapter_numbers) == 0:
        # If no chapter numbers are provided, extract all chapter names
        for entry in toc:
            _, title, _ = entry
            match = chapter_regex.match(title)
            if match:
                chapter_names.append(title)
        return chapter_names
    else:
        # Extract chapter names for the given chapter numbers
        for entry in toc:
            _, title, _ = entry
            match = chapter_regex.match(title)
            if match:
                chapter_number = int(match.group(1))
                if chapter_number in chapter_numbers:
                    chapter_names.append(title)
        return chapter_names



# Define the Pydantic model with default values
class PDFProcessingRequest(BaseModel):
    pdf_name: str = "rooks 9th edition.pdf"  # Default file name
    chapters: Optional[Union[List[int], List[tuple]]] = None  # Allow a list of chapters or ranges

# Helper function to extract subsections and format them as ## headers
def extract_subsections(subsections):
    """
    Recursively extracts subsection titles and returns them as a list.
    Each subsection title will be formatted as an H2 markdown header (##).
    """
    subsection_titles = []
    for subsection in subsections:
        subsection_titles.append(subsection['title'].strip())
        subsection_titles.extend(extract_subsections(subsection['subsections']))  # Recursively extract nested subsections
    return subsection_titles

# Helper function to expand chapter ranges
def expand_chapter_ranges(chapters: List[Union[int, tuple]]) -> List[int]:
    """
    Expand the chapter ranges if provided in the form of tuples.
    :param chapters: List of chapter numbers or ranges (tuples).
    :return: A flat list of individual chapter numbers.
    """
    expanded_chapters = []
    for item in chapters:
        if isinstance(item, tuple):
            # Assume the tuple is (start, end) and expand the range
            expanded_chapters.extend(range(item[0], item[1] + 1))
        else:
            # It's a single chapter, add it directly
            expanded_chapters.append(item)
    return expanded_chapters

# Function to process and index PDF chapters, now including markdown conversion
@router.post("/")
async def process_pdf_chapters(request: PDFProcessingRequest):
    """
    API endpoint to process and index chapters from a PDF.

    :param request: Request body containing PDF file path and list of chapter numbers to index.
    :return: Success message or error details.
    """
    print("Request", request)
    pdf_file = os.path.expanduser(PDF_FILES_FOLDER + request.pdf_name)
    chapter_numbers = request.chapters

    # If chapter_numbers is None, return an error or default to processing the whole PDF
    if chapter_numbers is None:
        return {"status": "No chapters provided. Defaulting to indexing the whole PDF."}

    # Expand any chapter ranges (e.g., 1-10) into individual chapter numbers
    expanded_chapters = expand_chapter_ranges(chapter_numbers)
    chapter_numbers=expanded_chapters;
    
    # Process the chapters (Placeholder for actual processing logic)
    print(f"Processing the following chapters: {expanded_chapters}")

    # Extract chapter names based on the provided chapter numbers
    chapter_names = extract_chapter_names_from_toc(pdf_file, expanded_chapters)
    add_or_update_file(request.pdf_name, expanded_chapters, chapter_names)

    if not os.path.exists(pdf_file):
        raise HTTPException(status_code=404, detail="PDF file not found.")

    doc = fitz.open(pdf_file)

    # Load TOC JSON
    toc_json_str = get_toc_json_from_pdf(pdf_file)
    if not toc_json_str:
        raise HTTPException(status_code=400, detail="Failed to extract TOC from PDF.")

    toc_json = json.loads(toc_json_str)
    chapter_count = 0

    # Function to extract chapters using regex and TOC
    def extract_chapters_from_toc(toc_entries):
        """
        Extract chapters from the Table of Contents (TOC) entries based on the chapter number.

        :param toc_entries: List of TOC entries (dictionaries).
        :return: List of chapters to be processed.
        """
        chapters = []
        chapter_regex = re.compile(r'^CHAPTER\s+(\d+).*')
        for entry in toc_entries:
            match = chapter_regex.match(entry['title'])
            if match:
                chapter_number = int(match.group(1))
                if chapter_numbers is None or chapter_number in chapter_numbers:
                    chapters.append(entry)
            chapters.extend(extract_chapters_from_toc(entry['subsections']))
        return chapters

    # Get the chapters to be processed based on the TOC
    chapters = extract_chapters_from_toc(toc_json)

    if not chapters:
        raise HTTPException(status_code=404, detail="No chapters found matching the provided numbers.")

    # Process each chapter
    for entry in chapters:
        chapter_title = entry['title']
        from_page = entry['from_page']
        to_page = entry['to_page']
        subsections = entry.get('subsections', [])

        print(f"Processing Chapter {chapter_count + 1}: '{chapter_title}' from page {from_page} to {to_page}...")

        if from_page > to_page:
            print(f"Invalid page range: Chapter '{chapter_title}' has from_page {from_page} > to_page {to_page}")
            continue

        if from_page < 1 or to_page > doc.page_count:
            print(f"Out of bounds: Chapter '{chapter_title}' has from_page {from_page} or to_page {to_page} outside the valid page range.")
            continue

        # Extract the text for the chapter
        chapter_text = ""
        for page_num in range(from_page - 1, to_page):
            page = doc.load_page(page_num)
            chapter_text += page.get_text("text") + "\n"

        if not chapter_text.strip():
            print(f"Chapter '{chapter_title}' could not be saved because it has no text.")
            continue

        # Convert chapter text to markdown format
        subsection_titles = extract_subsections(subsections)
        for subsection_title in subsection_titles:
            chapter_text = chapter_text.replace(subsection_title, f"## {subsection_title}")

        # Add the chapter title to the markdown format
        chapter_text_md = f"# {chapter_title}\n\n{chapter_text}"

        # Index the markdown content into the vector database
        try:
            response = process_text_and_index(chapter_text_md, source_id=chapter_title, file_name=request.pdf_name)
            if response:
                print(f"Chapter '{chapter_title}' successfully indexed as markdown.")
            else:
                print(f"Failed to index Chapter '{chapter_title}'.")
        except Exception as e:
            print(f"Error indexing Chapter '{chapter_title}': {e}")

        chapter_count += 1

    doc.close()

    return {"message": "Chapters successfully processed and indexed", "processed_chapters": chapter_numbers}

# GET endpoint to fetch all indexed files and their indexed chapters
@router.get("/indexed-chapters")
async def get_indexed_files():
    """
    API endpoint to get all indexed files and their indexed chapters.

    :return: List of indexed files with their chapters.
    """
    files = get_all_files()

    if not files:
        return []

    return files

# Initialize the database when the app starts
init_db()

@router.get("/toc")
async def get_pdf_toc(pdf_name="rooks 9th edition.pdf"):
    """
    API endpoint to extract and return the Table of Contents (TOC) of a PDF.
    
    :param pdf_file_path: Path to the PDF file.
    :return: JSON structure of the TOC.
    """
    pdf_file_path = os.path.expanduser(PDF_FILES_FOLDER + pdf_name)
    try:
        # Extract the TOC in JSON format
        toc = get_toc_json_from_pdf(pdf_file_path)
        
        if toc is None:
            raise HTTPException(status_code=404, detail="TOC not found in the PDF.")
        
        return {
            "status": "success",
            "toc": toc
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting TOC from PDF: {str(e)}")

# To use this router, remember to include it in your FastAPI app instance.