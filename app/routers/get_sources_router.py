import sqlite3
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

# Assuming these models are imported from another module
from app.routers.post_sources_router import SourceSchemaOutput, SourcesInput, SourcesOutput

# Initialize the router with your specified configuration
router = APIRouter(
    prefix="/sources",  # Customize the prefix according to your API context
    tags=["source"],  # Customize the tag for grouping API routes
    responses={404: {"description": "Not found"}},  # Custom responses, if needed
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

# GET endpoint to retrieve sources
@router.get("/", response_model=SourcesOutput)
def get_sources():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, text FROM sources ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    # Convert rows to a list of SourceSchema dictionaries
    sources = [{"id": row[0], "title": row[1], "summary": row[2], "text": row[3]} for row in rows]
    return SourcesOutput(sources=sources)


# DELETE endpoint to delete a source by its ID
@router.delete("/{source_id}")
def delete_source(source_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if the record exists
    cursor.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Source with ID {source_id} not found")
    
    # Delete the record
    cursor.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    conn.commit()
    conn.close()

    return {"message": f"Source with ID {source_id} has been deleted successfully"}

# Initialize the database when the app starts
init_db()
