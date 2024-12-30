from flask import Flask
import firebase_admin
from firebase_admin import credentials
from .extensions import db, migrate, ma
from .config import Config
from app.logging_config import configure_application_logging
from celery_factory import make_celery
from app.celery_worker.tasks import register_tasks


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

    # Initialize Celery for background tasks
    celery = make_celery(app)
    app.celery = celery
    register_tasks(celery)

    # Initialize application logging
    configure_application_logging(app)

    app.logger.info("Application instance created.")
    return app
