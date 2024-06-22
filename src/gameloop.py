# Standard imports
import copy
import pickle

# Local imports
import addressing
import interpreter
import gameparser
import utility

# Config imports
from config import game, state, local_dir, open_game
from view import view

def run(game_name):
    open_game(game_name)

    gameparser.construct_game(game)
    gameparser.add_flags(game)
    gameparser.add_vars_with_address(game, state, game, ())
    gameparser.add_module_vars(state)
    gameparser.parse(game, state)

    def make_choice(game, state, new_addr, command = "start"):
        state["bookmark"] = ()
        interpreter.make_bookmark(game, state, new_addr)
        state["choices"] = {}

        # Populate the state vars with args
        state["vars"]["_args"] = [0] * 10000
        for i, arg in enumerate(command[1:]):
            state["vars"]["_args"][i] = arg

        view.clear()

        while True:
            while interpreter.step(game, state):
                pass

            if "signal_run_statement" in state["msg"] and state["msg"]["signal_run_statement"]:
                state["msg"]["signal_run_statement"] = False
                # Store state, game, and view
                gameparser.remove_module_vars(state)

                temp_game = copy.deepcopy(game)
                temp_state = copy.deepcopy(state) # TODO: Store view!

                run("temp.yaml")

                game.clear()
                game.update(temp_game)
                state.clear()
                state.update(temp_state)

                gameparser.add_module_vars(state)

                view.clear()
            else:
                break

        state["last_address_list"].append(state["last_address"])

        view.print_choices()

    autostart = True

    if autostart:
        make_choice(game, state, state["choices"]["start"]["address"])

    while True:
        command = view.get_input()

        if command[0] == "choices":
            view.print_choices()
        elif command[0] == "exit":
            break
        elif command[0] == "goto":
            if len(command) < 2:
                view.print_feedback_message("goto_no_address_given")
            else:
                address_to_goto = None
                try:
                    address_to_goto = addressing.parse_addr(state["last_address_list"][-1], command[1]) # last_address_list should always be nonempty here since we just made a choice
                except Exception as e: # TODO: Catch only relevant exceptions
                    view.print_feedback_message("goto_invalid_address_given")
                if not (address_to_goto is None):
                    make_choice(game, state, address_to_goto) # TODO: Don't add to last_address_list for "back" command with gotos?
        elif command[0] == "help":
            view.print_feedback_message("help")
        elif command[0] == "inspect":
            if len(command) < 2:
                view.print_feedback_message("inspect_no_variable_given")
            else:
                try:
                    view.print_var_value(utility.collect_vars(state, state["last_address_list"][-1])[command[1]])
                except Exception as e:
                    view.print_feedback_message("inspect_invalid_variable_given")
        elif command[0] == "load":
            if len(command) == 1:
                view.print_feedback_message("load_no_file_given")
            else:
                try:
                    with open(local_dir + "saves/" + command[1], "rb") as file:
                        state.clear()
                        state.update(pickle.load(file))
                        gameparser.add_module_vars(state)
                        view.clear()
                        view.print_choices()
                except FileNotFoundError:
                    view.print_feedback_message("load_invalid_file_given")
        elif command[0] == "save":
            if len(command) == 1:
                if state["file_data"]["filename"] == "":
                    view.print_feedback_message("save_no_default_name_given")
                else:
                    with open(local_dir + "saves/" + state["file_data"]["filename"], "wb") as file:
                        gameparser.remove_module_vars(state)
                        pickle.dump(state, file)
                        gameparser.add_module_vars(state)
            else:
                with open(local_dir + "saves/" + command[1], "wb") as file:
                    gameparser.remove_module_vars(state)
                    pickle.dump(state, file)
                    gameparser.add_module_vars(state)
        elif command[0] == "settings":
            if len(command) < 2:
                view.print_feedback_message("settings_no_setting_given")
                view.print_settings()
            else:
                if command[1] == "show_flavor_text":
                    if len(command) < 3:
                        view.print_settings_flavor_text_get()
                    elif command[2] == "always" or command[2] == "once" or command[2] == "never":
                        state["settings"]["show_flavor_text"] = command[2]
                        view.print_settings_flavor_text_set(command[2])
                    else:
                        view.print_feedback_message("settings_flavor_invalid_val")
        elif command[0] in state["choices"]:
            choice = state["choices"][command[0]]
            if not ("missing" in choice):
                choice["missing"] = []
            if not ("modifications" in choice):
                choice["modifications"] = []

            if len(choice["missing"]) > 0:
                view.print_feedback_message("choice_missing_requirements")
            else:
                # Pay required costs
                for modification in choice["modifications"]:
                    if ("type_to_modify" in modification) and modification["type_to_modify"] == "bag":
                        modification["bag_ref"]["value"][modification["item"]] += modification["amount"]
                    else:
                        var_ref = utility.get_var(state["vars"], modification["var"], choice["choice_address"])
                        
                        var_ref["value"] += modification["amount"] # TODO: Print modifications

                make_choice(game, state, choice["address"], command)
        else:
            view.print_feedback_message("unrecognized_command")