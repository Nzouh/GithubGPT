from flask import Blueprint, render_template, request, session
from commonly_used.data_fetching import parse_github_url, fetch_pull_requests, fetch_pull_request_details, analyze_code_changes

pull_review = Blueprint("pull_review", __name__)


@pull_review.route("/pull-review", methods=["GET", "POST"])
def pull_review_page():
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
                # Fetch detailed information for the selected pull request
                pr_details = fetch_pull_request_details(owner, repo, pr_number, oauth_token)

                # Analyze code changes
                analysis_results = analyze_code_changes(pr_details["files"], owner, repo, oauth_token)

                return render_template(
                    "pull_review.html",
                    pull_requests=None,
                    pr_details=pr_details,
                    repo_url=repo_url,
                    analysis_results=analysis_results,
                )
            else:
                # Fetch all pull requests
                pull_requests = fetch_pull_requests(owner, repo, oauth_token)

                return render_template(
                    "pull_review.html",
                    pull_requests=pull_requests,
                    pr_details=None,
                    repo_url=repo_url,
                )
        except Exception as e:
            return render_template("error.html", message=f"Error fetching pull requests: {e}")

    return render_template("pull_review.html")
