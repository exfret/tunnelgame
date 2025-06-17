# Still TODO:
#   * Attached Blocks
#   * Call Stack
#   * Settings
#   * Story Data/Block Moves
#   * World


from typing import Any


class GameData:
    """
    Represents information that stays constant after loading the GameObject. Doesn't include the GameObject itself.
    This is passed by reference whenever a GameState needs to be passed on, and saving it is avoided when possible.

    Attributes:
        file_homes: A dict of addresses to whether they are the root address of some file
        node_contexts: A dict of node addresses to their context
    """


    file_homes : dict[tuple, bool]
    node_contexts : dict[tuple]


    def __init__(self):
        self.file_homes = {}
        self.node_contexts = {}


class ViewData:
    """
    Represents light amounts of data needed for the View, like on-screen text for saving/loading.

    Attributes:
        emit_intercepts: Intercepted socketio messages when in lookahead mode
        shown_vars: The variables to be shown in stats view
        story_text: Text on the story view
    """


    emit_intercepts : list
    shown_vars : list
    story_text : str


    def __init__(self):
        self.emit_intercepts = []
        self.shown_vars = []
        self.story_text = ""


class LightData:
    """
    Represents the lighter data for GameState.
    This is deepcopied when whenever a GameState needs to be passed on.

    Attributes:
        bookmark: Where you are in the story
        choices: The current choices presented to the user, including actions
        closed: Whether the game is closed
        command_buffer: The list of commands to be executed; each command is a tuple of strings
        command_macros: Dict of macros defined by user to be used in commands
        last_address: The instruction of the last address visited
        last_address_list: List of previous addresses visited
        last_autosave: Number of choices since the last autosave
        last_save_name: The name of the last save file used
        loop_interrupt_msgs: A way to communicate things to GameLoop
        random_buffer: A list of strings indicating which path the "random" instruction should take for determinism during tests
        storypoints: A dict of storypoint ID's to False/True based on whether they've been reached
        sub_stack: A tuple of bookmarks, representing the "stack" for subroutines
        total_choices_made: The total number of choices you've made in the story
        view: Short information about the view, such as text to display
    """


    bookmark : tuple[tuple]
    choices: dict[str, Any]
    closed : bool
    command_buffer : list[list[str]]
    command_macros : dict[str, list[str]]
    curr_image : None | str
    last_address : tuple
    last_address_list : list[tuple]
    last_autosave : int
    last_save_name : None | str
    loop_interrupt_msgs: dict
    random_buffer : list
    storypoints : dict
    sub_stack : tuple[tuple[tuple]]
    total_choices_made : int
    view : ViewData


    def __init__(self):
        self.bookmark = ()
        self.choices = {
            # This choice is made automatically and is currently only seen if the program needs to rewind due to too many instructions executed or something similar
            "start": {"text": "Start the game", "address": ("_content", 0), "choice_address": (), "action": False, "missing": [], "modifications": []}
        }
        self.closed = False
        self.command_buffer = []
        self.command_macros = {}
        self.curr_image = None
        self.last_address = ()
        self.last_address_list = []
        self.last_autosave = 0
        self.last_save_name = None
        self.loop_interrupt_msgs = {}
        self.random_buffer = []
        self.storypoints = {}
        self.sub_stack = ()
        self.total_choices_made = 0
        self.view = ViewData()


class LineData:
    """
    Represents information tied to a particular line of the story (like the number of times it was visited)

    Attributes:
        addr: The address of this line in the game
        choice_visits: If this line is for a choice node, how many times the choice was made (note that this is different from simply being visited)
        visits: Represents how many visits you've made to this line
    """


    addr: tuple
    choice_visits: int
    visits : int
    

    def __init__(self, addr):
        self.addr = addr
        self.choice_visits = 0
        self.visits = 0


class BulkData:
    """
    Represents the bulkier data for GameState.
    When needed, a GameState's BulkDataDiff's are used to reverse bulk data changes.
    
    Attributes:
        per_line: Individual per-line data
        vars: Dict of address to vars at that address
    """


    per_line : dict[tuple, LineData]
    vars : dict[tuple, Any]


    def __init__(self):
        self.per_line = {}
        self.vars = {}


class Diff:
    """
    A single diff representing the operation to undo a change to a single mutable object, or an entire LightData

    Attributes:
        data: The data used for reverting this diff
        diff_type: The type of diff this is, accepted types are:
            * choice_visit: Decreases number of times choice was made at data["addr"] by 1
            * flag_set: Sets flag named data["name"] to data["val"]
            * var_set: Sets variable at address data["addr"] named data["name"] to data["val"]
            * visit: Decreases number of visits to address data["addr"] by 1
    """


    diff_type : str
    data : Any


    def __init__(self, diff_type, data):
        self.diff_type = diff_type
        self.data = data


class DiffList(list):
    """
    A list of lists of BulkDataDiff's representing the diffs needed to undo changes to BulkData. The most recent diffs are last.
    This is passed by reference like BulkData, but new changes are appended to a new sublist. Each sublist represents the changes from one choice.
    """


class GameState:
    """
    Represents all information needed to load a savegame.
    """


    game : dict
    game_data : GameData
    light : LightData
    bulk : BulkData
    diffs : DiffList


    def __init__(self):
        self.game = {}
        self.game_data = GameData()
        self.light = LightData()
        self.bulk = BulkData()
        self.diffs = DiffList([[]])
    

    def reset(self):
        self.game = {}
        self.game_data = GameData()
        self.light = LightData()
        self.bulk = BulkData()
        self.diffs = DiffList([[]])
    

    def update(self, other_gamestate):
        self.game = other_gamestate.game
        self.game_data = other_gamestate.game_data
        self.light = other_gamestate.light
        self.bulk = other_gamestate.bulk
        self.diffs = other_gamestate.diffs
    

    def inc_visits(self, addr):
        self.bulk.per_line[addr].visits += 1
        self.diffs[-1].append(Diff(
            diff_type = "visit",
            data = {
                "addr": addr
            }
        ))

    
    def inc_choice_visits(self, addr):
        self.bulk.per_line[addr].choice_visits += 1
        self.diffs[-1].append(Diff(
            diff_type = "choice_visit",
            data = {
                "addr": addr
            }
        ))


    def modify_flag(self, name, val):
        # Need to keep what old value to set back to was
        self.diffs[-1].append(Diff(
            diff_type = "flag_set",
            data = {
                "name": name,
                "val": self.bulk.vars["flags"][name]
            }
        ))
        self.bulk.vars["flags"][name] = val
    

    def modify_var(self, addr, name, val):
        self.diffs[-1].append(Diff(
            diff_type = "var_set",
            data = {
                "addr": addr,
                "name": name,
                "val": self.bulk.vars[addr][name]["value"]
            }
        ))
        self.bulk.vars[addr][name]["value"] = val

    
    def reverse_last_diffs(self):
        # Check if we can even revert any further
        if len(self.diffs) == 0:
            return False

        last_diff_list = self.diffs.pop()

        while len(last_diff_list) > 0:
            last_diff = last_diff_list.pop()
            data = last_diff.data

            if last_diff.diff_type == "choice_visit":
                self.bulk.per_line[data["addr"]].choice_visits -= 1
            elif last_diff.diff_type == "flag_set":
                self.bulk.vars["flags"][data["name"]] = data["val"]
            elif last_diff.diff_type == "var_set":
                self.bulk.vars[data["addr"]][data["name"]]["value"] = data["val"]
            elif last_diff.diff_type == "visit":
                self.bulk.per_line[data["addr"]].visits -= 1