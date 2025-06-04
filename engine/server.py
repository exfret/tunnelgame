# server.py  (rename from main.py if you like)
import os, sys, copy, yaml
from flask import Flask, session, request
from flask_socketio import SocketIO, join_room, emit
from engine import config, view, gameparser
from engine.gameloop import run

# ────────────────────────────────────────────────────────────────
def create_app():
    """Application factory: returns (flask_app, socketio_instance)."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev‑only-secret")

    # Pick async driver + optional cross‑instance message queue
    socketio = SocketIO(
        app,
        async_mode="eventlet",                    # or "gevent"
        cors_allowed_origins="*",                # tighten later
        message_queue=os.getenv("REDIS_URL")     # "redis://redis:6379/0" in prod
    )

    # Select CLI or WebView
    config.view = view.WebView() if config.web_view else view.CLIView()

    # ───── Socket handlers ──────────────────────────────────────
    @socketio.on("connect")
    def handle_connect(auth=None):
        uid, sid = session["uid"], request.sid
        config.view.sid_to_uid[sid] = uid
        join_room(uid)

        game_state = config.view.web_state.get(uid)
        if needs_reset(game_state):
            game_state = {"game": None, "state": None, "client_side": {}}
            config.view.web_state[uid] = game_state

        emit("restore_state", game_state["client_side"])

        def start():
            if game_state["game"] and game_state["state"]:
                config.game.update(copy.deepcopy(game_state["game"]))
                config.state.update(copy.deepcopy(game_state["state"]))
                gameparser.add_module_vars()
                config.view.clear()
                config.view.print_choices()
                config.view.print_shown_vars(
                    config.state["view_text_info"]["shown_vars"],
                    config.state["last_address_list"][-1],
                )
                config.view.show_curr_image()
                run(config.story_name, packaged=True,
                    loaded_game_state=game_state, uid=uid)
            else:
                run(config.story_name, packaged=True, uid=uid)

        socketio.start_background_task(start)

    @socketio.on("disconnect")
    def handle_disconnect():
        config.view.sid_to_uid.pop(request.sid, None)

    return app, socketio
# ────────────────────────────────────────────────────────────────

def needs_reset(game_state):
    if not game_state or not game_state["game"] or not game_state["state"]:
        return True
    new_id = yaml.safe_load(
        (config.local_dir / "stories" / config.story_name).read_text()
    ).get("_game_id", "")
    old_id = game_state["game"].get("_game_id", "")
    return new_id != old_id


# ───── Development entry‑point ─────────────────────────────────
if __name__ == "__main__":
    app, socketio = create_app()
    if config.web_view:
        # Werkzeug dev server is fine for local hacking
        socketio.run(app, port=5001, debug=True)
    else:
        if len(sys.argv) == 1:
            run(config.story_name, packaged=True)
        else:
            run(sys.argv[1], packaged=False)
