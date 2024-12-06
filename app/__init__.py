import firebase_admin
from firebase_admin import credentials
from flask import Flask
from .extensions import db, migrate, ma
from .config import Config
from celery_app import make_celery
from app.celery_tasks import register_tasks


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Firebase Admin SDK to verify token
    cred = credentials.Certificate("app/serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)

    from app.main import main_bp

    app.register_blueprint(main_bp)

    # Initialize Celery for background task of generating weekly advice
    celery = make_celery(app)
    app.celery = celery
    # Import and register tasks AFTER celery is created
    register_tasks(celery)

    return app
