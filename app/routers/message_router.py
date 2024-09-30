from fastapi import APIRouter, Form, HTTPException
from typing import List

from fastapi.responses import JSONResponse
from app.routers.get_LLM_result import process_files_with_instruction

# Initialize the router
router = APIRouter(
    prefix="/post-message",
    tags=["message"],
    responses={404: {"description": "Not found"}},
)

@router.post("/")
async def post_message(
    file_names: List[str] = Form(...),  # Accept a list of file names
    message: str = Form(...)
):
    try:
        # # Call the get_template_json with the filenames and message
        # json_resp = get_template_json(file_names, message)
        # response_data = {
        #     "original_message": message,
        #     "uploaded_filenames": file_names,
        #     "data": json_resp
        # }
        # return JSONResponse(content=response_data)
        return "api called"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message with LLM: {str(e)}")

@router.get("/")
async def get_message():
    return {"message": "GET Message route"}
