from app import app, db
from app.auth import firebase_auth_required
from flask import jsonify, g, request
from app.models import User, Post, WeeklyAdvice

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

@app.route('/api')
@firebase_auth_required
def index():
    """
    Endpoint to test authentication.
    """
    return jsonify({'message': 'Authentication successful!'}), 200

@app.route('/api/posts', methods=['POST'])
@firebase_auth_required
def create_post():
    """
    Endpoint to retrieve user's posts.
    """
    firebase_uid = g.user['uid']
    user = get_or_create_user(firebase_uid)
    data = request.get_json()

    content = data.get('content')
    if not content:
        return jsonify({'error': 'Content is required.'}), 400
    
    sadness_amt = data.get('sadness_amt', 0.0)
    fear_amt = data.get('fear_amt', 0.0)
    joy_amt = data.get('joy_amt', 0.0)
    anger_amt = data.get('anger_amt', 0.0)

    new_post = Post(
        user_id=user.id,
        content=content,
        sadness_amt=sadness_amt,
        fear_amt=fear_amt,
        joy_amt=joy_amt,
        anger_amt=anger_amt
    )

    try:
        db.session.add(new_post)
        db.session.commit()
        return jsonify({
            'message': 'Post created successfully.',
            'post': {
                'id': new_post.id,
                'content': new_post.content,
                'sadness_amt': new_post.sadness_amt,
                'fear_amt': new_post.fear_amt,
                'joy_amt': new_post.joy_amt,
                'anger_amt': new_post.anger_amt,
                'created_at': new_post.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create post.', 'message': str(e)}), 500