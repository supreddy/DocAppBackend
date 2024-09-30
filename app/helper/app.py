import json
import os
import webbrowser
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import uuid

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/presentations']

def create_title_slide(service, presentation_id, title):
    title_id = f'title_{uuid.uuid4().hex}'
    
    requests = [
        {
            'createSlide': {
                'slideLayoutReference': {
                    'predefinedLayout': 'TITLE'
                },
                'placeholderIdMappings': [
                    {
                        'layoutPlaceholder': {
                            'type': 'CENTERED_TITLE'
                        },
                        'objectId': title_id
                    }
                ]
            }
        }
    ]

    response = service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()

    requests = [
        {
            'insertText': {
                'objectId': title_id,
                'text': title
            }
        }
    ]

    service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()

def create_content_slide(service, presentation_id, title, bullet_points):
    title_id = f'title_{uuid.uuid4().hex}'
    body_id = f'body_{uuid.uuid4().hex}'
    
    requests = [
        {
            'createSlide': {
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
        }
    ]

    response = service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()

    requests = [
        {
            'insertText': {
                'objectId': title_id,
                'text': title
            }
        },
        {
            'insertText': {
                'objectId': body_id,
                'text': '\n'.join(f'• {point}' for point in bullet_points)
            }
        }
    ]

    service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()

def main():
    filePath= os.path.expanduser("~/backend-MR/app/helper/credentials.json")
    filePath2= os.path.expanduser("~/backend-MR/app/helper/input.json")
    chrome_path = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
    webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
    creds = None
    flow = InstalledAppFlow.from_client_secrets_file(filePath, SCOPES)
    creds = flow.run_local_server(port=0,browser='chrome')

  
    service = build('slides', 'v1', credentials=creds)

    # Load and parse the JSON data
    with open(filePath2, 'r') as f:
        data = json.load(f)

    # Create a new presentation
    presentation = service.presentations().create(body={'title': data['title']}).execute()
    presentation_id = presentation['presentationId']

    # Create title slide
    create_title_slide(service, presentation_id, data['title'])

    # Create content slides
    for slide in data['content']:
        create_content_slide(service, presentation_id, slide['heading'], slide['bullet_points'])

    print(f'Presentation created: https://docs.google.com/presentation/d/{presentation_id}')

if __name__ == '__main__':
    main()