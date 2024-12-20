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


def return_previous_sunday(date : datetime.date) -> datetime.date:
    """Returns the datetime of latest previous (last week) Sunday before given
    date. The datetime is set to midnight UTC and is used to retrieve the latest
    week that has already passed.

    Args:
        date: UTC date to calculate the previous Sunday.

    Returns:
        datetime.date: Last week Sunday before the given date.
    """
    previous_sunday_date = date - datetime.timedelta(days=date.weekday() + 1)

    # Combine previous Sunday date with midnight time and UTC timezone.
    return datetime.datetime.combine(
        previous_sunday_date,
        datetime.time.min,
        tzinfo=datetime.timezone.utc
    )


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


def update_post_emotion(post_instance: Post) -> Post:
    """Analyze the emotion of post's content, and add/update post instance with emotion fields.

    Args:
        post_instance: The Post instance to analyze.

    Returns:
        post_instance: The updated Post instance with emotion scores.
    """
    # TODO: Refactor by handing-off to Celery Worker
    emotions_output = emotion_analyzer(post_instance.content)

    if not emotions_output:
        return post_instance

    for emotion_data in emotions_output[0]:
        emotion = emotion_data["label"].lower()
        score = emotion_data["score"]
        # Add emotion score to Post instance, otherwise update existing score.
        if emotion in SUPPORTED_EMOTIONS:
            setattr(post_instance, f"{emotion}_value", score)
    return post_instance


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

    Returns:
        201 OK: Message and serialized new post instance.

    Raises:
        400 Bad Request: If request body contains missing or invalid values.
        401 Unauthorized: If the token is invalid or missing.
        500 Internal Server Error: If a database error occurs.
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
    new_post = update_post_emotion(new_post)

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


@main_bp.route("/api/posts/modify/<int:post_id>/", methods=["PUT"])
@firebase_auth_required
def update_post(post_id):
    """Endpoint to update a post made by the authenticated user.

    Request Body:
        content (str): New content to update the existing post.
        formatting (JSON): A list of formatting objects describing how
            content should be formatted.

    Returns:
        200 OK: Message and serialized updated post instance.

    Raises:
        400 Bad Request: If request body contains missing or invalid values.
        401 Unauthorized: If the token is invalid or missing.
        404 Not Found: If specified post does not exist or associated with user.
        500 Internal Server Error: If a database error occurs.
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
    post_instance = Post.query.filter_by(id=post_id, user_id=user.id).first()
    if post_instance is None:
        return jsonify({
            "error": f"Post {post_id} cannot be found."}), 404

    # Update the post with new fields, otherwise keep existing content.
    post_instance.content = validated_data.get("content", post_instance.content)
    post_instance.formatting = validated_data.get("formatting", post_instance.formatting)
    update_post_emotion(post_instance)

    try:
        db.session.commit()
        serialized_modified_post = PostSchema().dump(post_instance)
        return jsonify({"message": f"Post {post_id} updated successfully.",
                        "post": serialized_modified_post}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": f"Post {post_id} cannot be updated due to database error.",
            "message": str(e)}), 500


@main_bp.route("/api/posts/", methods=["GET"])
@firebase_auth_required
def get_posts():
    """Endpoint to retrieve all posts made by the authenticated user.

    Request Header:
        Authorization (str): "Bearer <JWT_TOKEN>" (Firebase Auth Token)

    Returns:
        200 OK: Message and serialized list of all user's posts.

    Raises:
        401 Unauthorized: If the token is invalid or missing.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Retrieve all posts made by the user.
    post_instances = Post.query.filter_by(user_id=user.id).all()

    # Marshmallow serializes the post instances into JSON
    serialized_posts = PostSchema(many=True).dump(post_instances)
    return jsonify({
        "message": "All posts made by user retrieved successfully.",
        "posts": serialized_posts}), 200


# --------------------------------------------------
# Weekly Advice Routes
# --------------------------------------------------
@main_bp.route("/api/weekly_advice/", methods=["GET"])
@firebase_auth_required
def get_weekly_advice():
    """Endpoint to retrieve the latest weekly advice for the authenticated user.

    Request Header:
        Authorization (str): "Bearer <JWT_TOKEN>" (Firebase Auth Token)

    Returns:
        200 OK: Message and serialized latest weekly advice or empty List if no advice is found.

    Raises:
        401 Unauthorized: If the token is invalid or missing.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Calculate the most recent Sunday date given the current date.
    current_utc_date = datetime.now(datetime.timezone.utc).date()
    latest_sunday = return_previous_sunday(current_utc_date)

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
    """Retrieve the S3 bucket URL of the authenticated user's profile picture.

    Request Header:
        Authorization (str): "Bearer <JWT_TOKEN>" (Firebase Auth Token)

    Returns:
        200 OK: Message and the S3 bucket URL to the profile picture.

    Raises:
        401 Unauthorized: If the token is invalid or missing.
        404 Not Found: If the profile picture does not exist.
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
    """Endpoint to delete the authenticated user's profile picture.

    Request Header:
        Authorization (str): "Bearer <JWT_TOKEN>" (Firebase Auth Token)

    Returns:
        200 OK: Message indicating successful deletion of the profile picture.

    Raises:
        401 Unauthorized: If the token is invalid or missing.
        404 Not Found: If the profile picture does not exist.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    try:
        s3.delete_object(Bucket=os.environ.get("S3_BUCKET_NAME"),
                         Key=f"{user.id}.png")
    except Exception as e:
        return jsonify({"error": "Profile picture cannot be found.",
                        "message": str(e)}), 404

    return jsonify({"message": "Profile picture deleted successfully."}), 200


@main_bp.route("/api/pfp/", methods=["POST"])
@firebase_auth_required
def upload_users_pfp():
    """Endpoint to upload the authenticated user's profile picture to S3.

    Request Body:
        file (File): The profile picture file to be uploaded.

    Returns:
        201 Created: Message and S3 bucket URL of the uploaded profile picture.

    Raises:
        400 Bad Request: If no file is provided or upload fails.
        401 Unauthorized: If the token is invalid or missing.
        404 Not Found: If the profile picture cannot be found after upload.
    """
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Retrieve uploaded file from request "file" field.
    file_data = request.files.get('file', None)
    if file_data is None:
        return jsonify({"error": "Profile picture failed to upload."}), 400

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
