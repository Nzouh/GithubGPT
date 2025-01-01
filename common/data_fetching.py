import requests
import base64

def get_auth_headers(oauth_token):
    """
    Returns headers for authenticated GitHub API requests.
    """
    return {"Authorization": f"token {oauth_token}"}

def get_github_user(oauth_token):
    """
    Fetch the authenticated user's GitHub username.

    :param oauth_token: OAuth token obtained during authentication.
    :return: GitHub username (login).
    """
    url = "https://api.github.com/user"
    headers = get_auth_headers(oauth_token)
    response = requests.get(url, headers=headers)
    
    if response.status_code == 403:  # Handle rate limit exceeded
        raise Exception("Rate limit exceeded. Please try again later.")
    response.raise_for_status()  # Raise an error for bad responses
    user_data = response.json()
    return user_data["login"]

def get_repo_tree(owner, repo, branch, oauth_token, recursive=True):
    """
    Fetch the repository tree. If recursive=True, fetches all files in the repo.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive={1 if recursive else 0}"
    headers = get_auth_headers(oauth_token)
    response = requests.get(url, headers=headers)
    
    if response.status_code == 403:  # Handle rate limit exceeded
        raise Exception("Rate limit exceeded. Please try again later.")
    response.raise_for_status()
    
    return response.json().get("tree", [])

def get_file_content(owner, repo, file_path, oauth_token):
    """
    Fetch the content of a specific file.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = get_auth_headers(oauth_token)
    response = requests.get(url, headers=headers)
    
    if response.status_code == 403:  # Handle rate limit exceeded
        raise Exception("Rate limit exceeded. Please try again later.")
    response.raise_for_status()
    
    data = response.json()
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode("utf-8")
    return None

# Example usage with OAuth token
oauth_token = "client-oauth-token"  # Retrieved during login
owner = "client-username"
repo = "client-repo"
branch = "main"

try:
    # Fetch repository files
    tree = get_repo_tree(owner, repo, branch, oauth_token)
    files = [item["path"] for item in tree if item["type"] == "blob"]
    print(f"Files in the repository: {files}")
    
    # Fetch the content of the first file
    if files:
        content = get_file_content(owner, repo, files[0], oauth_token)
        print(f"Content of {files[0]}:\n{content}")
    else:
        print("No files found in the repository.")

except Exception as e:
    print(f"Error: {str(e)}")
