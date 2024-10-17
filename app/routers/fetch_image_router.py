import aiohttp
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/fetch-image/")
async def fetch_image(image_url: str):
    """
    Fetches an image from the provided URL and streams it back to the frontend.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status == 200:
                return StreamingResponse(response.content, media_type=response.headers['Content-Type'])
            else:
                raise HTTPException(status_code=404, detail="Image not found or URL blocked by CORS.")
