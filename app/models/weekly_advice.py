from marshmallow import validate
from app.extensions import db, ma


class WeeklyAdvice(db.Model):
    """
    Represents a user's weekly advice generated on behalf of an user by async workers every Sunday at 12:00 AM UTC.

    Attributes:
        - id (int): Primary key of the weekly advice.
        - user_id (int): Foreign key referencing the user's ID.
        - content (str): Content of the weekly advice.
        - created_at (datetime): UTC timestamp of when the weekly advice was created.
        - of_week (datetime): UTC timestamp of the week the advice is for.
    """

    __tablename__ = "weekly_advices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    of_week = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f"<Weekly Advice {self.id} for User {self.user_id}>"


class WeeklyAdviceSchema(ma.SQLAlchemySchema):
    """
    Marshmallow schema for serializing and deserializing WeeklyAdvice instances.
    """

    class Meta:
        model = WeeklyAdvice
        load_instance = True

    id = ma.auto_field()
    user_id = ma.auto_field(dump_only=True)
    content = ma.auto_field(dump_only=True, validate=validate.Length(min=1))
    created_at = ma.auto_field(dump_only=True)
    of_week = ma.auto_field(dump_only=True)
