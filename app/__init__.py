from flask import Flask
import json
import firebase_admin
from firebase_admin import credentials
from .extensions import db, migrate, ma
from .config import Config
from .logger import configure_application_logging
from celery_factory import make_celery
from app.celery_worker.tasks import register_tasks
from app.main import main_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Load Firebase Account Key to enable token verification
    cred_json = app.config["FIREBASE_CREDENTIAL"]
    parsed = json.loads(cred_json)
    cred = credentials.Certificate(parsed)
    firebase_admin.initialize_app(cred)

    # Register postgresql database and marshmallow schemas
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)

    # Register Blueprints
    app.register_blueprint(main_bp)

    # Create Celery worker and register tasks
    celery = make_celery(app)
    app.celery = celery
    register_tasks(celery)

    # Register logger for application
    configure_application_logging(app)

    app.logger.info("Application instance created.")
    return app
