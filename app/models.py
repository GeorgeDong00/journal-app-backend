from app import db

class User(db.Model):
    """
    User model 
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=False, index=True)
    posts = db.relationship('Post', backref='user', lazy=True, cascade="all, delete-orphan")
    weekly_advices = db.relationship('WeeklyAdvice', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.firebase_uid}>'

class Post(db.Model):
    """
    Post model
    """
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sadness_amt = db.Column(db.Float, default=0.0)
    fear_amt = db.Column(db.Float, default=0.0)
    joy_amt = db.Column(db.Float, default=0.0)
    anger_amt = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f'<Post {self.id} by User {self.user_id}>'

class WeeklyAdvice(db.Model):
    """
    WeeklyAdvice model
    """
    __tablename__ = 'weekly_advices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f'<WeeklyAdvice {self.id} for User {self.user_id}>'
