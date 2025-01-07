from . import celery_logger as logger
from app.models import User
from app.celery_worker.tasks_logic import (generate_weekly_advice_for_user,
                                           update_post_emotion)
from app.utils.exceptions import UserAdviceException, DependencyException
from app.utils.time import latest_monday

def register_tasks(celery):
    """Defines and register multiple tasks with the Celery workers. The tasks are enqueued by
    the Flask application onto RabbitMQ and executed by pool of workers.
    """
    @celery.task(name="enqueue_all_users_advice_generation", bind=True)
    def enqueue_all_users_advice_generation(self):
        """Defines a Celery task that enqueues a batch of `generate_user_advice` tasks. The batch enqueuing occurs
        in intervals and its size corresponds to the number of users.
        """
        task_id = self.request.id
        total_users, of_week = 0, latest_monday()
        logger.info(f"( TID {task_id}): Handling latest batch of advice for week of {of_week}.")

        try:
            users = User.query.all()
            total_users = len(users) if users else 0
            logger.info(f"The current batch has {total_users} advice generation tasks.")

            for user in users:
                response = celery.send_task("generate_user_advice", args=[user.id])
                logger.info(f"Enqueued advice generation task for user {user.id}: (Task ID {response.id})")
            message = f"Successfully enqueued {total_users} advice generation tasks for week of {of_week}."

        except Exception as e:
            logger.error(f"Failed to enqueue advice generation batch for week of {of_week}: {e}")
            message = f"An error occured during enqueuing latest batch for week of {of_week}."
            raise e
        finally:
            logger.info(f"(TID {task_id}): {message}")
            return {"message": message}

    @celery.task(name="generate_user_advice", bind=True, max_retries=2)
    def generate_user_advice(self, user_id):
        """Defines a Celery task that generates personalized, riddle-like advice from a user's latest week of posts.

        Args:
            user_id (int): User ID for whom the latest advice is generated
        """
        message, task_id = "", self.request.id
        logger.info(f"(TID {task_id}): Handling advice generation for user {user_id}.")

        try:
            user = User.query.get(user_id)
            new_advice_id = generate_weekly_advice_for_user(user)
            message = f"Successfully generated new advice ID {new_advice_id} for user {user_id}."

        except UserAdviceException as uae:
            logger.warning(f"Skipped advice generation for user {user_id}: {uae}")
            message = f"Skipped advice generation for user {user_id} because no posts or already generated advice."
        except DependencyException as de:
            logger.warning(f"Retrying advice generation for user {user_id} due to third party errors: {de}")
            raise self.retry(exc=de, countdown=20)
        except Exception as e:
            logger.error(f"Failed to generate advice for user {user_id}: {e}")
            message = f"An error occured during advice generation for user {user_id}."
            raise e
        finally:
            logger.info(f"(TID {task_id}): {message}")
            return {"message": message}

    @celery.task(name="generate_content_emotional_scores", bind=True, max_retries=2)
    def generate_content_emotional_scores(self, content, post_id):
        """
        Defines a Celery task that generates emotional scores from given content and updates corresponding posts.

        Args:
            post_content (str): Text content of a post.
        """
        message, task_id = "", self.request.id
        logger.info(f"(TID {task_id}): Handling emotion score generation for post {post_id}.")

        try:
            update_post_emotion(content, post_id)
            message = f"Successfully updated post {post_id} with new emotional scores."

        except DependencyException as de:
            logger.warning(f"Retrying emotional analysis for post {post_id} due to third party service error: {de}")
            raise self.retry(exc=de, countdown=20)
        except Exception as e:
            logger.error(f"Failed to update post {post_id} with emotional scores: {e}")
            message = f"An error occured when updating post {post_id} with new emotional scores."
            raise e
        finally:
            logger.info(f"(TID {task_id}): {message}")
            return {"message": message}
