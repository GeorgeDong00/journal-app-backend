import os

# Get the base directory of the current file
basedir = os.path.abspath(os.path.dirname(__file__))

class Config: 
    # Secret key for CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False