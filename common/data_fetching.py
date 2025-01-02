import requests
import base64

def get_auth_headers(oauth_token):
    """
    Returns headers for authenticated GitHub API requests.
    """
    return {"Authorization": f"token {oauth_token}"}

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

def fetch_coding_files(owner, repo, branch, oauth_token, extensions=None):
    """
    Fetch coding-related files (e.g., Python files, READMEs) from a GitHub repository.
    Filters files by specified extensions.

    :param owner: GitHub repo owner
    :param repo: GitHub repo name
    :param branch: Branch name
    :param oauth_token: OAuth token for authentication
    :param extensions: List of file extensions to filter, e.g., [".py", ".md"]
    :return: List of tuples containing (file_path, content)
    """
    extensions = extensions or [".py", ".md", ".txt"]  # Default extensions
    fetched_files = []

    try:
        # Fetch repository tree
        tree = get_repo_tree(owner, repo, branch, oauth_token)

        for item in tree:
            file_path = item["path"]
            file_type = item["type"]

            # Filter by file type and extension
            if file_type == "blob" and any(file_path.endswith(ext) for ext in extensions):
                print(f"Fetching content of: {file_path}")
                content = get_file_content(owner, repo, file_path, oauth_token)
                if content is not None:
                    # Prepend the file name to the content
                    marked_content = f"File Name: {file_path}\n\n{content}"
                    fetched_files.append((file_path, marked_content))
                else:
                    print(f"Failed to fetch content for {file_path}")

        return fetched_files

    except Exception as e:
        print(f"Error fetching coding files: {e}")
        return []

# Example usage
if __name__ == "__main__":
    oauth_token = "client-oauth-token"  # Replace with your actual GitHub token
    owner = "client-username"
    repo = "client-repo"
    branch = "main"

    # Specify extensions for coding-related files
    extensions = [".py", ".md", ".json", ".yaml", ".txt"]

    # Fetch coding files
    coding_files = fetch_coding_files(owner, repo, branch, oauth_token, extensions)

    # Print fetched files and their content
    for file_path, content in coding_files:
        print(f"--- {file_path} ---")
        print(content[:500])  # Print first 500 characters to avoid large outputs

