# Standard imports
import copy
import pickle
import time

from engine import addressing, config, gameparser, interpreter, utility


def run(game_name, packaged=True, parent_game=None, parent_state=None, exec_block=None, loaded_game_state=None, uid=None):
    game = None
    state = None
    curr_view = config.view
    
    if loaded_game_state is None:
        game = config.game
        state = config.state

        story_path = None
        if packaged:
            story_path = config.local_dir / "stories" / game_name
        else:
            story_path = config.stories / game_name
        gameparser.open_game(story_path)


        def setup_game():
            gameparser.construct_game(game, story_path)
            gameparser.expand_macros(game)

            # We need to do this after construct game and expand macros or else includes and such will be attempted again
            if exec_block is not None:
                addressing.get_node(exec_block, parent_game)["_exec"] = copy.deepcopy(game)
                game.clear()
                game.update(parent_game)

            gameparser.add_flags(game)
            gameparser.add_vars_with_address(game, ())
            gameparser.add_module_vars()
            gameparser.parse_game()
        setup_game()
    else:
        #config.view = loaded_game_state["view"]
        # TODO: print_displayed_text
        # TODO: Do I need to set view?
        game = config.game
        state = config.state


    # Sync state vars so that upstream state can be modified
    if exec_block is not None:
        state["command_macros"] = parent_state["command_macros"]
        # Choices won't be presented during exec, but new ones can be added
        state["choices"] = parent_state["choices"]
        state["story_points"] = parent_state["story_points"]
        # Vars added below
        state["visits"] = parent_state["visits"]
        state["visits_choices"] = parent_state["visits_choices"]
        
        for var_key, var_tbl in parent_state["vars"].items():
        # Don't override global vars
            if var_key not in state["vars"]:
                state["vars"][var_key] = var_tbl
            # Case of var_key being an address
            elif isinstance(var_key, tuple):
                for var_name, var in var_tbl.items():
                    # Override address vars
                    state["vars"][var_key][var_name] = var


    def save_game(save_slot):
        gameparser.remove_module_vars()
        (config.saves / save_slot).with_suffix(".pkl").write_bytes(pickle.dumps(state))
        gameparser.add_module_vars()


    def load_game(load_slot, add_save_text=False):
        contents = pickle.loads((config.saves / load_slot).with_suffix(".pkl").read_bytes())
        gameparser.remove_module_vars()
        old_state = copy.deepcopy(state)
        # Update state
        state.clear()
        state.update(contents)
        gameparser.add_module_vars()
        # Backwards compatibility: simply don't crash when we come across an old save that doesn't have "game"
        if "game" not in state:
            state.clear()
            state.update(old_state)
            gameparser.add_module_vars()
            return
        # Update game with state's game
        game.clear()
        game.update(state["game"])
        # Update view
        curr_view.clear(True) # True doesn't reset saved text
        if not config.web_view:
            curr_view.print_displayed_text(add_save_text=add_save_text)
        else:
            curr_view.clear_var_view()
            config.view.print_shown_vars(config.state["view_text_info"]["shown_vars"], config.state["last_address_list"][-1])
            config.view.show_curr_image()
            config.view.print_displayed_prints()
            config.view.print_choices()

            gameparser.remove_module_vars()
            config.view.save_game_state(uid, game, state)
            gameparser.add_module_vars()


    def make_choice(new_addr, command=["start"], choice={}, is_action_override=False):
        inj_list = []
        if "injections" in choice:
            inj_list = choice["injections"]

        if state["bookmark"] == False:
            state["bookmark"] = ()
        state["bookmark"] = addressing.make_bookmark((), new_addr, inj_list) + state["bookmark"]

        # Only get rid of old choices if this was a proper choice, not an action
        is_action = ("action" in choice and choice["action"]) or is_action_override
        if not is_action:
            state["choices"] = {}

        if not is_action:
            curr_view.clear()

        num_steps = 0
        while True:
            while interpreter.step():
                num_steps += 1
                if num_steps >= config.max_num_steps:
                    try:
                        load_game("_autosave")
                    except FileNotFoundError:
                        curr_view.print_feedback_message("could_not_load_autosave")
                    return

            if "signal_run_statement" in state["msg"] and state["msg"]["signal_run_statement"]:
                state["msg"]["signal_run_statement"] = False
                # Store state, game, and view
                gameparser.remove_module_vars()

                temp_game = copy.deepcopy(game)
                temp_state = copy.deepcopy(state)  # TODO: Store view!

                try:
                    run("_temp.yaml", packaged=False)
                except:
                    curr_view.print_feedback_message("run_instr_failed")

                game.clear()
                game.update(temp_game)
                state.clear()
                state.update(temp_state)

                gameparser.add_module_vars()

                curr_view.clear()
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

            curr_view.print_choices()
        
        
        # Update shown vars based off where the address for our last "proper" choice
        # Also update the image
        curr_view.clear_var_view()
        # Get shown vars
        def add_shown_vars_and_image(curr_shown_vars, curr_image_filenames, addr):
            curr_node = addressing.get_node(addr)
            if "_shown" in curr_node:
                for shown_var in curr_node["_shown"]:
                    curr_shown_vars.append(shown_var)
            if "_image" in curr_node:
                curr_image_filenames.append(curr_node["_image"])
        shown_vars = []
        partial_addr = ()
        image_filenames = []
        add_shown_vars_and_image(shown_vars, image_filenames, partial_addr)
        for tag in state["last_address_list"][-1]:
            partial_addr = partial_addr + (tag,)
            add_shown_vars_and_image(shown_vars, image_filenames, partial_addr)
        state["view_text_info"]["shown_vars"] = shown_vars
        if len(shown_vars) > 0:
            curr_view.print_shown_vars(shown_vars, state["last_address_list"][-1])
        # Only show the last image, if it exists
        if len(image_filenames) == 0:
            state["curr_image"] = None
        else:
            state["curr_image"] = image_filenames[-1]
        # Only show images in web view
        if config.web_view:
            curr_view.show_curr_image()
        

        # Save to view if this is a web state
        if config.web_view:
            gameparser.remove_module_vars()
            config.view.save_game_state(uid, game, state)
            gameparser.add_module_vars()


    # If this is an exec command, only run the block and then return
    if exec_block is not None:
        make_choice(exec_block + ("_exec", "_content", 0))
        return


    if loaded_game_state is None:
        curr_view.print_choices()

        autostart = True

        if autostart:
            save_game("_autosave")
            
            make_choice(state["choices"]["start"]["address"])


    # Load game if this is web view and we were refreshed
    #if config.web_view:
    #    try:
    #        contents = pickle.loads((config.saves / "_web_info").with_suffix(".pkl").read_bytes())
    #
    #        if contents["running"]:
    #            load_game("_autosave_short_" + str(contents["choice_num"] % 3))
    #    except:
    #        pass


    # Main game loop
    while True:
        if config.web_view:
            config.view.socketio.sleep(0)

        if len(state["command_buffer"]) == 0:
            command = curr_view.get_input()
        else:
            command = state["command_buffer"].pop(0)

        if len(command) == 0:
            continue

        # Autocomplete
        if state["settings"]["autocomplete"] == "on":
            autocomplete_possibilities = set()
            for built_in_command in {"clear", "define", "exec", "exit", "flag", "goto", "help", "info", "input", "inspect", "load", "repeat", "revert", "save", "set", "settings", "undefine", "unflag"}:
                if command[0] == built_in_command:
                    autocomplete_possibilities = False
                    break
                elif built_in_command.startswith(command[0]):
                    autocomplete_possibilities.add(built_in_command)
            if autocomplete_possibilities is not False:
                for choice_command in state["choices"]:
                    if command[0] == choice_command:
                        autocomplete_possibilities = False
                        break
                    elif choice_command.startswith(command[0]):
                        autocomplete_possibilities.add(choice_command)
            if autocomplete_possibilities is False:
                pass
            elif len(autocomplete_possibilities) == 0:
                curr_view.print_feedback_message("autocomplete_no_possibilities")
                continue
            elif len(autocomplete_possibilities) == 1:
                command[0] = next(iter(autocomplete_possibilities))
            elif len(autocomplete_possibilities) > 1:
                curr_view.print_feedback_message("autocomplete_multiple_possibilities")
                continue

        # Check for macros first so that they can be reversed if needed
        if command[0] == "define":
            if len(command) < 2:
                curr_view.print_feedback_message("define_no_name_given")
                continue
            state["command_macros"][command[1]] = command[2:]
            curr_view.print_feedback_message("define_successful")
            continue
        elif command[0] == "undefine":
            if len(command) < 2:
                curr_view.print_feedback_message("undefine_no_macro_given")
                continue
            if not command[1] in state["command_macros"]:
                curr_view.print_feedback_message("undefine_invalid_macro_given")
                continue
            curr_view.print_feedback_message("undefine_successful")
            del state["command_macros"][command[1]]
            continue

        # Recursively expand any macros
        macro_depth = 0
        macro_expanded = True
        while macro_expanded:
            macro_expanded = False
            curr_command = []
            for subcommand in command:
                if subcommand in state["command_macros"]:
                    for macro_subcommand in state["command_macros"][subcommand]:
                        macro_expanded = True
                        curr_command.append(macro_subcommand)
                else:
                    curr_command.append(subcommand)
            command = curr_command
            macro_depth += 1
            if macro_depth >= config.max_macro_depth:
                curr_view.print_feedback_message("max_macro_depth_exceeded")
                break
        if macro_depth >= config.max_macro_depth:
            continue

        if command[0] == "clear":
            curr_view.clear(True)
            # Not implemented in web view yet
            if not config.web_view:
                curr_view.set_displayed_text("game")
                curr_view.print_displayed_text()
            else:
                curr_view.print_displayed_prints
            curr_view.print_choices()
        # TODO: Fix for web view
        elif command[0] == "exec":
            # Note: Favor specific statements like "set" over doing an exec, this is more for show than anything
            # Enters a "ghost game" with added exec statements, then returns, keeping some modifications to state

            if len(command) < 2:
                curr_view.print_feedback_message("exec_no_story_given")
                continue

            old_game = copy.deepcopy(game)
            gameparser.remove_module_vars()
            old_state = copy.deepcopy(state)

            try:
                exec_block = addressing.get_block_part(state["last_address"])
                run(command[1], parent_game=old_game, parent_state=old_state, exec_block=exec_block)
                game.clear()
                game.update(old_game)
                state.clear()
                state.update(old_state)
                gameparser.add_module_vars()
            except:
                # Need to restor game/state before printing feedback message
                game.clear()
                game.update(old_game)
                state.clear()
                state.update(old_state)
                gameparser.add_module_vars()
                curr_view.print_feedback_message("exec_error_running_game")
            
            curr_view.clear(True)
            curr_view.print_displayed_text()
        elif command[0] == "exit":
            break
        elif command[0] == "flag":
            if len(command) < 2:
                curr_view.print_feedback_message("flag_no_flag_given")
            else:
                if command[1] not in state["vars"]["flags"]:
                    curr_view.print_feedback_message("flag_invalid_flag")
                else:
                    state["vars"]["flags"][command[1]] = True
                    curr_view.print_feedback_message("flag_set_successfully")
        elif command[0] == "goto":
            if len(command) < 2:
                curr_view.print_feedback_message("goto_no_address_given")
            else:
                address_to_goto = None
                try:
                    # last_address_list should always be nonempty here since we just made a choice
                    address_to_goto = addressing.parse_addr(state["last_address_list"][-1], command[1])
                except Exception as e:  # TODO: Catch only relevant exceptions
                    curr_view.print_feedback_message("goto_invalid_address_given")
                if not (address_to_goto is None):
                    make_choice(address_to_goto) # TODO: Don't add to last_address_list for "back" command with gotos?
        elif command[0] == "help":
            curr_view.print_feedback_message("help")
        elif command[0] == "info":
            if len(command) < 2:
                curr_view.print_feedback_message("info_options")
                continue
            if command[1] == "actions":
                curr_view.print_choices(True)  # Print actions
            elif command[1] == "choices":
                curr_view.print_choices()
            elif command[1] == "completion":
                if len(state["story_points"]) == 0:
                    curr_view.print_feedback_message("completion_not_supported")
                    continue

                num_complete = 0
                total_num = 0
                for val in state["story_points"].values():
                    if val:
                        num_complete += 1
                    total_num += 1

                if hasattr(curr_view, "print_completion_percentage"):
                    curr_view.print_completion_percentage(num_complete / total_num)
                else:
                    curr_view.print_feedback_message("command_not_supported")
            elif command[1] == "macros":
                curr_view.print_macros()
            elif command[1] == "vars":
                curr_view.print_vars_defined()
            elif command[1] == "word_count":
                # TODO: Only error when view doesn't have given method
                try:
                    curr_view.print_num_words(utility.count_words(game))
                except Exception:
                    curr_view.print_feedback_message("command_not_supported")
            elif command[1] == "words_seen":
                # TODO: Only error when view doesn't have given method
                try:
                    curr_view.print_num_words(utility.count_words(game, True))
                except Exception:
                    curr_view.print_feedback_message("command_not_supported")
            else:
                curr_view.print_feedback_message("info_invalid_option")
        elif command[0] == "input":
            reconstructed_input = ""
            for subcommand in command[1:]:
                reconstructed_input += subcommand + " "
            for subcommand in reconstructed_input.split(",")[::-1]:
                state["command_buffer"].insert(0, subcommand.split())
        elif command[0] == "inspect":
            if len(command) < 2:
                curr_view.print_feedback_message("inspect_no_variable_given")
            else:
                try:
                    curr_view.print_var_value(utility.collect_vars(state, state["last_address_list"][-1])[command[1]])
                except KeyError: # TODO: Make this custom MissingReference Error
                    curr_view.print_feedback_message("inspect_invalid_variable_given")
        elif command[0] == "load":
            if len(command) == 1:
                curr_view.print_feedback_message("load_no_file_given")
                continue
            try:
                load_game(command[1], add_save_text=True)
            except FileNotFoundError:
                curr_view.print_feedback_message("load_invalid_file_given")
        elif command[0] == "repeat":
            if len(command) < 2:
                curr_view.print_feedback_message("repeat_no_num_times_given")
                continue
            elif len(command) < 3:
                curr_view.print_feedback_message("repeat_no_command_given")
                continue
            else:
                num_repeats = 0

                try:
                    num_repeats = int(command[1])
                except Exception:
                    curr_view.print_feedback_message("repeat_incorrect_num_times_format")
                else:
                    for i in range(num_repeats):
                        state["command_buffer"].insert(0, command[2:])
        # TODO: Fix for web view
        elif command[0] == "revert":
            if len(state["history"]) == 0:
                curr_view.print_feedback_message("revert_no_reversions")
                continue
            
            history = state["history"]
            state.clear()
            state.update(history.pop(0))
            gameparser.add_module_vars()
            state["history"] = history

            curr_view.clear(True)
            curr_view.print_displayed_text()
        elif command[0] == "save":
            try:
                save_slot = command[1]
            except IndexError:
                save_slot = state["file_data"]["filename"]
            if not save_slot:
                curr_view.print_feedback_message("save_no_default_name_given")
                continue
            curr_view.print_feedback_message("save_completed", True) # "True" makes sure it doesn't save the "saved game" message to state
            save_game(save_slot)
        elif command[0] == "set":
            if len(command) < 2:
                curr_view.print_feedback_message("set_no_variable_given")
            else:
                if len(command) < 3:
                    curr_view.print_feedback_message("set_no_value_given")
                else:
                    var_dict = utility.collect_vars_with_dicts(state, state["last_address_list"][-1])
                    var_dict_vals = utility.collect_vars(state, state["last_address_list"][-1])
                    try:
                        var_dict[command[1]]["value"] = eval(command[2], {}, var_dict_vals)
                        curr_view.print_feedback_message("set_command_successful")
                    except:
                        curr_view.print_feedback_message("set_invalid_variable_given")
        elif command[0] == "settings":
            if len(command) < 2:
                curr_view.print_feedback_message("settings_no_setting_given")
                curr_view.print_settings()
            else:
                if command[1] == "autocomplete":
                    if len(command) < 3:
                        curr_view.print_settings_autocomplete_get()
                    elif command[2] in {"on", "off"}:
                        state["settings"]["autocomplete"] = command[2]
                        curr_view.print_settings_autocomplete_set(command[2])
                    else:
                        curr_view.print_feedback_message("settings_autocomplete_invalid_val")
                elif command[1] == "show_flavor_text":
                    if len(command) < 3:
                        curr_view.print_settings_flavor_text_get()
                    elif command[2] == "always" or command[2] == "once" or command[2] == "never":
                        state["settings"]["show_flavor_text"] = command[2]
                        curr_view.print_settings_flavor_text_set(command[2])
                    else:
                        curr_view.print_feedback_message("settings_flavor_invalid_val")
                elif command[1] == "descriptiveness":
                    if len(command) < 3:
                        curr_view.print_settings_descriptiveness_get()
                    elif command[2] == "descriptive" or command[2] == "moderate" or command[2] == "minimal":
                        state["settings"]["descriptiveness"] = command[2]
                        curr_view.print_settings_descriptiveness_set(command[2])
                    else:
                        curr_view.print_feedback_message("settings_descriptiveness_invalid_val")
        elif command[0] == "unflag":
            if len(command) < 2:
                curr_view.print_feedback_message("unflag_no_flag_given")
            else:
                if command[1] not in state["vars"]["flags"]:
                    curr_view.print_feedback_message("unflag_invalid_flag")
                else:
                    state["vars"]["flags"][command[1]] = False
                    curr_view.print_feedback_message("unflag_set_successfully")
        elif command[0] in state["choices"]:
            choice = state["choices"][command[0]]
            if "enforce" not in choice:
                choice["enforce"] = "True"
            if "missing" not in choice:
                choice["missing"] = []
            if "modifications" not in choice:
                choice["modifications"] = []
            
            # Populate the state vars with any given args
            state["vars"]["_args"] = utility.ArgsList()
            for arg in command[1:]:
                state["vars"]["_args"].append(arg)
            
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
                curr_view.print_feedback_message("choice_missing_requirements")
            elif not utility.eval_conditional(choice["enforce"], choice["choice_address"]):
                # TODO: Should autosaves/etc. happen after alt effects
                if choice["alt_address"]:
                    make_choice(choice["alt_address"], command, choice, is_action_override=True)
                else:
                    curr_view.print_feedback_message("choice_enforce_false")
            else:
                # Autosave after every choice, for last 3 choices
                save_game("_autosave_short_" + str(state["choice_num"] % 3))
                # If this is the web view, save some web info
                if config.web_view:
                    # TODO: What is this for?..
                    (config.saves / "_web_info").with_suffix(".pkl").write_bytes(pickle.dumps({"running": True, "choice_num": state["choice_num"]}))
                state["choice_num"] += 1

                # Second, do a less frequent autosave every 20 choices
                state["last_autosave"] += 1
                if state["last_autosave"] >= config.choices_between_autosaves:
                    state["last_autosave"] = 0
                    save_game("_autosave_long")

                gameparser.remove_module_vars()
                state_to_save = copy.deepcopy(state)
                gameparser.add_module_vars()
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

                if choice["choice_address"] not in state["visits_choices"]:
                    state["visits_choices"][choice["choice_address"]] = 0
                state["visits_choices"][choice["choice_address"]] += 1

                make_choice(choice["address"], command, choice)
        else:
            curr_view.print_feedback_message("unrecognized_command")
