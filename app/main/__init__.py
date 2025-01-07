# app/main/__init__.py
from flask import Blueprint

main_bp = Blueprint('main', __name__)

# Import routes for the main blueprint
from . import routes_posts, routes_profile_picture, routes_advices

# Import the error handler to catch custom HTTPExceptions
from .error_handler import http_exception_handler