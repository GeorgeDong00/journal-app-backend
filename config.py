import os

class Config: 
    # Secret key for CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY')