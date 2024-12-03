from app import app

@app.route('/')
@app.route('/api')
def index():
    user = {
        "id": "0",
        "firebase_uid": "1234567890",
        "name" : "Mock User"
    }

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

    return posts
    
