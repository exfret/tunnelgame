import os
from pathlib import Path
import pytest
import sys
import yaml


from engine.gameparser import GameParser


from tests.test_gamestate import gamestate_with_multiblock_game
from tests.test_config import config_for_view_for_testing
from tests.test_addressing import addressing_with_multiblock_game
from tests.test_utility import utility_with_multiblock_game


@pytest.fixture
def gameparser_with_hardcoded_multiblock_game():
    """
    GameParser object with gamestate determined by hardcoded values in gamestate_with_multiblock_game.
    """

    grammar = yaml.safe_load((Path(getattr(sys, '_MEIPASS', os.path.abspath('.'))) / "engine" / "grammar.yaml").read_text())

    gameparser = GameParser(gamestate_with_multiblock_game, config_for_view_for_testing, addressing_with_multiblock_game, utility_with_multiblock_game, grammar)

    return gameparser


def test_gameparser_fixture(gameparser_with_hardcoded_multiblock_game):
    assert(isinstance(gameparser_with_hardcoded_multiblock_game.grammar, dict))