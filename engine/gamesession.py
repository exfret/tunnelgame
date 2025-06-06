# Mirrors order of initialization
from engine.gameobject import GameObject
from engine.gamestate import GameState
from engine.config import Config
from engine.view import CLIView, WebView
from engine.addressing import Addressing
from engine.utility import Utility
from engine.gameparser import GameParser
from engine.interpreter import Interpreter
from engine.gameloop import GameLoop


class InvalidViewType(Exception):
    pass


class GameSession:
    def __init__(self, story_name, view_type, app=None, socketio=None, uid=None):
        self.gameobject = GameObject()
        self.gamestate = GameState()
        self.config = Config(story_name, view_type)
        self.addressing = Addressing(self.gameobject, self.gamestate)
        self.utility = Utility(self.gamestate, self.addressing)
        if view_type == "cli":
            self.view = CLIView(self.gamestate, self.config, self.addressing, self.utility)
        elif view_type == "web":
            self.view = WebView(self.gamestate, self.config, self.addressing, self.utility, app, socketio, uid)
        else:
            raise InvalidViewType()
        self.gameparser = GameParser(self.gameobject, self.gamestate, self.config, self.addressing, self.utility)
        self.interpreter = Interpreter(self.gameobject, self.gamestate, self.config, self.addressing, self.utility, self.view, self.gameparser)
        self.gameloop = GameLoop(self.gameobject, self.gamestate, self.config, self.addressing, self.utility, self.view, self.gameparser, self.interpreter)
    

    def close(self):
        self.gamestate.state["closed"] = True