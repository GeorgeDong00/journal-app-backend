from flask import g, jsonify, request
import datetime
import os
from marshmallow import ValidationError
from transformers import pipeline
import boto3

from app.extensions import db
from app.auth import firebase_auth_required
from app.models import User, Post, PostSchema, WeeklyAdvice, WeeklyAdviceSchema
from . import main_bp


# Initialize S3 client to store profile picture
s3 = boto3.client("s3")


# Initalization of LLM
emotion_analyzer = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=True,
)


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
# List of supported emotions to prevent HuggingFace model updates
# from breaking the Post model.
SUPPORTED_EMOTIONS = {
    "anger",
    "disgust",
    "fear",
    "joy",
    "neutral",
    "sadness",
    "surprise",
}


def return_last_sunday(date : datetime.date) -> datetime.date:
    """Returns the date of the most recent Sunday before the given date.

    Args:
        date: UTC date to find the most recent Sunday before.

    Returns:
        datetime.date: The most recent Sunday before the given date.
    """
    return date - datetime.timedelta(days=date.weekday() + 1)


def get_or_create_user(firebase_uid: str) -> User:
    """Retrieve or create a user from User table by Firebase UID.

    Args:
        firebase_uid: Firebase UID derived from request's header bearer token.

    Returns:
        user: Retrieved or newly created User instance.
    """
    user = User.query.filter_by(firebase_uid=firebase_uid).first()
    if not user:
        user = User(firebase_uid=firebase_uid)
        db.session.add(user)
        db.session.commit()
    return user


def update_post_emotion(post: Post) -> Post:
    """Analyze the emotion of post's content, and add/update post instance with emotion fields.

    Args:
        post: The Post instance to analyze.

    Returns:
        post: The updated Post instance with emotion scores.
    """
    # TODO: Refactor by handing-off to Celery Worker
    emotions_output = emotion_analyzer(post.content)

    if not emotions_output:
        return post

    for emotion_data in emotions_output[0]:
        emotion = emotion_data["label"].lower()
        score = emotion_data["score"]
        # Add emotion score to Post instance, otherwise update existing score.
        if emotion in SUPPORTED_EMOTIONS:
            setattr(post, f"{emotion}_value", score)
    return post


# --------------------------------------------------
# Post Routes
# --------------------------------------------------
@main_bp.route("/api/posts/", methods=["POST"])
@firebase_auth_required
def create_post():
    """Endpoint to create a new post for the authenticated user.

    Request Body:
        content (str): The content of the user's journal post.
        formatting (JSON): A list of formatting objects describing how
            content should be formatted.

    Responses:
        201: Post created successfully.
        400: Request body with missing data cannot be validated.
        500: Post creation failed due to database error.
    """
    # Retrieve the user from User model from the Authorization bearer token.
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Validate request 'content' and 'formatting' fields.
    data = request.get_json()
    try:
        # Schema replaces empty 'formatting' with empty List.
        validated_data = PostSchema().load(data)
    except ValidationError as ve:
        return jsonify({
            "error": "Request body cannot be validated.",
            "messages": ve.messages}), 400

    # Insert emotion analysis data into new post before committing to database
    new_post = Post(**validated_data)
    new_post.user_id = user.id
    new_post = update_post_emotion(data)

    # Save new Post to the database.
    try:
        db.session.add(new_post)
        db.session.commit()
        serialized_new_post = PostSchema().dump(new_post)
        return jsonify({
            "message": "Post created successfully.",
            "post": serialized_new_post}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Post cannot be created due to database error",
            "message": str(e)}), 500


@main_bp.route("/api/posts/modify/<int:post_id>/", methods=["POST"])
@firebase_auth_required
def update_post(post_id):
    """Endpoint to update post made by authenticated user.

    Request Body:
        content (str): New content to update existing post.
        formatting (JSON): List of formatting object for new content.

    Responses:
        200: Post updated successfully.
        400: Request body with missing data cannot be validated.
        404: Post does not exist or not associated with user.
        500: Post update failed due to database error.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)
    data = request.get_json()

    # Validate update request body
    try:
        validated_data = PostSchema().load(data)
    except ValidationError as ve:
        return jsonify({
            "error": "Request body cannot be validated.",
            "messages": ve.messages}), 400

    # Verify post existence and ownershiup
    post = Post.query.filter_by(id=post_id, user_id=user.id).first()
    if post is None:
        return jsonify({
            "error": f"Post {post_id} cannot be found."}), 404

    # Update the post with new fields, otherwise keep existing content.
    post.content = validated_data.get("content", post.content)
    post.formatting = validated_data.get("formatting", post.formatting)
    update_post_emotion(post)

    try:
        db.session.commit(post)
        serialized_modified_post = PostSchema().dump(post)
        return jsonify({"message": f"Post {post_id} updated successfully.",
                        "post": serialized_modified_post}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": f"Post {post_id} cannot be updated due to database error.",
            "message": str(e)}), 500


@main_bp.route("/api/posts/", methods=["GET"])
@firebase_auth_required
def get_posts():
    """Endpoint to retrieve all posts made by the authenticated users.

    Request Header:
        Authorization: "Bearer <JWT_TOKEN>" (Firebase Auth Token)

    Responses:
        200: All posts for (new) user retrieved successfully.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)
    posts = Post.query.filter_by(user_id=user.id).all()

    # Empty list is returned if user has no posts.
    serialized_posts = PostSchema(many=True).dump(posts)
    return jsonify({
        "message": "All posts for user retrieved successfully.",
        "posts": serialized_posts}), 200


