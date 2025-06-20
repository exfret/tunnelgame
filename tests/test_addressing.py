import pytest


from engine.addressing import Addressing


from tests.test_gamestate import gamestate_with_simple_game, gamestate_with_multiblock_game


@pytest.fixture
def addressing_with_simple_game(gamestate_with_simple_game):
    """
    Addressing fixture having a gamestate with a simple game inside.
    """

    addressing = Addressing(gamestate_with_simple_game)

    return addressing


@pytest.fixture
def addressing_with_multiblock_game(gamestate_with_multiblock_game):
    """
    Addressing fixture having a gamestate with a middling sized game inside.
    """

    addressing = Addressing(gamestate_with_multiblock_game)

    return addressing


def test_get_node_root(addressing_with_simple_game):
    assert(addressing_with_simple_game.get_node(()) == addressing_with_simple_game.gamestate.game)


def test_get_node_instr(addressing_with_simple_game):
    assert(addressing_with_simple_game.get_node(("_content", 0))) == addressing_with_simple_game.gamestate.game["_content"][0]


def test_get_next_addr_increment(addressing_with_multiblock_game):
    assert(addressing_with_multiblock_game.get_next_addr(("_content", 0)) == ("_content", 1))


def test_get_next_addr_spill(addressing_with_multiblock_game):
    assert(addressing_with_multiblock_game.get_next_addr(("_content", 1, "then", 0)) == ("_content", 2))


def test_get_next_addr_dont_spill(addressing_with_multiblock_game):
    assert(addressing_with_multiblock_game.get_next_addr(("_content", 2, "effects", 0)) == False)


def test_get_next_addr_block_exhausted(addressing_with_multiblock_game):
    assert(addressing_with_multiblock_game.get_next_addr(("_content", 3)) == False)


# TODO: Past get_next_addr