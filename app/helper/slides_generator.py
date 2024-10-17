# slides_generator.py
import os
from fastapi import  HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import textwrap
import uuid

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure the Google Slides API client
SCOPES = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']
# SERVICE_ACCOUNT_FILE = './helper/service_account.json'
SERVICE_ACCOUNT_FILE = os.path.expanduser("./helper/service_account.json") 

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
slides_service = build('slides', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)


def create_slide_requests(slide_data, insertion_index=0):
    slide_id = str(uuid.uuid4())
    
    requests = [
        {
            'createSlide': {
                'objectId': slide_id,
                'insertionIndex': str(insertion_index),
                'slideLayoutReference': {
                    'predefinedLayout': 'TITLE_AND_BODY'
                },
            }
        }
    ]

    return requests, slide_id, slide_data['title'], slide_data['content']

def split_content(content, max_chars_per_slide=250):
    slides = []
    current_slide = []
    current_char_count = 0

    for item in content:
        item_text = item['heading'] + '\n' + '\n'.join(f"• {point}" for point in item['bullet_points'])
        item_length = len(item_text)

        if current_char_count + item_length > max_chars_per_slide and current_slide:
            slides.append(current_slide)
            current_slide = []
            current_char_count = 0

        current_slide.append(item)
        current_char_count += item_length

    if current_slide:
        slides.append(current_slide)

    return slides



