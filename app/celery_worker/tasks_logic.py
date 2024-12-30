from datetime import datetime, timezone, timedelta
from openai import OpenAI
import os
import requests
from . import celery_logger as logger
from app.models import Post, WeeklyAdvice
from app.extensions import db


# List of supported emotions to prevent HuggingFace model updates from breaking the Post model.
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

def retrieve_user_recent_posts(user_id, window_seconds=604799):
    """
    Retrieves posts from the user within a specified time window.

    Parameters:
        user_id (int): User ID for whom the posts are to be retrieved.
        window_seconds (int): Time window in seconds, defaulting to 7 days

    Returns:
        List of posts from the user within the time window.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(window_seconds)
    return Post.query.filter(
        Post.user_id == user_id,
        Post.created_at >= cutoff_time
    ).all()


def call_openai_advice_generation(posts):
    """
    Invokes the OpenAI API to generate a JSON-based riddle and advice from a list of user posts.

    Parameters:
        posts (list): List of posts from an user.

    Returns:
        advice_content (str): Formatted string of user posts.
    """
    if not posts:
        logger.warning("No posts provided for OpenAI advice generation.")
        return None

    prompt = """

    You are a supportive mental health coach who also loves riddles. After reading the
    attached journal entries, craft a short, and encouraging weekly piece of advice
    disguised as a riddle. The riddle should revolve around the main theme and emotion of the
    journal entries.

    **Ensure that the answer to the riddle is a single word.**

    End with a simple, clear takeaway on how to approach the upcoming week. Please respond
    in the following JSON format:

    {{
        "riddle": "Your riddle here",
        "answer": "The answer to your riddle",
        "advice": "Your advice here"
    }}

    ---
    """
    prompt += "\n**Journal Entries**\n"
    for post in posts:
        prompt += f"- {post.content}\n"

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
            presence_penalty=0.0,

        )
        advice_content = response.choices[0].message.content
        logger.info(f"OpenAI request {response._request_id} returned: {advice_content}")
        return advice_content
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return None


def generate_weekly_advice_for_user(user):
    """
    Generates and stores the weekly advice for a given user by:
      1. Fetching the user's recent posts within a window.
      2. Calling the OpenAI endpoint to generate a JSON-based advice/riddle.
      3. Saving the result into the WeeklyAdvice table.

    Parameters:
        user (User): User instance for whom the advice is generated.

    Returns:
        weekly_advice: Newly created WeeklyAdvice instance or None if generation failed
    """
    # Retrieve the user's recent posts
    posts = retrieve_user_recent_posts(user.id, 604799)
    if not posts:
        logger.warning(f"No posts found for user {user.id}. Skipping advice generation")
        return None

    advice_content = call_openai_advice_generation(posts)
    if not advice_content:
        logger.warning("No advice content generated.")
        return None

    try:
        new_advice = WeeklyAdvice(user_id=user.id, content=advice_content)
        db.session.add(new_advice)
        db.session.commit()
        logger.info(f"Generated and stored new advice for {user}")
        return new_advice
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create new advice for {user} due to {e}.")
        return None

# --------------------------------------------------
# Sentiment Analysis and Emotion Scoring
# --------------------------------------------------

def call_hf_llm_api(content):
    headers = {"Authorization" : f"Bearer {os.environ.get('HUGGING_FACE_API_TOKEN')}"}
    payload = {"inputs": content}

    logger.info("Attempt to call Hugging Face API.")
    try:
        response = requests.post(os.environ.get("EMOTION_SCORE_API_URL"),
                                 headers=headers,
                                 json=payload)

        if response.status_code != 200:
            logger.warning(
                f"Failed HuggingFace request: {requests.status_codes}, {response.text}")
            return None

        logger.info("Successfully called Hugging Face.")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to initiate HuggingFace call: {e}.")
        return None


def update_post_emotion(content, post_id) -> Post:
    """Analyze the emotion of post's content, and add/update post instance with emotion fields.
    """
    try:
        post_instance = Post.query.get(post_id)

        if not post_instance:
            logger.error(f"Cannot find post {post_id}.")
            return False

        emotions_output = call_hf_llm_api(content)
        if not emotions_output or not emotions_output[0]:
            logger.warning(f"No sentiments returned for post {post_id}.")
            return False

        for emotion_data in emotions_output[0]:
            emotion = emotion_data["label"].lower()
            score = round(emotion_data["score"], 3)
            # Add emotion score to Post instance, otherwise update existing score.
            if emotion in SUPPORTED_EMOTIONS:
                setattr(post_instance, f"{emotion}_value", score)
                logger.info(f"Set {emotion} score {score} to {post_instance}.")

        db.session.commit()
        logger.info(f"Successfully updated post {post_id} with emotion scores.")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update post {post_id} with emotion scores: {e} ")
        return False
