import requests
import base64
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()

# Sanitize environment variables
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "").strip()
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "").rstrip('/').strip()
PINECONE_KEY = os.getenv("PINECONE_KEY", "").strip()
PINECONE_INDEX_HOST = os.getenv("PINECONE_INDEX_HOST", "").rstrip('/').strip()
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY", "").strip()

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

def parse_github_url(url):
    """
    Parse a GitHub repository URL and extract the owner and repo.
    """
    import re
    pattern = r"https://github\.com/([^/]+)/([^/]+)"
    match = re.match(pattern, url)
    if match:
        owner = match.group(1)
        repo = match.group(2).rstrip(".git")  # Remove ".git" if present
        return owner, repo
    return None, None

def fetch_pull_requests(owner, repo, oauth_token):
    """
    Fetch all open pull requests for a repository.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {oauth_token.strip()}"
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"GitHub API error: {response.json().get('message')}")

    return [
        {"number": pr["number"], "title": pr["title"], "user": pr["user"]["login"]}
        for pr in response.json()
    ]

import base64

def fetch_full_file_content(owner, repo, file_path, oauth_token):
    """
    Fetch the full content of a file in the repository.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {oauth_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        # File not found; log the error and return an empty string
        print(f"File not found: {file_path}")
        return None

    if response.status_code != 200:
        raise Exception(f"Error fetching file {file_path}: {response.json().get('message')}")

    file_content = base64.b64decode(response.json()["content"]).decode("utf-8")
    return file_content


def fetch_pull_request_details(owner, repo, pr_number, oauth_token):
    """
    Fetch detailed information about a specific pull request, including diffs and full file content.
    """
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {oauth_token}"}
    
    # Fetch pull request details
    pr_response = requests.get(pr_url, headers=headers)
    if pr_response.status_code != 200:
        raise Exception(f"GitHub API error: {pr_response.json().get('message')}")

    pr_data = pr_response.json()

    # Fetch modified files in the pull request
    files_url = pr_data["url"] + "/files"
    files_response = requests.get(files_url, headers=headers)
    if files_response.status_code != 200:
        raise Exception(f"GitHub API error: {files_response.json().get('message')}")

    files_data = files_response.json()

    # Fetch full content for each modified file
    for file in files_data:
        file_path = file["filename"]
        file["full_content"] = fetch_full_file_content(owner, repo, file_path, oauth_token)

    pr_data["files"] = files_data
    return pr_data

import re

def extract_referenced_files(file_content):
    """
    Parse the file content to extract referenced files (e.g., imports).
    """
    # Match common import patterns (Python-specific)
    matches = re.findall(r"from\s+([a-zA-Z0-9_\.]+)\s+import|import\s+([a-zA-Z0-9_\.]+)", file_content)
    referenced_files = set(match[0] or match[1] for match in matches if match)
    return referenced_files



from langchain_community.llms import OpenAI

def analyze_code_changes(files, owner, repo, oauth_token):
    """
    Analyze code changes using OpenAI, combining diffs and full file content.
    """
    openai = OpenAI(api_key=OPEN_AI_KEY)
    results = []

    for file in files:
        filename = file["filename"]
        full_content = file.get("full_content", "")
        changes = file.get("patch", "")

        if not full_content:
            print(f"Skipping {filename} due to missing content.")
            continue

        prompt = f"""
        You are a senior software engineer analyzing a pull request in a GitHub repository.
        File: {filename}

        Full File Content:
        {full_content[:3000]}

        Diff (Changes Made):
        {changes[:1500]}

        Provide:
        1. A summary of what the changes achieve.
        2. Potential issues (bugs, security, performance).
        3. Suggestions for improvement.
        4. High-level impact on the repository.
        """
        try:
            response = openai.generate([prompt], max_tokens=500)
            results.append({
                "file": filename,
                "analysis": response.generations[0][0].text.strip()
            })
        except Exception as e:
            results.append({"file": filename, "error": str(e)})

    return results



def summarize_large_file(file_content, filename):
    """
    Summarize large file content to stay within OpenAI's context limit.
    """
    prompt = f"""
    You are a senior software engineer reviewing a file that is too large to analyze in full. 
    Provide a summary that captures the key points and purpose of the file.

    File Name: {filename}

    Full File Content (Truncated):
    {file_content[:3000]}

    Summarization Instructions:
    1. Summarize the overall purpose of this file.
    2. Highlight the main components or sections in the code.
    3. Identify any patterns, conventions, or structural decisions used in the code.
    4. Provide any notable observations about the file's structure, logic, or style.

    Be concise and focus on providing a clear overview.
    """
    openai = OpenAI(api_key=OPEN_AI_KEY)
    try:
        response = openai.generate([prompt])
        return response.generations[0][0].text.strip()
    except Exception as e:
        return f"Error summarizing file: {e}"