async def create_presentation(content_input: Dict[str, Any], image_urls: List[str]):
    try:
        logger.debug(f"Received image_urls: {image_urls}")
        logger.debug(f"Received content_input: {content_input}")
        
        presentation = slides_service.presentations().create(body={}).execute()
        presentation_id = presentation['presentationId']
        logger.debug(f"Created presentation with ID: {presentation_id}")

        requests = []
        slide_data = []
        
        # Create title slide
        title_slide_requests, title_slide_id, _, _ = create_slide_requests({'title': content_input['slides'][0]['title'], 'content': []}, 0)
        requests.extend(title_slide_requests)
        slide_data.append((title_slide_id, content_input['slides'][0]['title'], None))

        # Create a slide for each heading
        for index, content_item in enumerate(content_input['slides'][0]['content'], start=1):
            slide_requests, slide_id, _, _ = create_slide_requests({'title': content_item['heading'], 'content': [content_item]}, index)
            requests.extend(slide_requests)
            slide_data.append((slide_id, content_item['heading'], [content_item]))

        # Execute the requests to create slides
        try:
            body = {'requests': requests}
            response = slides_service.presentations().batchUpdate(
                presentationId=presentation_id, body=body).execute()
            logger.debug(f"Created {len(slide_data)} slides")
        except HttpError as api_error:
            logger.error(f"Google Slides API error: {api_error}")
            logger.error(f"Error details: {api_error.error_details}")
            raise HTTPException(status_code=500, detail=f"Google Slides API error: {str(api_error)}")

        # Update text and add images
        text_requests = []
        image_requests = []
        for index, (slide_id, title, content) in enumerate(slide_data):
            logger.debug(f"Processing slide {index + 1} with ID: {slide_id}")
            
            # Get the slide
            slide = slides_service.presentations().pages().get(
                presentationId=presentation_id,
                pageObjectId=slide_id
            ).execute()

            # Find the title and body placeholders
            title_id = None
            body_id = None
            for element in slide.get('pageElements', []):
                if element['shape']['shapeType'] == 'TEXT_BOX':
                    if element['shape']['placeholder']['type'] == 'TITLE':
                        title_id = element['objectId']
                    elif element['shape']['placeholder']['type'] == 'BODY':
                        body_id = element['objectId']
            
            logger.debug(f"Title ID: {title_id}, Body ID: {body_id}")

            # Add requests to update text
            if title_id:
                text_requests.extend([
                    {
                        'insertText': {
                            'objectId': title_id,
                            'insertionIndex': 0,
                            'text': title
                        }
                    },
                    {
                        'updateTextStyle': {
                            'objectId': title_id,
                            'style': {
                                'fontSize': {'magnitude': 24, 'unit': 'PT'},
                                'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2}}},
                                'bold': True
                            },
                            'textRange': {'type': 'ALL'},
                            'fields': 'fontSize,foregroundColor,bold'
                        }
                    },
                    {
                        'updateShapeProperties': {
                            'objectId': title_id,
                            'shapeProperties': {
                                'shapeBackgroundFill': {
                                    'solidFill': {
                                        'color': {
                                            'rgbColor': {'red': 0.9, 'green': 0.9, 'blue': 1}
                                        }
                                    }
                                }
                            },
                            'fields': 'shapeBackgroundFill.solidFill.color'
                        }
                    }
                ])
                logger.debug(f"Added title: {title}")

            if body_id and content:
                content_text = ""
                for point in content[0]['bullet_points']:
                    content_text += f"• {point}\n"

                text_requests.extend([
                    {
                        'insertText': {
                            'objectId': body_id,
                            'insertionIndex': 0,
                            'text': content_text.strip()
                        }
                    },
                    {
                        'updateTextStyle': {
                            'objectId': body_id,
                            'style': {
                                'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}},
                                'fontSize': {'magnitude': 14, 'unit': 'PT'}
                            },
                            'textRange': {'type': 'ALL'},
                            'fields': 'foregroundColor,fontSize'
                        }
                    },
                    {
                        'updateShapeProperties': {
                            'objectId': body_id,
                            'shapeProperties': {
                                'shapeBackgroundFill': {
                                    'solidFill': {
                                        'color': {
                                            'rgbColor': {'red': 0, 'green': 0, 'blue': 0.8}
                                        }
                                    }
                                }
                            },
                            'fields': 'shapeBackgroundFill.solidFill.color'
                        }
                    }
                ])
                logger.debug(f"Added content: {content_text[:100]}...")

            # Add image if available
            if index > 0 and (index - 1) < len(image_urls) and image_urls[index - 1]:
                image_id = f'image_{index - 1}'
                image_requests.extend([
                    {
                        'createImage': {
                            'objectId': image_id,
                            'url': image_urls[index - 1],
                            'elementProperties': {
                                'pageObjectId': slide_id,
                                'size': {
                                    'width': {'magnitude': 300, 'unit': 'PT'},
                                    'height': {'magnitude': 200, 'unit': 'PT'}
                                },
                                'transform': {
                                    'scaleX': 1,
                                    'scaleY': 1,
                                    'translateX': 400,  # Right-aligned (720 - 300 - 20)
                                    'translateY': 140,  # Centered vertically
                                    'unit': 'PT'
                                }
                            }
                        }
                    },
                    {
                        'updatePageElementTransform': {
                            'objectId': body_id,
                            'applyMode': 'ABSOLUTE',
                            'transform': {
                                'scaleX': 0.5,  # Scale text box to half width
                                'scaleY': 1,
                                'translateX': 20,
                                'translateY': 140,
                                'unit': 'PT'
                            }
                        }
                    }
                ])
                logger.debug(f"Added image: {image_urls[index - 1]}")

        # Execute text update and image insertion requests
        all_requests = text_requests + image_requests
        if all_requests:
            try:
                body = {'requests': all_requests}
                response = slides_service.presentations().batchUpdate(
                    presentationId=presentation_id, body=body).execute()
                logger.debug("Successfully updated slides with text and images")
            except HttpError as api_error:
                logger.error(f"Google Slides API error during content update: {api_error}")
                logger.error(f"Error details: {api_error.error_details}")
                raise HTTPException(status_code=500, detail=f"Google Slides API error during content update: {str(api_error)}")

        # Set the presentation to be publicly accessible
        drive_service.permissions().create(
            fileId=presentation_id,
            body={
                'type': 'anyone',
                'role': 'reader'
            }
        ).execute()
        logger.debug("Set presentation to be publicly accessible")

        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit?usp=sharing"

        return {
            "presentation_id": presentation_id, 
            "slides_created": len(slide_data),
            "images_added": len([url for url in image_urls if url]),
            "public_url": presentation_url
        }

    except KeyError as e:
        logger.error(f"KeyError: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Missing required key in input: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))