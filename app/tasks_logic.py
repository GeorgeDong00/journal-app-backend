from datetime import datetime, timezone, timedelta
from app.models import Post, WeeklyAdvice
from app.extensions import db
from flask import current_app
import openai


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
    posts = Post.query.filter(
        Post.user_id == user.id, Post.created_at >= retrieval_window
    ).all()

    if not posts:
        return None

    advice_content = generate_advice(posts)
    if advice_content:
        weekly_advice = WeeklyAdvice(user_id=user.id, content=advice_content)
        db.session.add(weekly_advice)
        db.session.commit()
        return weekly_advice
    return None
