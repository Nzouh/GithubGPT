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

    if response.status_code == 403:
        raise Exception("Rate limit exceeded or insufficient permissions. Check your token and scopes.")
    if response.status_code == 404:
        raise Exception(f"Branch '{branch}' not found in repository '{owner}/{repo}'. Check the branch name.")
    response.raise_for_status()

    tree = response.json().get("tree", [])
    if not tree:
        raise Exception(f"No files found in the repository '{owner}/{repo}' on branch '{branch}'.")
    
    print(f"Fetched repository tree with {len(tree)} items.")  # Debugging
    return tree

def get_file_content(owner, repo, file_path, oauth_token):
    """
    Fetch the content of a specific file.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = get_auth_headers(oauth_token)
    response = requests.get(url, headers=headers)

    if response.status_code == 403:
        raise Exception("Rate limit exceeded or insufficient permissions. Check your token and scopes.")
    if response.status_code == 404:
        raise Exception(f"File '{file_path}' not found in repository '{owner}/{repo}'. Check the file path.")
    response.raise_for_status()

    data = response.json()
    if data.get("encoding") == "base64":
        try:
            return base64.b64decode(data["content"]).decode("utf-8")
        except Exception as e:
            raise Exception(f"Error decoding content for file '{file_path}': {e}")
    else:
        print(f"File '{file_path}' does not have Base64 encoding. Skipping.")  # Debugging

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
    extensions = extensions or [".py", ".md", ".txt", ".json", ".yaml", ".java", ".js", ".html", ".css"]
    fetched_files = []

    try:
        # Fetch repository tree
        tree = get_repo_tree(owner, repo, branch, oauth_token)

        for item in tree:
            file_path = item["path"]
            file_type = item["type"]

            # Filter by file type and extension
            if file_type == "blob" and any(file_path.endswith(ext) for ext in extensions):
                print(f"Fetching content of: {file_path}")  # Debugging
                content = get_file_content(owner, repo, file_path, oauth_token)
                if content is not None:
                    # Prepend the file name and path to the content
                    marked_content = f"File: {file_path}\n\n{content}"
                    fetched_files.append((file_path, marked_content))
                else:
                    print(f"Content not fetched or empty for file: {file_path}")

        if not fetched_files:
            print("No files matching the specified extensions were found.")
        
        return fetched_files

    except Exception as e:
        print(f"Error fetching coding files: {e}")
        return []
