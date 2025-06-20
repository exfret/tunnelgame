import pytest


from engine.view import ViewForTesting


from tests.test_gamestate import gamestate_with_multiblock_game
from tests.test_config import config_for_view_for_testing
from tests.test_addressing import addressing_with_multiblock_game
from tests.test_utility import utility_with_multiblock_game


@pytest.fixture
def view_with_multiblock_game():
    """
    A ViewForTesting object based on multiblock gameobject.
    """

    view = ViewForTesting(gamestate_with_multiblock_game, config_for_view_for_testing, addressing_with_multiblock_game, utility_with_multiblock_game)

    return view