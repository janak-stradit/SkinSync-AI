import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-skinsync-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres:postgres@localhost/skinsync'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATES_AUTO_RELOAD = True
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-jwt-key'
    JWT_ACCESS_TOKEN_EXPIRES = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads')
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL') or 'openai/gpt-5.1'
    OPENROUTER_BASE_URL = os.environ.get('OPENROUTER_BASE_URL') or 'https://openrouter.ai/api/v1'
    OPENROUTER_SITE_URL = os.environ.get('OPENROUTER_SITE_URL') or 'http://127.0.0.1:5000'
    OPENROUTER_APP_NAME = os.environ.get('OPENROUTER_APP_NAME') or 'SkinSync AI'
