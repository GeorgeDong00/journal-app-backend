from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
import boto3

db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()

def init_s3(app):
    """
    Initialize the S3 client for the Flask application.
    """
    global s3_client
    s3_client = boto3.client(
        service_name="s3",
        region_name=app.config.get("AWS_REGION"),
        aws_access_key_id=app.config.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=app.config.get("AWS_SECRET_ACCESS_KEY"),
    )
    app.extensions["s3_client"] = s3_client
