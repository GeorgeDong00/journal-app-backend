from marshmallow import validate
from app.extensions import db, ma


class Post(db.Model):
    """
    Represents a user's journal post including Large Language Model emotion analysis results.

    Attributes:
        - id (int): Primary key.
        - user_id (int): Foreign key referencing the user's ID.
        - content (str): The content of the user's journal post.
        - formatting (JSON): A list of formatting objects describing how content should be formatted.
        - anger_value (float): Detected anger emotion value.
        - disgust_value (float): Detected disgust emotion value.
        - fear_value (float): Detected fear emotion value.
        - joy_value (float): Detected joy emotion value.
        - neutral_value (float): Detected neutral emotion value.
        - sadness_value (float): Detected sadness emotion value.
        - surprise_value (float): Detected surprise emotion value.
        - created_at (datetime): Timestamp of when the post was created.

    Relationships:
        - user (User): Many-to-One relationship with the User model.
    """

    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    formatting = db.Column(db.JSON, nullable=False, default=[])
    anger_value = db.Column(db.Float, nullable=False, default=0.0)
    disgust_value = db.Column(db.Float, nullable=False, default=0.0)
    fear_value = db.Column(db.Float, nullable=False, default=0.0)
    joy_value = db.Column(db.Float, nullable=False, default=0.0)
    neutral_value = db.Column(db.Float, nullable=False, default=0.0)
    sadness_value = db.Column(db.Float, nullable=False, default=0.0)
    surprise_value = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f"<Post {self.id} by User {self.user_id}>"


class PostSchema(ma.SQLAlchemySchema):
    """
    Marshmallow schema for serializing and deserializing Post instances.

    Validation:
        - content: Required and must not be empty.
        - formatting: Must be a list of dictionaries.
        - emotion fields: Returned on serialization only.
    """

    class Meta:
        model = Post
        load_instance = True

    id = ma.auto_field()
    user_id = ma.auto_field(dump_only=True)
    content = ma.auto_field(required=True, validate=validate.Length(min=1))
    formatting = ma.List(ma.Dict(), missing=[])
    anger_value = ma.auto_field(dump_only=True)
    disgust_value = ma.auto_field(dump_only=True)
    fear_value = ma.auto_field(dump_only=True)
    joy_value = ma.auto_field(dump_only=True)
    neutral_value = ma.auto_field(dump_only=True)
    sadness_value = ma.auto_field(dump_only=True)
    surprise_value = ma.auto_field(dump_only=True)
    created_at = ma.auto_field(dump_only=True)
