import sqlite3
from fastapi import FastAPI, APIRouter, HTTPException, WebSocket
from pydantic import BaseModel, HttpUrl
from typing import List

from app.indexers.file_processor_with_indexing import process_text_and_index

# Initialize the router with your specified configuration
router = APIRouter(
    prefix="/post-sources",
    tags=["source"],
    responses={404: {"description": "Not found"}},
)

# Database file
DATABASE = "./test.db"

# Initialize the database and create the table if it doesn't exist
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Modify the table structure to add 'type' column if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            summary TEXT,
            type TEXT  -- New column to store the file type (e.g., image, text, link)
        )
    ''')
     
    conn.commit()
    conn.close()

# Function to add or update sources in the database
def add_source_to_db(title: str, summary: str, text: str, source_type: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO sources (title, summary, text, type)
            VALUES (?, ?, ?, ?)
        ''', (title, summary, text, source_type))
        conn.commit()
    finally:
        conn.close()

# Pydantic model to validate the request body
class SourceSchema(BaseModel):
    title: str
    summary: str = None
    text: str = None  # New field to accept the block of text
    type: str

class SourceSchemaOutput(BaseModel):
    id: int
    type: str
    title: str
    summary: str = None
    text: str = None  # New field to output the block of text

class SourcesInput(BaseModel):
    sources: List[SourceSchema]

class SourcesOutput(BaseModel):
    sources: List[SourceSchemaOutput]

# API endpoint to add sources
@router.post("/")
def add_sources(input_data: SourcesInput):
    sources = input_data.sources
    for source in sources:
        add_source_to_db(
            title=str(source.title),
            summary=source.summary,
            text=source.text,
            source_type=source.type  # Pass the type here
        )
        
        # Only call process_text_and_index if type is not 'image'
        if source.type.lower() != "image":
            process_text_and_index(source.text, source.title)
    
    return {"status": "Sources added successfully"}

# Initialize the database when the app starts
init_db()
