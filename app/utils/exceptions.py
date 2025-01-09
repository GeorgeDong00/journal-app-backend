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
    if issubclass(exception_class, HTTPException):
        exc = exception_class(description=exception_message or exception_class.description)
    else:
        exc = InternalServerError(description=exception_message or "An internal server error occurred.")

    # Attach additional data for error handler
    exc.data = {
        "error": failure_reason or exc.name
    }

    raise exc

class DependencyException(Exception):
    """
    An exception indicating that some external dependency failed or returned invalid response (e.g., request to
    HuggingFace or OpenAI APIs).
    """

    def __init__(self, message="A dependency failed."):
        super().__init__(message)

class UserAdviceException(Exception):
    """
    An exception indicating an user-scope problem during advice generation (i.e the user
    has already generated advice for the latest week, etc.) and will be skipped.
    """

    def __init__(self, message="User does not meet necessary requirement for advice generation."):
        super().__init__(message)
