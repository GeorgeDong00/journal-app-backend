from flask import Flask
from config import Config
import firebase_admin
from firebase_admin import credentials

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Firebase Admin SDK to verify token
cred = credentials.Certificate('app/serviceAccountKey.json')
firebase_admin.initialize_app(cred)

from app import routes
