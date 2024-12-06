from flask import g, jsonify, request
from marshmallow import ValidationError
from transformers import pipeline
import boto3
from app.extensions import db
import datetime
from app.auth import firebase_auth_required
from app.models import User, PostSchema
from . import main_bp


s3 = boto3.client("s3")

# Initalization of LLM
emotion_analyzer = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=True,  # Return scores for all emotions
)


def beginning_of_week(date):
    """
    Maps a given date to the most recent Sunday, which marks
    the beginning of the week that the date is in.

    Parameters:
        date (DateTime): The date to be mapped.

    Returns:
        DateTime: The most recent Sunday before the given date.
    """
    return date - datetime.timedelta(days=date.weekday() + 1)


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


@main_bp.route("/api/posts/", methods=["POST"])
@firebase_auth_required
def create_post():
    """
    Endpoint to create a new post for the authenticated user.
    """
    expected_emotions = [
        "neutral",
        "surprise",
        "disgust",
        "anger",
        "sadness",
        "fear",
        "joy",
    ]

    firebase_uid = g.user["uid"]
    # firebase_uid = "test_user"
    user = get_or_create_user(firebase_uid)
    data = request.get_json()

    emotions_output = emotion_analyzer(data["content"])
    for emotion in emotions_output[0]:
        label, score = emotion["label"], emotion["score"]
        if label in expected_emotions:
            data[f"{label}_value"] = score

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
        return (
            jsonify(
                {"message": "Post created successfully.", "post": serialized_new_post}
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create post.", "message": str(e)}), 500


@main_bp.route("/api/posts/", methods=["GET"])
# @firebase_auth_required
def get_users_posts():
    """
    Endpoint to retrieve all posts for the authenticated user.
    """
    # firebase_uid1 = g.user['uid']
    firebase_uid = "test_user"

    user = get_or_create_user(firebase_uid)
    posts = user.posts
    post_schema = PostSchema(many=True)
    serialized_posts = post_schema.dump(posts)

    return (
        jsonify(
            {"message": "All posts have been gathered.", "posts": serialized_posts}
        ),
        200,
    )


@main_bp.route("/api/pfp/", methods=["GET"])
# @firebase_auth_required
def get_users_pfp():
    """
    Endpoint to get a link to user's profile picture.
    """
    # firebase_uid = g.user['uid']
    firebase_uid = "test_user"

    user = get_or_create_user(firebase_uid)

    try:
        s3.head_object(Bucket="notetakingprofilepicturesbucket", Key=f"{user.id}.png")
    except:
        # The image does not exist.
        return jsonify({"message": "Could not retrieve profile picture."}), 404

    return (
        jsonify(
            {
                "message": "Found profile picture.",
                "link": "https://notetakingprofilepicturesbucket.s3.us-east-2.amazonaws.com/"
                + str(user.id),
            }
        ),
        200,
    )


@main_bp.route("/api/pfp/", methods=["DELETE"])
# @firebase_auth_required
def delete_users_pfp():
    """
    Endpoint to delete a user's profile picture.
    """

    # firebase_uid = g.user['uid']
    firebase_uid = "test_user"

    user = get_or_create_user(firebase_uid)

    try:
        s3.delete_object(Bucket="notetakingprofilepicturesbucket", Key=f"{user.id}.png")
    except:
        return jsonify({"message": "Could not delete profile picture."}), 404

    return jsonify({"message": "Profile picture deleted."}), 204


@main_bp.route("/api/pfp/", methods=["POST"])
# @firebase_auth_required
def upload_users_pfp():
    """
    Endpoint to upload a user's pfp to S3 and then return a link to the image.
    """
    uploaded_file = request.files
    file_data = uploaded_file.to_dict()[""]

    # firebase_uid = g.user['uid']
    firebase_uid = "test_user"

    user = get_or_create_user(firebase_uid)

    s3.upload_fileobj(
        file_data,
        "notetakingprofilepicturesbucket",
        f"{user.id}.png",
        ExtraArgs={"ACL": "public-read"},
    )

    try:
        s3.head_object(Bucket="notetakingprofilepicturesbucket", Key=f"{user.id}.png")
    except:
        # The image does not exist.
        return jsonify({"message": "Could not retrieve profile picture."}), 404

    return (
        jsonify(
            {
                "message": "Created profile picture.",
                "link": "https://notetakingprofilepicturesbucket.s3.us-east-2.amazonaws.com/"
                + str(user.id)
                + ".png",
            }
        ),
        200,
    )
