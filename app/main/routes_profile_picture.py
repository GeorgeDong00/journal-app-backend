from flask import current_app, g, jsonify, request
import os
from botocore.exceptions import ClientError
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
from . import main_bp
from app.utils.auth import firebase_auth_required, get_or_create_user
from app.utils.exceptions import raise_http_exception

# Instantiates the S3 bucket name and URL along with the allowed file extensions
s3_bucket_name = os.environ.get("S3_PROFILE_PIC_BUCKET")
s3_bucket_url = os.environ.get("S3_PROFILE_PIC_BUCKET_URL")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

@main_bp.route("/api/pfp/", methods=["GET"])
@firebase_auth_required
def get_profile_picture():
    """Retrieve the S3 bucket URL of the authenticated user's profile picture."""
    current_app.logger.info("Handling request to retrieve profile picture.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)
    s3_client, user_id = current_app.extensions["s3_client"], str(user.id)

    try:
        s3_client.head_object(
            Bucket=s3_bucket_name,
            Key=user_id
        )
        retrieval_link = f"{s3_bucket_url}/{user_id}"
        return jsonify({
            "message": "Successfully retrieved profile picture.",
            "link": retrieval_link
        }), 200

    except ClientError as ce:
        current_app.logger.error(f"Failed to retrieve profile picture: {ce}")
        error_message = ce.response.get("Error", {}).get("Message")
        if error_message in ["Not Found", "404"]:
            raise_http_exception(NotFound, "Profile picture not found.", str(error_message))
        raise_http_exception(InternalServerError, "S3 error when accessing profile picture.", str(error_message))

@main_bp.route("/api/pfp/", methods=["DELETE"])
@firebase_auth_required
def delete_users_pfp():
    """Endpoint to delete the authenticated user's profile picture."""
    current_app.logger.info("Handling request to delete profile picture.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)
    user_id = str(user.id)
    s3_client = current_app.extensions["s3_client"]

    try:
        # Verify the user's profile picture exists in S3 before deletion
        s3_client.head_object(Bucket=s3_bucket_name, Key=user_id)

        # Delete the user's profile picture from S3
        s3_client.delete_object(
            Bucket=s3_bucket_name,
            Key=user_id
        )
        deleted_link = f"{s3_bucket_url}/{user_id}"
        return jsonify({
            "message": "Successfully deleted profile picture.",
            "link": deleted_link
        }), 200

    except ClientError as ce:
        current_app.logger.error(f"Failed to delete profile picture: {ce}.")
        error_message = ce.response.get("Error", {}).get("Message")
        if error_message in ["Not Found", "404"]:
            raise_http_exception(NotFound, "Failed to delete profile picture.", str(error_message))
        raise_http_exception(InternalServerError, "S3 error when deleting profile picture.", str(error_message))

@main_bp.route("/api/pfp/", methods=["POST"])
@firebase_auth_required
def upload_users_pfp():
    """Endpoint to upload the authenticated user's profile picture to S3. The original API design was to
    overwrite the existing profile picture with the new one.
    """
    current_app.logger.info("Handling request to upload profile picture.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)
    user_id = str(user.id)
    s3_client = current_app.extensions["s3_client"]

    try:
        # Verifies request has proper file data and profile picture is of supported file type
        if "ImageFile" not in request.files:
            raise KeyError("Missing ImageFile key within the request form body.")

        image_file = request.files.get('ImageFile')
        if image_file.filename == "":
            raise KeyError("No image file was found within request.")

        file_name = image_file.filename
        extension = file_name.rsplit('.', 1)[1].lower() if '.' in file_name else ''
        if extension not in ALLOWED_EXTENSIONS:
            raise KeyError(f"Invalid image file type. Only {', '.join(ALLOWED_EXTENSIONS)} files are supported.")

    # Uploads the profile picture to S3 with the user's ID as its name
        s3_client.upload_fileobj(
            Fileobj=image_file,
            Bucket=s3_bucket_name,
            Key=user_id,
            ExtraArgs={"ContentType": image_file.content_type, "ACL": "public-read"}
        )
        profile_picture_link = f"{s3_bucket_url}/{user_id}"
        return jsonify({
            "message": "Successfully uploaded profile picture.",
            "link": profile_picture_link}
        ), 201

    except KeyError as ke:
        current_app.logger.error(f"Invalid upload profile picture request: {ke}")
        raise_http_exception(BadRequest, "Invalid request or form data provided.", str(ke))
    except ClientError as ce:
        current_app.logger.error(f"An error occured during profile picture upload for {user_id}: {ce}.")
        error_message = ce.response.get("Error", {}).get("Message")
        raise_http_exception(InternalServerError, "S3 error when uploading profile picture.", str(error_message))
