from flask import session, request
from flask_socketio import join_room, emit
import sys

import copy
import os
import pickle
import yaml

from engine.server import Server
from engine.gamesession import GameSession


story_name = "tunnel/new_encounter_demo.yaml"
# Valid choices are...
#  cli
#  test
#  web
view_type = "web"

# Enforce to demo version on web if this is deployed to render
# Actually, for now choose it manually
#if os.getenv("RENDER") == "TRUE":
#    story_name = "tunnel/05-demo/root.yaml"
#    view_type = "web"


app = None
if view_type == "web":
    server = Server()
    app = server.app

    uid_to_gamesession = {}


    @server.socketio.on("connect")
    def handle_connect(auth):
        uid = session["uid"]
        sid = request.sid
        server.sid_to_uid[sid] = uid
        join_room(uid)

        gamesession = uid_to_gamesession.get(uid) or GameSession(story_name, "web", server.app, server.socketio, uid)
        uid_to_gamesession[uid] = gamesession

        gamesession.view.load_web_state()

        web_state = gamesession.view.web_state.get(uid)


        # See whether to reset game state
        # Load the game once just to see if its _game_id is different from before
        reset_game_state = False
        if web_state is None or web_state["game"] is None or web_state["state"] is None:
            reset_game_state = True
        else:
            game_to_load = yaml.safe_load((gamesession.config.local_dir / "stories" / story_name).read_text())
            new_game_id = ""
            if "_game_id" in game_to_load:
                new_game_id = game_to_load["_game_id"]
            old_game_id = ""
            if "_game_id" in web_state["game"]:
                old_game_id = web_state["game"]["_game_id"]
            if new_game_id != old_game_id:
                reset_game_state = True
        if reset_game_state:
            web_state = {"game": None, "state": None, "client_side": {}}
            gamesession.view.web_state[uid] = web_state
        
        # restore_state itself currently doesn't do anything
        # Currently main work is done by the print_choices and print_shown_vars calls in start()
        emit("restore_state", web_state["client_side"], room=uid)


        def start():
            if web_state["game"] is not None and web_state["state"] is not None:
                gamesession.gameobject.game = copy.deepcopy(web_state["game"])
                gamesession.gamestate.state = copy.deepcopy(web_state["state"])
                gamesession.gameparser.add_module_vars()

                gamesession.view.clear()
                gamesession.view.print_choices()
                gamesession.view.print_shown_vars(gamesession.gamestate.state["view_text_info"]["shown_vars"], gamesession.gamestate.state["last_address_list"][-1])
                gamesession.view.show_curr_image()

                gamesession.gameloop.run(story_name, packaged=True, loaded_game_state=web_state, uid=uid, do_lookaheads=True)
            else:
                gamesession.gameloop.run(story_name, packaged=True, uid=uid, do_lookaheads=True)


        server.socketio.start_background_task(start)


    @server.socketio.on("disconnect")
    def handle_disconnect():
        uid = server.sid_to_uid.pop(request.sid)
        if not any(sid_uid == uid for sid_uid in server.sid_to_uid.values()):
            uid_to_gamesession.pop(uid).close()


    @server.socketio.on("make_choice")
    def handle_choice(data):
        gamesession = uid_to_gamesession[session["uid"]]
        gamesession.gamestate.state["command_buffer"].append(data["choice_id"].split())
    

    @server.socketio.on("command")
    def handle_command(data):
        gamesession = uid_to_gamesession[session["uid"]]
        gamesession.gamestate.state["command_buffer"].append(data["command"].split())


    @server.socketio.on("restart")
    def handle_restart(data):
        gamesession = uid_to_gamesession[session["uid"]]
        gamesession.view.web_state[session["uid"]] = {
            "game": None,
            "state": None,
            "client_side": {}
        }

        (gamesession.config.saves_dir / ("_web_state_" + str(session["uid"]))).with_suffix(".pkl").write_bytes(pickle.dumps(gamesession.view.web_state))


def main():
    if view_type == "web":
        server.socketio.run(server.app, port=5001, debug=True)
    else:
        gamesession = GameSession(story_name, view_type)

        if len(sys.argv) == 1:
            gamesession.gameloop.run(story_name, packaged=True)
        else:
            gamesession.gameloop.run(sys.argv[1], packaged=False)


if __name__ == "__main__":
    main()