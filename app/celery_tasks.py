from app.tasks_logic import generate_weekly_advice_for_user
from app.models import User


def register_tasks(celery):
    """
    Defines and register multiple Celery tasks with the Celery instance.

    Parameters:
        celery (Celery): Instance to which tasks will be registered to.
    """

    @celery.task(name="generate_all_users_weekly_advice")
    def generate_all_users_weekly_advice():
        """
        Defines a Celery task that generates personalized weekly advice for each unqiue user.

        Returns:
            str: Message indicating the completion status of the task.
        """
        users = User.query.all()
        for user in users:
            generate_weekly_advice_for_user(user)
        return "Completed Celery Task: Generated all users' weekly advice."

    @celery.task(name="test_task")
    def test_task():
        print("Test task is running every 15 seconds!")
        return "Test task completed."
