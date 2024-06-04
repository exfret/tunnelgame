# Standard imports
import os
import pickle
import yaml

# Local imports
import addressing
import interpreter
import gameparser

# Config imports
from config import game, state

gameparser.add_vars(game, state)
gameparser.add_module_vars(state)
gameparser.parse(game, state)

# verify also creates vars on the fly, so it needs the state
# gameparser.verify(game, state)
# gameparser.init_vars(game, state)

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

def make_choice(game, state, new_addr, command = "start"):
    state["bookmark"] = ()
    interpreter.make_bookmark(game, state, new_addr)
    state["choices"] = {}

    # Populate the state vars with args
    state["vars"]["_args"] = []
    for arg in command[1:]:
        state["vars"]["_args"].append(arg)

    os.system("clear")

    while interpreter.step(game, state):
        pass

    print_choices(state)

autostart = True

if autostart:
    make_choice(game, state, state["choices"]["start"]["address"])

while True:
    command = input("\n> ")
    command = command.split()
    print("") # Add a new line

    if command[0] == "exit":
        break
    elif command[0] == "goto":
        if len(command) < 2:
            print("Must give an address.")
        else:
            address_to_goto = None
            try:
                address_to_goto = addressing.parse_addr(game, ("story",), command[1])
            except Exception as e:
                print("Incorrect address") # TODO: Catch only relevant exceptions
            if not (address_to_goto is None):
                make_choice(game, state, address_to_goto[1:]) # TODO: Get rid of the 1:, it's here for backwards compatibility reasons
    elif command[0] == "help":
        print("Valid commands are 'exit', 'go', 'help', 'inspect', 'load', 'save', and 'settings'.")
    elif command[0] == "inspect":
        if len(command) < 2:
            print("Must give a variable to print the value of.")
        else:
            if command[1] in state["vars"]:
                print(state["vars"][command[1]])
            else:
                print("That's not a valid variable")
    elif command[0] == "load":
        if len(command) == 1:
            print("Must supply file to load.")
        else:
            try:
                with open("/Users/kylehess/Documents/programs/tunnelgame/saves/" + command[1], "rb") as file:
                    state = pickle.load(file)
                    gameparser.add_module_vars(state)
                    os.system("clear")
                    print_choices(state)
            except FileNotFoundError:
                print("Load file not found.")
    elif command[0] == "save":
        if len(command) == 1:
            if state["file_data"]["filename"] == "":
                print("Must supply default save name.")
            else:
                with open("/Users/kylehess/Documents/programs/tunnelgame/saves/" + state["file_data"]["filename"], "wb") as file:
                    gameparser.remove_module_vars(state)
                    pickle.dump(state, file)
                    gameparser.add_module_vars(state)
        else:
            with open("/Users/kylehess/Documents/programs/tunnelgame/saves/" + command[1], "wb") as file:
                gameparser.remove_module_vars(state)
                pickle.dump(state, file)
                gameparser.add_module_vars(state)
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
                state["vars"][modification["var"]] += modification["amount"] # TODO: Print modifications

            make_choice(game, state, choice["address"], command)
    else:
        print("Unrecognized command/choice. Type 'help' for commands or 'choices' for a list of choices.")