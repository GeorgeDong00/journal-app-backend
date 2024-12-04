from flask import request, jsonify, g
from functools import wraps
from firebase_admin import auth
from . import auth_bp


def firebase_auth_required(f):
    """
    The decorator is used to protect routes that require authentication.

    Usage: Frontend sends a request with an Authorization header containing a Bearer token.
    The token is then verified using Firebase Admin SDK. If the token is valid, the route is executed.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = None
        # Get the token from the Authorization header
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                id_token = auth_header.split("Bearer ")[1]

        if id_token:
            try:
                decoded_token = auth.verify_id_token(id_token)
                g.user = decoded_token
            except Exception as e:
                return jsonify({"error": "Invalid token", "message": str(e)}), 401
        else:
            return jsonify({"error": "Authorization token missing"}), 401

        return f(*args, **kwargs)

    return decorated_function
