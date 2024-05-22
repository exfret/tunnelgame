# Standard imports
import os
import yaml

# Local imports
import interpreter
import gameparser

with open(
    "/Users/kylehess/Documents/programs/tunnelgame/stories/exploration_basic.yaml", "r"
) as file:
    game = yaml.safe_load(file)

state = {
    "choices": {"start": {"text": "Start the game", "address": ("_content", 0)}}, # Dict of choice ID's to new locations and descriptions
    "bookmark": (), # bookmark is a queue (tuple) of call stacks (tuples) containing addresses (tuples)
    "metadata": {"node_types": {}},
    "settings": {"show_flavor_text": "once"},
    "vars": {},
    "visits": {}
}

gameparser.add_vars(game, state)
gameparser.parse(game, state)

# verify also creates vars on the fly, so it needs the state
# gameparser.verify(game, state)
# gameparser.init_vars(game, state)

os.system("clear")

def print_choices(state):
    print("\n        Choices are as follows...")
    for choice_id, choice in state["choices"].items():
        choice_color = "\033[32m"
        text_color = "\033[0m"
        if len(choice["missing"]) > 0:
            choice_color = "\033[90m"
            text_color = "\033[90m"
        new_text = ""
        if state["visits"][choice["choice_address"]] <= 1:
            new_text = "\033[33m(New) "
        print("        " + text_color + " * " + new_text + choice_color + choice_id + text_color + " " + choice["text"])
        if len(choice["missing"]) > 0:
            missing_text = "              Missing: "
            for missing in choice["missing"]:
                missing_text += missing + ", "
            missing_text = missing_text[:-2]
            print(missing_text)

autostart = True

if autostart:
    state["bookmark"] = ()
    interpreter.make_bookmark(game, state, state["choices"]["start"]["address"])
    state["choices"] = {}

    while interpreter.step(game, state):
        pass

    print_choices(state)

while True:
    command = input("\n> ")
    command = command.split(" ")
    print("") # Add a new line

    if command[0] == "exit":
        break
    elif command[0] == "help":
        print("Valid commands are 'exit', 'help', 'inspect', and 'settings'.")
    elif command[0] == "inspect":
        if len(command) < 2:
            print("Must give a variable to print the value of.")
        else:
            if command[1] in state["vars"]:
                print(state["vars"][command[1]])
            else:
                print("That's not a valid variable")
    elif command[0] == "settings":
        if len(command) < 2:
            print("Must give a setting to give a new value to or test the current value of. Here is a list of settings:\n")
            for key in state["settings"].keys():
                print(" * " + key)
        else:
            if command[1] == "show_flavor_text":
                if len(command) < 3:
                    print("Allowed values are 'always', 'once', and 'never'. The current value of this setting is '" + state["settings"]["show_flavor_text"] + "'")
                elif command[2] == "always" or command[2] == "once" or command[2] == "never":
                    state["settings"]["show_flavor_text"] = command[2]
                    print("Set show_flavor_text to '" + command[2] + "'")
                else:
                    print("That's not an allowed value of show_flavor_text. Allowed values are 'always', 'once', and 'never'")
    elif command[0] in state["choices"]:
        choice = state["choices"][command[0]]
        if not ("missing" in choice):
            choice["missing"] = []
        if not ("modifications" in choice):
            choice["modifications"] = []

        if len(choice["missing"]) > 0:
            print("Missing required materials.")
        else:
            # Pay required costs
            for modification in choice["modifications"]:
                state["vars"][modification["var"]] += modification["amount"]
            
            state["bookmark"] = ()
            interpreter.make_bookmark(game, state, choice["address"])
            state["choices"] = {}
            # Populate the state vars with args
            state["vars"]["_args"] = []
            for arg in command[1:]:
                state["vars"]["_args"].append(arg)

            os.system("clear")
            
            while interpreter.step(game, state):
                pass

            print_choices(state)
    else:
        print("Unrecognized command/choice. Type 'help' for commands or 'choices' for a list of choices.")