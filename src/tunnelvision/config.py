from pathlib import Path
import yaml

from tunnelvision import (
    gameloop,
    interpreter,
    utility,
    addressing,
    gameparser,
    view as V,
)


###########################################################
# Data sources
###########################################################

local_dir = Path(__file__).parent
stories = local_dir / "stories"
saves = local_dir / "saves"
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
