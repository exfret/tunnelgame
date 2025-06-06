from flask import Flask, render_template, jsonify, session, request
from flask_socketio import SocketIO, emit, join_room
from uuid import uuid4

class Server:
    def __init__(self):
        self.app = Flask(__name__)
        # TODO: Figure out what the secret key is needed for
        # Having this was suggested by ChatGPT
        self.app.config["SECRET_KEY"] = "password"
        self.app.config.update(
            SESSION_COOKIE_SAMESITE="None",
            SESSION_COOKIE_SECURE=True   # Required when SameSite=None
        )
        self.socketio = SocketIO(self.app, async_mode="eventlet", manage_session=True)
        self.setup_routes()
        self.sid_to_uid = {}
    

    def setup_routes(self):
        @self.app.route('/')
        def index():
            session.setdefault("uid", str(uuid4()))
            return render_template("index.html")