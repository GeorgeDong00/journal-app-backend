from marshmallow import validate
from app.extensions import db, ma

class WeeklyAdvice(db.Model):
    """
    WeeklyAdvice model representing advice provided to a user on a weekly basis.
    """

    __tablename__ = "weekly_advices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f"<WeeklyAdvice {self.id} for User {self.user_id}>"


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
    user_id = ma.auto_field(dump_only=True)
    content = ma.auto_field(required=True, validate=validate.Length(min=1))
    created_at = ma.auto_field()