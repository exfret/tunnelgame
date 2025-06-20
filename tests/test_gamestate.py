import copy
import pytest


from engine.gamestate import GameState, LineData, Diff


# _content:
#   - Hello, World!
gameobject_simple = {
    "_content": [
        "Hello, World!"
    ]
}


# _content:
#   - Hello, World!
#   - if: True
#     then:
#       - This should spill!
#   - choice: child1
#     effects:
#       - goto: /child1
#   - Don't spill here!
# child1:
#   - goto: ./child2/child1
# child2:
#   _content:
#     - Goodbye, World!
#   child1:
#     _content:
#       - goto: child2
#   child2:
#     - goto: ..
gameobject_multiblock = {
    "_content": [
        "Hello, World!",
        {
            "if": True,
            "then": [
                "This should spill!"
            ]
        },
        {
            "choice": "child1",
            "effects": [
                {
                    "goto": "/child1"
                }
            ]
        },
        "Don't spill here!"
    ],
    "child1": [
        {
            "goto": "./child2/child1"
        }
    ],
    "child2": {
        "_content": [
            "Goodbye, World"
        ],
        "child1": {
            "_content": [
                {
                    "goto": "child2"
                }
            ]
        },
        "child2": [
            {
                "goto": ".."
            }
        ]
    }
}


@pytest.fixture
def gamestate_empty():
    """
    Fresh GameState for every test.
    """
    return GameState()


@pytest.fixture
def gamestate_with_simple_game():
    """
    GameState with mock game inside. Also has GameData manually populated.
    """

    gamestate = GameState()

    gamestate.game = gameobject_simple

    # GameData stuff
    gamestate.game_data.file_homes = {
        (): True
    }
    gamestate.game_data.node_contexts = {
        (): {
            "START": True
        },
        ("_content",): {
            "CONTENT": True
        },
        ("_content", 0): {
            "INSTR": True,
            "_text": True
        }
    }

    return gamestate


@pytest.fixture
def gamestate_with_multiblock_game():
    """
    GameState with a middling sized game inside, first made for testing Addressing. Has no GameData.
    Is populated with simple vars, which are manually added (the story doesn't define them).
    """

    gamestate = GameState()

    gamestate.game = gameobject_multiblock

    gamestate.bulk.vars = {
        (): {
            "test": {"address": (), "locale": "Test", "possible_values": None, "value": 0, "global": False, "hidden": False},
            "test2": {"address": (), "locale": "Test2", "possible_values": None, "value": False, "global": False, "hidden": False},
            "test3": {"address": (), "locale": "Test2", "possible_values": None, "value": "test", "global": False, "hidden": False}
        },
        ("child1"): {
            "test": {"address": ("child1"), "locale": "TestInChild1", "possible_values": None, "value": 1, "global": False, "hidden": False}
        }
    }

    return gamestate


def test_inc_visits(gamestate_empty):
    gamestate_empty.bulk.per_line[()] = LineData(())
    assert(gamestate_empty.bulk.per_line[()].visits == 0)
    gamestate_empty.inc_visits(())
    assert(gamestate_empty.bulk.per_line[()].visits == 1)
    gamestate_empty.reverse_last_diffs()
    assert(gamestate_empty.bulk.per_line[()].visits == 0)


def test_inc_choice_visits(gamestate_empty):
    gamestate_empty.bulk.per_line[()] = LineData(())
    assert(gamestate_empty.bulk.per_line[()].choice_visits == 0)
    gamestate_empty.inc_choice_visits(())
    assert(gamestate_empty.bulk.per_line[()].choice_visits == 1)
    gamestate_empty.reverse_last_diffs()
    assert(gamestate_empty.bulk.per_line[()].choice_visits == 0)


def test_modify_flag(gamestate_empty):
    gamestate_empty.bulk.vars["flags"] = {
        "test": False
    }
    gamestate_empty.modify_flag("test", True)
    assert(gamestate_empty.bulk.vars["flags"]["test"] is True)
    gamestate_empty.reverse_last_diffs()
    assert(gamestate_empty.bulk.vars["flags"]["test"] is False)
    # Need to append another diffs list for next text
    gamestate_empty.diffs.append([])
    # Also test that it stays its original value if there was no change
    gamestate_empty.modify_flag("test", False)
    assert(gamestate_empty.bulk.vars["flags"]["test"] is False)


def test_modify_var(gamestate_empty):
    gamestate_empty.bulk.vars[()] = {
        "test": {"address": (), "locale": "test", "possible_values": None, "value": 0, "global": False, "hidden": False}
    }
    gamestate_empty.modify_var((), "test", 1)
    assert(gamestate_empty.bulk.vars[()]["test"]["value"] == 1)
    gamestate_empty.reverse_last_diffs()
    assert(gamestate_empty.bulk.vars[()]["test"]["value"] == 0)


def test_reverse_diff_list(gamestate_empty):
    gamestate_empty.bulk.per_line[()] = LineData(())
    gamestate_empty.bulk.vars["flags"] = {
        "test": False
    }
    gamestate_empty.bulk.vars[()] = {
        "test": {"address": (), "locale": "test", "possible_values": None, "value": 0, "global": False, "hidden": False}
    }
    gamestate_empty.modify_flag("test", True)
    gamestate_empty.modify_var((), "test", 1)
    gamestate_empty.inc_visits(())
    gamestate_empty.inc_visits(())
    gamestate_empty.inc_choice_visits(())
    gamestate_empty.modify_flag("test", False)
    gamestate_empty.modify_var((), "test", 2)
    gamestate_empty.reverse_last_diffs()
    assert(gamestate_empty.bulk.vars[()]["test"]["value"] == 0)
    assert(gamestate_empty.bulk.vars["flags"]["test"] is False)
    assert(gamestate_empty.bulk.per_line[()].visits == 0)
    assert(gamestate_empty.bulk.per_line[()].choice_visits == 0)


def test_reverse_diff_multiple_lists(gamestate_empty):
    gamestate_empty.bulk.per_line[()] = LineData(())
    gamestate_empty.inc_visits(())
    gamestate_empty.create_new_diff_list()
    gamestate_empty.inc_visits(())
    gamestate_empty.inc_visits(())
    gamestate_empty.inc_visits(())
    gamestate_empty.create_new_diff_list()
    gamestate_empty.reverse_last_diffs()
    assert(gamestate_empty.bulk.per_line[()].visits == 4)
    gamestate_empty.reverse_last_diffs()
    assert(gamestate_empty.bulk.per_line[()].visits == 1)
    gamestate_empty.reverse_last_diffs()
    assert(gamestate_empty.bulk.per_line[()].visits == 0)


# TODO: Add tests for applying diffs?