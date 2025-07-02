import pytest


from tests.test_gamesession import gamesession_from_standard_test_story


def test_command_define(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_define("define blop begin".split())
    gamesession_from_standard_test_story.gamestate.light.command_buffer.append("blop".split())
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made"])


def test_command_define_recursion(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_define("define blop begin".split())
    gamesession_from_standard_test_story.gameloop.command_define("define derp input blop, next".split())
    gamesession_from_standard_test_story.gamestate.light.command_buffer.append("derp".split())
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made", "okay"])


def test_command_undefine(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_define("define blop begin".split())
    assert(len(gamesession_from_standard_test_story.gamestate.light.command_macros) == 1)
    gamesession_from_standard_test_story.gameloop.command_undefine("undefine blop".split())
    assert(len(gamesession_from_standard_test_story.gamestate.light.command_macros) == 0)
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gamestate.light.command_buffer.append("blop".split())
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started"])


def test_command_clear(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_clear("clear".split())
    assert(gamesession_from_standard_test_story.gamestate.light.view.testing_commands_called[-2]["id"] == "clear")
    assert(gamesession_from_standard_test_story.gamestate.light.view.testing_commands_called[-1]["id"] == "print_choices")


def test_command_exit(gamesession_from_standard_test_story):
    """
    Does not test actual exit process, just that gamestate.light.closed is set to True
    """
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_exit("exit".split())
    assert(gamesession_from_standard_test_story.gamestate.light.closed is True)


def test_command_flag(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    assert(gamesession_from_standard_test_story.gamestate.bulk.vars["flags"]["this_is_a_flag"] is False)
    gamesession_from_standard_test_story.gameloop.command_flag("flag this_is_a_flag".split())
    assert(gamesession_from_standard_test_story.gamestate.bulk.vars["flags"]["this_is_a_flag"] is True)


def test_command_goto(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    assert(gamesession_from_standard_test_story.gamestate.light.last_address == ("_content", 2))
    gamesession_from_standard_test_story.gameloop.command_goto("goto begin".split())
    assert(gamesession_from_standard_test_story.gamestate.light.last_address == ("begin", "_content", 3))
    gamesession_from_standard_test_story.gameloop.command_goto("goto ..".split())
    assert(gamesession_from_standard_test_story.gamestate.light.last_address == ("_content", 2))


def test_command_help(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_help("help".split())
    assert(gamesession_from_standard_test_story.gamestate.light.view.testing_commands_called[-1]["msg"] == "help")


def test_command_help_info(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_help("help input".split())
    assert(gamesession_from_standard_test_story.gamestate.light.view.testing_commands_called[-1]["msg"] == "help_input")


def test_command_info(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_info("info".split())
    assert(gamesession_from_standard_test_story.gamestate.light.view.testing_commands_called[-1]["msg"] == "info_options")


def test_command_input_choices(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_input("input begin, next".split())
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made", "okay"])


def test_command_inspect(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.gameloop.command_inspect("inspect test".split())
    assert(gamesession_from_standard_test_story.gamestate.light.view.testing_commands_called[-1]["id"] == "print_var_value")
    assert(gamesession_from_standard_test_story.gamestate.light.view.testing_commands_called[-1]["var_value"] == 0)


def test_command_save_load(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True, starting_input=["save test".split(), "confirm".split()])
    gamesession_from_standard_test_story.gamestate.light.command_buffer.append("load test".split())
    # Need to add module vars with prerun since exiting removed them
    gamesession_from_standard_test_story.gameloop.prerun(loaded_game_state={"state": gamesession_from_standard_test_story.gamestate})
    gamesession_from_standard_test_story.gameloop.run_step()
    assert("begin" in gamesession_from_standard_test_story.gamestate.light.choices)


def test_command_repeat_with_input(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.prerun(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True, starting_input=["repeat 10 input nah, up".split()])
    assert(len(gamesession_from_standard_test_story.gamestate.light.command_buffer) == 1)
    gamesession_from_standard_test_story.gameloop.run(loaded_game_state={"state": gamesession_from_standard_test_story.gamestate})
    assert(len(gamesession_from_standard_test_story.view.get_text_commands_called()) == 21)
    assert(gamesession_from_standard_test_story.view.get_text_commands_called()[-2:] == ["ah", "started"])


# Don't test restart unless it starts being an issue, since it's not too compatible with ViewForTesting


def test_command_revert_basic(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True, starting_input=["begin".split()])
    gamesession_from_standard_test_story.gameloop.command_revert("revert".split())
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started"])


def test_command_revert_from_beginning(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True, starting_input=[])
    gamesession_from_standard_test_story.gameloop.command_revert("revert".split())
    gamesession_from_standard_test_story.gameloop.command_revert("revert".split())
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started"])


def test_command_revert_back_and_forth(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True, starting_input=["begin".split(), "next".split()])
    assert(len(gamesession_from_standard_test_story.gamestate.diffs) == 3)
    assert(len(gamesession_from_standard_test_story.gamestate.diffs[0]) == 4)
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made", "okay"])
    gamesession_from_standard_test_story.gameloop.command_revert("revert".split())
    assert(len(gamesession_from_standard_test_story.gamestate.diffs[0]) == 4)
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made"])
    gamesession_from_standard_test_story.gameloop.command_revert("revert".split())
    assert(len(gamesession_from_standard_test_story.gamestate.diffs[0]) == 4)
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started"])
    gamesession_from_standard_test_story.gameloop.command_revert("revert".split())
    assert(len(gamesession_from_standard_test_story.gamestate.diffs[0]) == 4)
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started"])
    assert(len(gamesession_from_standard_test_story.gamestate.diffs) == 1)
    gamesession_from_standard_test_story.gamestate.light.command_buffer = []
    gamesession_from_standard_test_story.gameloop.prerun(loaded_game_state={"state": gamesession_from_standard_test_story.gamestate})
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gameloop.run_step()
    gamesession_from_standard_test_story.gameloop.run_step()
    # This gobbles memory for some reason
    #gamesession_from_standard_test_story.gameloop.run(loaded_game_state={"state": gamesession_from_standard_test_story.gamestate})
    assert(len(gamesession_from_standard_test_story.gamestate.diffs[0]) == 4)
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started"])
    assert(len(gamesession_from_standard_test_story.gamestate.diffs) == 1)
    gamesession_from_standard_test_story.gamestate.light.command_buffer.append("begin".split())
    gamesession_from_standard_test_story.gamestate.light.command_buffer.append("next".split())
    gamesession_from_standard_test_story.gameloop.run(loaded_game_state={"state": gamesession_from_standard_test_story.gamestate})
    
    assert(gamesession_from_standard_test_story.gamestate.diffs[-1][-1].diff_type is False)
    assert(len(gamesession_from_standard_test_story.gamestate.diffs[0]) == 4)
    #assert(len(gamesession_from_standard_test_story.gamestate.diffs) == 3)

    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made", "okay"])
    gamesession_from_standard_test_story.gameloop.command_revert("revert".split())
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made"])


# Then, test with gotos