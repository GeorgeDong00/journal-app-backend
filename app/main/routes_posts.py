from flask import current_app, g, jsonify, request
from marshmallow import ValidationError
from . import main_bp
from app.extensions import db
from app.models import Post, PostSchema, PostSchemaNoEmotions
from app.utils.auth import firebase_auth_required, get_or_create_user


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
    current_app.logger.info("Handling request to create a new post.")
    # Retrieve the user from User model from the Authorization bearer token.
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

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
