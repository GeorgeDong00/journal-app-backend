from flask import request, jsonify, g, current_app
from functools import wraps
from firebase_admin import auth as firebase_auth
from app.models import User
from app.extensions import db


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
                decoded_token = firebase_auth.verify_id_token(id_token)
                g.user = decoded_token
            except Exception as e:
                return jsonify({"error": "Invalid token", "message": str(e)}), 401
        else:
            return jsonify({"error": "Authorization token missing"}), 401

        return f(*args, **kwargs)

    return decorated_function


def get_or_create_user(firebase_uid: str) -> User:
    """Retrieve or create a user from User table by Firebase UID.

    Args:
        firebase_uid: Firebase UID derived from request's header bearer token.

    Returns:
        user: Retrieved or newly created User instance.
    """
    user = User.query.filter_by(firebase_uid=firebase_uid).first()
    current_app.logger.info(f"Retrieved {user} of Firebase UID {firebase_uid}.")

    if not user:
        user = User(firebase_uid=firebase_uid)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"Created {user} of Firebase UID {firebase_uid}.")
    return user
