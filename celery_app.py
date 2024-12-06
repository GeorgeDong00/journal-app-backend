from celery import Celery
from celery.schedules import crontab


def make_celery(app):
    """
    A factory function to create a Celery instance that is aware
    of Flask application's context and configuration variables.

    Parameters:
        app (Flask) : Flask application instance

    Returns:
        Celery : Configured Celery instance
    """
    celery = Celery(app.import_name)
    celery.conf.broker_url = app.config["BROKER_URL"]
    celery.conf.result_backend = app.config["RESULT_BACKEND"]

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        """
        Baseline Task class to wrap every Celery task with Flask
        application context, allowing access to OpenAI API key,
        database connection, and etc.
        """

        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    celery.conf.timezone = "UTC"

    # Setup a weekly schedule
    celery.conf.beat_schedule = {
        "generate-weekly-advice-every-sunday-midnight": {
            "task": "generate_all_users_weekly_advice",
            "schedule": crontab(day_of_week="sunday", hour=0, minute=0),
        }
    }

    return celery
