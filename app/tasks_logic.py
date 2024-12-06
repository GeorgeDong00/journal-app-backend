from datetime import datetime, timezone, timedelta
from app.models import User, Post, WeeklyAdvice
from app.extensions import db
from flask import current_app

def generate_advice(posts):
    """
    Invokes OpenAI API to generate personalized advice based on the posts.

    Parameters:
        posts (list): List of posts from an user.
    
    Returns:
        openAI_response (str): Formatted string of user posts.
    """
    prompt = "User had the following posts last week: \n\n"
    for post in posts:
        prompt += f"{post.content}\n"
    return prompt

def generate_weekly_advice_for_user(user):
    """
    Queries the user's posts from specified days, calls OpenAI API to generates personalized weekly advice, and stores output advice in the weekly_advice database.
    
    Parameters:
        user (User): User for whom the advice is to be generated.
    
    Returns:
        weekly_advice: Generated weekly advice through OpenAI API.
    """
    retrieval_window = datetime.now(timezone.utc) - timedelta(days=7)
    posts = Post.query.filter(
        Post.user_id == user.id,
        Post.created_at >= retrieval_window
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
