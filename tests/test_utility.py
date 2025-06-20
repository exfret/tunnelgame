import pytest


from engine.utility import Utility


from tests.test_gamestate import gamestate_with_multiblock_game
from tests.test_addressing import addressing_with_multiblock_game


@pytest.fixture
def utility_with_multiblock_game():
    """
    Takes a multiblock game and makes a simple Utility object from it.
    """

    utility = Utility(gamestate_with_multiblock_game, addressing_with_multiblock_game)

    return utility