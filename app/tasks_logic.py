from datetime import datetime, timezone, timedelta
from app.models import Post, WeeklyAdvice
from app.extensions import db
from flask import current_app
import openai
import os
import requests


def generate_advice(posts):
    """
    Invokes OpenAI API to generate personalized advice based on the posts.

    Parameters:
        posts (list): List of posts from an user.

    Returns:
        openAI_response (str): Formatted string of user posts.
    """
    prompt = "The user had the following posts last week:\n\n"
    for post in posts:
        prompt += f"- {post.content}\n"

    prompt += (
        "\nGiven these entries, please provide a short, encouraging piece of weekly advice "
        "focused on mental health and well-being. The advice should be empathetic, "
        "supportive, and actionable, guiding the user on how to approach the coming week."
    )

    openai.api_key = current_app.config.get("OPENAI_API_KEY")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a supportive mental health profession who gives actionable tips.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=250,
        )
        advice_content = response["choices"][0]["message"]["content"].strip()
        return advice_content
    except Exception as e:
        current_app.logger.error(f"OpenAI API call failed: {e}")
        return None


def generate_weekly_advice_for_user(user):
    """
    Queries the user's posts from specified days, calls OpenAI API to generates personalized weekly
    advice, and stores output advice in the weekly_advice database.

    Parameters:
        user (User): User for whom the advice is to be generated.

    Returns:
        weekly_advice: Generated weekly advice through OpenAI API.
    """
    retrieval_window = datetime.now(timezone.utc) - timedelta(seconds=60)
    posts = Post.query.filter(Post.user_id == user.id,
                              Post.created_at >= retrieval_window).all()
    if not posts:
        return None

    advice_content = generate_advice(posts)
    if advice_content:
        weekly_advice = WeeklyAdvice(user_id=user.id, content=advice_content)
        db.session.add(weekly_advice)
        db.session.commit()
        return weekly_advice
    return None


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


def query_hugging_face_llm(content):
    headers = {"Authorization" : f"Bearer {os.environ.get('HUGGING_FACE_API_TOKEN')}"}
    payload = {"inputs": content}

    response = requests.post(os.environ.get("EMOTION_SCORE_API_URL"),
                             headers=headers,
                             json=payload)

    current_app.logger.info(f"Returned from API call with status code {response.status_code}.")
    current_app.logger.info(f"Response: {response.json()}")
    return response.json()


def update_post_emotion(content, post_id) -> Post:
    """Analyze the emotion of post's content, and add/update post instance with emotion fields.
    """
    try:
        post_instance = Post.query.get(post_id)

        if not post_instance:
            current_app.logger.error(f"Cannot find post {post_id}.")
            return False

        current_app.logger.info(f"Attempt to call Hugging Face API for {post_instance}.")
        emotions_output = query_hugging_face_llm(content)
        if not emotions_output or len(emotions_output[0]) == 0:
            current_app.logger.warning("No sentiments returned.")
            return False

        for emotion_data in emotions_output[0]:
            emotion = emotion_data["label"].lower()
            score = round(emotion_data["score"], 3)
            # Add emotion score to Post instance, otherwise update existing score.
            if emotion in SUPPORTED_EMOTIONS:
                setattr(post_instance, f"{emotion}_value", score)
                current_app.logger.info(f"Added {emotion} score {score} to {post_instance}.")

        db.session.commit()
        current_app.logger.info(f"Successfully updated post {post_id} with emotion scores.")
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating post emotion: {e}")
        return False
