import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-skinsync-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres:postgres@localhost/skinsync'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATES_AUTO_RELOAD = True
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-jwt-key'
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads')
