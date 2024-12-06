from flask import g, jsonify, request
from marshmallow import ValidationError
from app.extensions import db
import app.models.post as post
import app.models.weekly_advice as weekly_advice
import datetime
from app.auth import firebase_auth_required
import boto3


s3 = boto3.client('s3')

from app.models import (
    User,
    Post, 
    PostSchema
)
from . import main_bp
from transformers import pipeline 


# Initalization of LLM
emotion_analyzer = pipeline(
    "text-classification", 
    model="j-hartmann/emotion-english-distilroberta-base", 
   return_all_scores=True  # Return scores for all emotions
)


def returnLastSunday(date):
    '''
    @param date - datetime object
    
    '''

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


@main_bp.route("/api/posts/", methods=["POST"])
#@firebase_auth_required
def create_post():
    """
    Endpoint to create a new post for the authenticated user.
    """
 #  firebase_uid = g.user['uid']
    firebase_uid = "test_user"
    user = get_or_create_user(firebase_uid)
    data = request.get_json()
    emotions = emotion_analyzer(data['content'])
    print(emotions)
  
    data['anger_value'] = emotions[0][0]['score']
    data['disgust_value'] = emotions[0][1]['score']
    data['fear_value'] = emotions[0][2]['score']
    data['joy_value'] = emotions[0][3]['score']
    data['neutral_value'] = emotions[0][4]['score']
    data['sadness_value'] = emotions[0][5]['score']
    data['surprise_value'] = emotions[0][6]['score']

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


  
@main_bp.route("/api/posts/", methods=["GET"])
#@firebase_auth_required
def get_users_posts():
    """
    Endpoint to create a new post for the authenticated user.
    """

    #firebase_uid1 = g.user['uid']
    firebase_uid = "test_user"
    user = get_or_create_user(firebase_uid)


    posts = user.posts

    post_schema = PostSchema()

    all_posts = []
    for post in posts:
        post = post_schema.dump(post)
        all_posts.append(post)

    return jsonify({"message": "All posts have been gathered.", "posts": all_posts}),200


@main_bp.route("/api/pfp/", methods=["GET"])
#@firebase_auth_required
def get_users_pfp():
    """
    Endpoint to get a link to user's profile picture.
    """

    #firebase_uid = g.user['uid']
    firebase_uid = "test_user"

    user = get_or_create_user(firebase_uid)

    try:
        s3.head_object(Bucket='notetakingprofilepicturesbucket', Key=f'{user.id}.png')
    except:
        # The image does not exist.
        return jsonify({"message": "Could not retrieve profile picture."}),404

    return jsonify({"message": "Found profile picture.", "link" : "https://notetakingprofilepicturesbucket.s3.us-east-2.amazonaws.com/" + str(user.id)}),200

@main_bp.route("/api/pfp/", methods=["DELETE"])
#@firebase_auth_required
def delete_users_pfp():

    """
    Endpoint to delete a user's profile picture.
    """

    #firebase_uid = g.user['uid']
    firebase_uid = "test_user"

    user = get_or_create_user(firebase_uid)

    try:
        response = s3.delete_object(Bucket='notetakingprofilepicturesbucket', Key=f'{user.id}.png')
    except:
        return jsonify({"message": "Could not delete profile picture."}),404

    return jsonify({"message": "Profile picture deleted."}),204


@main_bp.route("/api/pfp/", methods=["POST"])
#@firebase_auth_required
def upload_users_pfp():
    """
    Endpoint to upload a user's pfp to S3 and then return a link to the image. 
    """
    uploaded_file = request.files
    file_data = uploaded_file.to_dict()['']
    
   # firebase_uid = g.user['uid']
    firebase_uid = "test_user"

    user = get_or_create_user(firebase_uid)

    s3.upload_fileobj(file_data, "notetakingprofilepicturesbucket", f'{user.id}.png', ExtraArgs = {"ACL" : "public-read"})

    try:
        s3.head_object(Bucket='notetakingprofilepicturesbucket', Key=f'{user.id}.png')
    except:
        # The image does not exist.
        return jsonify({"message": "Could not retrieve profile picture."}),404

    return jsonify({"message": "Created profile picture.", "link" : "https://notetakingprofilepicturesbucket.s3.us-east-2.amazonaws.com/" + str(user.id) + '.png'}),200

    

