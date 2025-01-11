import os
from datetime import timedelta

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'test-secret-key')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Database
    DB_USER = os.getenv('POSTGRES_USER', 'postgres')
    DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'blackout-08-bremen')
    DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    DB_NAME = os.getenv('POSTGRES_DB', 'blackout-08-bremen')
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API
    API_TOKEN = os.getenv('API_TOKEN', 'test-token')
    
    # Socket IO
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
config = {
    'default': Config,
}