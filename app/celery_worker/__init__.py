from app.logger import configure_worker_logging

celery_logger = configure_worker_logging()
celery_logger.info("Created logger for Celery worker.")
