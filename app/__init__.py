from flask import Flask

def create_app():
    """
    Factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.secret_key = "your_secret_key_here"  # Replace with a secure, random secret key

    # Register Blueprints
    from .routes import main
    app.register_blueprint(main)

    from .pull_review_routes import pull_review  # Import the Blueprint
    app.register_blueprint(pull_review)  # Register the Blueprint

    return app
