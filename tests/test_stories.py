# Tests for:
#   - Local variables
#   - 

# In test_gameloop.py
import os
from pathlib import Path
import sys

# Add the path to the src directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from config import game, state, local_dir
from gameloop import run
from interpreter import ErrorNode
from view import view

######################################################################
# examples
######################################################################

# Just make sure the examples compile
def test_examples():
    directory_path = Path(local_dir + "stories/examples")

    for folder_path in directory_path.iterdir():
        if folder_path.is_dir():
            for file_path in folder_path.iterdir():
                if file_path.is_file() and file_path.suffix in {".yaml", ".yml"}:
                    # Now remove the absolute part of the string
                    absolute_part = len(local_dir + "stories/")
                    path_name = str(file_path)
                    path_name = path_name[absolute_part:]

                    run(str(path_name))

######################################################################
# basic_syntax
######################################################################

def test_error():
    view.update_choice_list([])
    try:
        run("test/basic_syntax/error.yaml")
    except ErrorNode:
        pass
    else:
        assert(False)

def test_hello_world():
    view.update_choice_list([])
    run("test/basic_syntax/hello_world.yaml")
    assert view.get_text_commands_called() == ["Hello, World!"]

def test_list_block():
    view.update_choice_list(["stay", "leave"])
    run("test/basic_syntax/list_block.yaml")
    assert view.get_text_commands_called() == ["a", "b", "b", "c"]

def test_print_with_vars():
    view.update_choice_list([])
    run("test/basic_syntax/print_with_vars.yaml")
    assert view.get_text_commands_called() == ["Hello, World!"]

def test_set_instr():
    view.update_choice_list([])
    run("test/basic_syntax/set_instr.yaml")
    assert view.get_text_commands_called() == ["2", "-1", "1"]

def test_simple_choice_goto():
    view.update_choice_list(["good"])
    run("test/basic_syntax/simple_choice_goto.yaml")
    assert view.get_text_commands_called() == ["This is the start of the program.", "Now you make a choice (this should only appear once).", "You're headed to the good block.", "You're in the good block."]

    view.update_choice_list(["bad"])
    run("test/basic_syntax/simple_choice_goto.yaml")
    assert view.get_text_commands_called() == ["This is the start of the program.", "Now you make a choice (this should only appear once).", "You're headed to the bad block.", "You're in the bad block."]

def test_simple_choice():
    view.update_choice_list(["continue"])
    run("test/basic_syntax/simple_choice.yaml")
    assert view.get_text_commands_called() == ["This is the start of the program.", "This is the text after the choice.", "You made a choice."]

def test_simple_goto():
    view.update_choice_list([])
    run("test/basic_syntax/simple_goto.yaml")
    assert view.get_text_commands_called() == ["This is the start of the program.", "Arrived at other block.", "Arrived at child block. End of program."]

######################################################################
# game_objects
######################################################################

def test_game_objects():
    view.update_choice_list([])
    run("test/game_objects/simple_bags.yaml")
    assert view.get_text_commands_called() == ["0", "2", "2"]