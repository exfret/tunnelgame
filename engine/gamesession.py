import yaml


# Mirrors order of initialization
from engine.gamestate import GameState
from engine.config import Config
from engine.view import View, CLIView, ViewForTesting, WebView
from engine.addressing import Addressing
from engine.utility import Utility
from engine.gameparser import GameParser
from engine.interpreter import Interpreter
from engine.gameloop import GameLoop


class InvalidViewType(Exception):
    pass


class GameSession:
    gamestate : GameState
    config : Config
    addressing : Addressing
    utility : Utility
    view : View
    gameparser : GameParser
    interpreter : Interpreter
    gameloop : GameLoop


    def __init__(self, story_name, view_type, app=None, socketio=None, uid=None, profiling=False):        
        self.gamestate = GameState()
        self.config = Config(story_name, view_type, profiling=profiling)

        # Load grammar once so it doesn't have to keep getting reloaded
        self.grammar = yaml.safe_load((self.config.grammar_dir).read_text())

        self.addressing = Addressing(self.gamestate)
        self.utility = Utility(self.gamestate, self.addressing)
        if view_type == "cli":
            self.view = CLIView(self.gamestate, self.config, self.addressing, self.utility)
        elif view_type == "test":
            self.view = ViewForTesting(self.gamestate, self.config, self.addressing, self.utility)
        elif view_type == "web":
            self.view = WebView(self.gamestate, self.config, self.addressing, self.utility, app, socketio, uid)
        else:
            raise InvalidViewType()
        self.gameparser = GameParser(self.gamestate, self.config, self.addressing, self.utility, self.grammar)
        self.interpreter = Interpreter(self.gamestate, self.config, self.addressing, self.utility, self.view, self.gameparser)
        self.gameloop = GameLoop(self.gamestate, self.config, self.addressing, self.utility, self.view, self.gameparser, self.interpreter)
    

    def close(self):
        self.gamestate.light.closed = True