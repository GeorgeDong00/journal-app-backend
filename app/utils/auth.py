from flask import request, g, current_app
from functools import wraps
from firebase_admin import auth
from werkzeug.exceptions import BadRequest, Unauthorized
from app.models import User
from app.extensions import db
from app.utils.exceptions import raise_http_exception

def firebase_auth_required(f):
    """The authentication decorator restricts access by verifying the request header bearer token.
    Once validated, the user's Firebase Auth information are stored in the Flask global (g).

    The valid authorization header format is:
        "Authorization": "Bearer <JWT_TOKEN>" (Firebase Auth Token)
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise KeyError("Missing or malformed Authorization header.")

            id_token = auth_header.split("Bearer ")[1]
            if not id_token:
                raise KeyError("No bearer token found in Authorization header.")

            decoded_token = auth.verify_id_token(id_token)
            g.user = decoded_token

        except (auth.ExpiredIdTokenError, auth.InvalidIdTokenError) as fbe:
            current_app.logger.error(f"Invalid or expired Firebase token: {fbe}")
            raise_http_exception(Unauthorized, "Invalid or expired token provided.", str(fbe))
        except KeyError as ke:
            current_app.logger.error(f"Authorization header error: {ke}")
            raise_http_exception(BadRequest, "Invalid request header.", str(ke))
        except Exception as e:
            current_app.logger.error(f"Unexpected error during Firebase authorization: {e}")
            raise_http_exception(Unauthorized, "An error occurred while verifying the token.", str(e))

        return f(*args, **kwargs)
    return decorated_function

def get_or_create_user(firebase_uid: str) -> User:
    """Retrieve the user with given firebase uid from the database. If user does not exist,
    then create a new user instance.

    Args:
        firebase_uid (str): The firebase UID obtained from the bearer token.

    Returns:
        user (User): The existing or newly created User instance.
    """
    try:
        existing_user = User.query.filter_by(firebase_uid=firebase_uid).first()
        if existing_user:
            current_app.logger.info(f"User retrieved (ID: {existing_user.id}).")
            return existing_user

        current_app.logger.info(f"User with {firebase_uid} cannot be found. Creating new user.")
        new_user = User(firebase_uid=firebase_uid)
        db.session.add(new_user)
        db.session.commit()
        current_app.logger.info(f"New user created (ID {new_user.id}).")
        return new_user

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to retrieve or create user: {e}")
        raise e
