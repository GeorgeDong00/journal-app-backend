from flask import current_app, g, jsonify, request
from marshmallow import ValidationError
from werkzeug.exceptions import NotFound
from . import main_bp
from app.extensions import db
from app.models import Post, PostSchema, PostSchemaNoEmotions
from app.utils.auth import firebase_auth_required, get_or_create_user
from app.utils.exceptions import raise_http_exception


@main_bp.route("/api/posts/", methods=["POST"])
@firebase_auth_required
def create_post():
    """Endpoint to create a new post for the authenticated user."""
    current_app.logger.info("Handling request to create a new post.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    try:
        # Validate Request 'content' and 'formatting' fields.
        data = request.get_json()
        validated_data = PostSchema().load(data)

        # Create a new Post instance with user ID and validated data.
        new_post = Post(**validated_data, user_id=user.id)
        current_app.logger.info(f"Created new post instance by user {user.id}.")

        # Save new Post instance to the database.
        db.session.add(new_post)
        db.session.commit()
        current_app.logger.info(f"Add and committed new post {new_post.id}.")

        # Offload emotion analysis to Celery Worker.
        current_app.celery.send_task(
            "generate_content_emotional_scores",
            args=[new_post.content, new_post.id]
        )
        current_app.logger.info(f"Enqueued Celery task to add emotional scores to post {new_post.id}.")

        serialized_new_post = PostSchemaNoEmotions().dump(new_post)
        return jsonify({
            "message": "Successfully created new post. Check back in a minute for emotional score.",
            "post": serialized_new_post
        }), 200

    except ValidationError as ve:
        current_app.logger.error(f"Failed to validate request to create new post: {ve}")
        raise ve
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create new post: {e}")
        raise e


@main_bp.route("/api/posts/<int:post_id>/", methods=["PUT"])
@firebase_auth_required
def update_post(post_id):
    """Endpoint to update a post made by the authenticated user."""
    current_app.logger.info(f"Handling request to update post instance {post_id}.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    try:
        # Validate update post request body.
        data = request.get_json()
        validated_data = PostSchema().load(data)

        # Verify post existence and ownership.
        post_instance = Post.query.filter_by(id=post_id,
                                             user_id=user.id).first()
        if post_instance is None:
            raise LookupError(f"User is not associated with post {post_id}.")

        # Update the post with request fields with support for idempotency.
        old_content, old_format = post_instance.content, post_instance.formatting
        post_instance.content = validated_data.get("content", old_content)
        post_instance.formatting = validated_data.get("formatting", old_format)
        current_app.logger.info(f"Updated post {post_instance.id} with request data.")

        # Commit the updated post to the database.
        db.session.commit()
        current_app.logger.info(f"Committed updated post {post_instance.id} to database.")

        # Offload emotion analysis to Celery Worker.
        current_app.celery.send_task(
            "generate_content_emotional_scores",
            args=[post_instance.content, post_instance.id]
        )
        current_app.logger.info(f"Enqueued Celery task to update post {post_instance.id} with new emotional scores.")

        serialized_modified_post = PostSchemaNoEmotions().dump(post_instance)
        return jsonify({
            "message": f"Successfully updated post {post_id}. Check back in a minute for emotional score.",
            "post": serialized_modified_post
        }), 200

    except ValidationError as ve:
        current_app.logger.error(f"Failed to validate request to update post: {ve}")
        raise ve
    except LookupError as le:
        current_app.logger.error(f"Failed to find request post: {le}.")
        raise_http_exception(NotFound, f"Post {post_id} cannot be found.", str(le))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update post {post_instance.id}: {e}")
        raise e


@main_bp.route("/api/posts/", methods=["GET"])
@firebase_auth_required
def get_posts():
    """Endpoint to retrieve all posts made by the authenticated user."""
    current_app.logger.info("Handling request to retrieve all post instances.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    try:
        # Retrieve all posts made by the user.
        post_instances = Post.query.filter_by(user_id=user.id).all()
        current_app.logger.info(f"Retrieved {len(post_instances)} posts by user {user.id}.")

        # Marshmallow serializes the post instances into JSON.
        serialized_posts = PostSchema(many=True).dump(post_instances)
        return jsonify({
            "message": f"Successfully retrieved {len(post_instances)} posts by user {user.id}.",
            "posts": serialized_posts
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to retrieve all posts by user {user.id}: {e}.")
        raise e


@main_bp.route("/api/posts/<int:post_id>/", methods=["GET"])
@firebase_auth_required
def get_post(post_id):
    """Endpoint to retrieve a specific post made by the authenticated user."""
    current_app.logger.info(f"Handling request to retrieve post instance {post_id}.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    try:
        # Retrieve the post instance and validate ownership.
        post_instance = Post.query.filter_by(id=post_id,
                                             user_id=user.id).first()
        if not post_instance:
            raise LookupError(f"User is not associated with a post {post_id}.")

        current_app.logger.info(f"Retrieved post {post_instance.id} by user {user.id}.")
        serialized_post = PostSchema().dump(post_instance)
        return jsonify({
            "message": f"Successfully retrieved post {post_id}.",
            "post": serialized_post
        }), 200

    except LookupError as le:
        current_app.logger.error(f"Failed to requested post: {le}")
        raise_http_exception(NotFound, f"Post {post_id} cannot be found.", str(le))
    except Exception as e:
        current_app.logger.error(f"Failed to retrieve post {post_id}: {e}.")
        raise e
