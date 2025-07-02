import pytest


from engine.interpreter import Interpreter


from tests.test_gamestate import gamestate_with_multiblock_game
from tests.test_config import config_for_view_for_testing
from tests.test_addressing import addressing_with_multiblock_game
from tests.test_utility import utility_with_multiblock_game
from tests.test_view import view_with_multiblock_game
from tests.test_gameparser import gameparser_with_hardcoded_multiblock_game


@pytest.fixture
def interpreter_with_hardcoded_multiblock_game(gamestate_with_multiblock_game, config_for_view_for_testing, addressing_with_multiblock_game, utility_with_multiblock_game, view_with_multiblock_game, gameparser_with_hardcoded_multiblock_game):
    """
    Interpreter instance having game object hardcoded.
    """

    interpreter = Interpreter(gamestate_with_multiblock_game, config_for_view_for_testing, addressing_with_multiblock_game, utility_with_multiblock_game, view_with_multiblock_game, gameparser_with_hardcoded_multiblock_game)

    return interpreter