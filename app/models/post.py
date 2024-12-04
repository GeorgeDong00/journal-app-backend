from marshmallow import validate
from app.extensions import db, ma

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

    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sadness_amt = db.Column(db.Float, default=0.0)
    fear_amt = db.Column(db.Float, default=0.0)
    joy_amt = db.Column(db.Float, default=0.0)
    anger_amt = db.Column(db.Float, default=0.0)
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
    sadness_amt = ma.auto_field(validate=validate.Range(min=0.0, max=1.0))
    fear_amt = ma.auto_field(validate=validate.Range(min=0.0, max=1.0))
    joy_amt = ma.auto_field(validate=validate.Range(min=0.0, max=1.0))
    anger_amt = ma.auto_field(validate=validate.Range(min=0.0, max=1.0))
    created_at = ma.auto_field()