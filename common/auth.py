from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI')

# Test the values
print("Client ID:", GITHUB_CLIENT_ID)
print("Client Secret:", GITHUB_CLIENT_SECRET)
print("Redirect URI:", GITHUB_REDIRECT_URI)
