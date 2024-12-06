from celery import Celery

def make_celery(app):
    """
    A factory function to create a Celery instance that is aware of Flask application's context and configuration variables.

    Parameters:
        app (Flask) : Flask application instance
    
    Returns:
        Celery : Configured Celery instance
    """
    celery = Celery(app.import_name, 
                    broker=app.config['CELERY_BROKER_URL'],
                    backend=app.config['CELERY_RESULT_BACKEND'])
    celery.conf.update(app.config)

    TaskBase = celery.Task
    class ContextTask(TaskBase):
        """
        Baseline Task class to wrap every Celery task with Flask application context, allowing access to OpenAI API key, database connection, and etc.
        """
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
