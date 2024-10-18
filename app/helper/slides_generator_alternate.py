import os
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
import json
from typing import List, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import uuid
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
SCOPES = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.path.expanduser("./helper/service_account.json")

# Configure the Google Slides API client
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
slides_service = build('slides', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)

class SlideContent(BaseModel):
    title: str
    content: List[Dict[str, Any]]

class PresentationInput(BaseModel):
    slides: List[SlideContent]

def create_slide_requests(slide_data: SlideContent, insertion_index: int = 0):
    slide_id = str(uuid.uuid4())
    return [{
        'createSlide': {
            'objectId': slide_id,
            'insertionIndex': str(insertion_index),
            'slideLayoutReference': {'predefinedLayout': 'BLANK'},
        }
    }], slide_id, slide_data.title, slide_data.content

def create_image_slide(image_url: str, index: int):
    image_slide_id = str(uuid.uuid4())  # Unique slide ID for the image slide
    image_id = str(uuid.uuid4())  # Unique image ID
    
    # Slide dimensions (Google Slides default size)
    slide_width = 720  # Points
    slide_height = 540  # Points
    
    # Assuming the image aspect ratio will be maintained, we'll set maximum dimensions for the image
    max_image_width = slide_width
    max_image_height = slide_height
    
    # Add the image to take up the entire slide, maintaining the aspect ratio
    return [{
        'createSlide': {
            'objectId': image_slide_id,
            'insertionIndex': str(index),
            'slideLayoutReference': {'predefinedLayout': 'BLANK'},
        }
    }, {
        'createImage': {
            'objectId': image_id,  # Use the unique image ID
            'url': image_url,
            'elementProperties': {
                'pageObjectId': image_slide_id,
                'size': {
                    'width': {'magnitude': max_image_width, 'unit': 'PT'},
                    'height': {'magnitude': max_image_height, 'unit': 'PT'}
                },
                'transform': {
                    'scaleX': 1,
                    'scaleY': 1,
                    'translateX': 0,  # Centering the image horizontally
                    'translateY': 0,  # Centering the image vertically
                    'unit': 'PT'
                }
            }
        }
    }], image_slide_id

def create_text_box(slide_id: str, box_id: str, text: str, x: int, y: int, width: int, height: int, 
                    font_size: int, is_title: bool = False, add_bullets: bool = False, line_spacing: float = 115):
    requests = [{
        'createShape': {
            'objectId': box_id,
            'shapeType': 'TEXT_BOX',
            'elementProperties': {
                'pageObjectId': slide_id,
                'size': {'width': {'magnitude': width, 'unit': 'PT'}, 'height': {'magnitude': height, 'unit': 'PT'}},
                'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': x, 'translateY': y, 'unit': 'PT'}
            }
        }
    }, {
        'insertText': {
            'objectId': box_id,
            'insertionIndex': 0,
            'text': text
        }
    }, {
        'updateTextStyle': {
            'objectId': box_id,
            'style': {
                'fontSize': {'magnitude': font_size, 'unit': 'PT'},
                'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}},
                'bold': is_title,
                'fontFamily': 'Arial'
            },
            'textRange': {'type': 'ALL'},
            'fields': 'fontSize,foregroundColor,bold,fontFamily'
        }
    }]
    
    # Adjust line spacing for bullet points or content
    if not is_title:
        requests.append({
            'updateParagraphStyle': {
                'objectId': box_id,
                'style': {
                    'lineSpacing': line_spacing
                },
                'textRange': {'type': 'ALL'},
                'fields': 'lineSpacing'
            }
        })
    
    # If it's not a title and bullet points are required, apply bullet formatting
    if add_bullets and not is_title:
        requests.append({
            'createParagraphBullets': {
                'objectId': box_id,
                'textRange': {'type': 'ALL'},
                'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'  # Bullet point style
            }
        })
    
    return requests

