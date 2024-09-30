import sqlite3
from typing import List

# Database file
DATABASE = "./test.db"

def init_db():
    """
    Initialize the database and create the 'indexed_files' table if it doesn't exist.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create a table to track indexed files and chapters
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indexed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL UNIQUE,
            indexed_chapters TEXT,  -- Comma-separated list of indexed chapter numbers
            chapter_names TEXT      -- Comma-separated list of indexed chapter names
        )
    ''')
    
    conn.commit()
    conn.close()

def add_or_update_file(file_name: str, chapter_numbers: List[int] = None, chapter_names: List[str] = None):
    """
    Add or update the file entry in the database with indexed chapters and chapter names.

    If the file already exists, append new chapters and chapter names to the existing ones.
    If the file doesn't exist, insert a new entry.

    If chapter_numbers is None, set 'indexed_chapters' to 'all'.
    
    :param file_name: Name of the file.
    :param chapter_numbers: List of chapters that were indexed. If None, set to 'all'.
    :param chapter_names: List of chapter names corresponding to the chapters.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if the file already exists
    cursor.execute('SELECT indexed_chapters, chapter_names FROM indexed_files WHERE file_name = ?', (file_name,))
    result = cursor.fetchone()

    if chapter_numbers is None:
        # If chapter_numbers is None, set indexed_chapters to 'all'
        chapters_str = "all"
    else:
        # Convert chapter numbers to a comma-separated string
        chapters_str = ",".join(map(str, chapter_numbers))

    if result:
        # File exists, update the indexed chapters and names
        existing_chapters = result[0].split(",") if result[0] != "all" else ["all"]
        existing_names = result[1].split(",") if result[1] else []
        
        # Merge new chapters and names with existing ones
        if "all" in existing_chapters:
            updated_chapters = ["all"]  # Keep 'all' as the only chapter
        else:
            updated_chapters = sorted(set(existing_chapters + list(map(str, chapter_numbers or []))))
        
        updated_chapter_names = sorted(set(existing_names + (chapter_names or [])))

        updated_chapters_str = ",".join(updated_chapters)
        updated_chapter_names_str = ",".join(updated_chapter_names)

        cursor.execute('''
            UPDATE indexed_files 
            SET indexed_chapters = ?, chapter_names = ? 
            WHERE file_name = ?
        ''', (updated_chapters_str, updated_chapter_names_str, file_name))
    else:
        # File doesn't exist, insert new record
        chapter_names_str = ",".join(chapter_names or [])

        cursor.execute('''
            INSERT INTO indexed_files (file_name, indexed_chapters, chapter_names)
            VALUES (?, ?, ?)
        ''', (file_name, chapters_str, chapter_names_str))

    conn.commit()
    conn.close()


def get_all_files():
    """
    Retrieve all files and their indexed chapters and names from the database.

    :return: List of dictionaries containing file names, indexed chapters, and chapter names.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_name, indexed_chapters, chapter_names FROM indexed_files')
    files = cursor.fetchall()

    conn.close()

    if not files:
        return []

    return [{"file_name": file[0], "indexed_chapters": file[1].split(","), "chapter_names": file[2].split(",")} for file in files]
