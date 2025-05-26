import os
from pathlib import Path
import sys
import yaml


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


web_view = True
story_name = "gather_game/intro.yaml"


local_dir = Path(getattr(sys, '_MEIPASS', os.path.abspath('.')))
stories = story_dir
saves = saves_dir
grammar = yaml.safe_load((local_dir / "engine" / "grammar.yaml").read_text())
max_num_steps = 20000
max_macro_depth = 100
choices_between_autosaves = 20


game = {}
state = {}
view = None