from app import db, ma
from marshmallow import fields, validate

class User(db.Model):
    """
    User model representing the journal user and their daily posts and weekly advices. 

    Attributes:
    - id (int): Autogenerated primary key
    - firebase_uid (str): Retrieved from Firebase Bearer token and used as a index

    Relationships:
    - posts (List[Post]): One-to-Many relationship with Post model
    - weekly_advices (List[WeeklyAdvice]): One to Many relationship with WeeklyAdvice model
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=False, index=True)
    posts = db.relationship('Post', backref='user', lazy=True, cascade="all, delete-orphan")
    weekly_advices = db.relationship('WeeklyAdvice', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        """
        String representation of the User instance
        """
        return f'<User {self.firebase_uid}>'

class UserSchema(ma.SQLAlchemySchema):
    """
    Marshmallow schema for serializing and deserializing User instances.

    Data Validation:
    - firebase_uid: Required and cannot be empty
    """
    class Meta:
        model = User
        load_instance = True

    id = ma.auto_field()
    firebase_uid = ma.auto_field(required=True, validate=validate.Length(min=1))

class Post(db.Model):
    """
    Post model representing a user's journal post with detected emotions derived from a LLM (Large Language Model).

    Attributes:
    - id (int): Autogenerated primary key
    - user_id (int): Foreign key referencing the User
    - content (str): Journal post content
    - sadness_amt (float): Detected sadness emotion amount
    - fear_amt (float): Detected fear emotion amount
    - joy_amt (float): Detected joy emotion amount
    - anger_amt (float): Detected anger emotion amount
    - created_at (datetime): UTC Datetime of the post creation

    Inverse Relationship:
    - user (User): Many-to-One relationship with User model
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
    
class PostSchema(ma.SQLAlchemySchema):
    """
    Marshmallow schema to serializing and deserializing Post instances.

    Data Validation:
    - user_id: Required
    - content: Required and cannot be empty
    - emotion fields: Fields are within the range of 0.0 to 1.0
    """
    class Meta:
        model = Post
        load_instance = True

    id = ma.auto_field()
    user_id = ma.auto_field(required=True)
    content = ma.auto_field(required=True, validate=validate.Length(min=1))
    sadness_amt = ma.auto_field(validate=validate.Range(min=0.0, max=1.0))
    fear_amt = ma.auto_field(validate=validate.Range(min=0.0, max=1.0))
    joy_amt = ma.auto_field(validate=validate.Range(min=0.0, max=1.0))
    anger_amt = ma.auto_field(validate=validate.Range(min=0.0, max=1.0))
    created_at = ma.auto_field()

class WeeklyAdvice(db.Model):
    """
    WeeklyAdvice model representing advice provided to a user on a weekly basis.
    """
    __tablename__ = 'weekly_advices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f'<WeeklyAdvice {self.id} for User {self.user_id}>'
    
class WeeklyAdviceSchema(ma.SQLAlchemySchema):
    """
    Marshmallow schema for serializing and deserializing WeeklyAdvice instances.

    Data Validation:
    - user_id: Required
    - content: Required and cannot be empty
    """
    class Meta:
        model = WeeklyAdvice
        load_instance = True

    id = ma.auto_field()
    user_id = ma.auto_field(required=True)
    content = ma.auto_field(required=True, validate=validate.Length(min=1))
    created_at = ma.auto_field()