import logging
import os
from logging.handlers import RotatingFileHandler


def create_log_directory():
    """Create a log directory if it doesn't exist."""
    if not os.path.exists('logs'):
        os.mkdir('logs')

def configure_application_logging(app, log_file="logs/application.log"):
    """Configure logging for the Flask application."""
    create_log_directory()

    # Rotate logs after 1MB is reached then save backups in logs directory
    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)

    # Log Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    file_handler.setLevel(logging.INFO)

    # Timestamp [Log Level] Logger Name: Log Message [in File Path:Line Number]
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    file_handler.setFormatter(formatter)

    # Attach file handler to Flask’s built-in logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Flask application logging configured.")


def configure_worker_logging(log_file="logs/worker.log", logger_name="celery_worker"):
    """Configure logging for the Celery worker."""
    create_log_directory()

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Creates rotating file handler for the formatted worker logs
    worker_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    worker_handler.setFormatter(formatter)
    logger.addHandler(worker_handler)

    # Prevents double logging
    logger.propagate = False

    logger.info("Celery worker logging configured.")
    return logger
