from flask import Flask
from config import Config
import firebase_admin
from firebase_admin import credentials
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Firebase Admin SDK to verify token
cred = credentials.Certificate('app/serviceAccountKey.json')
firebase_admin.initialize_app(cred)

# Initialize SQLAlchemy and Migrate
db = SQLAlchemy(app)
# migrate = Migrate(app, db)

from app import routes, models