from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
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

@main_bp.app_errorhandler(ValidationError)
def validation_exception_handler(ve):
    """A marshmallow ValidationError handler to catch request body exceptions.

    Args:
        ve (ValidationError): The ValidationError instance to handle.

    Returns:
        JSON: A JSON response with 400 (BadRequest) status.
    """
    ve_description = ve.messages['content'][0]
    response = {
        "error": "Invalid or malformed request.",
        "message": ve_description,
    }
    return jsonify(response), 400

@main_bp.app_errorhandler(Exception)
def handle_general_exception(e):
    """Fallback handler for all unhandled exceptions.

    Args:
        e (Exception): The unhandled exception instance.

    Returns:
        JSON: A JSON response with 500 (InternalServerError) status
    """
    response = {
        "error": "An unexpected error occured.",
        "message": str(e),
    }
    return jsonify(response), 500
