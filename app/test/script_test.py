import re
import fitz  # PyMuPDF
import json
import os

# Class to represent a TOC entry with hierarchical structure
class TOCNode:
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

# Method 1: Return TOC JSON from a PDF
def get_toc_json_from_pdf(pdf_file):
    """Extract the TOC from a PDF and return it as a JSON structure."""
    # Open the PDF file
    doc = fitz.open(pdf_file)

    # Extract the Table of Contents (TOC)
    toc = doc.get_toc()

    if not toc:
        print("No Table of Contents found in the PDF.")
        return None

    # The root will hold all the top-level parts
    root = []

    # Dictionary to store the last node at each level
    last_node_at_level = {}

    # Loop through the TOC entries
    for entry in toc:
        level, title, page_num = entry
        new_node = TOCNode(title, page_num)

        if level == 1:
            # If it's a part (level 1), add it directly to the root
            root.append(new_node)
            last_node_at_level[level] = new_node
        else:
            # For chapters (level 2) and subsections (level 3), find the parent
            parent_node = last_node_at_level.get(level - 1)
            if parent_node:
                parent_node.add_subsection(new_node)
                last_node_at_level[level] = new_node

    # Set the 'to' pages after processing the TOC
    set_to_pages(root, doc.page_count)

    # Convert the TOC structure to JSON and return
    toc_json = [node.to_dict() for node in root]
    return json.dumps(toc_json, indent=4)

# Function to set the "to" pages for each chapter/section based on the deepest subsection
def set_to_pages(toc_root, total_pages):
    """Assign 'to' pages for each TOC entry based on its subsections or next item."""
    
    # Recursive function to calculate the "to" page
    def calculate_to_pages(node, next_page):
        """Recursively calculate the 'to' page for each node."""
        if node.subsections:
            # If the node has subsections, the "to" page should be the "to" page of the last subsection
            last_subsection = node.subsections[-1]
            calculate_to_pages(last_subsection, next_page)
            node.set_to_page(last_subsection.to_page)
        else:
            # If no subsections, the "to" page is just before the next node or total_pages
            node.set_to_page(next_page - 1)

        # Recursively calculate for all subsections
        for i in range(len(node.subsections) - 1, -1, -1):
            current_subsection = node.subsections[i]
            next_subsection_page = node.subsections[i + 1].from_page if i + 1 < len(node.subsections) else node.to_page + 1
            calculate_to_pages(current_subsection, next_subsection_page)

    # Process the root nodes
    for i in range(len(toc_root)):
        next_part_page = toc_root[i + 1].from_page if i + 1 < len(toc_root) else total_pages + 1
        calculate_to_pages(toc_root[i], next_part_page)

# Method 2: Extract **only chapters** as PDFs
def extract_chapter_pdfs(pdf_file, num_chapters):
    """Extract chapter-wise PDFs based on the TOC and save each chapter as a separate PDF."""
    doc = fitz.open(pdf_file)
    toc_json = json.loads(get_toc_json_from_pdf(pdf_file))

    # Ensure the output directory exists
    output_dir = "chapters"
    os.makedirs(output_dir, exist_ok=True)

    chapter_count = 0

    def extract_chapters_from_toc(toc_entries):
        """Extract chapters from TOC using regex matching for 'CHAPTER XX'."""
        chapters = []
        chapter_regex = re.compile(r'^CHAPTER\s+\d+.*')  # Matches 'CHAPTER' followed by one or more spaces and digits

        for entry in toc_entries:
            # Check if the title matches the regex 'CHAPTER XX'
            if chapter_regex.match(entry['title']):
                chapters.append(entry)
            # Recursively check subsections if any
            chapters.extend(extract_chapters_from_toc(entry['subsections']))

        return chapters

    # Get only chapters
    chapters = extract_chapters_from_toc(toc_json)

    # Process the chapters up to the specified number
    for entry in chapters:
        # if chapter_count >= num_chapters:
        #     break  # Stop after extracting the specified number of chapters
        
        # Get chapter details
        chapter_title = entry['title']
        from_page = entry['from_page']
        to_page = entry['to_page']

        # Create a new PDF for this chapter
        chapter_pdf = fitz.open()

        # Add pages for this chapter from the original PDF
        for page_num in range(from_page - 1, to_page):  # Pages in PyMuPDF are zero-indexed
            chapter_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
            # Check if the chapter has 0 pages (from_page == to_page)
            
        
        # Save the chapter PDF
        sanitized_title = "".join([c for c in chapter_title if c.isalnum() or c == ' ']).rstrip()  # Sanitize title for filenames
        output_path = os.path.join(output_dir, f"{chapter_count + 1} - {sanitized_title}.pdf")
        # Check if the chapter PDF has pages before saving
        if chapter_pdf.page_count == 0:
            print(f"Chapter '{chapter_title}' could not be saved because it has zero pages.")
            chapter_pdf.close()
            continue
        chapter_pdf.save(output_path)
        chapter_pdf.close()

        print(f"Chapter {chapter_count + 1}: '{chapter_title}' saved as {output_path}")

        chapter_count += 1

    doc.close()

# Example usage
if __name__ == "__main__":
    # PDF file path you provided
    file_path = os.path.expanduser("~/backend-MR/files/rooks 9th edition.pdf")

    # Method 1: Get TOC as JSON
    toc_json = get_toc_json_from_pdf(file_path)
    if toc_json:
        print("TOC JSON:\n", toc_json)

    # Method 2: Extract first 10 chapters as individual PDFs (ignoring parts and subsections)
    num_chapters_to_extract = 150
    extract_chapter_pdfs(file_path, num_chapters_to_extract)
