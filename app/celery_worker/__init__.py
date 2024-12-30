from app.logging_config import configure_worker_logging

celery_logger = configure_worker_logging()
celery_logger.info("Initialized Celery worker logging.")
