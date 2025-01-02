from flask import Blueprint, redirect, request, session, url_for, jsonify
from common.auth import get_github_auth_url, get_access_token
from common.data_fetching import fetch_coding_files
import re
from semantic_search.embedding_generator import process_and_store_all
from semantic_search.embedding_generator import answer
import tempfile
import os
from flask import render_template





main = Blueprint("main", __name__)

@main.route("/")
def home():
    """
    Home page to check login status.
    """
    oauth_token = session.get("oauth_token")
    if oauth_token:
        return "Logged in. Ready to fetch files! <a href='/fetch-files'>Go to Fetch Files</a>"
    return '<a href="/login">Login with GitHub</a>'

@main.route("/login")
def login():
    """
    Redirect to GitHub's login page.
    """
    return redirect(get_github_auth_url())

@main.route("/callback")
def callback():
    """
    GitHub OAuth callback route.
    """
    code = request.args.get("code")
    try:
        token = get_access_token(code)
        session["oauth_token"] = token
        return redirect(url_for("main.fetch_files"))  # Redirect to /fetch-files
    except Exception as e:
        return jsonify({"error": str(e)}), 400



@main.route("/fetch-files", methods=["GET", "POST"])
def fetch_files():
    oauth_token = session.get("oauth_token")
    if not oauth_token:
        return render_template("error.html", message="User not authenticated. Please log in.")

    if request.method == "POST":
        owner = request.form.get("owner")
        repo = request.form.get("repo")
        branch = request.form.get("branch", "main")
        extensions = request.form.get("extensions", ".py,.md,.txt").split(",")

        if not owner or not repo:
            return render_template("error.html", message="Owner and repository name are required.")

        try:
            # Fetch files from GitHub
            files = fetch_coding_files(owner, repo, branch, oauth_token, extensions)

            # Process and store all files
            process_and_store_all(files)

            return render_template("query.html", message="Files processed successfully. You can now query!")
        except Exception as e:
            return render_template("error.html", message=f"Error processing files: {e}")

    return render_template("fetch_files.html")




def parse_github_url(url):
    """
    Parse a GitHub repository URL and extract the owner and repo.
    """
    pattern = r"https://github\.com/([^/]+)/([^/]+)"
    match = re.match(pattern, url)
    if match:
        owner = match.group(1)
        repo = match.group(2)
        # Remove ".git" if present at the end of the repo name
        repo = repo.rstrip(".git")
        return owner, repo
    return None, None

@main.route("/query", methods=["GET", "POST"])
def query():
    if request.method == "POST":
        query_text = request.form.get("query")
        namespace = request.form.get("namespace", "default")

        if not query_text:
            return render_template("error.html", message="Query is required.")

        try:
            response = answer(query_text, namespace)
            return render_template("query_results.html", query=query_text, response=response)
        except Exception as e:
            print(f"Error querying embeddings: {e}")
            return render_template("error.html", message=f"Error querying embeddings: {e}")

    return render_template("query.html")
