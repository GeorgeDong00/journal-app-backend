import os
from celery.schedules import crontab

# Get the base directory of the current file
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask and Auth Security
    SECRET_KEY = os.environ.get("SECRET_KEY")
    FIREBASE_CREDENTIAL = os.environ.get("FIREBASE_CREDENTIAL", "")

    # PostgreSQL Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # RabbitMQ for enqueueing Celery tasks
    BROKER_URL = os.environ.get("RABBITMQ_BROKER_URL")
    RESULT_BACKEND = os.environ.get("RABBITMQ_RESULT_BACKEND")

    # Celery Beat Schedule for Periodic Tasks (UTC)
    CELERY_BEAT_SCHEDULE = {
        "weekly-advice-generation": {
            "task": "enqueue_all_users_advice_generation",
            "schedule": crontab(hour=12, minute=0, day_of_week='sunday'),
            "args": (),
        },
    }

    # AWS S3 Bucket for Profile Pictures
    AWS_REGION = os.environ.get("AWS_REGION", None)
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
    S3_PROFILE_PIC_BUCKET = os.environ.get("S3_PROFILE_PIC_BUCKET", None)
    S3_PROFILE_PIC_BUCKET_URL = os.environ.get("S3_PROFILE_PIC_BUCKET_URL", None)
