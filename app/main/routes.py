from flask import g, jsonify, request
from marshmallow import ValidationError
from app.extensions import db
import app.models.post as post
import app.models.weekly_advice as Weekly_Advice
import datetime
from app.auth import firebase_auth_required
import boto3
import io
import json

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
@firebase_auth_required
def create_post():
    """
    Endpoint to create a new post for the authenticated user.
    """
    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)
    data = request.get_json()
    emotions = emotion_analyzer(data['content'])
  
    data['anger_value'] = emotions[0][0]['score']
    data['disgust_value'] = emotions[0][1]['score']
    data['fear_value'] = emotions[0][2]['score']
    data['joy_value'] = emotions[0][3]['score']
    data['neutral_value'] = emotions[0][4]['score']
    data['sadness_value'] = emotions[0][5]['score']
    data['surprise_value'] = emotions[0][6]['score']

    # This is awful
    content = data['formatting']

    data.pop('formatting')

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

        #Blank formatting array for front end
        json_string = json.dumps(content)
        json_file_like = io.BytesIO(json_string.encode('utf-8'))
        s3.upload_fileobj(json_file_like, "notetakingprofilepicturesbucket", "formatting" + str(new_post.id) + ".json", ExtraArgs = {"ACL" : "public-read"})
        serialized_new_post['formatting'] = content

        return jsonify({"message": "Post created successfully.", "post": serialized_new_post}),201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create post.", "message": str(e)}), 500

@main_bp.route("/api/posts/modify/<int:post_id>/", methods=["POST"])
@firebase_auth_required
def modify_post(post_id):
    """
    Endpoint to modify for the authenticated user.
    """
    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)
    data = request.get_json()

    post = Post.query.filter_by(id=post_id).first()
    if(post is None):
        return jsonify({"error": "Failed to find find existing post with that id."}), 500
    elif(post.user_id != user.id):
        return jsonify({"error": "You cannot modify another user's post!"}), 500

    post.content = data['content']

    emotions = emotion_analyzer(data['content'])
  
    post.anger_value = emotions[0][0]['score']
    post.disgust_value = emotions[0][1]['score']
    post.fear_value = emotions[0][2]['score']
    post.joy_value = emotions[0][3]['score']
    post.neutral_value = emotions[0][4]['score']
    post.sadness_value = emotions[0][5]['score']
    post.surprise_value = emotions[0][6]['score']

    try:
        db.session.commit()
        post_schema = PostSchema()
        serialized_modified_post = post_schema.dump(post)
        #Blank formatting array for front end
        return jsonify({"message": "Post created successfully.", "post": serialized_modified_post, "formatting" : []}),201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to modify post.", "message": str(e)}), 500
  
@main_bp.route("/api/posts/", methods=["GET"])
@firebase_auth_required
def get_users_posts():
    """
    Endpoint to get a user's posts for the authenticated user.
    """

    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)
    posts = user.posts
    post_schema = PostSchema()
    all_posts = []

    for post in posts:
        post = post_schema.dump(post)
        response = s3.get_object(Bucket="notetakingprofilepicturesbucket", Key="formatting" + str(post['id']) + ".json")
        content = response['Body'].read().decode('utf-8')
        
        # Parse JSON content into a Python dictionary
        data = json.loads(content)
        post['formatting'] = data

        all_posts.append(post)
    
    return jsonify({"message": "All posts have been gathered.", "posts": all_posts}),200


@main_bp.route("/api/weekly_advice/", methods=["GET"])
@firebase_auth_required
def get_users_weekly_advice():
    """
    Endpoint to create a new post for the authenticated user.
    """

    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)
    weekly_advices = user.weekly_advices
    weekly_advice_schema = Weekly_Advice.WeeklyAdviceSchema()
    lastSunday = returnLastSunday(datetime.date.today())

    for weekly_advice in weekly_advices:
        if(weekly_advice.of_week.date() == lastSunday):
            serialized_weekly_advice = weekly_advice_schema.dump(weekly_advice)
            return jsonify({"message": "Weekly Advice of week " + str(lastSunday) + " has been retrieved", 'weekly_advice' : serialized_weekly_advice}),200

    return jsonify({"message": "Unable to find a weekly advice for " + str(lastSunday)}),404


@main_bp.route("/api/pfp/", methods=["GET"])
@firebase_auth_required
def get_users_pfp():
    """
    Endpoint to get a link to user's profile picture.
    """

    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)

    try:
        s3.head_object(Bucket='notetakingprofilepicturesbucket', Key=f'{user.id}.png')
    except:
        # The image does not exist.
        return jsonify({"message": "Could not retrieve profile picture."}),404

    return jsonify({"message": "Found profile picture.", "link" : "https://notetakingprofilepicturesbucket.s3.us-east-2.amazonaws.com/" + str(user.id) + '.png'} ),200

@main_bp.route("/api/pfp/", methods=["DELETE"])
@firebase_auth_required
def delete_users_pfp():
    """
    Endpoint to delete a user's profile picture.
    """

    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)

    try:
        response = s3.delete_object(Bucket='notetakingprofilepicturesbucket', Key=f'{user.id}.png')
    except:
        return jsonify({"message": "Could not delete profile picture."}),404

    return jsonify({"message": "Profile picture deleted."}),201

@main_bp.route("/api/posts/<int:post_id>/", methods=["DELETE"])
@firebase_auth_required
def delete_users_post(post_id):
    """
    Endpoint to delete a user's post.
    """

    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)
    post = Post.query.filter_by(id=post_id).first()

    if(post.user_id != user.id):
        return jsonify({"message": "You cannot delete another user's notes!"}),404

    if(post is None):
        return jsonify({"message": "Post not found!"}),404

    db.session.delete(post)
    db.session.commit()

    return jsonify({"message": "Post deleted."}),201



@main_bp.route("/api/pfp/", methods=["POST"])
@firebase_auth_required
def upload_users_pfp():
    """
    Endpoint to upload a user's pfp to S3 and then return a link to the image. 
    """

    uploaded_file = request.files
    file_data = uploaded_file.to_dict().get('',None) 

    if(file_data is None):
        return jsonify({"message": "Could not retrieve profile picture."}),404

    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)

    s3.upload_fileobj(file_data, "notetakingprofilepicturesbucket", f'{user.id}.png', ExtraArgs = {"ACL" : "public-read"})

    try:
        s3.head_object(Bucket='notetakingprofilepicturesbucket', Key=f'{user.id}.png')
    except:
        # The image does not exist.
        return jsonify({"message": "Could not retrieve profile picture."}),404

    return jsonify({"message": "Created profile picture.", "link" : "https://notetakingprofilepicturesbucket.s3.us-east-2.amazonaws.com/" + str(user.id) + '.png'}),200
routes.py
9 KB
