from flask import Flask, jsonify, request
from flask_login import login_user, logout_user, login_required, current_user
# from flask_socketio import emit
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from redis import Redis

from server.extensions import db, migrate, socketio, login_manager
from server.models.user import User, FrameData, ScoreHistory
from server.config import config

import json
from datetime import datetime

import numpy as np
import cv2

from frame_analyzer import analyze_frame

def create_app():
    app = Flask(__name__)
    app.config.from_object(config['default'])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins=[])
    login_manager.init_app(app)

    return app

app = create_app()
logging.basicConfig(level=logging.INFO)

def require_api_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing API token'}), 401
        
        token = auth_header.split(' ')[1]
        if token != app.config['API_TOKEN']:
            return jsonify({'error': 'Invalid API token'}), 401
            
        return f(*args, **kwargs)
    return decorated

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class FrameBuffer:
    def __init__(self):
        self.scores = []

    def add_score(self, score):
        self.scores.append(score)

@app.route('/register', methods=['POST'])
@require_api_token
def register():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing username or password'}), 400
        
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409
        
    user = User(
        username=data['username'],
        password_hash=generate_password_hash(data['password'])
    )
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
@require_api_token
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing username or password'}), 400
        
    user = User.query.filter_by(username=data['username']).first()

    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
        
    login_user(user)
    return jsonify({'message': 'Logged in successfully'}), 200

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

from flask import request, jsonify
from flask_login import login_required, current_user
import base64

@app.route('/video_frame', methods=['POST'])
@login_required
def process_video_frame():
    try:
        if 'frame_id' not in request.form:
            return jsonify({'error': 'Missing frame_id'}), 400
            
        # Check if file is in request
        if 'frame' not in request.files:
            return jsonify({'error': 'No frame file'}), 400
            
        frame_file = request.files['frame']
        frame_id = int(request.form['frame_id'])

        # Decode base64 frame
        file_bytes = np.frombuffer(frame_file.read(), np.uint8)
        frame_array = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        frame_data = analyze_frame(frame_array)

        # Placeholder for score calculation and road outline detection
        score = frame_data['score']  # Example score
        road_outline = {
            "bottom_x_r": frame_data['road_outline']['bottom_x_r'],
            "bottom_x_s": frame_data['road_outline']['bottom_x_s'],
            "bottom_y": frame_data['road_outline']['bottom_y'],
            "top_x_r": frame_data['road_outline']['top_x_r'],
            "top_x_s": frame_data['road_outline']['top_x_s'],
            "top_y": frame_data['road_outline']['top_y'] 
        }

        # Store score in Db
        frame_data = FrameData(
            user_id=current_user.id,
            frame_id=frame_id,
            score=score,
        )
        db.session.add(frame_data)
        db.session.commit()

        response = {
            "score": score,
            "frame_id": frame_id,
            "road_outline": road_outline
        }

        return jsonify(response), 200

    except Exception as e:
        logging.error(f"Error processing video frame: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
@app.route('/endride', methods=['POST'])
@login_required
def end_ride():
    try:
        # Get all frame scores for current user
        frame_scores = FrameData.query.filter_by(user_id=current_user.id).all()
        
        if not frame_scores:
            return jsonify({'average_point': 0.0}), 200
        
        # Calculate average score
        average_score = sum(frame.score for frame in frame_scores) / len(frame_scores)
        
        # Save to score history
        score_history = ScoreHistory(
            user_id=current_user.id,
            score=average_score,
            created_at=datetime.utcnow()
        )
        db.session.add(score_history)
        
        # Clear frame data
        FrameData.query.filter_by(user_id=current_user.id).delete()
        
        # Commit changes
        db.session.commit()
        
        return jsonify({
            'average_point': average_score
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in end_ride: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
