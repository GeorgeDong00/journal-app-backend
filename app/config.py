import os
from datetime import timedelta

# Get the base directory of the current file
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Secret key for CSRF protection
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Celery Configuration
    BROKER_URL = os.environ.get("BROKER_URL") or "redis://localhost:6379/0"
    RESULT_BACKEND = os.environ.get("RESULT_BACKEND") or "redis://localhost:6379/0"

    CELERY_BEAT_SCHEDULE = {
        "weekly-advice-generation": {
            "task": "generate_all_users_weekly_advice",
            "schedule": timedelta(seconds=60),
            "args": (),
        },
    }
