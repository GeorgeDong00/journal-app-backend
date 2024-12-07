from marshmallow import validate
from app.extensions import db, ma


class Post(db.Model):
    """
    Post model representing a user's journal post with detected emotions derived from a LLM (Large Language Model).

    Attributes:
    - id (int): Autogenerated primary key
    - user_id (int): Foreign key referencing the User
    - content (str): Journal post content
    - anger_value (float): Detected anger emotion amount
    - disgust_value (float): Detected disgust emotion amount
    - fear_value (float): Detected fear emotion amount
    - joy_value (float): Detected joy emotion amount
    - neutral_value (float): Detected neutral emotion amount
    - surprise_value (float): Detected surprise emotion amount
    - created_at (datetime): UTC Datetime of the post creation

    Inverse Relationship:
    - user (User): Many-to-One relationship with User model
    """

    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    anger_value = db.Column(db.Float, nullable=False)
    disgust_value = db.Column(db.Float, nullable=False)
    fear_value = db.Column(db.Float, nullable=False)
    joy_value = db.Column(db.Float, nullable=False)
    neutral_value = db.Column(db.Float, nullable=False)
    sadness_value = db.Column(db.Float, nullable=False)
    surprise_value = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f"<Post {self.id} by User {self.user_id}>"


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
    user_id = ma.auto_field(dump_only=True)
    content = ma.auto_field(required=True, validate=validate.Length(min=1))
    anger_value = ma.auto_field(dump_only=True)
    disgust_value = ma.auto_field(dump_only=True)
    fear_value = ma.auto_field(dump_only=True)
    joy_value = ma.auto_field(dump_only=True)
    neutral_value = ma.auto_field(dump_only=True)
    sadness_value = ma.auto_field(dump_only=True)
    surprise_value = ma.auto_field(dump_only=True)
    created_at = ma.auto_field()
