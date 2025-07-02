import pytest


from engine.gamesession import GameSession


@pytest.fixture
def gamesession_from_standard_test_story():
    """
    Loads a GameSession normally using the tests/standard.yaml file
    """

    gamesession = GameSession("test/standard.yaml", "test")

    return gamesession


def test_lookaheads_populated_after_prerun(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.prerun(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    assert(len(gamesession_from_standard_test_story.gameloop.lookahead_data) == 2)


def test_lookaheads_modify_light_state(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.prerun(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    assert(len(gamesession_from_standard_test_story.gamestate.light.choices) == 2)
    assert(gamesession_from_standard_test_story.gamestate.light.storypoints["first"] is False)
    gamesession_from_standard_test_story.view.update_choice_list(["begin"])
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(len(gamesession_from_standard_test_story.gamestate.light.choices) == 1)
    assert(gamesession_from_standard_test_story.gamestate.light.storypoints["first"] is True)
    # Make sure view's gamestate is the same as ours
    assert(gamesession_from_standard_test_story.view.gamestate is gamesession_from_standard_test_story.gamestate)


def test_lookaheads_populated_after_one_choice(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.prerun(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    assert(len(gamesession_from_standard_test_story.gameloop.lookahead_data) == 2)
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started"])
    gamesession_from_standard_test_story.view.update_choice_list(["begin"])
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(len(gamesession_from_standard_test_story.gameloop.lookahead_data) == 1)
    assert(next(iter(gamesession_from_standard_test_story.gameloop.lookahead_data.keys())) == "next")
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made"])


def test_lookaheads_populated_after_two_choices(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.prerun(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    gamesession_from_standard_test_story.view.update_choice_list(["begin"])
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(gamesession_from_standard_test_story.gamestate.bulk.vars[()]["test"]["value"] == 1)
    gamesession_from_standard_test_story.view.update_choice_list(["next"])
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(gamesession_from_standard_test_story.gamestate.bulk.vars[()]["test"]["value"] == 2)
    assert(len(gamesession_from_standard_test_story.gamestate.light.choices) == 3)
    assert(len(gamesession_from_standard_test_story.gameloop.lookahead_data) == 3)


def test_lookaheads_multi_text_catching(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.prerun(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True)
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started"])
    gamesession_from_standard_test_story.view.update_choice_list(["begin"])
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made"])
    gamesession_from_standard_test_story.view.update_choice_list(["next"])
    gamesession_from_standard_test_story.gameloop.run_step()
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made", "okay"])


def test_basic_choices_with_lookaheads(gamesession_from_standard_test_story):
    gamesession_from_standard_test_story.gameloop.run(game_name=gamesession_from_standard_test_story.config.story_name, do_lookaheads=True, starting_input=["begin".split(), "next".split()])
    assert(gamesession_from_standard_test_story.view.get_text_commands_called() == ["started", "made", "okay"])