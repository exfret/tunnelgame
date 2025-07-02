import pytest


from engine.gameloop import GameLoop


from tests.test_gamestate import gamestate_with_multiblock_game
from tests.test_config import config_for_view_for_testing
from tests.test_addressing import addressing_with_multiblock_game
from tests.test_utility import utility_with_multiblock_game
from tests.test_view import view_with_multiblock_game
from tests.test_gameparser import gameparser_with_hardcoded_multiblock_game
from tests.test_interpreter import interpreter_with_hardcoded_multiblock_game


@pytest.fixture
def gameloop_with_hardcoded_multiblock_game(gamestate_with_multiblock_game, config_for_view_for_testing, addressing_with_multiblock_game, utility_with_multiblock_game, view_with_multiblock_game, gameparser_with_hardcoded_multiblock_game, interpreter_with_hardcoded_multiblock_game):
    """
    GameLoop instance with hardcoded simple game.
    """

    gameloop = GameLoop(gamestate_with_multiblock_game, config_for_view_for_testing, addressing_with_multiblock_game, utility_with_multiblock_game, view_with_multiblock_game, gameparser_with_hardcoded_multiblock_game, interpreter_with_hardcoded_multiblock_game)

    return gameloop


def test_gameloop_start_choice(gameloop_with_hardcoded_multiblock_game):
    gameloop_with_hardcoded_multiblock_game.setup_game()
    assert(len(gameloop_with_hardcoded_multiblock_game.gamestate.light.choices) == 1)
    assert(next(iter(gameloop_with_hardcoded_multiblock_game.gamestate.light.choices.keys())) == "start")


def test_calc_lookahead_gamesession_info(gameloop_with_hardcoded_multiblock_game):
    gameloop_with_hardcoded_multiblock_game.setup_game()
    gameloop_with_hardcoded_multiblock_game.calc_lookaheads()
    assert(len(gameloop_with_hardcoded_multiblock_game.lookahead_data) == 1)
    assert(next(iter(gameloop_with_hardcoded_multiblock_game.lookahead_data.keys())) == "start")
    gameloop_with_hardcoded_multiblock_game.make_choice(gameloop_with_hardcoded_multiblock_game.gamestate.light.choices["start"]["address"])
    gameloop_with_hardcoded_multiblock_game.calc_lookaheads()
    assert(len(gameloop_with_hardcoded_multiblock_game.lookahead_data) == 1)
    assert(next(iter(gameloop_with_hardcoded_multiblock_game.lookahead_data.keys())) == "child1")


def test_gameloop_run_basic(gameloop_with_hardcoded_multiblock_game):
    gameloop_with_hardcoded_multiblock_game.setup_game()
    gameloop_with_hardcoded_multiblock_game.run(loaded_game_state={"client_side": None, "state": gameloop_with_hardcoded_multiblock_game.gamestate}, do_lookaheads=True, starting_input=["child1", "exit"])