async def create_presentation(content_input: Dict[str, Any], image_urls: List[str] = None):
    try:
        logger.debug(f"Received content_input: {json.dumps(content_input, indent=2)}")
        logger.debug(f"Received image_urls: {image_urls}")

        # Ensure content_input has the correct structure
        if 'slides' not in content_input:
            if 'content' in content_input and 'slides' in content_input['content']:
                content_input = content_input['content']
            else:
                logger.error(f"Invalid content structure: {content_input}")
                raise ValueError("Invalid content structure: 'slides' not found")

        # Validate and convert the input
        try:
            presentation_data = PresentationInput(**content_input)
        except ValidationError as ve:
            logger.error(f"Validation error: {ve}")
            raise HTTPException(status_code=422, detail=f"Invalid input data: {ve}")

        presentation = slides_service.presentations().create(body={}).execute()
        presentation_id = presentation['presentationId']
        logger.debug(f"Created presentation with ID: {presentation_id}")

        # Get the title of the first slide
        first_slide_title = presentation_data.slides[0].title

        # Rename the presentation file in Google Drive
        drive_service.files().update(
            fileId=presentation_id,
            body={'name': first_slide_title}
        ).execute()

        requests = []
        slide_data = []

        # Create title slide
        title_slide_requests, title_slide_id, _, _ = create_slide_requests(presentation_data.slides[0], 0)
        requests.extend(title_slide_requests)
        slide_data.append((title_slide_id, presentation_data.slides[0].title, None, True))

        # Create content slides
        for index, content_item in enumerate(presentation_data.slides[0].content, start=1):
            slide_requests, slide_id, _, _ = create_slide_requests(SlideContent(title=content_item['heading'], content=[content_item]), index)
            requests.extend(slide_requests)
            slide_data.append((slide_id, content_item['heading'], [content_item], False))

        # Execute slide creation requests
        body = {'requests': requests}
        slides_service.presentations().batchUpdate(presentationId=presentation_id, body=body).execute()
        logger.debug(f"Created {len(slide_data)} slides")

        # Add content to slides
        content_requests = []
        for index, (slide_id, title, content, is_title_slide) in enumerate(slide_data):
            # Add background color
            content_requests.append({
                'updatePageProperties': {
                    'objectId': slide_id,
                    'pageProperties': {
                        'pageBackgroundFill': {
                            'solidFill': {'color': {'rgbColor': {'red': 0.3, 'green': 0.5, 'blue': 0.75}}}
                        }
                    },
                    'fields': 'pageBackgroundFill.solidFill.color'
                }
            })

            # Add title box
            title_box_height = 80 if is_title_slide else 50
            content_requests.extend(create_text_box(slide_id, f'title_box_{index}', title, 20, 20, 720, title_box_height, 36, True))

            if not is_title_slide and content:
                # Add bullet point content
                bullet_point_padding = 130
                content_text = "\n".join(point for item in content for point in item['bullet_points'])
                content_requests.extend(create_text_box(slide_id, f'content_box_{index}', content_text, 40, bullet_point_padding, 660, 400, 18, add_bullets=True, line_spacing=150))

            # Add footer with slide number
            content_requests.extend(create_text_box(slide_id, f'footer_text_{index}', f"Slide {index + 1} of {len(slide_data)}", 20, 500, 100, 20, 12))

        # Add image slides
        if image_urls:
            for image_url in image_urls:
                if image_url:
                    image_requests, image_slide_id = create_image_slide(image_url, len(slide_data) + 1)
                    content_requests.extend(image_requests)
                    logger.debug(f"Added image slide for URL: {image_url}")

        # Execute content update requests
        body = {'requests': content_requests}
        slides_service.presentations().batchUpdate(presentationId=presentation_id, body=body).execute()
        logger.debug("Successfully updated slides with text and images")

        # Set the presentation to be publicly accessible
        drive_service.permissions().create(
            fileId=presentation_id,
            body={'type': 'anyone', 'role': 'writer'}
        ).execute()
        logger.debug("Set presentation to be publicly accessible")

        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit?usp=sharing"

        return {
            "presentation_id": presentation_id,
            "slides_created": len(slide_data),
            "public_url": presentation_url
        }

    except HttpError as api_error:
        logger.error(f"Google Slides API error: {api_error}")
        raise HTTPException(status_code=500, detail=f"Google Slides API error: {str(api_error)}")
    except KeyError as e:
        logger.error(f"KeyError: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Missing required key in input: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))