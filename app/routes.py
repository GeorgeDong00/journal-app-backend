from app import app
from app.auth import firebase_auth_required
from flask import jsonify, g

posts = [
    {
        "id" : "0",
        "user_id" : "0", 
        "created_at" : "Hello, World!", 
        "post_content" : "This is a test post.",
        "sadness_amt" : 0.5,
        "fear_amt" : 0.5,
        "joy_amt" : 0.5,
        "anger_amt" : 0.5
    }
]

@app.route('/api')
@firebase_auth_required
def index():
    """
    Endpoint to test authentication.
    """
    return jsonify({'message': 'Authentication successful!'}), 200

@app.route('/api/posts')
@firebase_auth_required
def get_posts():
    """
    Endpoint to retrieve user's posts.
    """
    return jsonify({"posts" : posts}), 200