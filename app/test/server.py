from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import uvicorn

app = FastAPI()

# Serve static files from the 'static' directory
app.mount("/home/cyrilvarghese/backend-MR/app/test/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse('index.html')

# Replace with your actual Client ID and Client Secret
CLIENT_ID = '1026739460310-455aa8bcbb3tkmbo1bavbh7e1gs4d71j.apps.googleusercontent.com'  # Replace with your Client ID
CLIENT_SECRET = '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'  # Replace with your Client Secret

@app.post("/exchange-code")
async def exchange_code(data: dict = Body(...)):
    code = data.get('code')
    code_verifier = data.get('code_verifier')
    redirect_uri = data.get('redirect_uri')
    print(code_verifier)
    print(code)
    print(redirect_uri)
    token_endpoint = 'https://oauth2.googleapis.com/token'

    payload = {
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,  # Required when using Authorization Code flow
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
        'code_verifier': code_verifier
    }

    response = requests.post(token_endpoint, data=payload)
    token_data = response.json()
    print(token_data)
    if 'access_token' in token_data:
        access_token = token_data.get('access_token')

        # Create a new presentation using the Google Slides API
        presentation_id = create_slide_presentation(access_token)

        if presentation_id:
            return {'status': 'success', 'presentation_id': presentation_id}
        else:
            return JSONResponse(status_code=500, content={'status': 'error', 'message': 'Failed to create presentation'})
    else:
        return JSONResponse(status_code=400, content={'status': 'error', 'message': 'Failed to exchange code'})

def create_slide_presentation(access_token):
    try:
        credentials = Credentials(token=access_token)
        service = build('slides', 'v1', credentials=credentials)

        presentation = {
            'title': 'New Presentation from OAuth Demo'
        }

        presentation = service.presentations().create(body=presentation).execute()
        print('Created presentation with ID: {0}'.format(presentation.get('presentationId')))
        return presentation.get('presentationId')
    except Exception as e:
        print('An error occurred: %s' % e)
        return None

if __name__ == '__main__':
    # Start the server using uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)
