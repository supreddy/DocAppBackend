import sqlite3
from fastapi import FastAPI, APIRouter, HTTPException,WebSocket
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            summary TEXT,
            text TEXT  -- New column to store the block of text
        )
    ''')
    conn.commit()
    conn.close()

# Function to add sources to the database
def add_source_to_db(title: str, summary: str, text: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO sources (title, summary, text)
            VALUES (?, ?, ?)
        ''', (title, summary, text))
        conn.commit()
    finally:
        conn.close()

class SourceSchema(BaseModel):
    title: str
    summary: str = None
    text: str = None  # New field to accept the block of text

class SourceSchemaOutput(BaseModel):
    id: int
    title: str
    summary: str = None
    text: str = None  # New field to output the block of text

class SourcesInput(BaseModel):
    sources: List[SourceSchema]

class SourcesOutput(BaseModel):
    sources: List[SourceSchemaOutput]

@router.post("/")
def add_sources(input_data: SourcesInput):
    sources = input_data.sources
    for source in sources:
        add_source_to_db(title=str(source.title), summary=source.summary, text=source.text)
        process_text_and_index(source.text,source.title)    
    return {"status": "Sources added successfully "}



# Initialize the database when the app starts
init_db()