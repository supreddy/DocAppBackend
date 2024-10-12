# slides_generator.py
import os
from fastapi import  HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
import uuid



# Configure the Google Slides API client
SCOPES = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']
# SERVICE_ACCOUNT_FILE = './helper/service_account.json'
SERVICE_ACCOUNT_FILE = os.path.expanduser("~/DocAppBackend/app/helper/service_account.json") 

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
slides_service = build('slides', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)

def create_slide_requests(slide_data):
    slide_id = str(uuid.uuid4())
    title_id = str(uuid.uuid4())
    body_id = str(uuid.uuid4())

    requests = [
        {
            'createSlide': {
                'objectId': slide_id,
                'insertionIndex': '1',
                'slideLayoutReference': {
                    'predefinedLayout': 'TITLE_AND_BODY'
                },
                'placeholderIdMappings': [
                    {
                        'layoutPlaceholder': {
                            'type': 'TITLE'
                        },
                        'objectId': title_id
                    },
                    {
                        'layoutPlaceholder': {
                            'type': 'BODY'
                        },
                        'objectId': body_id
                    }
                ]
            }
        },
        {
            'insertText': {
                'objectId': title_id,
                'insertionIndex': 0,
                'text': slide_data['title']
            }
        }
    ]

    content_text = ""
    for item in slide_data['content']:
        content_text += f"{item['heading']}\n"
        for point in item['bullet_points']:
            content_text += f"• {point}\n"
        content_text += "\n"

    requests.append({
        'insertText': {
            'objectId': body_id,
            'insertionIndex': 0,
            'text': content_text
        }
    })

    return requests

async def create_presentation(content_input: Dict[str, Any]):
    try:
        # Create a new presentation
        presentation = slides_service.presentations().create(body={}).execute()
        presentation_id = presentation['presentationId']

        # Create requests for all slides
        requests = []
        for index, slide in enumerate(content_input['slides']):
            requests.extend(create_slide_requests(slide))

        # Execute the requests
        body = {'requests': requests}
        response = slides_service.presentations().batchUpdate(
            presentationId=presentation_id, body=body).execute()

        # Set the presentation to be publicly accessible
        drive_service.permissions().create(
            fileId=presentation_id,
            body={
                'type': 'anyone',
                'role': 'reader'
            }
        ).execute()

        # Get the presentation URL
        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit?usp=sharing"

        return {
            "presentation_id": presentation_id, 
            "slides_created": len(content_input['slides']),
            "public_url": presentation_url
        }

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required key in input: {str(e)}")
    except Exception as e:
        print("error ", e)
        raise HTTPException(status_code=500, detail=str(e))

