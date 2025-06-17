# Standard imports
import copy
import pickle
import time

from engine.addressing import Addressing
from engine.utility import Utility
from engine.view import WebView
from engine.gameparser import GameParser
from engine.interpreter import Interpreter


class GameLoop:
    def __init__(self, gameobject, gamestate, config, addressing, utility, view, gameparser, interpreter):
        self.gameobject = gameobject
        self.gamestate = gamestate
        self.config = config
        self.addressing = addressing
        self.utility = utility
        self.view = view
        self.gameparser = gameparser
        self.interpreter = interpreter


    def run(self, game_name, packaged=True, parent_game=None, parent_state=None, exec_block=None, loaded_game_state=None, uid=None, do_lookaheads=False, starting_input=[], is_lookahead=False):
        if loaded_game_state is None:
            story_path = None
            if packaged:
                story_path = self.config.local_dir / "stories" / game_name
            else:
                story_path = self.config.story_dir / game_name
            self.gameparser.open_game(story_path)


            def setup_game():
                self.gameparser.construct_game(self.gameobject.game, story_path)
                self.gameparser.expand_macros(self.gameobject.game)

                # We need to do this after construct game and expand macros or else includes and such will be attempted again
                if exec_block is not None:
                    self.addressing.get_node(exec_block, parent_game)["_exec"] = copy.deepcopy(self.gameobject.game)
                    self.gameobject.game.clear()
                    self.gameobject.game.update(parent_game)

                self.gameparser.add_flags(self.gameobject.game)
                self.gameparser.add_vars_with_address(self.gameobject.game, ())
                self.gameparser.add_module_vars()
                self.gameparser.parse_game()
            setup_game()
        else:
            #config.view = loaded_game_state["view"]
            # TODO: print_displayed_text
            # TODO: Do I need to set view?
            # Load module vars, just in case they weren't loaded yet
            self.gameparser.add_module_vars()


        # Sync state vars so that upstream state can be modified
        if exec_block is not None:
            self.gamestate.state["command_macros"] = parent_state["command_macros"]
            # Choices won't be presented during exec, but new ones can be added
            self.gamestate.state["choices"] = parent_state["choices"]
            self.gamestate.state["story_points"] = parent_state["story_points"]
            # Vars added below
            self.gamestate.state["visits"] = parent_state["visits"]
            self.gamestate.state["visits_choices"] = parent_state["visits_choices"]
            
            for var_key, var_tbl in parent_state["vars"].items():
                # Don't override global vars
                if var_key not in self.gamestate.state["vars"]:
                    self.gamestate.state["vars"][var_key] = var_tbl
                # Case of var_key being an address
                elif isinstance(var_key, tuple):
                    for var_name, var in var_tbl.items():
                        # Override address vars
                        self.gamestate.state["vars"][var_key][var_name] = var


        def save_game(save_slot):
            self.gameparser.remove_module_vars()
            self.gamestate.state["game"] = copy.deepcopy(self.gameobject.game)
            (self.config.saves_dir / save_slot).with_suffix(".pkl").write_bytes(pickle.dumps(self.gamestate.state))
            self.gameparser.add_module_vars()
            del self.gamestate.state["game"]


        def load_game(load_slot, add_save_text=False):
            contents = pickle.loads((self.config.saves_dir / load_slot).with_suffix(".pkl").read_bytes())
            self.gameparser.remove_module_vars()
            old_state = copy.deepcopy(self.gamestate.state)
            # Update state
            self.gamestate.state.clear()
            self.gamestate.state.update(contents)
            self.gameparser.add_module_vars()
            # Backwards compatibility: simply don't crash when we come across an old save that doesn't have "game"
            if "game" not in self.gamestate.state:
                self.gamestate.state.clear()
                self.gamestate.state.update(old_state)
                self.gameparser.add_module_vars()
                return
            # Update game with state's game
            self.gameobject.game.clear()
            self.gameobject.game.update(self.gamestate.state["game"])
            # Remove game from state (only put there for saving)
            del self.gamestate.state["game"]
            # Update view
            self.view.clear(True) # True doesn't reset saved text
            if self.config.view_type != "web":
                self.view.print_displayed_text(add_save_text=add_save_text)
            else:
                self.view.clear_var_view()
                self.view.print_shown_vars(self.gamestate.state["view_text_info"]["shown_vars"], self.gamestate.state["last_address_list"][-1])
                self.view.show_curr_image()
                self.view.print_displayed_prints()
                self.view.print_choices()

                self.gameparser.remove_module_vars()
                self.view.save_game_state(self.gameobject.game, self.gamestate.state)
                self.gameparser.add_module_vars()
        

        def do_autosaves():
            # Autosave after every choice, for last 3 choices
            #save_game("_autosave_short_" + str(self.gamestate.state["choice_num"] % 3))
            # If this is the web view, save some web info
            if self.config.view_type == "web":
                # TODO: What is this for?..
                (self.config.saves_dir / "_web_info").with_suffix(".pkl").write_bytes(pickle.dumps({"running": True, "choice_num": self.gamestate.state["choice_num"]}))
            self.gamestate.state["choice_num"] += 1

            # Second, do a less frequent autosave every 20 choices
            self.gamestate.state["last_autosave"] += 1
            if self.gamestate.state["last_autosave"] >= self.config.choices_between_autosaves:
                self.gamestate.state["last_autosave"] = 0
                save_game("_autosave_long")
            
            self.gameparser.remove_module_vars()
            state_to_save = copy.deepcopy(self.gamestate.state)
            self.gameparser.add_module_vars()
            del state_to_save["history"]
            self.gamestate.state["history"] = [state_to_save,] + self.gamestate.state["history"]
            if len(self.gamestate.state["history"]) > 10:
                self.gamestate.state["history"].pop()


        def make_choice(new_addr, command=["start"], choice={}, is_action_override=False):
            inj_list = []
            if "injections" in choice:
                inj_list = choice["injections"]

            if self.gamestate.state["bookmark"] == False:
                self.gamestate.state["bookmark"] = ()
            self.gamestate.state["bookmark"] = self.addressing.make_bookmark((), new_addr, inj_list) + self.gamestate.state["bookmark"]

            # Only get rid of old choices if this was a proper choice, not an action
            is_action = ("action" in choice and choice["action"]) or is_action_override
            if not is_action:
                self.gamestate.state["choices"] = {}

            if not is_action:
                self.view.clear()

            num_steps = 0
            while True:
                while self.interpreter.step():
                    num_steps += 1
                    if num_steps >= self.config.max_num_steps:
                        try:
                            load_game("_autosave")
                        except FileNotFoundError:
                            self.view.print_feedback_message("could_not_load_autosave")
                        return

                if "signal_run_statement" in self.gamestate.state["msg"] and self.gamestate.state["msg"]["signal_run_statement"]:
                    self.gamestate.state["msg"]["signal_run_statement"] = False
                    # Store state, game, and view
                    self.gameparser.remove_module_vars()

                    temp_game = copy.deepcopy(self.gameobject.game)
                    temp_state = copy.deepcopy(self.gamestate.state)  # TODO: Store view!

                    try:
                        self.run("_temp.yaml", packaged=False)
                    except:
                        self.view.print_feedback_message("run_instr_failed")

                    self.gameobject.game.clear()
                    self.gameobject.game.update(temp_game)
                    self.gamestate.state.clear()
                    self.gamestate.state.update(temp_state)

                    self.gameparser.add_module_vars()

                    self.view.clear()
                else:
                    break
            if self.config.profiling:
                #print("\nInstruction time info:")
                #print(self.config.total_num_instrs)
                #print(self.config.total_instr_time)
                #print(self.config.total_instr_time / self.config.total_num_instrs)
                self.config.total_instr_time = 0
                self.config.total_num_instrs = 0
            

            # Update the choices now with proper costs and such
            def update_choice_reqs():
                # Choices now have cost_spec, req_spec, and shown_spec
                # TODO: Evaluate missing at choice printing (here)

                for choice_id, choice in self.gamestate.state["choices"].items():
                    # Evaluate costs/requirements/shown
                    if not "missing" in choice:
                        choice["missing"] = []
                    if not "modifications" in choice:
                        choice["modifications"] = []


                    def parse_modification_spec(choice, spec_type):
                        for modification in choice[spec_type]:
                            var_dict_vals = self.utility.collect_vars(choice["choice_address"])
                            var_val = var_dict_vals[modification["var"]]
                            expr_val = eval(modification["amount"], {}, var_dict_vals)

                            if spec_type == "req_spec" or spec_type == "cost_spec":
                                if var_val < expr_val:
                                    choice["missing"].append(self.utility.localize(modification["var"], choice["choice_address"]))
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
                self.gamestate.state["last_address_list"].append(self.gamestate.state["last_address"])

                self.view.print_choices()
            
            
            # Update shown vars based off where the address for our last "proper" choice
            # Also update the image
            self.view.clear_var_view()
            # Get shown vars
            def add_shown_vars_and_image(curr_shown_vars, curr_image_filenames, addr):
                curr_node = self.addressing.get_node(addr)
                if "_shown" in curr_node:
                    for shown_var in curr_node["_shown"]:
                        curr_shown_vars.append(shown_var)
                if "_image" in curr_node:
                    curr_image_filenames.append(curr_node["_image"])
            shown_vars = []
            partial_addr = ()
            image_filenames = []
            add_shown_vars_and_image(shown_vars, image_filenames, partial_addr)
            for tag in self.gamestate.state["last_address_list"][-1]:
                partial_addr = partial_addr + (tag,)
                add_shown_vars_and_image(shown_vars, image_filenames, partial_addr)
            self.gamestate.state["view_text_info"]["shown_vars"] = shown_vars
            if len(shown_vars) > 0:
                self.view.print_shown_vars(shown_vars, self.gamestate.state["last_address_list"][-1])
            # Only show the last image, if it exists
            if len(image_filenames) == 0:
                self.gamestate.state["curr_image"] = None
            else:
                self.gamestate.state["curr_image"] = image_filenames[-1]
            # Only show images in web view
            if self.config.view_type == "web":
                self.view.show_curr_image()
            

            # Save to view if this is a web state
            if self.config.view_type == "web":
                self.gameparser.remove_module_vars()
                self.view.save_game_state(self.gameobject.game, self.gamestate.state)
                self.gameparser.add_module_vars()


        # If this is an exec command, only run the block and then return
        if exec_block is not None:
            make_choice(exec_block + ("_exec", "_content", 0))
            return


        if loaded_game_state is None:
            self.view.print_choices()

            autostart = True

            if autostart:
                save_game("_autosave")
                
                make_choice(self.gamestate.state["choices"]["start"]["address"])
        

        # Append passed input to gamestate input
        self.gamestate.state["command_buffer"].extend(starting_input)


        # If we have lookaheads, we need to populate the history now
        if do_lookaheads:
            do_autosaves()

        
        # TODO: Should this go in state?
        # Seems like not
        lookahead_gamesession_info = None

        def calc_lookahead_gamesession_info():
            start_time = None
            time_doing_copies = 0
            if self.config.profiling:
                start_time = time.time()

            new_lookahead_gamesession_info = {}
            for lookahead_choice_id in self.gamestate.state["choices"]:
                self.gameparser.remove_module_vars()

                # TODO: Make sure doing a reference to the original gameobject doesn't break anything
                new_game = self.gameobject
                # To make up for legacy code/saves, delete "game" from gamestate if it's still there
                if "game" in self.gamestate.state:
                    del self.gamestate.state["game"]
                # Backwards compatibility: Just don't deepcopy visits, which will make it inaccurate but at least not crash
                old_visits = self.gamestate.state["visits"]
                old_story_data = self.gamestate.state["story_data"]
                del self.gamestate.state["visits"]
                del self.gamestate.state["story_data"]

                start_time_doing_copy = time.time()
                new_state = copy.deepcopy(self.gamestate)
                time_doing_copies += time.time() - start_time_doing_copy

                new_state.state["visits"] = old_visits
                new_state.state["story_data"] = old_story_data
                self.gamestate.state["visits"] = old_visits
                self.gamestate.state["story_data"] = old_story_data
                # TODO: Also make sure having the config not change doesn't break anything
                new_config = self.config

                # We need to initialize these to make sure they're given the proper gameobjects and gamestates
                new_addressing = Addressing(new_game, new_state)
                new_utility = Utility(new_state, new_addressing)
                # We can't deepcopy view (no pickling the socketio stuff), but it should be stateless enough 
                new_view = WebView(new_state, new_config, new_addressing, new_utility, self.view.app, self.view.socketio, uid, is_lookahead=True)
                # Since view is inside gameparser and interpreter, we need to just create new ones of those
                new_gameparser = GameParser(new_game, new_state, new_config, new_addressing, new_utility)
                new_interpreter = Interpreter(new_game, new_state, new_config, new_addressing, new_utility, new_view, new_gameparser)
                new_gameloop = GameLoop(new_game, new_state, new_config, new_addressing, new_utility, new_view, new_gameparser, new_interpreter)

                new_lookahead_gamesession_info[lookahead_choice_id] = new_gameloop.run(game_name=game_name, packaged=packaged, loaded_game_state={"game": new_game, "state": new_state}, uid=uid, do_lookaheads=False, starting_input=[lookahead_choice_id.split(), "exit".split()], is_lookahead=True)
                
                self.gameparser.add_module_vars()
                new_view.is_lookahead = False

            if self.config.profiling:
                print("\nLookahead calculation time: " + str(time.time() - start_time))
                print("Time that was spent on copies: " + str(time_doing_copies))
            
            return new_lookahead_gamesession_info
        if do_lookaheads:
            lookahead_gamesession_info = calc_lookahead_gamesession_info()


        # Load game if this is web view and we were refreshed
        #if config.web_view:
        #    try:
        #        contents = pickle.loads((config.saves_dir / "_web_info").with_suffix(".pkl").read_bytes())
        #
        #        if contents["running"]:
        #            load_game("_autosave_short_" + str(contents["choice_num"] % 3))
        #    except:
        #        pass


        def do_profiling(start_time):
            if self.config.profiling:
                print("\nCommand time info:")
                print(time.time() - start_time)


        start_time = None


        # Main game loop
        while True:
            # Do profiling from last start time
            if start_time is not None:
                do_profiling(start_time)
                start_time = None


            # Check if the game's been closed
            if "closed" in self.gamestate.state and self.gamestate.state["closed"] is True:
                self.gameparser.remove_module_vars()
                return {"game": self.gameobject.game, "state": self.gamestate.state, "view": self.view}


            if self.config.view_type == "web":
                self.view.socketio.sleep(0)


            if len(self.gamestate.state["command_buffer"]) == 0:
                command = self.view.get_input()
            else:
                command = self.gamestate.state["command_buffer"].pop(0)


            if len(command) == 0:
                continue


            start_time = time.time()


            # Check for macros first so that they can be reversed if needed
            if command[0] == "define":
                if len(command) < 2:
                    self.view.print_feedback_message("define_no_name_given")
                    continue
                self.gamestate.state["command_macros"][command[1]] = command[2:]
                self.view.print_feedback_message("define_successful")
                continue
            elif command[0] == "undefine":
                if len(command) < 2:
                    self.view.print_feedback_message("undefine_no_macro_given")
                    continue
                if not command[1] in self.gamestate.state["command_macros"]:
                    self.view.print_feedback_message("undefine_invalid_macro_given")
                    continue
                self.view.print_feedback_message("undefine_successful")
                del self.gamestate.state["command_macros"][command[1]]
                continue


            # Recursively expand any macros
            macro_depth = 0
            macro_expanded = True
            while macro_expanded:
                macro_expanded = False
                curr_command = []
                for subcommand in command:
                    if subcommand in self.gamestate.state["command_macros"]:
                        for macro_subcommand in self.gamestate.state["command_macros"][subcommand]:
                            macro_expanded = True
                            curr_command.append(macro_subcommand)
                    else:
                        curr_command.append(subcommand)
                command = curr_command
                macro_depth += 1
                if macro_depth >= self.config.max_macro_depth:
                    self.view.print_feedback_message("max_macro_depth_exceeded")
                    # TODO: Should it do a continue in this case too without checking the command
                    break
            if macro_depth >= self.config.max_macro_depth:
                continue


            # "Autocomplete"
            # This must be done after macro expansion, which means define/undefine isn't sensed, and neither are macros, but that's fine
            if self.gamestate.state["settings"]["autocomplete"] == "on":
                autocomplete_possibilities = set()
                for built_in_command in {"clear", "define", "exec", "exit", "flag", "goto", "help", "info", "input", "inspect", "load", "repeat", "restart", "revert", "save", "set", "settings", "undefine", "unflag"}:
                    if command[0] == built_in_command:
                        autocomplete_possibilities = False
                        break
                    elif built_in_command.startswith(command[0]):
                        autocomplete_possibilities.add(built_in_command)
                if autocomplete_possibilities is not False:
                    for choice_command in self.gamestate.state["choices"]:
                        if command[0] == choice_command:
                            autocomplete_possibilities = False
                            break
                        elif choice_command.startswith(command[0]):
                            autocomplete_possibilities.add(choice_command)
                if autocomplete_possibilities is False:
                    pass
                elif len(autocomplete_possibilities) == 0:
                    self.view.print_feedback_message("autocomplete_no_possibilities")
                    continue
                elif len(autocomplete_possibilities) == 1:
                    command[0] = next(iter(autocomplete_possibilities))
                elif len(autocomplete_possibilities) > 1:
                    self.view.print_feedback_message("autocomplete_multiple_possibilities")
                    continue


            if command[0] == "clear":
                self.view.clear(True)
                # Not implemented in web view yet
                if self.config.view_type != "web":
                    self.view.set_displayed_text("game")
                    self.view.print_displayed_text()
                else:
                    self.view.print_displayed_prints()
                self.view.print_choices()
            # TODO: Fix for web view
            elif command[0] == "exec":
                # Note: Favor specific statements like "set" over doing an exec, this is more for show than anything
                # Enters a "ghost game" with added exec statements, then returns, keeping some modifications to state

                if len(command) < 2:
                    self.view.print_feedback_message("exec_no_story_given")
                    continue

                old_game = copy.deepcopy(self.gameobject.game)
                self.gameparser.remove_module_vars()
                old_state = copy.deepcopy(self.gamestate.state)

                try:
                    exec_block = self.addressing.get_block_part(self.gamestate.state["last_address"])
                    self.run(command[1], parent_game=old_game, parent_state=old_state, exec_block=exec_block)
                    self.gameobject.game.clear()
                    self.gameobject.game.update(old_game)
                    self.gamestate.state.clear()
                    self.gamestate.state.update(old_state)
                    self.gameparser.add_module_vars()
                except:
                    # Need to restore game/state before printing feedback message
                    self.gameobject.game.clear()
                    self.gameobject.game.update(old_game)
                    self.gamestate.state.clear()
                    self.gamestate.state.update(old_state)
                    self.gameparser.add_module_vars()
                    self.view.print_feedback_message("exec_error_running_game")
                
                self.view.clear(True)
                self.view.print_displayed_text()
            elif command[0] == "exit":
                # Return in case this was a lookahead
                self.gameparser.remove_module_vars()
                return {"game": self.gameobject.game, "state": self.gamestate.state, "view": self.view}
            elif command[0] == "flag":
                if len(command) < 2:
                    self.view.print_feedback_message("flag_no_flag_given")
                else:
                    if command[1] not in self.gamestate.state["vars"]["flags"]:
                        self.view.print_feedback_message("flag_invalid_flag")
                    else:
                        self.gamestate.state["vars"]["flags"][command[1]] = True
                        self.view.print_feedback_message("flag_set_successfully")
            elif command[0] == "goto":
                if len(command) < 2:
                    self.view.print_feedback_message("goto_no_address_given")
                else:
                    address_to_goto = None
                    try:
                        # last_address_list should always be nonempty here since we just made a choice
                        address_to_goto = self.addressing.parse_addr(self.gamestate.state["last_address_list"][-1], command[1])
                    except Exception as e:  # TODO: Catch only relevant exceptions
                        self.view.print_feedback_message("goto_invalid_address_given")
                    if not (address_to_goto is None):
                        make_choice(address_to_goto) # TODO: Don't add to last_address_list for "back" command with gotos?
            elif command[0] == "help":
                self.view.print_feedback_message("help")
            elif command[0] == "info":
                if len(command) < 2:
                    self.view.print_feedback_message("info_options")
                    continue
                if command[1] == "actions":
                    self.view.print_choices(True)  # Print actions
                elif command[1] == "choices":
                    self.view.print_choices()
                elif command[1] == "completion":
                    if len(self.gamestate.state["story_points"]) == 0:
                        self.view.print_feedback_message("completion_not_supported")
                        continue

                    num_complete = 0
                    total_num = 0
                    for val in self.gamestate.state["story_points"].values():
                        if val:
                            num_complete += 1
                        total_num += 1

                    if hasattr(self.view, "print_completion_percentage"):
                        self.view.print_completion_percentage(num_complete / total_num)
                    else:
                        self.view.print_feedback_message("command_not_supported")
                elif command[1] == "macros":
                    self.view.print_macros()
                elif command[1] == "vars":
                    self.view.print_vars_defined()
                elif command[1] == "word_count":
                    # TODO: Only error when view doesn't have given method
                    try:
                        self.view.print_num_words(self.utility.count_words(self.gameobject.game))
                    except Exception:
                        self.view.print_feedback_message("command_not_supported")
                elif command[1] == "words_seen":
                    # TODO: Only error when view doesn't have given method
                    try:
                        self.view.print_num_words(self.utility.count_words(self.gameobject.game, True))
                    except Exception:
                        self.view.print_feedback_message("command_not_supported")
                else:
                    self.view.print_feedback_message("info_invalid_option")
            elif command[0] == "input":
                reconstructed_input = ""
                for subcommand in command[1:]:
                    reconstructed_input += subcommand + " "
                for subcommand in reconstructed_input.split(",")[::-1]:
                    self.gamestate.state["command_buffer"].insert(0, subcommand.split())
            elif command[0] == "inspect":
                if len(command) < 2:
                    self.view.print_feedback_message("inspect_no_variable_given")
                else:
                    try:
                        self.view.print_var_value(self.utility.collect_vars(self.gamestate.state["last_address_list"][-1])[command[1]])
                    except KeyError: # TODO: Make this custom MissingReference Error
                        self.view.print_feedback_message("inspect_invalid_variable_given")
            elif command[0] == "load":
                if len(command) == 1:
                    self.view.print_feedback_message("load_no_file_given")
                    continue
                try:
                    load_game(command[1], add_save_text=True)
                except FileNotFoundError:
                    self.view.print_feedback_message("load_invalid_file_given")
            elif command[0] == "repeat":
                if len(command) < 2:
                    self.view.print_feedback_message("repeat_no_num_times_given")
                    continue
                elif len(command) < 3:
                    self.view.print_feedback_message("repeat_no_command_given")
                    continue
                else:
                    num_repeats = 0

                    try:
                        num_repeats = int(command[1])
                    except Exception:
                        self.view.print_feedback_message("repeat_incorrect_num_times_format")
                    else:
                        for i in range(num_repeats):
                            self.gamestate.state["command_buffer"].insert(0, command[2:])
            # TODO: Fix for console view
            elif command[0] == "restart":
                if self.config.view_type != "web":
                    self.view.print_feedback_message("command_not_supported")
                    continue
                
                self.view.socketio.emit("restart_html", {})
            elif command[0] == "revert":
                if (len(self.gamestate.state["history"]) == 0) or (len(self.gamestate.state["history"]) == 1 and do_lookaheads):
                    self.view.print_feedback_message("revert_no_reversions")
                    continue
                
                history = self.gamestate.state["history"]
                # Need to do an extra pop with lookaheads since the history is stored *after* the choice is made
                if do_lookaheads:
                    history.pop(0)
                    self.gamestate.state.clear()
                    self.gamestate.state.update(copy.deepcopy(history[0]))
                else:
                    self.gamestate.state.clear()
                    self.gamestate.state.update(history.pop(0))
                self.gameparser.add_module_vars()
                self.gamestate.state["history"] = history

                self.view.clear(True)
                if self.config.view_type != "web":
                    self.view.print_displayed_text()
                else:
                    self.view.clear_var_view()
                    self.view.print_shown_vars(self.gamestate.state["view_text_info"]["shown_vars"], self.gamestate.state["last_address_list"][-1])
                    self.view.show_curr_image()
                    self.view.print_displayed_prints()
                    self.view.print_choices()

                    self.gameparser.remove_module_vars()
                    self.view.save_game_state(self.gameobject.game, self.gamestate.state)
                    self.gameparser.add_module_vars()
                if do_lookaheads:
                    lookahead_gamesession_info = calc_lookahead_gamesession_info()
            elif command[0] == "save":
                try:
                    save_slot = command[1]
                except IndexError:
                    save_slot = self.gamestate.state["file_data"]["filename"]
                if not save_slot:
                    self.view.print_feedback_message("save_no_default_name_given")
                    continue
                self.view.print_feedback_message("save_completed", True) # "True" makes sure it doesn't save the "saved game" message to state
                save_game(save_slot)
            elif command[0] == "set":
                if len(command) < 2:
                    self.view.print_feedback_message("set_no_variable_given")
                else:
                    if len(command) < 3:
                        self.view.print_feedback_message("set_no_value_given")
                    else:
                        var_dict = self.utility.collect_vars_with_dicts(self.gamestate.state["last_address_list"][-1])
                        var_dict_vals = self.utility.collect_vars(self.gamestate.state["last_address_list"][-1])
                        try:
                            var_dict[command[1]]["value"] = eval(command[2], {}, var_dict_vals)
                            self.view.print_feedback_message("set_command_successful")
                        except:
                            self.view.print_feedback_message("set_invalid_variable_given")
            elif command[0] == "settings":
                if len(command) < 2:
                    self.view.print_feedback_message("settings_no_setting_given")
                    self.view.print_settings()
                else:
                    if command[1] == "autocomplete":
                        if len(command) < 3:
                            self.view.print_settings_autocomplete_get()
                        elif command[2] in {"on", "off"}:
                            self.gamestate.state["settings"]["autocomplete"] = command[2]
                            self.view.print_settings_autocomplete_set(command[2])
                        else:
                            self.view.print_feedback_message("settings_autocomplete_invalid_val")
                    elif command[1] == "show_flavor_text":
                        if len(command) < 3:
                            self.view.print_settings_flavor_text_get()
                        elif command[2] == "always" or command[2] == "once" or command[2] == "never":
                            self.gamestate.state["settings"]["show_flavor_text"] = command[2]
                            self.view.print_settings_flavor_text_set(command[2])
                        else:
                            self.view.print_feedback_message("settings_flavor_invalid_val")
                    elif command[1] == "descriptiveness":
                        if len(command) < 3:
                            self.view.print_settings_descriptiveness_get()
                        elif command[2] == "descriptive" or command[2] == "moderate" or command[2] == "minimal":
                            self.gamestate.state["settings"]["descriptiveness"] = command[2]
                            self.view.print_settings_descriptiveness_set(command[2])
                        else:
                            self.view.print_feedback_message("settings_descriptiveness_invalid_val")
            elif command[0] == "unflag":
                if len(command) < 2:
                    self.view.print_feedback_message("unflag_no_flag_given")
                else:
                    if command[1] not in self.gamestate.state["vars"]["flags"]:
                        self.view.print_feedback_message("unflag_invalid_flag")
                    else:
                        self.gamestate.state["vars"]["flags"][command[1]] = False
                        self.view.print_feedback_message("unflag_set_successfully")
            elif command[0] in self.gamestate.state["choices"]:
                choice = self.gamestate.state["choices"][command[0]]
                if "enforce" not in choice:
                    choice["enforce"] = "True"
                if "missing" not in choice:
                    choice["missing"] = []
                if "modifications" not in choice:
                    choice["modifications"] = []
                
                # Populate the state vars with any given args
                self.gamestate.state["vars"]["_args"] = self.utility.get_args_list()
                for arg in command[1:]:
                    self.gamestate.state["vars"]["_args"].append(arg)
                
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
                    self.view.print_feedback_message("choice_missing_requirements")
                elif not self.utility.eval_conditional(choice["enforce"], choice["choice_address"]):
                    # TODO: Should autosaves/etc. happen after alt effects
                    # TODO: Also need to make this work with lookahead
                    if choice["alt_address"]:
                        make_choice(choice["alt_address"], command, choice, is_action_override=True)
                    else:
                        self.view.print_feedback_message("choice_enforce_false")
                else:
                    if do_lookaheads:
                        new_gamesession_info = lookahead_gamesession_info[command[0]]

                        # Game doesn't change anymore between lookaheads
                        #self.gameobject.game.clear()
                        #self.gameobject.game.update(new_gamesession_info["game"])
                        self.gamestate.state.clear()
                        self.gamestate.state.update(new_gamesession_info["state"])
                        self.gameparser.add_module_vars()
                        self.view.do_emits(new_gamesession_info["view"].lookahead_emits)

                        self.view.socketio.sleep(0)

                        do_autosaves()

                        # Need to manually save game state since the lookaheads don't
                        self.gameparser.remove_module_vars()
                        self.view.save_game_state(self.gameobject.game, self.gamestate.state)
                        self.gameparser.add_module_vars()

                        # For each new choice in new gamestate, try making that choice
                        # How to communicate results/new gamesessions?

                        lookahead_gamesession_info = calc_lookahead_gamesession_info()
                    else:
                        if not is_lookahead:
                            do_autosaves()

                        # Pay required costs
                        for modification in choice["modifications"]:
                            if ("type_to_modify" in modification) and modification["type_to_modify"] == "bag":
                                modification["bag_ref"]["value"][modification["item"]] += modification["amount"]
                            else:
                                var_ref = self.utility.get_var(self.gamestate.state["vars"], modification["var"], choice["choice_address"])

                                var_ref["value"] += modification["amount"]  # TODO: Print modifications

                        if choice["choice_address"] not in self.gamestate.state["visits_choices"]:
                            self.gamestate.state["visits_choices"][choice["choice_address"]] = 0
                        self.gamestate.state["visits_choices"][choice["choice_address"]] += 1

                        make_choice(choice["address"], command, choice)
            else:
                self.view.print_feedback_message("unrecognized_command")