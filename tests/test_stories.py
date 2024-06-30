# Tests for:
#   - Local variables
#   -

# In test_gameloop.py
import pytest
from tunnelvision import config
from tunnelvision.config import stories
from tunnelvision.gameloop import run
from tunnelvision.interpreter import ErrorNode
from tunnelvision.view import ViewForTesting

######################################################################
# fixtures
######################################################################


@pytest.fixture(autouse=True)
def view():
    original_view = config.view
    config.load(view=ViewForTesting())
    yield config.view
    config.load(view=original_view)


######################################################################
# examples
######################################################################

# Just make sure the examples compile
def test_examples():
    for story_yaml in (stories / "examples").glob("*.yaml"):
        run(str(story_yaml.relative_to(stories)))


######################################################################
# basic_syntax
######################################################################


def test_error():
    try:
        run("test/basic_syntax/error.yaml")
    except ErrorNode:
        pass
    else:
        assert(False)


def test_hello_world(view):
    run("test/basic_syntax/hello_world.yaml")
    assert view.get_text_commands_called() == ["Hello, World!"]


def test_list_block(view):
    view.update_choice_list(["stay", "leave"])
    run("test/basic_syntax/list_block.yaml")
    assert view.get_text_commands_called() == ["a", "b", "b", "c"]


def test_print_with_vars(view):
    run("test/basic_syntax/print_with_vars.yaml")
    assert view.get_text_commands_called() == ["Hello, World!"]


def test_set_instr(view):
    run("test/basic_syntax/set_instr.yaml")
    assert view.get_text_commands_called() == ["2", "-1", "1"]


def test_simple_choice_goto(view):
    view.update_choice_list(["good"])
    run("test/basic_syntax/simple_choice_goto.yaml")
    assert view.get_text_commands_called() == ["This is the start of the program.", "Now you make a choice (this should only appear once).", "You're headed to the good block.", "You're in the good block."]

    view.update_choice_list(["bad"])
    run("test/basic_syntax/simple_choice_goto.yaml")
    assert view.get_text_commands_called() == ["This is the start of the program.", "Now you make a choice (this should only appear once).", "You're headed to the bad block.", "You're in the bad block."]


def test_simple_choice(view):
    view.update_choice_list(["continue"])
    run("test/basic_syntax/simple_choice.yaml")
    assert view.get_text_commands_called() == ["This is the start of the program.", "This is the text after the choice.", "You made a choice."]


def test_simple_goto(view):
    run("test/basic_syntax/simple_goto.yaml")
    assert view.get_text_commands_called() == ["This is the start of the program.", "Arrived at other block.", "Arrived at child block. End of program."]


######################################################################
# game_objects
######################################################################


def test_game_objects(view):
    view.update_choice_list([])
    run("test/game_objects/simple_bags.yaml")
    assert view.get_text_commands_called() == ["0", "2", "2"]
