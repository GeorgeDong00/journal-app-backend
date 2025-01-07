# app/utils/exceptions.py
from werkzeug.exceptions import HTTPException, InternalServerError

def raise_http_exception(exception_class, failure_reason="", exception_message=""):
    """
    Raises a HTTPException (e.g., BadRequest, Unauthorized) with additional data.
    The global error handler will process this exception and generate a JSON response with its status
    code, a high-level error message, and the original exception message.

    Args:
        exception_class (type): A subclass of HTTPException, otherwise InternalServerError is used.
        failure_reason (str): A short message describing the context or reason for the failure.
        exception_message (str): The message from a caught exception.

    Raises:
        HTTPException: The specified or default HTTPException with added data.
    """
    # Validates the existence of HTTPException subclass.
    http_exc_subclass = InternalServerError("Modified exception is missing a HTTPException subclass.")
    if issubclass(exception_class, HTTPException):
        http_exc_subclass = exception_class

    # Create the HTTPException instance with .
    exc = http_exc_subclass(description=exception_message)
    exc.data = {
        "error": failure_reason
    }

    raise exc
