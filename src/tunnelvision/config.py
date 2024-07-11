import os
from pathlib import Path
import sys
import yaml

from tunnelvision import (
    gameloop,
    interpreter,
    utility,
    addressing,
    gameparser,
    view as V,
)


# Make new data dir
data_dir = Path.home() / "tunnelgame"
data_dir.mkdir(exist_ok=True)
story_dir = data_dir / "stories"
story_dir.mkdir(exist_ok=True)
saves_dir = data_dir / "saves"
saves_dir.mkdir(exist_ok=True)


###########################################################
# Data sources
###########################################################

local_dir = Path(getattr(sys, '_MEIPASS', os.path.abspath('.')))
stories = story_dir
saves = saves_dir
grammar = yaml.safe_load((local_dir / "grammar.yaml").read_text())
max_num_steps = 20000
choices_between_autosaves = 20


###########################################################
# Injections
###########################################################

injections = ["game", "state", "view"]
# Default values
game = {}
state = {}
view = V.CLIView()
targets = [
    addressing,  # game
    gameloop,  # game, state, view
    gameparser,  # game, state
    interpreter,  # game, state, view
    utility,  # state
    V,  # state
]


def load(**config_dict):
    # Update config
    for variable, value in config_dict.items():
        if variable not in injections:
            raise ValueError(f"Invalid config item: {variable}")
        globals()[variable] = value

    # Publish config
    for module in targets:
        for service in injections:
            setattr(module, service, globals()[service])


# Publish default config
load()
