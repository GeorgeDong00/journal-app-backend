from flask import current_app, g, jsonify, request
import boto3
import os
from . import main_bp
from app.utils.auth import firebase_auth_required, get_or_create_user


# Initialize S3 client to store profile picture
s3 = boto3.client("s3")

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
