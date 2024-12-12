"""
run.py

Entry point for creating and running the Flask application. It also initializes and exposes the Celery instance for processing lengthly background task such as generating weekly advice for users.
"""

from app import create_app

# Create an instance of the Flask application using the factory function
app = create_app()

# Access the Celery instance from the Flask app
celery = app.celery

# Start the Flask server
if __name__ == "__main__":
    app.run()