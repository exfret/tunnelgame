import yaml

with open(
    "/Users/kylehess/Documents/programs/tunnelgame/stories/machine_plot.yaml", "r"
) as file:
    game = yaml.safe_load(file)

state = {
    "choices": {"start": {"text": "Start the game", "address": ("_content", 0)}}, # Dict of choice ID's to new locations and descriptions
    "bookmark": (), # bookmark is a queue (tuple) of call stacks (tuples) containing addresses (tuples)
    "file_data": {"filename": ""}, # TODO: Include some sort of hash or name of game
    "map": {},
    "metadata": {"node_types": {}}, # TODO: Rename to 'story_data' or something such, maybe remove after parsing overhaul
    "settings": {"show_flavor_text": "once"},
    "vars": {},
    "visits": {}
}