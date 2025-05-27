# Tests for:
#   - Local variables

# In test_gameloop.py
from engine import config, view
from engine.config import stories
from engine.gameloop import run
from engine.interpreter import ErrorNode
from engine.gameparser import IncorrectStructureError


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


def test_game_objects_simple_bags():
    curr_view.update_choice_list([])
    run("test/game_objects/simple_bags.yaml")
    assert curr_view.get_text_commands_called() == ["0", "2", "2"]


######################################################################
# instruction
######################################################################


def test_instruction_back_basic():
    curr_view.update_choice_list(["forward", "return"])
    run("test/instruction/back/basic.yaml")
    assert curr_view.get_text_commands_called() == ["beginning", "forward", "beginning"]


def test_instruction_back_syntactic_sugar():
    curr_view.update_choice_list(["forward", "back"])
    run("test/instruction/back/syntactic_sugar.yaml")
    assert curr_view.get_text_commands_called() == ["beginning", "forward", "beginning"]


def test_instruction_back_twice():
    curr_view.update_choice_list(["first", "second", "back", "back"])
    run("test/instruction/back/twice.yaml")
    assert curr_view.get_text_commands_called() == ["beginning", "first", "second", "first", "beginning"]


def test_instruction_choice_alt_effects():
    curr_view.update_choice_list(["false_choice"])
    run("test/instruction/choice/alt_effects.yaml")
    assert curr_view.get_text_commands_called() == ["start", "Not true"]


def test_instruction_choice_enforce():
    curr_view.update_choice_list(["impossible", "possible"])
    run("test/instruction/choice/enforce.yaml")
    assert curr_view.get_text_commands_called() == ["start", "This should print"]


def test_instruction_choice_selectable_once():
    curr_view.update_choice_list(["select", "select"])
    run("test/instruction/choice/selectable_once.yaml")
    assert curr_view.get_text_commands_called() == ["start", "start"]


def test_instruction_flag_basic():
    curr_view.update_choice_list(["flagit"])
    run("test/instruction/flag/basic.yaml")
    assert curr_view.get_text_commands_called() == ["start", "flagging", "start", "flagged"]


def test_instruction_if_dict_condition():
    curr_view.update_choice_list([])
    run("test/instruction/if/dict_condition.yaml")
    assert curr_view.get_text_commands_called() == ["nay", "yay"]


def test_instruction_spill_basic():
    curr_view.update_choice_list(["hi"])
    run("test/instruction/spill/basic.yaml")
    assert curr_view.get_text_commands_called() == ["blop", "okay", "blop"]


def test_instruction_spill_parse_catch():
    try:
        run("test/instruction/spill/parse_catch.yaml")
    except IncorrectStructureError:
        pass
    else:
        assert False


######################################################################
# vars
######################################################################


def test_vars_args_print():
    curr_view.update_choice_list(["print_arg hi"])
    run("test/vars/args_print.yaml")
    assert curr_view.get_text_commands_called() == ["start", "hi"]


def test_vars_args_out_of_bounds():
    curr_view.update_choice_list(["out_of_bounds"])
    run("test/vars/args_out_of_bounds.yaml")
    assert curr_view.get_text_commands_called() == ["start", "yes"]


def test_vars_floats():
    curr_view.update_choice_list(["shop"])
    run("test/vars/floats.yaml")
    assert curr_view.get_text_commands_called() == ["3.5", "2.7"]


def test_vars_locale_basic():
    curr_view.update_choice_list([])
    run("test/vars/locale_basic.yaml")
    assert curr_view.get_text_commands_called() == ["has_no_locale", "This has a locale"]


def test_vars_locale_plurals():
    curr_view.update_choice_list([])
    run("test/vars/locale_plurals.yaml")
    assert curr_view.get_text_commands_called() == ["happy", "happy"]