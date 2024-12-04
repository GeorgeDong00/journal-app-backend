from flask import g, jsonify, request
from marshmallow import ValidationError
from app.extensions import db
from app.auth import firebase_auth_required
from app.models import (
    User,
    Post, 
    PostSchema
)
from . import main_bp


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
@firebase_auth_required
def create_post():
    """
    Endpoint to create a new post for the authenticated user.
    """
    firebase_uid = g.user['uid']
    # firebase_uid = "test_user"
    user = get_or_create_user(firebase_uid)
    data = request.get_json()

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
