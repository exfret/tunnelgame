import copy
import sys
import yaml

local_dir = "/Users/kylehess/Documents/programs/tunnelgame/"

class Sensor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.data = {
                "game": {},
                "state": {}
            }
        return cls._instance
sensor = Sensor()
game = sensor.data["game"]
state = sensor.data["state"]

def open_game(game_name):
    game.clear()
    state.clear()

    with open(
        local_dir + "stories/" + game_name, "r"
    ) as file:
        game.update(yaml.safe_load(file))

    starting_state = {
        "choices": {"start": {"text": "Start the game", "address": ("_content", 0)}}, # Dict of choice ID's to new locations and descriptions
        "bookmark": (), # bookmark is a queue (tuple) of call stacks (tuples) containing addresses (tuples)
        "file_data": {"filename": ""}, # TODO: Include some sort of hash or name of game
        "last_address_list": [],
        "map": {},
        "metadata": {"node_types": {}}, # TODO: Rename to 'story_data' or something such, maybe remove after parsing overhaul
        "settings": {"show_flavor_text": "once"},
        "vars": {},
        "visits": {}
    }
    state.update(copy.deepcopy(starting_state))