# --------------------------------------------------
# Weekly Advice Routes
# --------------------------------------------------
@main_bp.route("/api/weekly_advice/", methods=["GET"])
@firebase_auth_required
def get_weekly_advice():
    """Endpoint to retrieve latest weekly advice for the authenticated user.

    Request Header:
        Authorization: "Bearer <JWT_TOKEN>" (Firebase Auth Token)

    Responses:
        200: Retrieved advice of week {latest_sunday}.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Calculate the most recent Sunday date given the current date.
    latest_sunday = return_last_sunday(datetime.date.today())

    # Retrieve the latest weekly advice for the user.
    weekly_advice = WeeklyAdvice.query.filter_by(user_id=user.id,
                                                 of_week=latest_sunday).first()

    # Empty dictionary is returned if no advice is found.
    serialized_weekly_advice = WeeklyAdviceSchema().dump(weekly_advice)
    return jsonify({"message": f"Retrieved advice of week {latest_sunday}.",
                    "weekly_advice": serialized_weekly_advice}), 200


# --------------------------------------------------
# Profile Picture Routes
# --------------------------------------------------
@main_bp.route("/api/pfp/", methods=["GET"])
@firebase_auth_required
def get_profile_picture():
    """Retrieve S3 Bucket URL to user's profile picture.

    Request Header:
        Authorization: Bearer <JWT_TOKEN> (Firebase Authentication Token)

    Responses:
        200: Retrieved profile picture successfully.
        404: Profile picture does not exist.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    try:
        s3.head_object(Bucket=os.environ.get("S3_BUCKET_NAME"),
                       Key=f"{user.id}.png")
    except Exception as e:
        return jsonify({"error": "Profile picture cannot be found.",
                        "message" : str(e)}), 404

    return jsonify({
        "message": "Retrieved profile picture S3 URL.",
        "link": os.environ.get("S3_BUCKET_URL") + str(user.id) + ".png"}), 200


@main_bp.route("/api/pfp/", methods=["DELETE"])
@firebase_auth_required
def delete_users_pfp():
    """Endpoint to delete an user's profile picture.

    Request Header:
        Authorization: Bearer <JWT_TOKEN> (Firebase Authentication Token)

    Responses:
        201: Successfully deleted profile picture.
        404: Profile picture does not exist.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    try:
        s3.delete_object(Bucket=os.environ.get("S3_BUCKET_NAME"),
                         Key=f"{user.id}.png")
    except Exception as e:
        return jsonify({"error": "Profile picture cannot be found.",
                        "message": str(e)}), 404

    return jsonify({"message": "Profile picture deleted successfully."}), 201


@main_bp.route("/api/pfp/", methods=["POST"])
@firebase_auth_required
def upload_users_pfp():
    """Endpoint to upload a user's profile picture to S3 bucket."""
    uploaded_file = request.files
    file_data = uploaded_file.to_dict().get("", None)

    if file_data is None:
        return jsonify({"error": "Profile picture failed to upload."}), 404

    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    s3.upload_fileobj(file_data,
                      os.environ.get("S3_BUCKET_NAME"),
                      f"{user.id}.png",
                      ExtraArgs={"ACL": "public-read"})

    try:
        s3.head_object(Bucket=os.environ.get("S3_BUCKET_NAME"),
                       Key=f"{user.id}.png")
    except:
        return jsonify({"error": "Profile picture cannot be found."}), 404

    return jsonify({
        "message": "Upload profile picture successfully.",
        "link": os.environ.get("S3_BUCKET_URL") + str(user.id) + ".png"}), 201
