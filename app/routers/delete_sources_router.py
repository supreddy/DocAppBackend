# Initialize the router with your specified configuration
import sqlite3
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List

from app.routers.post_sources_router import SourcesInput



router = APIRouter(
    prefix="/delete-sources",  # Customize the prefix according to your API context
    tags=["source"],  # Customize the tag for grouping API routes
    responses={404: {"description": "Not found"}},  # Custom responses, if needed
)

# Database file
DATABASE = "./test.db"

 # DELETE endpoint to remove all sources from the database
@router.delete("/")
def delete_sources():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sources")
    conn.commit()
    conn.close()
    return {"status": "All sources deleted successfully"}
 
 