# Standard imports
import copy
import keyboard
from pathlib import Path
import pickle

from tunnelvision import addressing, interpreter, gameparser, utility
from tunnelvision.config import saves, max_num_steps, choices_between_autosaves

def run(game_name):
    gameparser.open_game(game_name)

    def setup_game():
        gameparser.construct_game(game)
        gameparser.expand_macros(game)
        gameparser.add_flags(game)
        gameparser.add_vars_with_address(game, state, game, ())
        gameparser.add_module_vars(state)
        gameparser.parse_game()
    setup_game()

    def save_game(save_slot):
        gameparser.remove_module_vars(state)
        (saves / save_slot).with_suffix(".pkl").write_bytes(pickle.dumps(state))
        gameparser.add_module_vars(state)

    def load_game(load_slot):
        contents = pickle.loads((saves / load_slot).with_suffix(".pkl").read_bytes())
        state.clear()
        state.update(contents)
        gameparser.add_module_vars(state)
        view.clear(True) # True doesn't reset saved text
        view.print_displayed_text()

    def make_choice(new_addr, command=["start"], choice={}):
        inj_list = []
        if "injections" in choice:
            inj_list = choice["injections"]

        state["bookmark"] = ()
        addressing.make_bookmark(new_addr, inj_list)

        # Only get rid of old choices if this was a proper choice, not an action
        is_action = "action" in choice and choice["action"]
        if not is_action:
            state["choices"] = {}

        # Populate the state vars with args
        state["vars"]["_args"] = [0] * 10000
        for i, arg in enumerate(command[1:]):
            state["vars"]["_args"][i] = arg

        if not is_action:
            view.clear()

        num_steps = 0
        while True:
            while interpreter.step(game, state):
                num_steps += 1
                if num_steps >= max_num_steps:
                    try:
                        load_game("autosave.yaml")
                    except FileNotFoundError:
                        view.print_feedback_message("could_not_load_autosave")
                    return

            if "signal_run_statement" in state["msg"] and state["msg"]["signal_run_statement"]:
                state["msg"]["signal_run_statement"] = False
                # Store state, game, and view
                gameparser.remove_module_vars(state)

                temp_game = copy.deepcopy(game)
                temp_state = copy.deepcopy(state)  # TODO: Store view!

                run("temp.yaml")

                game.clear()
                game.update(temp_game)
                state.clear()
                state.update(temp_state)

                gameparser.add_module_vars(state)

                view.clear()
            else:
                break
        
        # Update the choices now with proper costs and such
        def update_choice_reqs():
            # Choices now have cost_spec, req_spec, and shown_spec
            # TODO: Evaluate missing at choice printing (here)

            for choice_id, choice in state["choices"].items():
                # Evaluate costs/requirements/shown
                if not "missing" in choice:
                    choice["missing"] = []
                if not "modifications" in choice:
                    choice["modifications"] = []

                def parse_modification_spec(choice, spec_type):
                    for modification in choice[spec_type]:
                        var_dict_vals = utility.collect_vars(state, choice["choice_address"])
                        var_val = var_dict_vals[modification["var"]]
                        expr_val = eval(modification["amount"], {}, var_dict_vals)

                        if spec_type == "req_spec" or spec_type == "cost_spec":
                            if var_val < expr_val:
                                choice["missing"].append(utility.localize(modification["var"], choice["choice_address"]))
                        sign = 1
                        if spec_type == "cost_spec":
                            sign = -1
                        if spec_type == "cost_spec" or spec_type == "shown_spec":
                            choice["modifications"].append({"var": modification["var"], "amount": sign * expr_val})

                        #choice[spec_type]["final_var"] = var_dict[modification["var"]]
                        #choice[spec_type]["final_val"] = eval(modification["amount"], {}, var_dict_vals)

                for spec_type in ["cost_spec", "req_spec", "shown_spec", "per_cost_spec", "per_req_spec", "per_shown_spec"]:
                    if spec_type in choice and len(choice[spec_type]) > 0:
                        parse_modification_spec(choice, spec_type)
        
        update_choice_reqs()

        # Only change where we were in the story for "proper" choices
        if not is_action:
            state["last_address_list"].append(state["last_address"])

            view.print_choices()

    view.print_choices()

    autostart = True

    if autostart:
        save_game("autosave")
        
        make_choice(state["choices"]["start"]["address"])

    while True:
        if len(state["command_buffer"]) == 0:
            command = view.get_input()
        else:
            command = state["command_buffer"].pop(0)

        if len(command) == 0:
            continue

        if command[0] == "actions":
            view.print_choices(True)  # Print actions
        elif command[0] == "choices":
            view.print_choices()
        elif command[0] == "exec":
            continue # Not yet implemented
            if len(command) < 2:
                view.print_feedback_message("exec_no_story_given")
                continue
            # Save game and state, then make the new game a "subgame" of the old one
            old_game = copy.deepcopy(game)
            gameparser.remove_module_vars(state)
            old_state = copy.deepcopy(state)
            new_game = None
            try:
                gameparser.open_game(command[1])
                setup_game()
                new_game = copy.deepcopy(game)
            except Exception as e:
                print(e)
                view.print_feedback_message("exec_invalid_file_given")
            finally:
                game.clear()
                game.update(old_game)
                state.clear()
                state.update(old_state)
                gameparser.add_module_vars(state)
            
            # Check if we were able to load the new game
            if new_game is not None:
                game["_exec"] = new_game
                make_choice() # Do this as an action... TODO: Figure out how to make the signature right
        elif command[0] == "exit":
            break
        elif command[0] == "goto":
            if len(command) < 2:
                view.print_feedback_message("goto_no_address_given")
            else:
                address_to_goto = None
                try:
                    address_to_goto = addressing.parse_addr(
                        state["last_address_list"][-1], command[1]
                    )  # last_address_list should always be nonempty here since we just made a choice
                except Exception as e:  # TODO: Catch only relevant exceptions
                    view.print_feedback_message("goto_invalid_address_given")
                if not (address_to_goto is None):
                    make_choice(address_to_goto) # TODO: Don't add to last_address_list for "back" command with gotos?
        elif command[0] == "help":
            view.print_feedback_message("help")
        elif command[0] == "input":
            reconstructed_input = ""
            for subcommand in command[1:]:
                reconstructed_input += subcommand + " "
            for subcommand in reconstructed_input.split(",")[::-1]:
                state["command_buffer"].insert(0, subcommand.split())
        elif command[0] == "inspect":
            if len(command) < 2:
                view.print_feedback_message("inspect_no_variable_given")
            else:
                try:
                    view.print_var_value(utility.collect_vars(state, state["last_address_list"][-1])[command[1]])
                except KeyError: # TODO: Make this custom MissingReference Error
                    view.print_feedback_message("inspect_invalid_variable_given")
        elif command[0] == "load":
            if len(command) == 1:
                view.print_feedback_message("load_no_file_given")
                continue
            try:
                load_game(command[1])
            except FileNotFoundError:
                view.print_feedback_message("load_invalid_file_given")
        elif command[0] == "repeat":
            if len(command) < 2:
                view.print_feedback_message("repeat_no_num_times_given")
                continue
            elif len(command) < 3:
                view.print_feedback_message("repeat_no_command_given")
                continue
            else:
                num_repeats = 0

                try:
                    num_repeats = int(command[1])
                except Exception:
                    view.print_feedback_message("repeat_incorrect_num_times_format")
                else:
                    for i in range(num_repeats):
                        state["command_buffer"].insert(0, command[2:])
        elif command[0] == "revert":
            if len(state["history"]) == 0:
                view.print_feedback_message("revert_no_reversions")
                continue
            
            history = state["history"]
            state.clear()
            state.update(history.pop(0))
            gameparser.add_module_vars(state)
            state["history"] = history

            view.clear(True)
            view.print_displayed_text()
        elif command[0] == "save":
            try:
                save_slot = command[1]
            except IndexError:
                save_slot = state["file_data"]["filename"]
            if not save_slot:
                view.print_feedback_message("save_no_default_name_given")
                continue
            view.print_feedback_message("save_completed", True) # "True" makes sure it doesn't save the "saved game" message to state
            save_game(save_slot)
        elif command[0] == "set":
            if len(command) < 2:
                view.print_feedback_message("set_no_variable_given")
            else:
                if len(command) < 3:
                    view.print_feedback_message("set_no_value_given")
                else:
                    var_dict = utility.collect_vars_with_dicts(state, state["last_address_list"][-1])
                    var_dict_vals = utility.collect_vars(state, state["last_address_list"][-1])
                    try:
                        var_dict[command[1]]["value"] = eval(command[2], {}, var_dict_vals)
                        view.print_feedback_message("set_command_successful")
                    except:
                        view.print_feedback_message("set_invalid_variable_given")
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
            
            # Unfinished code, I should have committed before writing this since it started requiring large-scale changes that I wasn't ready to make
            #def find_modifications_and_missing(choice, spec_type):
            #    for spec in choice[spec_type]:
            #        # First calculate things missing from cost or require
            #        if not spec["final_var"] in choice["total_var_mods"]:
            #            choice["total_var_mods"]["final_var"] = {"var": }
            #        else:
            #           pass
            #choice["total_var_mods"] = {} # Dict with key as var_names, and including vars and modification values for cost, and requirements for require (evaluated first)
            #for spec_type in ["cost_spec", "req_spec", "shown_spec", "per_cost_spec", "per_req_spec", "per_shown_spec"]:

            if len(choice["missing"]) > 0:
                view.print_feedback_message("choice_missing_requirements")
            else:
                # First, save the state in an autosave after every 20 choices
                state["last_autosave"] += 1
                if state["last_autosave"] >= choices_between_autosaves:
                    state["last_autosave"] = 0
                    save_game("autosave")

                gameparser.remove_module_vars(state)
                state_to_save = copy.deepcopy(state)
                gameparser.add_module_vars(state)
                del state_to_save["history"]
                state["history"] = [state_to_save,] + state["history"]
                if len(state["history"]) > 10:
                    state["history"].pop()

                # Pay required costs
                for modification in choice["modifications"]:
                    if ("type_to_modify" in modification) and modification["type_to_modify"] == "bag":
                        modification["bag_ref"]["value"][modification["item"]] += modification["amount"]
                    else:
                        var_ref = utility.get_var(state["vars"], modification["var"], choice["choice_address"])

                        var_ref["value"] += modification["amount"]  # TODO: Print modifications

                if not choice["address"] in state["visits_choices"]:
                    state["visits_choices"][choice["choice_address"]] = 0
                state["visits_choices"][choice["choice_address"]] += 1

                make_choice(choice["address"], command, choice)
        else:
            view.print_feedback_message("unrecognized_command")
