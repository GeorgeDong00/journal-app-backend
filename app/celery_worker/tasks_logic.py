from datetime import datetime, timezone
from openai import OpenAI
import os
import json
import requests
from . import celery_logger as logger
from app.models import Post, WeeklyAdvice
from app.extensions import db
from app.utils.time import latest_monday
from app.utils.advice_generation import openai_prompt
from app.utils.exceptions import DependencyException, UserAdviceException


# Dictionary of supported emotions to prevent HuggingFace model updates from
# breaking the Post model.
SUPPORTED_EMOTIONS = {
    "anger",
    "disgust",
    "fear",
    "joy",
    "neutral",
    "sadness",
    "surprise",
}

# --------------------------------------------------
# Advice Generation
# --------------------------------------------------
def retrieve_user_latest_posts(user_id, start_of_week):
    """Retrieves a week worth of posts from the user.

    Args:
        user_id (int): User ID for whom the posts are to be retrieved.

    Returns:
        latest_posts (List): Posts from the past seven days.

    Raises:
        UserAdviceException: If no posts were created within this week.
    """
    current_time = datetime.now(timezone.utc).date()
    latest_posts = Post.query.filter(Post.user_id == user_id,
                                     Post.created_at >= start_of_week).all()
    if not latest_posts:
        logger.warning(f"User {user_id} has zero post from {start_of_week} - {current_time}.")
        raise UserAdviceException(f"Cannot find any posts from {start_of_week} - {current_time}.")

    logger.info(f"User {user_id} has {len(latest_posts)} posts from {start_of_week} - {current_time}.")
    return latest_posts


def call_openai_advice_generation(posts):
    """Invokes the OpenAI API to generate a JSON-based riddle and advice from a list of user posts.

    Args:
        posts (list): List of posts from an user.

    Returns:
        advice_content (str): Formatted string of user posts.

    Raises:
        DependencyException: If call fails or the response is not as expected.
    """
    prompt = openai_prompt() + "\n**Journal Entries**\n"
    for post in posts:
        prompt += f"- {post.content}\n"

    logger.info("Sending prompt through OpenAI API for advice generation.")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2048,
            top_p=1.0,
            frequency_penalty=0.2,
            presence_penalty=0.0
        )
        advice_content = response.choices[0].message.content
        logger.info(f"OpenAI response {response._request_id} returned an advice: {advice_content}")

        # Parse and return the advice content as a JSON.
        sanitized_advice = advice_content.replace("```json", "").replace("```", "").strip()
        new_advice = json.loads(sanitized_advice)
        return new_advice

    except Exception as e:
        logger.error(f"An error occured during OpenAI API call: {e}")
        raise DependencyException(f"OpenAI failed to generate latest advice: {e}")


def generate_weekly_advice_for_user(user):
    """
    Generates and stores the advice for the current week.

    Args:
        user (User): User instance for whom the advice is generated.

    Returns:
        new_advice_id: ID of the newly created WeeklyAdvice instance.
    """
    try:
        # Verify the user has not generated any advice for this week.
        user_id, of_week = user.id, latest_monday()

        # Retrieves the entries user has posted during this week.
        posts = retrieve_user_latest_posts(user_id, of_week)

        # Call OpenAI endpoint to generate the JSON-based advice/riddle.
        advice_content = call_openai_advice_generation(posts)

        # Create a new advice instance, assign corresponding week date, and save.
        new_advice = WeeklyAdvice(user_id=user_id,
                                  content=advice_content,
                                  of_week=of_week)
        db.session.add(new_advice)
        db.session.commit()
        logger.info(f"Successfully generated new advice for user {user_id} for week of {of_week}.")
        return new_advice.id

    except UserAdviceException as ae:
        raise ae
    except DependencyException as de:
        raise de
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create new advice for {user}: {e}.")
        raise e


# --------------------------------------------------
# Sentiment Analysis and Emotion Scoring
# --------------------------------------------------
def call_hf_llm_api(content):
    """Calls a Hugging Face serverless API to execute sentiment analysis on post content, and score each emotion
    category with a float between 0 and 1, where higher values indicate higher confidence in detected emotions.

    The LLM model can be found here: https://huggingface.co/j-hartmann/emotion-english-distilroberta-base

    Args:
        content (str): Text content of a post.

    Returns:
        emotion_data (List): List of dictionaries containing emotion labels and scores.

    Raises:
        DependencyException: If call fails or the response is not as expected.
    """
    headers = {"Authorization" : f"Bearer {os.environ.get('HUGGING_FACE_API_TOKEN')}"}
    payload = {"inputs": content}

    try:
        # Initiate a call to Hugging Face for sentiment analysis and scoring.
        logger.info("Sending POST request to Hugging Face serverless API.")
        response = requests.post(os.environ.get("EMOTION_SCORE_API_URL"),
                                 headers=headers,
                                 json=payload)

        # Validate the response status code and JSON data.
        if response.status_code != 200:
            logger.info(f"Call to Hugging Face LLM returned with HTTP status {response.status_code}: {response.text}")
            raise DependencyException(f"Response was of HTTP status {response.status_code}.")

        # Validate emotional score data exist within a successful response.
        emotion_data = response.json()[0]
        if not emotion_data or len(emotion_data) < 7:
            raise DependencyException("Response contains invalid or missing emotional score data.")

        logger.info("Successfully recieved emotional score data from Hugging Face API.")
        return emotion_data

    except Exception as e:
        logger.error(f"An error occured when making request to Hugging Face: {e}.")
        raise DependencyException(e)


def update_post_emotion(content, post_id) -> Post:
    """Extracts the emotional data from content, then add or updates each emotion fields for the post.

    Args:
        content (str): Text content of a post.
        post_id (int): Post ID to update the emotional scores.

    Returns:
        post_id (int): Post ID that was successfully updated.
    """
    try:
        # Retrieve the Post instance and calls the Hugging Face API.
        post_instance = Post.query.get(post_id)
        emotion_data = call_hf_llm_api(content)
        logger.info(f"Received emotion scores for post {post_id}.")

        # Add emotion scores Post instance, otherwise update existing score.
        for category in emotion_data:
            emotion = category["label"].lower()
            score = round(category["score"], 3)
            if emotion in SUPPORTED_EMOTIONS:
                setattr(post_instance, f"{emotion}_value", score)
                logger.info(f"Set {emotion} score: {score}")

        # Add updated post to the database.
        db.session.commit()
        logger.info(f"Successfully updated post {post_id} with emotion scores.")
        return post_id

    except DependencyException as de:
        raise de
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update post {post_id} with emotion scores: {e} ")
        raise e
