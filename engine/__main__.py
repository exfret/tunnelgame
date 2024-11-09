import socketio
import sys

from engine import config, view
from engine.gameloop import run

web_view = False
story_name = "tunnel/03-abstract/intro.yaml"

if web_view:
    config.view = view.WebView()
else:
    config.view = view.CLIView()

if web_view:
    @config.view.socketio.on("connect")
    def handle_connect():
        def start():
            run(story_name, packaged=True)

        config.view.socketio.start_background_task(start)

def main():
    if web_view:
        config.view.socketio.run(config.view.app, port=5001, debug=True)
    else:
        if len(sys.argv) == 1:
            run(story_name, packaged=True)
        else:
            run(sys.argv[1], packaged=False)

if __name__ == "__main__":
    main()