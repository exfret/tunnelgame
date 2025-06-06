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

    gamesession.view.update_choice_list([])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["Hello, World!"]


def test_list_block():
    test_file = "test/basic_syntax/list_block.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["stay", "leave"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["a", "b", "b", "c"]


def test_print_with_vars():
    test_file = "test/basic_syntax/print_with_vars.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list([])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["Hello, World!"]


def test_shop():
    test_file = "test/basic_syntax/shop.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["use", "buy", "buy", "use"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["5", "0", "bought", "2", "1", "used", "2", "1"]


def test_set_instr():
    test_file = "test/basic_syntax/set_instr.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list([])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["2", "-1", "1"]


def test_simple_choice_goto():
    test_file = "test/basic_syntax/simple_choice_goto.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["good"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == [
        "This is the start of the program.",
        "Now you make a choice (this should only appear once).",
        "You're headed to the good block.",
        "You're in the good block.",
    ]

    # TODO: Should we separate this out like we have the others?
    gamesession.view.update_choice_list(["bad"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == [
        "This is the start of the program.",
        "Now you make a choice (this should only appear once).",
        "You're headed to the bad block.",
        "You're in the bad block.",
    ]


def test_simple_choice():
    test_file = "test/basic_syntax/simple_choice.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["continue"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == [
        "This is the start of the program.",
        "This is the text after the choice.",
        "You made a choice.",
    ]


def test_simple_goto():
    test_file = "test/basic_syntax/simple_goto.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list([])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == [
        "This is the start of the program.",
        "Arrived at other block.",
        "Arrived at child block. End of program.",
    ]


######################################################################
# game_objects
######################################################################


def test_game_objects_simple_bags():
    test_file = "test/game_objects/simple_bags.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list([])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["0", "2", "2"]


######################################################################
# instruction
######################################################################


def test_instruction_back_basic():
    test_file = "test/instruction/back/basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["forward", "return"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["beginning", "forward", "beginning"]


def test_instruction_back_syntactic_sugar():
    test_file = "test/instruction/back/syntactic_sugar.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["forward", "back"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["beginning", "forward", "beginning"]


def test_instruction_back_twice():
    test_file = "test/instruction/back/twice.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["first", "second", "back", "back"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["beginning", "first", "second", "first", "beginning"]


def test_instruction_choice_alt_effects():
    test_file = "test/instruction/choice/alt_effects.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["false_choice"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["start", "Not true"]


def test_instruction_choice_enforce():
    test_file = "test/instruction/choice/enforce.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["impossible", "possible"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["start", "This should print"]


def test_instruction_choice_selectable_once():
    test_file = "test/instruction/choice/selectable_once.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["select", "select"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["start", "start"]


def test_instruction_flag_basic():
    test_file = "test/instruction/flag/basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["flagit"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["start", "flagging", "start", "flagged"]


def test_instruction_if_dict_condition():
    test_file = "test/instruction/if/dict_condition.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list([])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["nay", "yay"]


def test_instruction_remove_choice_basic():
    test_file = "test/instruction/remove_choice/basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["removed", "not_removed"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["start", "yep"]


def test_instruction_spill_basic():
    test_file = "test/instruction/spill/basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["hi"])
    gamesession.gameloop.run(test_file)
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


######################################################################
# vars
######################################################################


def test_vars_args_print():
    test_file = "test/vars/args_print.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["print_arg hi"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["start", "hi"]


def test_vars_args_out_of_bounds():
    test_file = "test/vars/args_out_of_bounds.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["out_of_bounds"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["start", "yes"]


def test_vars_floats():
    test_file = "test/vars/floats.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list(["shop"])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["3.5", "2.7"]


def test_vars_locale_basic():
    test_file = "test/vars/locale_basic.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list([])
    gamesession.gameloop.run("test/vars/locale_basic.yaml")
    assert gamesession.view.get_text_commands_called() == ["has_no_locale", "This has a locale"]


def test_vars_locale_plurals():
    test_file = "test/vars/locale_plurals.yaml"
    gamesession = GameSession(test_file, "test")

    gamesession.view.update_choice_list([])
    gamesession.gameloop.run(test_file)
    assert gamesession.view.get_text_commands_called() == ["happy", "happy"]