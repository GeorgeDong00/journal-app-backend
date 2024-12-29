import logging
import os
from logging.handlers import RotatingFileHandler

# Instantiate worker logger that stores logs in logs/worker.log
logger = logging.getLogger("celery_worker")
logger.setLevel(logging.INFO)

if not os.path.exists('logs'):
    os.makedirs('logs')

# Rotating file handler
worker_handler = RotatingFileHandler('logs/worker.log',
                                     maxBytes=1024 * 1024,
                                     backupCount=5)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
worker_handler.setFormatter(formatter)
logger.addHandler(worker_handler)

# Prevent double logging
logger.propagate = False

logger.info("Worker logger initialized.")
