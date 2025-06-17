import os
from pathlib import Path
import sys


class Config:
    def __init__(self, story_name, view_type, profiling=False):
        if os.getenv("RENDER") == "TRUE":
            self.data_dir = Path("/data")
        else:
            self.data_dir = Path(os.getenv("TUNNELGAME_DATA_DIR", Path.home() / "tunnelgame"))
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.graphics_dir = self.data_dir / "graphics"
        self.graphics_dir.mkdir(exist_ok=True, parents=True)
        self.story_dir = self.data_dir / "stories"
        self.story_dir.mkdir(exist_ok=True, parents=True)
        self.saves_dir = self.data_dir / "saves"
        self.saves_dir.mkdir(exist_ok=True, parents=True)

        self.story_name = story_name
        self.view_type = view_type
        self.profiling = profiling

        self.last_instr_time = None
        self.total_instr_time = 0
        self.total_num_instrs = 0

        # Removed graphics, stories, etc., now it just lives in dir
        self.local_dir = Path(getattr(sys, '_MEIPASS', os.path.abspath('.')))
        # Changed to just the dir from the actual object
        self.grammar_dir = self.local_dir / "engine" / "grammar.yaml"

        self.max_num_steps = 20000
        self.max_macro_depth = 100
        self.choices_between_autosaves = 20