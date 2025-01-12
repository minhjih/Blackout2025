from flask import Flask
from flask_socketio import SocketIO
from flask_session import Session

from server.config import config
from server.extensions import db, migrate, socketio, login_manager

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    login_manager.init_app(app)
    Session(app)

    return app
