import sys
import os
from flask import Blueprint, redirect, request, session, url_for, jsonify, render_template
from commonly_used.auth import get_github_auth_url, get_access_token
from commonly_used.data_fetching import fetch_coding_files
from semantic_search.search_engine import process_and_index_repository, answer, clear_namespace, get_pinecone_index

GITHUB_REDIRECT_URI = os.environ.get('GITHUB_REDIRECT_URI')
print(GITHUB_REDIRECT_URI)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

        # Use default namespace for simplicity
        namespace = "default"

        try:
            # Initialize Pinecone index
            index = get_pinecone_index()

            # Clear the namespace to avoid conflicts
            clear_namespace(index, namespace)

            # Fetch files from GitHub
            files = fetch_coding_files(owner, repo, branch, oauth_token, extensions)

            # Process and index all files in the repository
            process_and_index_repository(files, namespace=namespace)

            return render_template("query.html", message="Files processed successfully. You can now query!")
        except Exception as e:
            return render_template("error.html", message=f"Error processing files: {e}")

    return render_template("fetch_files.html")

@main.route("/query", methods=["GET", "POST"])
def query():
    """
    Query the indexed files and code blocks.
    """
    if request.method == "POST":
        query_text = request.form.get("query")
        namespace = "default"  # Use default namespace
        top_k = int(request.form.get("top_k", 5))

        if not query_text:
            return render_template("error.html", message="Query is required.")

        try:
            # Use the answer function to get AI-driven responses
            response = answer(query_text, namespace=namespace, top_k=top_k)
            if not response:
                return render_template("query_results.html", query=query_text, response="No relevant results found.")

            return render_template("query_results.html", query=query_text, response=response)
        except Exception as e:
            print(f"Error querying embeddings: {e}")
            return render_template("error.html", message=f"Error querying embeddings: {e}")

    return render_template("query.html")
