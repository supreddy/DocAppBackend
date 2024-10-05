from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import fitz  # PyMuPDF
import json
import os
from app.indexers.file_processor_with_indexing import process_text_and_index  # Importing the indexing function
from pydantic import BaseModel
from typing import Optional

from app.indexers.update_indexed_files import add_or_update_file, get_all_files, init_db
from config import PDF_FILES_FOLDER
 

# Initialize the router
router = APIRouter(
    prefix="/process-pdf",
    tags=["PDF Processing"],
    responses={404: {"description": "Not found"}},
)


# Initialize the database when the app starts
init_db()
 
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
    :return: JSON string of the TOC or None if an error occurs.
    """
    try:
        doc = fitz.open(pdf_file)
    except fitz.FileDataError as e:
        print(f"MuPDF error while opening PDF: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error opening PDF: {e}")
        return None

    try:
        toc = doc.get_toc()
    except fitz.FileDataError as e:
        print(f"MuPDF error while getting TOC: {e}")
        doc.close()
        return None
    except Exception as e:
        print(f"Unexpected error getting TOC: {e}")
        doc.close()
        return None

    if not toc:
        print("No TOC found in the PDF")
        doc.close()
        return None

    root = []
    last_node_at_level = {}

    try:
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
    except Exception as e:
        print(f"Error processing TOC: {e}")
        doc.close()
        return None

    doc.close()
    return json.dumps(toc_json)  # Convert the list to a JSON string
   

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




# Define the Pydantic model with default values
class PDFProcessingRequest(BaseModel):
    pdf_name: str = "rooks 9th edition.pdf"  # Default file name

def process_pdf_chunk(pdf_file: str, start_page: int, end_page: int, chunk_size: int = 50) -> Optional[bool]:
    """Process a chunk of pages from the PDF."""
    doc = None
    try:
        doc = fitz.open(pdf_file)
        total_pages = min(end_page, doc.page_count)
        
        chunk_text = ""
        for page_num in range(start_page, total_pages):
            page = doc.load_page(page_num)
            chunk_text += page.get_text("text") + "\n"
        
        if chunk_text.strip():
            chunk_title = f"Pages {start_page+1}-{total_pages}"
            metadata = {
                "pdf_name": os.path.basename(pdf_file),
                "start_page": start_page + 1,
                "end_page": total_pages,
                "total_pages": doc.page_count
            }
            response = process_text_and_index(chunk_text, source_id=chunk_title, file_name=os.path.basename(pdf_file), metadata=metadata)
            return response is not None
        return True
    except Exception as e:
        print(f"Error processing PDF chunk (pages {start_page+1}-{end_page}): {str(e)}")
        return False
    finally:
        if doc:
            doc.close()


def process_whole_book(pdf_file: str) -> bool:
    """Process the entire book in chunks."""
    try:
        with fitz.open(pdf_file) as doc:
            total_pages = doc.page_count

        chunk_size = 50  # Adjust this based on your needs and memory constraints
        successful_chunks = 0
        total_chunks = (total_pages + chunk_size - 1) // chunk_size

        for start_page in range(0, total_pages, chunk_size):
            end_page = min(start_page + chunk_size, total_pages)
            success = process_pdf_chunk(pdf_file, start_page, end_page, chunk_size)
            if success:
                successful_chunks += 1
            else:
                print(f"Failed to process chunk starting at page {start_page}")

        # Update the indexed files record
        add_or_update_file(os.path.basename(pdf_file), list(range(1, total_pages + 1)), ["Whole Book"])

        print(f"Processed {successful_chunks} out of {total_chunks} chunks successfully.")
        return successful_chunks == total_chunks
    except Exception as e:
        print(f"Error processing whole book: {str(e)}")
        return False
    

@router.post("/whole-book")
async def process_whole_pdf(request: PDFProcessingRequest, background_tasks: BackgroundTasks):
    """
    API endpoint to process and index an entire PDF book.

    :param request: Request body containing PDF file name.
    :param background_tasks: FastAPI BackgroundTasks for asynchronous processing.
    :return: Status message.
    """
    pdf_file = os.path.expanduser(os.path.join(PDF_FILES_FOLDER, request.pdf_name))
    
    if not os.path.exists(pdf_file):
        raise HTTPException(status_code=404, detail="PDF file not found.")

    # Start processing in the background
    background_tasks.add_task(process_whole_book, pdf_file)

    return {
        "message": "PDF processing started in the background.",
        "pdf_name": request.pdf_name
    }



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
        
        # Send a json back
        toc_object = json.loads(toc)
        
        return {
            "status": "success",
            "toc": toc_object
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Error decoding TOC JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting TOC from PDF: {str(e)}")