from flask import Blueprint, render_template, request, session
from commonly_used.data_fetching import parse_github_url, fetch_pull_requests, fetch_pull_request_details, analyze_code_changes

pull_review = Blueprint("pull_review", __name__)


@pull_review.route("/pull-review", methods=["GET", "POST"])
def pull_review_page():
    """
    Handle pull request analysis and display results.
    """
    oauth_token = session.get("oauth_token")
    if not oauth_token:
        return render_template("error.html", message="User not authenticated. Please log in.")

    if request.method == "POST":
        repo_url = request.form.get("repo_url")
        pr_number = request.form.get("pr_number")
        owner, repo = parse_github_url(repo_url)

        if not owner or not repo:
            return render_template("error.html", message="Invalid Repository URL.")

        try:
            if pr_number:
                # Fetch pull request details
                pr_details = fetch_pull_request_details(owner, repo, pr_number, oauth_token)

                # Analyze the code changes
                analysis_results = analyze_code_changes(pr_details["files"], owner, repo, oauth_token)
                session["analysis_results"] = [
                    {
                        "file": file["filename"],
                        "analysis": analysis.get("analysis", "No analysis available."),
                        "diff": file.get("patch", "No diff available.")
                    }
                    for file, analysis in zip(pr_details["files"], analysis_results)
                ]

                return render_template(
                    "pull_review.html",
                    pull_requests=None,
                    pr_details=pr_details,
                    repo_url=repo_url,
                    analysis_results=session["analysis_results"],
                )
            else:
                # Fetch all pull requests for the repository
                pull_requests = fetch_pull_requests(owner, repo, oauth_token)

                return render_template(
                    "pull_review.html",
                    pull_requests=pull_requests,
                    pr_details=None,
                    repo_url=repo_url,
                )
        except Exception as e:
            print(f"Error during pull request analysis: {e}")
            return render_template("error.html", message=f"Error fetching pull requests: {e}")

    return render_template("pull_review.html")



from flask import jsonify
from langchain_community.llms import OpenAI

import os
from langchain_community.llms import OpenAI

@pull_review.route("/pull-review/query", methods=["POST"])
def pull_review_query():
    """
    Handle user queries about the pull review analysis.
    """
    data = request.get_json()
    query = data.get("query")
    analysis_results = session.get("analysis_results", [])

    if not query:
        return jsonify({"response": "Query cannot be empty."}), 400

    try:
        # Combine analysis results into a single context
        context = "\n\n".join([f"{res['file']}: {res['analysis']}" for res in analysis_results])

        prompt = f"""
        You are an assistant helping with a GitHub pull request review. 
        Based on the following analysis, answer the user's question concisely:

        Context:
        {context}

        User Question:
        {query}
        """

        # Use OpenAI with the API key loaded from the environment
        api_key = os.getenv("OPEN_AI_KEY")
        if not api_key:
            raise ValueError("OPEN_AI_KEY is not set in the environment variables.")
        
        response = OpenAI(api_key=api_key).generate([prompt], max_tokens=300)
        return jsonify({"response": response.generations[0][0].text.strip()}), 200
    except Exception as e:
        return jsonify({"response": f"Error processing query: {e}"}), 500


@pull_review.route("/pull-review/chat", methods=["GET"])
def pull_review_chat():
    """
    Render the chatbot UI for pull review queries.
    """
    # Verify session data exists
    analysis_results = session.get("analysis_results", [])
    if not analysis_results:
        return render_template("error.html", message="No analysis data available. Please analyze a pull request first.")
    
    return render_template("pull_review_chat.html")




