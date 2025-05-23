import socketio
import sys

from engine import config, view
from engine.gameloop import run

if config.web_view:
    config.view = view.WebView()
else:
    config.view = view.CLIView()

if config.web_view:
    @config.view.socketio.on("connect")
    def handle_connect():
        def start():
            run(config.story_name, packaged=True)

        config.view.socketio.start_background_task(start)

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