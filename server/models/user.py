from datetime import datetime
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSONB
from server.extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with frame data
    frame_data = db.relationship('FrameData', backref='user', lazy=True)

class FrameData(db.Model):
    __tablename__ = 'frame_data'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, nullable=False)
    score = db.Column(db.Float, default=0)
    frame_id = db.Column(db.Integer, primary_key=True, nullable=False)

class ScoreHistory(db.Model):
    __tablename__ = 'score_history'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, nullable=False)
    score = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, primary_key=True, default=datetime.utcnow)
