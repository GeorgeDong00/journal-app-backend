# app/main/error_handler.py
from flask import jsonify
from werkzeug.exceptions import HTTPException
from . import main_bp

@main_bp.app_errorhandler(HTTPException)
def http_exception_handler(exc):
    """An API route scope HTTPExceptions handler that returns a JSON response.

    Args:
        exc (HTTPException): The HTTPException instance to handle.

    Returns:
        JSON: A JSON response with HTTP status
    """
    response = {
        "error": exc.data.get("error", "Invalid modified HTTPException."),
        "message": exc.description,
    }
    return jsonify(response), exc.code
