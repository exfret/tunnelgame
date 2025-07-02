# Standard imports
import copy
import pickle
import random


from engine.gamestate import GameState, Diff
from engine.config import Config
from engine.addressing import Addressing
from engine.utility import Utility
from engine.view import View, ViewForTesting, WebView
from engine.gameparser import GameParser
from engine.interpreter import Interpreter


class GameLoop:
    gamestate : GameState
    config : Config
    addressing : Addressing
    utility : Utility
    view : View
    gameparser : GameParser
    interpreter : Interpreter


    def __init__(self, gamestate, config, addressing, utility, view, gameparser, interpreter):
        self.gamestate = gamestate
        self.config = config
        self.addressing = addressing
        self.utility = utility
        self.view = view
        self.gameparser = gameparser
        self.interpreter = interpreter

        # Populated later, mostly defined here for testing purposes (so the mock GameLoops still have this property)
        self.uid = None
        self.do_lookaheads = None
        self.is_lookahead = None
        self.lookahead_data = None


    def setup_game(self, story_path=None):
        self.gameparser.construct_game(self.gamestate.game, story_path)
        self.gameparser.add_flags(self.gamestate.game)
        self.gameparser.add_vars_with_address(self.gamestate.game, ())
        self.gameparser.add_module_vars()
        self.gameparser.parse_game()

    
    def initialize_new_game(self, game_name, packaged):
        story_path = None
        if packaged:
            story_path = self.config.local_dir / "stories" / game_name
        else:
            story_path = self.config.story_dir / game_name
        self.gameparser.open_game(story_path)

        self.setup_game(story_path)
    

    def initialize_game(self, loaded_game_state, game_name=None, packaged=False):
        if loaded_game_state is None:
            self.initialize_new_game(game_name, packaged)
        else:
            #config.view = loaded_game_state["view"]
            # TODO: print_displayed_text
            # TODO: Do I need to set view?
            # Load module vars, just in case they weren't loaded yet
            self.gameparser.add_module_vars()
    

    def save_game(self, save_slot):
        self.gameparser.remove_module_vars()
        (self.config.saves_dir / save_slot).with_suffix(".pkl").write_bytes(pickle.dumps(self.gamestate))
        self.gameparser.add_module_vars()


    def load_game(self, load_slot, add_save_text=False):
        contents = pickle.loads((self.config.saves_dir / load_slot).with_suffix(".pkl").read_bytes())
        self.gameparser.remove_module_vars()
        self.gamestate.update(contents)
        self.gameparser.add_module_vars()

        # Update view
        self.view.clear(True) # True doesn't reset saved text
        if self.config.view_type == "cli":
            self.view.print_displayed_text(add_save_text=add_save_text)
        elif self.config.view_type == "web":
            self.view.clear_var_view()
            self.view.print_shown_vars(self.gamestate.light.view.shown_vars, self.gamestate.light.last_address_list[-1])
            self.view.show_curr_image()
            self.view.print_emit_intercepts()
            self.view.print_choices()

            self.gameparser.remove_module_vars()
            self.view.save_game_state()
            self.gameparser.add_module_vars()
    

    def do_autosaves(self):
        # Autosave after every choice, for last 3 choices
        #save_game("_autosave_short_" + str(self.gamestate.light.total_choices_made % 3))
        # If this is the web view, save some web info
        if self.config.view_type == "web":
            # TODO: What is this for?..
            (self.config.saves_dir / "_web_info").with_suffix(".pkl").write_bytes(pickle.dumps({"running": True, "choice_num": self.gamestate.light.total_choices_made}))
        self.gamestate.light.total_choices_made += 1

        # Second, do a less frequent autosave every 20 choices
        self.gamestate.light.last_autosave += 1
        if self.gamestate.light.last_autosave >= self.config.choices_between_autosaves:
            self.gamestate.light.last_autosave = 0
            self.save_game("_autosave_long")
    

    def run_interpreter(self):
        num_steps = 0
        while self.interpreter.step():
            num_steps += 1
            if num_steps >= self.config.max_num_steps:
                try:
                    self.load_game("_autosave")
                except FileNotFoundError:
                    self.view.print_feedback_message("could_not_load_autosave")
                return
    

    def parse_modification_spec(self, choice, spec_type):
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
    

    def update_choice_requirements(self):
        for choice in self.gamestate.light.choices.values():
            # Evaluate costs/requirements/shown
            if not "missing" in choice:
                choice["missing"] = []
            if not "modifications" in choice:
                choice["modifications"] = []

            for spec_type in ["cost_spec", "req_spec", "shown_spec", "per_cost_spec", "per_req_spec", "per_shown_spec"]:
                if spec_type in choice and len(choice[spec_type]) > 0:
                    self.parse_modification_spec(choice, spec_type)


    def update_vars_and_image(self):
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
        for tag in self.gamestate.light.last_address_list[-1]:
            partial_addr = partial_addr + (tag,)
            add_shown_vars_and_image(shown_vars, image_filenames, partial_addr)
        self.gamestate.light.view.shown_vars = shown_vars
        if len(shown_vars) > 0:
            self.view.print_shown_vars(shown_vars, self.gamestate.light.last_address_list[-1])
        # Only show the last image, if it exists
        if len(image_filenames) == 0:
            self.gamestate.light.curr_image = None
        else:
            self.gamestate.light.curr_image = image_filenames[-1]
        # Only show images in web view
        if self.config.view_type == "web":
            self.view.show_curr_image()


    def make_choice(self, new_addr, choice={}, is_action_override=False):
        inj_list = []
        if "injections" in choice:
            inj_list = choice["injections"]

        if self.gamestate.light.bookmark == False:
            self.gamestate.light.bookmark = ()
        self.gamestate.light.bookmark = self.addressing.make_bookmark((), new_addr, inj_list) + self.gamestate.light.bookmark

        # Only get rid of old choices if this was a proper choice, not an action
        is_action = ("action" in choice and choice["action"]) or is_action_override
        if not is_action:
            self.gamestate.light.choices = {}

        if not is_action:
            self.view.clear()

        self.run_interpreter()        

        # Update the choices now with proper costs and such
        self.update_choice_requirements()

        # Only change where we were in the story for "proper" choices
        if not is_action:
            self.gamestate.light.last_address_list.append(self.gamestate.light.last_address)

            self.view.print_choices()
        
        # Update shown vars based off where the address for our last "proper" choice
        # Also update the image
        self.update_vars_and_image()
        
        # Save to view if this is a web state
        if self.config.view_type == "web":
            self.gameparser.remove_module_vars()
            self.view.save_game_state()
            self.gameparser.add_module_vars()
    

    def calc_lookaheads(self):
        new_lookahead_data = {}
        for lookahead_choice_id in self.gamestate.light.choices:
            new_state = GameState()
            new_state.game = self.gamestate.game
            new_state.game_data = self.gamestate.game_data
            new_state.light = copy.deepcopy(self.gamestate.light)
            new_state.bulk = self.gamestate.bulk
            new_state.diffs = self.gamestate.diffs
            new_state.create_new_diff_list()

            # TODO: Also make sure having the config not change doesn't break anything
            new_config = self.config
            # We need to initialize these to make sure they're given the proper gameobjects and gamestates
            new_addressing = Addressing(new_state)
            new_utility = Utility(new_state, new_addressing)
            new_view = None
            if self.config.view_type == "web":
                # We can't deepcopy view (no pickling the socketio stuff), but it should be stateless enough 
                new_view = WebView(new_state, new_config, new_addressing, new_utility, self.view.app, self.view.socketio, self.uid, is_lookahead=True)
            elif self.config.view_type == "test":
                new_view = ViewForTesting(new_state, new_config, new_addressing, new_utility)
            # Since view is inside gameparser and interpreter, we need to just create new ones of those
            new_gameparser = GameParser(new_state, new_config, new_addressing, new_utility, self.gameparser.grammar)
            new_interpreter = Interpreter(new_state, new_config, new_addressing, new_utility, new_view, new_gameparser)
            new_gameloop = GameLoop(new_state, new_config, new_addressing, new_utility, new_view, new_gameparser, new_interpreter)

            new_lookahead_data[lookahead_choice_id] = new_gameloop.run(loaded_game_state={"state": new_state}, uid=self.uid, do_lookaheads=False, starting_input=[lookahead_choice_id.split(), "exit".split()], is_lookahead=True)
            new_lookahead_data[lookahead_choice_id]["diffs"] = copy.deepcopy(new_lookahead_data[lookahead_choice_id]["state"].diffs[-1])
            # Append the light data changes
            new_lookahead_data[lookahead_choice_id]["diffs"].append(Diff(
                diff_type = "light_data",
                data = new_lookahead_data[lookahead_choice_id]["state"].light
            ))

            # Undo modifications
            self.gamestate.reverse_last_diffs()
            self.gameparser.add_module_vars()
            new_view.is_lookahead = False
        
        self.lookahead_data = new_lookahead_data


    def close_game(self):
        self.gameparser.remove_module_vars()
        # Make the game not considered closed anymore so it doesn't just auto-close next time
        self.gamestate.light.closed = False
        return {"state": self.gamestate, "view": self.view}


    def command_define(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("define_no_name_given")
            return
        self.gamestate.light.command_macros[command[1]] = command[2:]
        self.view.print_feedback_message("define_successful")


    def command_undefine(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("undefine_no_macro_given")
            return
        if not command[1] in self.gamestate.light.command_macros:
            self.view.print_feedback_message("undefine_invalid_macro_given")
            return
        self.view.print_feedback_message("undefine_successful")
        del self.gamestate.light.command_macros[command[1]]


    def expand_command_macros(self, command):
        # Recursively expand any macros
        macro_depth = 0
        macro_expanded = True
        while macro_expanded:
            macro_expanded = False
            curr_command = []
            for subcommand in command:
                if subcommand in self.gamestate.light.command_macros:
                    for macro_subcommand in self.gamestate.light.command_macros[subcommand]:
                        macro_expanded = True
                        curr_command.append(macro_subcommand)
                else:
                    curr_command.append(subcommand)
            command = curr_command
            macro_depth += 1
            if macro_depth >= self.config.max_macro_depth:
                self.view.print_feedback_message("max_macro_depth_exceeded")
                break
        if macro_depth >= self.config.max_macro_depth:
            return False
        return command
    

    def command_confirm(self, command):
        if self.gamestate.light.action_to_confirm is not None:
            self.gamestate.light.action_to_confirm()
            self.gamestate.light.action_to_confirm = None
        else:
            self.view.print_feedback_message("confirm_nothing_to_confirm")
    

    def command_clear(self, command):
        self.view.clear(True)
        # Not implemented in web view yet
        if self.config.view_type == "cli":
            self.view.set_displayed_text("game")
            self.view.print_displayed_text()
        elif self.config.view_type == "web":
            self.view.print_emit_intercepts()
        self.view.print_choices()
    
    
    def command_exit(self, command):
        self.gamestate.light.closed = True
    

    def command_flag(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("flag_no_flag_given")
        else:
            if command[1] not in self.gamestate.bulk.vars["flags"]:
                self.view.print_feedback_message("flag_invalid_flag")
            else:
                self.gamestate.modify_flag(command[1], True)
                if self.do_lookaheads:
                    self.calc_lookaheads()
                self.view.print_feedback_message("flag_set_successfully")
    

    def command_goto(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("goto_no_address_given")
        else:
            address_to_goto = None
            try:
                # last_address_list should always be nonempty here since we just made a choice
                address_to_goto = self.addressing.parse_addr(self.gamestate.light.last_address_list[-1], command[1])
            except Exception as e:  # TODO: Catch only relevant exceptions
                self.view.print_feedback_message("goto_invalid_address_given")
            if not (address_to_goto is None):
                # NOTE: I think the following means "revert" not "back", maybe it used to be named differently?
                # TODO: Don't add to last_address_list for "back" command with gotos?
                self.make_choice(address_to_goto)
                if self.do_lookaheads:
                    self.calc_lookaheads()
    

    def command_help(self, command):
        if len(command) == 1:
            self.view.print_feedback_message("help")
            return
        
        if command[1] == "clear":
            self.view.print_feedback_message("help_clear")
        elif command[1] == "define":
            self.view.print_feedback_message("help_define")
        elif command[1] == "flag":
            self.view.print_feedback_message("help_flag")
        elif command[1] == "goto":
            self.view.print_feedback_message("help_goto")
        elif command[1] == "help":
            self.view.print_feedback_message("help_help")
        elif command[1] == "info":
            self.view.print_feedback_message("help_info")
        elif command[1] == "input":
            self.view.print_feedback_message("help_input")
        elif command[1] == "inspect":
            self.view.print_feedback_message("help_inspect")
        elif command[1] == "load":
            self.view.print_feedback_message("help_load")
        elif command[1] == "repeat":
            self.view.print_feedback_message("help_repeat")
        elif command[1] == "restart":
            self.view.print_feedback_message("help_restart")
        elif command[1] == "revert":
            self.view.print_feedback_message("help_revert")
        elif command[1] == "save":
            self.view.print_feedback_message("help_save")
        elif command[1] == "set":
            self.view.print_feedback_message("help_set")
        elif command[1] == "undefine":
            self.view.print_feedback_message("help_undefine")
        elif command[1] == "unflag":
            self.view.print_feedback_message("help_unflag")
        else:
            self.view.print_feedback_message("help_invalid_command")
    

    def command_info(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("info_options")
            return
        if command[1] == "actions":
            self.view.print_choices(True)  # Print actions
        elif command[1] == "choices":
            self.view.print_choices()
        elif command[1] == "completion":
            if len(self.gamestate.light.storypoints) == 0:
                self.view.print_feedback_message("completion_not_supported")
                return

            num_complete = 0
            total_num = 0
            for val in self.gamestate.light.storypoints.values():
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
                self.view.print_num_words(self.utility.count_words(self.gamestate.game))
            except Exception:
                self.view.print_feedback_message("command_not_supported")
        elif command[1] == "words_seen":
            # TODO: Only error when view doesn't have given method
            try:
                self.view.print_num_words(self.utility.count_words(self.gamestate.game, True))
            except Exception:
                self.view.print_feedback_message("command_not_supported")
        else:
            self.view.print_feedback_message("info_invalid_option")


    def command_input(self, command):
        reconstructed_input = ""
        for subcommand in command[1:]:
            reconstructed_input += subcommand + " "
        for subcommand in reconstructed_input.split(",")[::-1]:
            self.gamestate.light.command_buffer.insert(0, subcommand.split())
        if self.do_lookaheads:
            self.calc_lookaheads()


    def command_inspect(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("inspect_no_variable_given")
        else:
            try:
                self.view.print_var_value(self.utility.collect_vars(self.gamestate.light.last_address_list[-1])[command[1]])
            except KeyError: # TODO: Make this custom MissingReference Error
                self.view.print_feedback_message("inspect_invalid_variable_given")
    

    def command_load(self, command):
        if len(command) == 1:
            self.view.print_feedback_message("load_no_file_given")
            return
        try:
            self.load_game(command[1], add_save_text=True)
        except FileNotFoundError:
            self.view.print_feedback_message("load_invalid_file_given")
    

    def command_repeat(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("repeat_no_num_times_given")
            return
        elif len(command) < 3:
            self.view.print_feedback_message("repeat_no_command_given")
            return
        else:
            num_repeats = 0

            try:
                num_repeats = int(command[1])
            except Exception:
                self.view.print_feedback_message("repeat_incorrect_num_times_format")
            else:
                for i in range(num_repeats):
                    self.gamestate.light.command_buffer.insert(0, command[2:])
    

    def command_restart(self, command):
        if self.config.view_type != "web":
            self.view.print_feedback_message("command_not_supported")
            return
        
        self.view.socketio.emit("restart_html", {})
    

    def command_revert(self, command):
        if len(self.gamestate.diffs) == 1:
            self.view.print_feedback_message("revert_no_reversions")
            return
        
        self.gamestate.reverse_last_diffs()

        self.view.clear(True)
        if self.config.view_type == "cli":
            self.view.print_displayed_text()
        elif self.config.view_type == "web":
            self.view.clear_var_view()
            self.view.print_shown_vars(self.gamestate.light.view.shown_vars, self.gamestate.light.last_address_list[-1])
            self.view.show_curr_image()
            self.view.print_emit_intercepts()
            self.view.print_choices()

            self.gameparser.remove_module_vars()
            self.view.save_game_state()
            self.gameparser.add_module_vars()
        if self.do_lookaheads:
            self.calc_lookaheads()
    

    def command_save(self, command):
        try:
            save_slot = command[1]
        except IndexError:
            save_slot = self.gamestate.light.last_save_name
        if not save_slot:
            self.view.print_feedback_message("save_no_default_name_given")
            return
        if (self.config.saves_dir / save_slot).with_suffix(".pkl").exists():
            def finish_saving():
                self.view.print_feedback_message("save_completed", True) # "True" makes sure it doesn't save the "saved game" message to state
                self.save_game(save_slot)
            self.gamestate.light.action_to_confirm = finish_saving
            self.view.print_feedback_message("save_override")
            return
        self.view.print_feedback_message("save_completed", True) # "True" makes sure it doesn't save the "saved game" message to state
        self.save_game(save_slot)
    

    def command_set(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("set_no_variable_given")
        else:
            if len(command) < 3:
                self.view.print_feedback_message("set_no_value_given")
            else:
                var_dict = self.utility.collect_vars_with_dicts(self.gamestate.light.last_address_list[-1])
                var_dict_vals = self.utility.collect_vars(self.gamestate.light.last_address_list[-1])
                try:
                    var = var_dict[command[1]]
                    self.gamestate.modify_var(var["address"], command[1], eval(command[2], {}, var_dict_vals))
                    self.view.print_feedback_message("set_command_successful")
                except:
                    self.view.print_feedback_message("set_invalid_variable_given")
    

    def command_unflag(self, command):
        if len(command) < 2:
            self.view.print_feedback_message("unflag_no_flag_given")
        else:
            if command[1] not in self.gamestate.bulk.vars["flags"]:
                self.view.print_feedback_message("unflag_invalid_flag")
            else:
                self.gamestate.modify_flag(command[1], False)
                self.view.print_feedback_message("unflag_set_successfully")

    
    def run_step(self):
        # Yield control to other processes
        if self.config.view_type == "web":
            self.view.socketio.sleep(0)

        # Get next command
        if len(self.gamestate.light.command_buffer) == 0:
            command = self.view.get_input()
        else:
            command = self.gamestate.light.command_buffer.pop(0)

        if len(command) == 0:
            return

        # Check for macros first so that they can be reversed if needed
        if command[0] == "define":
            self.command_define(command)
            return
        elif command[0] == "undefine":
            self.command_undefine(command)
            return

        command = self.expand_command_macros(command)
        if command is False:
            return

        if command[0] == "confirm":
            return self.command_confirm(command)
        self.gamestate.light.action_to_confirm = None
        
        command_to_handler = {
            "clear": self.command_clear,
            "exit": self.command_exit,
            "flag": self.command_flag,
            "goto": self.command_goto,
            "help": self.command_help,
            "info": self.command_info,
            "input": self.command_input,
            "inspect": self.command_inspect,
            "load": self.command_load,
            "repeat": self.command_repeat,
            "restart": self.command_restart,
            "revert": self.command_revert,
            "save": self.command_save,
            "set": self.command_set,
            "unflag": self.command_unflag
        }

        if command[0] in command_to_handler:
            command_to_handler[command[0]](command)
        # TODO: Separate this into its own function
        elif command[0] in self.gamestate.light.choices:
            choice = self.gamestate.light.choices[command[0]]
            if "enforce" not in choice:
                choice["enforce"] = "True"
            if "missing" not in choice:
                choice["missing"] = []
            if "modifications" not in choice:
                choice["modifications"] = []
            
            # Populate the state vars with any given args
            self.gamestate.bulk.vars["_args"] = self.utility.get_args_list()
            for arg in command[1:]:
                self.gamestate.bulk.vars["_args"].append(arg)
            
            if len(choice["missing"]) > 0:
                self.view.print_feedback_message("choice_missing_requirements")
            elif not self.utility.eval_conditional(choice["enforce"], choice["choice_address"]):
                # TODO: Should autosaves/etc. happen after alt effects
                # TODO: Also need to make this work with lookahead
                if choice["alt_address"]:
                    self.make_choice(choice["alt_address"], choice, is_action_override=True)
                else:
                    self.view.print_feedback_message("choice_enforce_false")
            else:
                if self.do_lookaheads:
                    # TODO: Don't allow cli view to get here or implement cli view
                    # CLI view currently not supported with lookaheads
                    new_gamesession_info = self.lookahead_data[command[0]]

                    self.gamestate.apply_diffs(self.lookahead_data[command[0]]["diffs"])
                    self.gameparser.add_module_vars()

                    if self.config.view_type == "web":
                        self.view.do_emits(new_gamesession_info["view"].lookahead_emits)

                        # Yield control before we do complex state saving operations
                        self.view.socketio.sleep(0)

                    self.do_autosaves()

                    if self.config.view_type == "web":
                        # Need to manually save game state since the lookaheads don't
                        self.gameparser.remove_module_vars()
                        self.view.save_game_state()
                        self.gameparser.add_module_vars()

                    # For each new choice in new gamestate, try making that choice

                    self.calc_lookaheads()
                else:
                    if not self.is_lookahead:
                        self.do_autosaves()

                    # Pay required costs
                    for modification in choice["modifications"]:
                        if ("type_to_modify" in modification) and modification["type_to_modify"] == "bag":
                            modification["bag_ref"]["value"][modification["item"]] += modification["amount"]
                        else:
                            var_ref = self.utility.get_var(self.gamestate.bulk.vars, modification["var"], choice["choice_address"])

                            self.gamestate.modify_var(var_ref["address"], modification["var"], var_ref["value"] + modification["amount"])

                            # TODO: Print modifications?

                    self.gamestate.inc_choice_visits(choice["choice_address"])

                    self.make_choice(choice["address"], choice)
        else:
            self.view.print_feedback_message("unrecognized_command")
    

    def prerun(self, game_name=None, packaged=True, loaded_game_state=None, uid=None, do_lookaheads=False, starting_input=[], is_lookahead=False):
        # Make random number generation deterministic
        random.seed(23)
        
        self.uid = uid
        if self.uid is None:
            # Just set a dummy UID if this is a web view
            self.uid = ""
        self.do_lookaheads = do_lookaheads
        self.is_lookahead = is_lookahead
        
        self.initialize_game(loaded_game_state, game_name, packaged)

        if loaded_game_state is None:
            self.view.print_choices()

            self.save_game("_autosave")
            self.make_choice(self.gamestate.light.choices["start"]["address"])
        
        # Append passed input to gamestate input
        for command in self.gamestate.light.command_buffer:
            starting_input.append(command)
        self.gamestate.light.command_buffer = starting_input

        # If we have lookaheads, we need to populate the history now
        # TODO: Do I need to do history autosaves still?..
        if self.do_lookaheads:
            self.do_autosaves()
        
        # TODO: Should this go in state?
        # Seems like not (having trouble pickling it!)
        self.lookahead_data = None
        
        if self.do_lookaheads:
            self.calc_lookaheads()
            

    def run(self, game_name=None, packaged=True, loaded_game_state=None, uid=None, do_lookaheads=False, starting_input=[], is_lookahead=False):
        self.prerun(game_name=game_name, packaged=packaged, loaded_game_state=loaded_game_state, uid=uid, do_lookaheads=do_lookaheads, starting_input=starting_input, is_lookahead=is_lookahead)

        # Main game loop
        while True:
            # Check if the game's been closed
            if self.gamestate.light.closed:
                return self.close_game()
            
            self.run_step()