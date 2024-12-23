from flask import g, jsonify, request, current_app
import datetime
import os
from marshmallow import ValidationError
import boto3

from app.extensions import db
from app.auth import firebase_auth_required
from app.models import (User,
                        Post, PostSchema, PostSchemaNoEmotions,
                        WeeklyAdvice, WeeklyAdviceSchema)
from . import main_bp


# Initialize S3 client to store profile picture
s3 = boto3.client("s3")


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
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
    current_app.logger.info(f"Retrieved {user} of Firebase UID {firebase_uid}.")

    if not user:
        user = User(firebase_uid=firebase_uid)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"Created {user} of Firebase UID {firebase_uid}.")
    return user


# --------------------------------------------------
# Post Routes
# --------------------------------------------------
@main_bp.route("/api/posts/", methods=["POST"])
# @firebase_auth_required
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
    current_app.logger.info("Handling request to create a new post.")
    # Retrieve the user from User model from the Authorization bearer token.
    # firebase_uid = g.user["uid"]
    user = get_or_create_user("test=user")

    # Validate request 'content' and 'formatting' fields.
    data = request.get_json()
    try:
        # Empty 'formatting' data will be replaced with empty List.
        validated_data = PostSchema().load(data)
        current_app.logger.info("Validated request data.")

    except ValidationError as ve:
        current_app.logger.error(f"{ve.messages["content"][0]}")
        return jsonify({"error": f"Failed validation with {ve.messages['content'][0]}."}), 400

    new_post = Post(**validated_data)
    new_post.user_id = user.id
    current_app.logger.info(f"Added user id to {new_post}.")

    # Save new Post to the database.
    try:
        db.session.add(new_post)
        db.session.commit()
        current_app.logger.info(f"Committed {new_post} to database.")
        serialized_new_post = PostSchemaNoEmotions().dump(new_post)

        # Offload emotion analysis to Celery Worker
        current_app.celery.send_task("generate_content_emotional_scores",
                                     args=[new_post.content, new_post.id])
        return jsonify({"message": ("Post created successfully. "
                                    "Currently analyzing emotions—check back in one minute."),
                        "post": serialized_new_post}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Rollback occured since creation failed with {str(e)}.")
        return jsonify({"error": f"Post cannot be created with {str(e)}."}), 500


@main_bp.route("/api/post/<int:post_id>/", methods=["PUT"])
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
    current_app.logger.info(f"Handling request to update post instance {post_id}.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)
    data = request.get_json()

    # Validate update request body
    try:
        validated_data = PostSchema().load(data)
    except ValidationError as ve:
        return jsonify({"error": f"Failed validation with {ve.messages['content'][0]}."}), 400

    # Verify post existence and ownershiup
    post_instance = Post.query.filter_by(id=post_id, user_id=user.id).first()
    current_app.logger.info(f"Retrieved {post_instance}.")
    if post_instance is None:
        return jsonify({"error": f"Post {post_id} cannot be found."}), 404

    # Update the post with new fields, otherwise keep existing content.
    post_instance.content = validated_data.get("content", post_instance.content)
    post_instance.formatting = validated_data.get("formatting", post_instance.formatting)
    current_app.logger.info(f"Updated {post_instance} with new content.")

    try:
        db.session.commit()
        current_app.logger.info(f"Committed new {post_instance} to database.")
        serialized_modified_post = PostSchemaNoEmotions().dump(post_instance)

        # Offload emotion analysis to Celery Worker
        current_app.celery.send_task("generate_content_emotional_scores",
                                     args=[post_instance.content, post_instance.id])

        return jsonify({"message": (f"Post {post_id} updated successfully. "
                                    "Currently analyzing emotions—check back in one minute."),
                        "post": serialized_modified_post}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Rollback occured since update failed with {str(e)}.")
        return jsonify({"error": f"Failed to update Post {post_id} with {str(e)}."}), 500


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
    current_app.logger.info("Handling request to retrieve all post instances.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Retrieve all posts made by the user.
    post_instances = Post.query.filter_by(user_id=user.id).all()
    current_app.logger.info(f"Retrieved {len(post_instances)} post instances.")

    # Marshmallow serializes the post instances into JSON
    serialized_posts = PostSchema(many=True).dump(post_instances)
    return jsonify({
        "message": "All posts made by user retrieved successfully.",
        "posts": serialized_posts}), 200

@main_bp.route("/api/post/<int:post_id>/", methods=["GET"])
@firebase_auth_required
def get_post(post_id):
    """Endpoint to retrieve a specific post made by the authenticated user.

    Request Header:
        Authorization (str): "Bearer <JWT_TOKEN>" (Firebase Auth Token)
        post_id (int): The ID of the post to retrieve.

    Returns:
        200 OK: Message and serialized list of all user's posts.

    Raises:
        400 Bad Request: If the post ID is invalid.
        401 Unauthorized: If the token is invalid or missing.
        404 Not Found: If the post does not exist or is not associated with the user.
    """
    current_app.logger.info(f"Handling request to retrieve post instance {post_id}.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    if post_id and post_id <= 0:
        current_app.logger.error(f"Invalid post id {post_id} provided.")
        return jsonify({"error": "Requested post id cannot be zero or less."}), 400

    post_instance = Post.query.filter_by(id=post_id,
                                         user_id=user.id).first()
    if not post_instance:
        return jsonify({"error": f"Post {post_id} cannot be found."}), 404

    current_app.logger.info(f"Retrieved {post_instance}.")
    serialized_post = PostSchema().dump(post_instance)
    return jsonify({"message": "Post retrieved successfully.",
                    "post": serialized_post}), 200


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
    current_app.logger.info("Handling request to retrieve latest weekly advice.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Calculate the most recent Sunday date given the current date.
    current_utc_date = datetime.now(datetime.timezone.utc).date()
    latest_sunday = return_previous_sunday(current_utc_date)
    current_app.logger(f"Returned latest Sunday date as {latest_sunday}.")

    # Retrieve the latest weekly advice for the user.
    advice = WeeklyAdvice.query.filter_by(user_id=user.id,
                                          of_week=latest_sunday).first()
    current_app.logger.info(f"Retrieved {advice}.")

    # Empty dictionary is returned if no advice is found.
    serialized_weekly_advice = WeeklyAdviceSchema().dump(advice)
    return jsonify({"message": f"Week of {latest_sunday} has {len(advice)} advice.",
                    "advice": serialized_weekly_advice}), 200


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
    current_app.logger.info("Handling request to retrieve profile picture.")
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
    current_app.logger.info("Handling request to delete profile picture.")
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
    current_app.logger.info("Handling request to upload profile picture.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Retrieve uploaded file from request "file" field.
    file_data = request.files.get('ImageFile', None)
    if file_data is None:
        return jsonify({"error": "Request is missing image or `ImageFile` key."}), 400

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
