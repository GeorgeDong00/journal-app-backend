from flask import g, jsonify, request
from marshmallow import ValidationError
from app.extensions import db
import app.models.post as post
import app.models.weekly_advice as weekly_advice
import datetime
from app.auth import firebase_auth_required

from app.models import (
    User,
    Post, 
    PostSchema
)
from . import main_bp
#from transformers import pipeline
#emotion = pipeline('sentiment-analysis', model='arpanghoshal/EmoRoBERTa')


def serializePost(post):
    post_data = {}
    post_data["id"] = post.id
    post_data["user_id"] = post.user_id
    post_data["content"] = post.content
    post_data["dominant_emotion"] = post.dominant_emotion
    post_data["dominant_emotion_value"] = post.dominant_emotion_value
    post_data["created_at"] = post.created_at

    return post_data

def returnLastSunday(date):
    return date - datetime.timedelta(days=date.weekday()+1)

def get_or_create_user(firebase_uid):
    """
    Helper function to retrieve a user by firebase_uid.
    If the user does not exist, create a new one.
    """
    user = User.query.filter_by(firebase_uid=firebase_uid).first()
    if not user:
        user = User(firebase_uid=firebase_uid)
        db.session.add(user)
        db.session.commit()
    return user


@main_bp.route("/api")
@firebase_auth_required
def index():
    """
    Endpoint to test authentication.
    """
    return jsonify({"message": "Authentication successful!"}), 200


@main_bp.route("/api/posts", methods=["POST"])
#@firebase_auth_required
def create_post():
    """
    Endpoint to create a new post for the authenticated user.
    """
    #firebase_uid = g.user['uid']
    firebase_uid = "test_user"
    user = get_or_create_user(firebase_uid)
    data = request.get_json()
    emotion_label = emotion(data['content'])
    data['dominant_emotion'] = emotion_label[0]['label']
    data['dominant_emotion_value'] = emotion_label[0]['score']
  

    # Validate request data
    post_schema = PostSchema()
    try:
        post_data = post_schema.load(data)
    except ValidationError as ve:
        return jsonify({"error": "Validation failed.", "messages": ve.messages}), 400

    new_post = post_data
    new_post.user_id = user.id
    try:
        db.session.add(new_post)
        db.session.commit()

        serialized_new_post = post_schema.dump(new_post)
        return jsonify({"message": "Post created successfully.", "post": serialized_new_post}),201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create post.", "message": str(e)}), 500


  



@main_bp.route("/api/posts/<int:users_id>/", methods=["GET"])
#@firebase_auth_required
def get_users_posts(users_id):
    """
    Endpoint to create a new post for the authenticated user.
    """
    #firebase_uid = g.user['uid']
    firebase_uid = "test_user"
    user = get_or_create_user(firebase_uid)

    user = db.session.query(User).filter_by(id = users_id).first()

    posts = user.posts

    #print(returnLastSunday(datetime.datetime(2023, 12, 30, 12, 0)))

    #userSummaries = db.session.query(weekly_advice.WeeklyAdvice).filter_by(user_id = users_id)
   # print(userSummaries)    
    #result = db.session.execute(userSummaries)

    all_posts = []
    for post in posts:
        all_posts.append(serializePost(post))

    return jsonify({"message": "Post created successfully.", "posts": all_posts}),200
