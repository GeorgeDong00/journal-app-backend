import firebase_admin
from firebase_admin import credentials
from flask import Flask
from .extensions import db, migrate, ma
from .config import Config
from celery_factory import make_celery
from app.celery_worker.tasks import register_tasks
import logging
from logging.handlers import RotatingFileHandler
import os


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Firebase Admin SDK to verify token
    cred = credentials.Certificate("app/serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

    # Initialize Database and Marshmallow
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)

    # Initialize Blueprints (routes and authentication decorators)
    from app.main import main_bp
    app.register_blueprint(main_bp)

    # Initialize Celery for background task of generating weekly advice
    celery = make_celery(app)
    app.celery = celery
    register_tasks(celery)

    # Initialize Logging Directory and Configuration
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Rotate logs after 1MB is reached then save backups in logs directory
    file_handler = RotatingFileHandler('logs/application.log',
                                       maxBytes=1024 * 1024,
                                       backupCount=5)

    # Log Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    file_handler.setLevel(logging.INFO)

    # Timestamp [Log Level] Logger Name: Log Message [in File Path:Line Number]
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.info("Application and dependencies initialized.")

    return app
