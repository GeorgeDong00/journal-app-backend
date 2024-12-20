import os
from datetime import timedelta

# Get the base directory of the current file
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Secret key for CSRF protection
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # PostgreSQL Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Celery Configuration
    BROKER_URL = os.environ.get("BROKER_URL")
    RESULT_BACKEND = os.environ.get("RESULT_BACKEND")

    CELERY_BEAT_SCHEDULE = {
        "weekly-advice-generation": {
            "task": "generate_all_users_weekly_advice",
            "schedule": timedelta(seconds=60),
            "args": (),
        },
    }
