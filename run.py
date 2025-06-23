import uvicorn
import os
from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()
    DROPBOX_APP_KEY = os.getenv('DROPBOX_APP_KEY')
    DROPBOX_APP_SECRET = os.getenv('DROPBOX_APP_SECRET')
    DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')

    if DROPBOX_APP_KEY is None:
        DROPBOX_APP_KEY = input('Input your dropbox app key')

    if DROPBOX_APP_SECRET is None:
        DROPBOX_APP_SECRET = input('Input your dropbox app secret')
    uvicorn.run("backend.main:app", host="localhost", port=8000, reload=True)
