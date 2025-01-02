from dotenv import load_dotenv
import os
import requests
import urllib.parse

# Load environment variables
load_dotenv()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
GITHUB_REDIRECT_URI = GITHUB_REDIRECT_URI.rstrip('\\').strip()

def get_github_auth_url():

    """
    Generate GitHub OAuth authorization URL.
    """
    base_url = "https://github.com/login/oauth/authorize"
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "repo",
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def get_access_token(code):
    """
    Exchange authorization code for an access token.
    """
    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_REDIRECT_URI,
    }
    response = requests.post(token_url, headers=headers, data=data)
    response.raise_for_status()
    return response.json().get("access_token")
