# In test_gameloop.py
import sys
import os

# Add the path to the src directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from config import game, state
from gameloop import run
from interpreter import ErrorNode
from view import view

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

def test_print_with_vars():
    view.update_choice_list([])
    run("test/basic_syntax/print_with_vars.yaml")
    assert view.get_text_commands_called() == ["Hello, World!"]

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
