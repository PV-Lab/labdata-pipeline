import dropbox.exceptions
import uvicorn
import os
from dotenv import load_dotenv

import http.server
import socketserver
import webbrowser
import urllib.parse
import requests
import dropbox

def generate_refresh_token():
    REDIRECT_URI = "http://localhost:8080"
    SCOPES = "account_info.read files.content.write files.content.read"

    # Step 1: Direct user to auth URL
    params = {
        "response_type": "code",
        "client_id": APP_KEY,
        "redirect_uri": REDIRECT_URI,
        "token_access_type": "offline",
        "scope": SCOPES
    }
    auth_url = f"https://www.dropbox.com/oauth2/authorize?{urllib.parse.urlencode(params)}"
    print("Opening browser for authorization...")
    webbrowser.open(auth_url)

    # Step 2: Wait for redirect with code
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            code = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('code')
            if code:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"You can close this window now.")
                self.server.code = code[0]

    with socketserver.TCPServer(("localhost", 8080), Handler) as httpd:
        print("Waiting for Dropbox auth response...")
        httpd.handle_request()
        auth_code = httpd.code

    # Step 3: Exchange code for refresh token
    response = requests.post("https://api.dropbox.com/oauth2/token", data={
        "code": auth_code,
        "grant_type": "authorization_code",
        "client_id": APP_KEY,
        "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI
    })
    response.raise_for_status()
    tokens = response.json()
    return tokens["refresh_token"]


def main():
    global APP_KEY, APP_SECRET, REFRESH_TOKEN, CHEMICALS_API_KEY
    while True:
        try:
            invalid_input = (not APP_KEY) or (not APP_SECRET) or (not REFRESH_TOKEN)
            if invalid_input:
                raise dropbox.exceptions.AuthError(1, 'Missing Dropbox API keys ...')
            dbx = dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN)
            dbx.users_get_current_account()
            break
        except requests.exceptions.ConnectionError as e:
            print(f"No internet connection!!!!")
            return
        except (dropbox.exceptions.AuthError, dropbox.exceptions.BadInputError) as e:
            print('Dropbox Authentification Keys missing/invalid ...')
            APP_KEY = input('Input your dropbox app key: ').strip()

            APP_SECRET = input('Input your dropbox app secret: ').strip()

            while True:
                answer = input('I have a valid refresh token (Enter 1)/ I want to generate a new refresh token (Enter 0): ').strip()
                if answer == '0':
                    REFRESH_TOKEN = generate_refresh_token()
                    break
                elif answer == '1':
                    REFRESH_TOKEN = input('Input your refresh token: ').strip()
                    break
        except Exception as e:
            print('Unexpected error: ', e)
            return

    if CHEMICALS_API_KEY is None:
        CHEMICALS_API_KEY = input('Input the chemical inventory API key: ').strip()

    with open('.env', 'w') as f:
        f.write(f"DROPBOX_APP_KEY = '{APP_KEY}'\n")
        f.write(f"DROPBOX_APP_SECRET = '{APP_SECRET}'\n")
        f.write(f"DROPBOX_REFRESH_TOKEN = '{REFRESH_TOKEN}'\n")
        f.write(f"CHEMICALS_API_KEY = '{CHEMICALS_API_KEY}'\n")
    uvicorn.run("backend.main:app", host="localhost", port=8000, reload=True)

if __name__ == '__main__':
    load_dotenv()
    APP_KEY = os.getenv('DROPBOX_APP_KEY')
    APP_SECRET = os.getenv('DROPBOX_APP_SECRET')
    REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
    CHEMICALS_API_KEY = os.getenv('CHEMICALS_API_KEY')
    main()
