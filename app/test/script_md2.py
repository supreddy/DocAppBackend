import fitz  # PyMuPDF
import json
import os
import re  # Import the regex module

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
    doc = fitz.open(pdf_file)
    toc = doc.get_toc()

    if not toc:
        print("No Table of Contents found in the PDF.")
        return None

    root = []
    last_node_at_level = {}

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

    set_to_pages(root, doc.page_count)

    toc_json = [node.to_dict() for node in root]
    return json.dumps(toc_json, indent=4)

# Function to set the "to" pages for each chapter/section based on the deepest subsection
def set_to_pages(toc_root, total_pages):
    """Assign 'to' pages for each TOC entry based on its subsections or next item."""
    
    def calculate_to_pages(node, next_page):
        """Recursively calculate the 'to' page for each node."""
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

# Function to extract subsections and format them as ## headers
def extract_subsections(subsections):
    subsection_titles = []
    for subsection in subsections:
        subsection_titles.append(subsection['title'].strip())
        subsection_titles.extend(extract_subsections(subsection['subsections']))  # Recursively extract nested subsections
    return subsection_titles

# Method 2: Extract chapters and save them as Markdown or PDF files
def extract_chapter(pdf_file, output_format="pdf"):
    """Extract chapter-wise content from a PDF and save each chapter as a Markdown or PDF file."""
    doc = fitz.open(pdf_file)

    # Load TOC JSON
    toc_json_str = get_toc_json_from_pdf(pdf_file)
    if not toc_json_str:
        print("Failed to extract TOC JSON.")
        return
    
    toc_json = json.loads(toc_json_str)

    # Ensure the output directory exists
    output_dir = "chapters_md" if output_format == "md" else "chapters_pdf"
    os.makedirs(output_dir, exist_ok=True)

    chapter_count = 0

    # Function to extract chapters using regex
    def extract_chapters_from_toc(toc_entries):
        chapters = []
        chapter_regex = re.compile(r'^CHAPTER\s+\d+.*')
        for entry in toc_entries:
            if chapter_regex.match(entry['title']):
                chapters.append(entry)
            chapters.extend(extract_chapters_from_toc(entry['subsections']))
        return chapters

    chapters = extract_chapters_from_toc(toc_json)

    for entry in chapters:
        chapter_title = entry['title']
        from_page = entry['from_page']
        to_page = entry['to_page']
        subsections = entry['subsections']  # Extract subsections

        print(f"Processing Chapter {chapter_count + 1}: '{chapter_title}' from page {from_page} to {to_page}...")

        if from_page > to_page:
            print(f"Invalid page range: Chapter '{chapter_title}' has from_page {from_page} > to_page {to_page}")
            continue

        if from_page < 1 or to_page > doc.page_count:
            print(f"Out of bounds: Chapter '{chapter_title}' has from_page {from_page} or to_page {to_page} outside the valid page range.")
            continue

        chapter_text = ""
        for page_num in range(from_page - 1, to_page):
            page = doc.load_page(page_num)
            chapter_text += page.get_text("text") + "\n"

        if not chapter_text.strip():
            print(f"Chapter '{chapter_title}' could not be saved because it has no text.")
            continue

        # Extract subsection titles and prepend ## to each title
        subsection_titles = extract_subsections(subsections)
        for subsection_title in subsection_titles:
            chapter_text = chapter_text.replace(subsection_title, f"## {subsection_title}")

        # Save the chapter based on the output format
        sanitized_title = "".join([c for c in chapter_title if c.isalnum() or c == ' ']).rstrip()
        if output_format == "md":
            output_md_path = os.path.join(output_dir, f"{chapter_count + 1} - {sanitized_title}.md")
            with open(output_md_path, 'w', encoding='utf-8') as md_file:
                md_file.write(f"# {chapter_title}\n\n")
                md_file.write(chapter_text)
            print(f"Chapter {chapter_count + 1}: '{chapter_title}' saved as {output_md_path}")
        else:
            chapter_pdf = fitz.open()
            for page_num in range(from_page - 1, to_page):
                chapter_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            if chapter_pdf.page_count == 0:
                print(f"Chapter '{chapter_title}' could not be saved because it has zero pages.")
                chapter_pdf.close()
                continue

            output_pdf_path = os.path.join(output_dir, f"{chapter_count + 1} - {sanitized_title}.pdf")
            chapter_pdf.save(output_pdf_path)
            chapter_pdf.close()
            print(f"Chapter {chapter_count + 1}: '{chapter_title}' saved as {output_pdf_path}")

        chapter_count += 1

    doc.close()

# Example usage
if __name__ == "__main__":
    file_path = os.path.expanduser("~/backend-MR/files/rooks 9th edition.pdf")
    output_format = "md"  # Change to "pdf" to save as PDF
    extract_chapter(file_path, output_format)
