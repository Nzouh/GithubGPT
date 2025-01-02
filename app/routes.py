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
    Home page with a modern login button and additional options for logged-in users.
    """
    oauth_token = session.get("oauth_token")
    if oauth_token:
        return render_template(
            "index.html",
            message="Welcome back! Choose an action below.",
            logged_in=True
        )
    return render_template("index.html", message="Log in with GitHub to get started.", logged_in=False)



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
        return redirect(url_for("main.home"))  # Redirect to /
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
        try:
            # Adjust for AJAX JSON data
            data = request.get_json()  # Get JSON data from the request
            query_text = data.get("query")
            namespace = data.get("namespace", "default")  # Default namespace
            top_k = int(data.get("top_k", 5))  # Default top_k to 5 if not provided

            if not query_text:
                return {"result": "Query is required."}, 400

            # Use the answer function to get AI-driven responses
            response = answer(query_text, namespace=namespace, top_k=top_k)
            if not response:
                return {"result": "No relevant results found."}, 200

            return {"result": response}, 200

        except Exception as e:
            print(f"Error querying embeddings: {e}")
            return {"result": f"Error querying embeddings: {e}"}, 500

    # Render the query form for GET requests
    return render_template("query.html")
