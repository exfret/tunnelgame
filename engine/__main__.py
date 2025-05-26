from flask import session, request
from flask_socketio import join_room, emit
import sys

import copy

from engine import config, view, gameparser
from engine.gameloop import run


if config.web_view:
    config.view = view.WebView()
else:
    config.view = view.CLIView()


if config.web_view:
    @config.view.socketio.on("connect")
    def handle_connect():
        uid = session["uid"]
        sid = request.sid
        config.view.sid_to_uid[sid] = uid
        join_room(uid)

        game_state = config.view.web_state.get(uid)
        if game_state is None:
            game_state = {"game": None, "state": None, "client_side": {}}
            config.view.web_state[uid] = game_state
        
        # restore_state itself currently doesn't do anything
        # Currently main work is done by the print_choices and print_shown_vars calls in start()
        emit("restore_state", game_state["client_side"])


        def start():
            if game_state["game"] is not None and game_state["state"] is not None:
                config.game.update(copy.deepcopy(game_state["game"]))
                config.state.update(copy.deepcopy(game_state["state"]))
                gameparser.add_module_vars()

                config.view.clear()
                config.view.print_choices()
                config.view.print_shown_vars(config.state["view_text_info"]["shown_vars"], config.state["last_address_list"][-1])

                run(config.story_name, packaged=True, loaded_game_state=game_state, uid=uid)
            else:
                run(config.story_name, packaged=True, uid=uid)


        config.view.socketio.start_background_task(start)


    @config.view.socketio.on("disconnect")
    def handle_disconnect():
        uid = config.view.sid_to_uid.pop(request.sid, None)


def main():
    if config.web_view:
        config.view.socketio.run(config.view.app, port=5001, debug=True)
    else:
        if len(sys.argv) == 1:
            run(config.story_name, packaged=True)
        else:
            run(sys.argv[1], packaged=False)


if __name__ == "__main__":
    main()