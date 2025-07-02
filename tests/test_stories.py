import os
from pathlib import Path

from engine.interpreter import ErrorNode
from engine.gameparser import IncorrectStructureError
from engine.gamesession import GameSession


######################################################################
# examples
######################################################################


# Just make sure the examples compile
def test_examples():
    # Repeated code for getting stories path
    stories_path = Path(os.getenv("TUNNELGAME_DATA_DIR", Path.home() / "tunnelgame")) / "stories"
    for story_yaml in (stories_path / "stories").rglob("*.yaml"):
        gamesession = GameSession(story_yaml, "test")
        gamesession.gameloop.run(str(story_yaml.relative_to(stories_path)))


######################################################################
# basic_syntax
######################################################################


def test_error():
    test_file = "test/basic_syntax/error.yaml"
    gamesession = GameSession(test_file, "test")

    try:
        gamesession.gameloop.run(test_file)
    except ErrorNode:
        pass
    else:
        assert False


def test_hello_world():
    test_file = "test/basic_syntax/hello_world.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["Hello, World!"]


def test_list_block():
    test_file = "test/basic_syntax/list_block.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["stay".split(), "leave".split()])
    assert gamesession.view.get_text_commands_called() == ["a", "b", "b", "c"]


def test_print_with_vars():
    test_file = "test/basic_syntax/print_with_vars.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["Hello, World!"]


def test_shop():
    test_file = "test/basic_syntax/shop.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["use".split(), "buy".split(), "buy".split(), "use".split()])
    assert gamesession.view.get_text_commands_called() == ["5", "0", "bought", "2", "1", "used", "2", "1"]


def test_set_instr():
    test_file = "test/basic_syntax/set_instr.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["2", "-1", "1"]


def test_simple_choice_goto():
    test_file = "test/basic_syntax/simple_choice_goto.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["good".split()])
    assert gamesession.view.get_text_commands_called() == [
        "This is the start of the program.",
        "Now you make a choice (this should only appear once).",
        "You're headed to the good block.",
        "You're in the good block.",
    ]

    # TODO: Should we separate this out like we have the others?
    gamesession.gameloop.run(test_file, starting_input=["bad".split()])
    assert gamesession.view.get_text_commands_called() == [
        "This is the start of the program.",
        "Now you make a choice (this should only appear once).",
        "You're headed to the bad block.",
        "You're in the bad block.",
    ]


def test_simple_choice():
    test_file = "test/basic_syntax/simple_choice.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["continue".split()])
    assert gamesession.view.get_text_commands_called() == [
        "This is the start of the program.",
        "This is the text after the choice.",
        "You made a choice.",
    ]


def test_simple_goto():
    test_file = "test/basic_syntax/simple_goto.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == [
        "This is the start of the program.",
        "Arrived at other block.",
        "Arrived at child block. End of program.",
    ]


######################################################################
# instruction
######################################################################


def test_instruction_choice_alt_effects():
    test_file = "test/instruction/choice/alt_effects.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["false_choice".split()])
    assert gamesession.view.get_text_commands_called() == ["start", "Not true"]


def test_instruction_choice_enforce():
    test_file = "test/instruction/choice/enforce.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["impossible".split(), "possible".split()])
    assert gamesession.view.get_text_commands_called() == ["start", "This should print"]


def test_instruction_choice_selectable_once():
    test_file = "test/instruction/choice/selectable_once.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["select".split(), "select".split()])
    assert gamesession.view.get_text_commands_called() == ["start", "start"]


def test_instruction_flag_basic():
    test_file = "test/instruction/flag/basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["flagit".split()])
    assert gamesession.view.get_text_commands_called() == ["start", "flagging", "start", "flagged"]


def test_instruction_if_dict_condition():
    test_file = "test/instruction/if/dict_condition.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["nay", "yay"]


def test_instruction_inject_basic():
    test_file = "test/instruction/inject/basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["first".split(), "second".split(), "third".split()])
    assert gamesession.view.get_text_commands_called() == ["Hi", "First", "Bye", "Hi", "First", "Bye", "afterward", "First", "Something", "Bye"]


def test_instruction_remove_choice_basic():
    test_file = "test/instruction/remove_choice/basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["removed".split(), "not_removed".split()])
    assert gamesession.view.get_text_commands_called() == ["start", "yep"]


def test_instruction_spill_basic():
    test_file = "test/instruction/spill/basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["hi".split()])
    assert gamesession.view.get_text_commands_called() == ["blop", "okay", "blop"]


def test_instruction_spill_parse_catch():
    test_file = "test/instruction/spill/parse_catch.yaml"
    gamesession = GameSession(test_file, "test")

    try:
        gamesession.gameloop.run(test_file)
    except IncorrectStructureError:
        pass
    else:
        assert False


def test_instruction_stop_text():
    test_file = "test/instruction/stop/text.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["First"]


def test_instruction_stop_choice():
    test_file = "test/instruction/stop/choice.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["second".split(), "first".split(), "second".split()])
    assert gamesession.view.get_text_commands_called() == ["yay", "nay"]


######################################################################
# vars
######################################################################


def test_vars_args_print():
    test_file = "test/vars/args_print.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["print_arg hi".split()])
    assert gamesession.view.get_text_commands_called() == ["start", "hi"]


def test_vars_args_out_of_bounds():
    test_file = "test/vars/args_out_of_bounds.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["out_of_bounds".split()])
    assert gamesession.view.get_text_commands_called() == ["start", "yes"]


def test_vars_floats():
    test_file = "test/vars/floats.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file, starting_input=["shop".split()])
    assert gamesession.view.get_text_commands_called() == ["3.5", "2.7"]


def test_vars_locale_basic():
    test_file = "test/vars/locale_basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run("test/vars/locale_basic.yaml")
    assert gamesession.view.get_text_commands_called() == ["has_no_locale", "This has a locale"]


def test_vars_locale_plurals():
    test_file = "test/vars/locale_plurals.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["happy", "happy"]