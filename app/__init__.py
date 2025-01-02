from flask import Flask
from flask import session

def create_app():
    """
    Factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.secret_key = "your_secret_key_here"  # Replace with a secure, random secret key

    # Register Blueprints
    from .routes import main
    app.register_blueprint(main)

    return app
