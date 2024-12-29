from time import sleep
from flask import current_app

from app.celery_tasks_logic import (generate_weekly_advice_for_user,
                                    update_post_emotion)
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
        current_app.logger.info(f"Celery Task: Generate weekly advices for {len(users)} users.")

        for user in users:
            try:
                current_app.logger.info(f"Generating weekly advice for user {user}.")
                advice = generate_weekly_advice_for_user(user)
                if not advice:
                    current_app.logger.warning(f"Failed to generate advice for User {user}.")

                current_app.logger.info("Completed Celery Task: Generated all weekly advice.")
                return True
            except Exception as e:
                current_app.logger.error(f"Error occured during advice generation: {e}")
                return False

    @celery.task(name="test_task")
    def test_task():
        print("Test task is running every 15 seconds!")
        return "Test task completed."

    @celery.task(name="generate_content_emotional_scores")
    def generate_content_emotional_scores(content, post_id):
        """
        Defines a Celery task that calls a serverless Hugging Face API URL to generates emotional
        scores for a given post content. The inference API is load balanced, the worker
        will attempt twice with 20 seconds in between before failing.

        Parameters:
            post_content (str): Text content of a post.

        Returns:
            status

        """
        current_app.logger.info(f"Celery Task: Generate emotional scores for post {post_id}.")
        attempts = 2
        for i in range(attempts):
            try:
                success = update_post_emotion(content, post_id)
                if success:
                    current_app.logger.info(
                        f"Successfully updated post {post_id} on attempt #{i + 1}.")
                    return True
                else:
                    current_app.logger.warning(
                        f"Attempt #{i + 1} to update post {post_id} failed."
                        + ("" if i == attempts - 1 else " Will retry in 20s.")
                    )
            except Exception as e:
                current_app.logger.warning(f"Error occured for attempt #{i + 1}: {e}.")

            # Sleep for 20 seconds before retrying
            if i < attempts - 1:
                sleep(20)

        current_app.logger.error(f"Failed to update post {post_id} after {attempts} attempts.")
        return False
