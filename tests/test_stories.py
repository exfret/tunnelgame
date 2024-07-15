# Tests for:
#   - Local variables

# In test_gameloop.py
from engine import config, view
from engine.config import stories
from engine.gameloop import run
from engine.interpreter import ErrorNode


config.view = view.ViewForTesting()
curr_view = config.view


######################################################################
# examples
######################################################################


# Just make sure the examples compile
def test_examples():
    for story_yaml in (stories / "examples").rglob("*.yaml"):
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
        assert False


def test_hello_world():
    curr_view.update_choice_list([])
    run("test/basic_syntax/hello_world.yaml")
    assert curr_view.get_text_commands_called() == ["Hello, World!"]


def test_list_block():
    curr_view.update_choice_list(["stay", "leave"])
    run("test/basic_syntax/list_block.yaml")
    assert curr_view.get_text_commands_called() == ["a", "b", "b", "c"]


def test_print_with_vars():
    curr_view.update_choice_list([])
    run("test/basic_syntax/print_with_vars.yaml")
    assert curr_view.get_text_commands_called() == ["Hello, World!"]


def test_shop():
    curr_view.update_choice_list(["use", "buy", "buy", "use"])
    run("test/basic_syntax/shop.yaml")
    assert curr_view.get_text_commands_called() == ["5", "0", "bought", "2", "1", "used", "2", "1"]


def test_set_instr():
    curr_view.update_choice_list([])
    run("test/basic_syntax/set_instr.yaml")
    assert curr_view.get_text_commands_called() == ["2", "-1", "1"]


def test_simple_choice_goto():
    curr_view.update_choice_list(["good"])
    run("test/basic_syntax/simple_choice_goto.yaml")
    assert curr_view.get_text_commands_called() == [
        "This is the start of the program.",
        "Now you make a choice (this should only appear once).",
        "You're headed to the good block.",
        "You're in the good block.",
    ]

    curr_view.update_choice_list(["bad"])
    run("test/basic_syntax/simple_choice_goto.yaml")
    assert curr_view.get_text_commands_called() == [
        "This is the start of the program.",
        "Now you make a choice (this should only appear once).",
        "You're headed to the bad block.",
        "You're in the bad block.",
    ]


def test_simple_choice():
    curr_view.update_choice_list(["continue"])
    run("test/basic_syntax/simple_choice.yaml")
    assert curr_view.get_text_commands_called() == [
        "This is the start of the program.",
        "This is the text after the choice.",
        "You made a choice.",
    ]


def test_simple_goto():
    curr_view.update_choice_list([])
    run("test/basic_syntax/simple_goto.yaml")
    assert curr_view.get_text_commands_called() == [
        "This is the start of the program.",
        "Arrived at other block.",
        "Arrived at child block. End of program.",
    ]


######################################################################
# game_objects
######################################################################


def test_game_objects():
    curr_view.update_choice_list([])
    run("test/game_objects/simple_bags.yaml")
    assert curr_view.get_text_commands_called() == ["0", "2", "2"]


######################################################################
# vars
######################################################################


def test_floats():
    curr_view.update_choice_list(["shop"])
    run("test/vars/floats.yaml")
    assert curr_view.get_text_commands_called() == ["3.5", "2.7"]