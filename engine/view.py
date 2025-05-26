# Web imports
from flask import Flask, render_template, jsonify, session
from flask_socketio import SocketIO, emit, join_room
from uuid import uuid4

import copy
import pickle
import textwrap

# Module imports
from engine import addressing, config, utility


game = config.game
state = config.state


feedback_msg = {
    "run_instr_failed": "Warning: Run statement failed, returning to main game.",
    "could_not_load_autosave": "Could not revert to autosave",
    "completion_not_supported": "This story doesn't support completion percentage.",
    "autocomplete_no_possibilities": "No possibilities for autocompleting invalid command.",
    "autocomplete_multiple_possibilities": "Multiple possibilities for autocompleting invalid command.",
    "define_no_name_given": "Must give a name for the macro.",
    "define_successful": "Macro successfully bound.",
    "exec_no_story_given": "Must give path to story to execute.",
    "exec_invalid_file_given": "Story to be loaded not found.",
    "exec_error_running_game": "Error occurred while running game. Changes to state may have still occurred. Resuming outer game.",
    "flag_no_flag_given": "Must provide flag.",
    "flag_invalid_flag": "Invalid flag given.",
    "flag_set_successfully": "Flag set successfully",
    "goto_invalid_address_given": "Incorrect address given.",
    "goto_no_address_given": "Must give an address.",
    "help": "Valid commands are 'clear', 'define', 'exec', 'exit', 'flag', 'goto', 'help', 'info', 'input', 'inspect', 'load', 'repeat', revert', 'save', 'set', 'settings', 'undefine', 'unflag'.",
    "info_options": "Valid options for info are 'actions', 'choices', 'completion', 'macros', 'vars', 'word_count', and 'words_seen'.",
    "info_invalid_option": "Invalid option given for info. Type 'info' for valid options.",
    "inspect_no_variable_given": "Must give a variable to print the value of.",
    "inspect_invalid_variable_given": "That's not a valid variable.",
    "load_no_file_given": "Must supply file to load.",
    "load_invalid_file_given": "File to be loaded not found.",
    "repeat_no_num_times_given": "Must supply number of times to repeat command.",
    "repeat_no_command_given": "Must supply a command to repeat.",
    "repeat_incorrect_num_times_format": "Number times to repeat not an integer.",
    "revert_no_reversions": "Can't revert any further.",
    "save_no_default_name_given": "Must supply default save name.",
    "save_completed": "Save complete!",
    "set_no_variable_given": "Must supply a variable to set the value of.",
    "set_no_value_given": "Must supply a new value for the variable.",
    "set_invalid_variable_given": "Invalid variable given to set value of.",
    "set_command_successful": "Successfully set variable to new value.",
    "settings_no_setting_given": "Must give a setting to give a new value to or test the current value of. Here is a list of settings:",
    "settings_autocomplete_invalid_val": "That's not an allowed value of descriptiveness. Allowed values are 'on' and 'off'.'",
    "settings_descriptiveness_invalid_val": "That's not an allowed value of descriptiveness. Allowed values are 'descriptive', 'moderate', and 'minimal'.",
    "settings_flavor_invalid_val": "That's not an allowed value of show_flavor_text. Allowed values are 'always', 'once', and 'never'.",
    "unflag_no_flag_given": "Must provide flag.",
    "unflag_invalid_flag": "Invalid flag given.",
    "unflag_set_successfully": "Flag unset successfully",
    "undefine_no_macro_given": "No macro given to undefine.",
    "undefine_invalid_macro_given": "Invalid macro given.",
    "undefine_successful": "Macro successfully unbound.",
    "max_macro_depth_exceeded": "Error: maximum macro expansion depth exceeded. Make sure there are no circular macro definitions.",
    "command_not_supported": "This command is not supported by the current view.",
    "choice_missing_requirements": "Missing requirements.",
    "choice_enforce_false": "You can't make this choice.",
    "runtime_error_invalid_seed": "\033[33mWarning:\033[0m Seeded value doesn't correspond to valid choice in random block, stopping execution.",
    "unrecognized_command": "Unrecognized command/choice. Type 'help' for commands or 'choices' for a list of choices.",
    "default": "Error: Invalid feedback message key.",
}


old_print = print

# Valid views are game and console
# Only game is currently implemented (everything else is just "console")
def print(text="", view=None, dont_save_print=False):
    # Having __null__ in the string indicates it should not be printed
    # TODO: Some way to escape __null__ like with a backslash?
    if isinstance(text, str) and "__null__" in text:
        return
    
    if not dont_save_print:
        if view is not None and view in state["view_displayed_text"]:
            # TODO: Some sort of warning if view is not in state["view_displayed_text"]
            state["view_displayed_text"][view] += str(text) + "\n"
        state["displayed_text"] += str(text) + "\n"

    old_print(text)


# In newer versions, this only accepts two descriptiveness levels, descriptive/moderate (equivalent), and minimal
def parse_text(text):
    # Decide what part of the text to print
    split_text = text.split("-->")
    if len(split_text) == 1:
        text = split_text[0]
    elif len(split_text) > 1:
        if state["settings"]["descriptiveness"] == "minimal":
            text = split_text[1].strip()
        else:
            text = split_text[0].strip()

    return text


# Story board (Left up) - Supports different views, currently just story view which displays story and flavor-related text
# Stats board (Right up) - Will support buttons to change views of story board, currently just var changes
# Console (bottom) - Prints feedback and takes input


class CLIView:
    def __init__(self):
        pass


    ######################################################################
    # Miscellaneous
    ######################################################################


    # Clears console and story view
    def clear(self, dont_reset_displayed_text=False):
        if not dont_reset_displayed_text:
            state["displayed_text"] = ""
            
            for key in state["view_displayed_text"].keys():
                state["view_displayed_text"][key] = ""

        # Clears console with ansi code
        old_print("\033[H\033[J", end="")

    
    # Sets the displayed text to just be the text from one display
    def set_displayed_text(self, view):
        if view in state["view_displayed_text"]:
            state["displayed_text"] = state["view_displayed_text"][view]


    # Reprints displayed text for save/loads
    def print_displayed_text(self, view=None, add_save_text=False):
        old_print(state["displayed_text"], end="")

        # Whether to print a mock "save text" since the "Save complete!" text isn't saved
        if add_save_text:
            self.print_feedback_message("save_completed")


    ######################################################################
    # Story board
    ######################################################################


    def print_flavor_text(self, text, dont_save_print=False):
        self.print_text(text, view="game", dont_save_print=dont_save_print)


    def print_separator(self, dont_save_print=False):
        print("-" * 90 + "\n", view="game", dont_save_print=dont_save_print)


    def print_table(self, tbl_to_display, dont_save_print=False):
        border = f"+-{'-' * len(tbl_to_display[0])}-+"
        print(border, view="game", dont_save_print=dont_save_print)
        for row in tbl_to_display:
            row = map(str, row)
            print(f"| {''.join(row)} |", view="game")
        print(border, view="game", dont_save_print=dont_save_print)


    def print_text(self, text, style="", view="game", dont_save_print=False):
        ansi_code = "\033[0m"
        if style == "bold":
            ansi_code = "\033[1m"

        string_to_print = utility.format.vformat(text, (), utility.collect_vars(state))  # TODO: Exceptions in case of syntax errors
        string_to_print = parse_text(string_to_print)
        print(ansi_code + textwrap.fill(string_to_print, 100) + "\033[0m\n", view=view, dont_save_print=dont_save_print)


    ######################################################################
    # Stats board
    ######################################################################


    def clear_var_view(self):
        pass


    def print_shown_vars(self, shown_vars, vars_address):
        print("\nRelevant values:")
        var_dict_vals = utility.collect_vars(state, vars_address)
        for var_group in shown_vars:
            if isinstance(var_group, str):
                print(utility.localize(var_group, vars_address) + ":\t" + str(var_dict_vals[var_group]))
            elif isinstance(var_group, dict):
                label = next(iter(var_group))
                print(label + "...")
                for var in var_group[label]:
                    print("\t" + utility.localize(var, vars_address) + ":\t" + str(var_dict_vals[var]))


    def print_var(self, text):
        print(text)


    def print_var_modification(self, text_to_show_spec, dont_save_print=False):
        operation_text = None
        new_text = ""
        if text_to_show_spec["op"] == "add":
            print(f"[+{text_to_show_spec['amount']} {text_to_show_spec['var']['locale']}]\n", dont_save_print=dont_save_print)
        elif text_to_show_spec["op"] == "subtract":
            print(f"[-{text_to_show_spec['amount']} {text_to_show_spec['var']['locale']}]\n", dont_save_print=dont_save_print)
        elif text_to_show_spec["op"] == "set":
            print(f"[Set {text_to_show_spec['var']['locale']} to {text_to_show_spec['amount']}]\n", dont_save_print=dont_save_print)


    ######################################################################
    # Console
    ######################################################################


    def print_choices(self, display_actions=False):
        # Choices now have cost_spec, req_spec, and shown_spec
        # TODO: Evaluate missing at choice printing (here)

        text_to_display = ""
        if not display_actions:
            text_to_display += "\n        Choices...\n"
        else:
            text_to_display += "\n        Actions...\n"
        for choice_id, choice in state["choices"].items():
            is_action = "action" in choice and choice["action"]

            # Display only actions/choices, whichever is selected
            if not display_actions and is_action:
                continue
            if display_actions and not is_action:
                continue

            var_dict_vals = utility.collect_vars(state, choice["choice_address"])

            # Evaluate costs/requirements/shown
            # This is sorta duplicated between here and gameloop
            # TODO: Un-duplicate this
            def parse_modification_spec(choice, spec, spec_type):
                effects_text = ""
                if spec_type == "cost_spec":
                    effects_text = "\033[0m [\033[31mCost:\033[0m "
                if spec_type == "req_spec":
                    effects_text = "\033[0m [\033[38;2;255;165;0mRequired:\033[0m "
                if spec_type == "shown_spec":
                    effects_text = "\033[0m [\033[34mEffects:\033[0m "
                for modification in spec:
                    expr_val = eval(modification["amount"], {}, var_dict_vals)
                    sign = ""
                    if expr_val >= 0:
                        sign = "+"
                    if spec_type == "req_spec" or spec_type == "cost_spec":
                        sign = ""
                    effects_text += f"{sign}{expr_val} {utility.localize(modification["var"], choice["choice_address"])}, "
                effects_text = effects_text[:-2]
                effects_text += "]"
                return effects_text
            effects_text = ""
            if "cost_spec" in choice and len(choice["cost_spec"]) > 0:
                effects_text += parse_modification_spec(choice, choice["cost_spec"], "cost_spec")
            if "req_spec" in choice and len(choice["req_spec"]) > 0:
                effects_text += parse_modification_spec(choice, choice["req_spec"], "req_spec")
            if "shown_spec" in choice and len(choice["shown_spec"]) > 0:
                effects_text += parse_modification_spec(choice, choice["shown_spec"], "shown_spec")

            choice_color = "\033[32m"
            text_color = "\033[0m" # This appears to actually just be the color for the initial * in a choice?
            if "missing" in choice and len(choice["missing"]) > 0:
                choice_color = "\033[90m"
                text_color = "\033[90m"
            new_text = ""
            if state["visits"][choice["choice_address"]] <= 1:
                new_text = "\033[33m(New) "

            text_for_choice = ""
            if "text" in choice:
                text_for_choice = " " + parse_text(choice["text"])
            print(f"        {text_color} * {new_text}{choice_color}{choice_id}{text_color}{text_for_choice}{effects_text}")
            if len(choice["missing"]) > 0:
                missing_text = "\033[90m              Missing: "
                for missing in choice["missing"]:
                    if isinstance(missing, dict):
                        if missing["type_missing"] == "bag":
                            missing_text += f"{missing['item']} in {missing['bag_name']}, "
                        else:
                            # The only special missing type right now is a bag
                            raise Exception()
                    else:
                        missing_text += missing + ", "
                missing_text = missing_text[:-2]
                print(missing_text + "\033[0m")


    def print_completion_percentage(self, percentage):
        print(f"Completed {(100 * percentage):.1f}% of the story!")


    # Made feedback messages not save by default
    def print_feedback_message(self, msg_type, dont_save=True):
        if dont_save:
            # TODO: Switch to just using dont_save_print in new print function
            if not (msg_type in feedback_msg):
                old_print(feedback_msg["default"])
            else:
                old_print(feedback_msg[msg_type])
        else:
            if not (msg_type in feedback_msg):
                print(feedback_msg["default"])
            else:
                print(feedback_msg[msg_type])
    

    def print_macros(self):
        if len(state["command_macros"].items()) == 0:
            print("No macros defined.")
            return
        
        for macro_name, macro_def in state["command_macros"].items():
            print(macro_name + ": " + " ".join(macro_def))
    

    def print_num_words(self, num_words):
        print(num_words)


    def print_settings(self):
        displayed_text = ""
        for key in state["settings"].keys():
            print(f" * {key}")

    
    def print_settings_autocomplete_get(self):
        print(f"Allowed values are 'on' and 'off'. The current value of this setting is '{state['settings']['autocomplete']}'.")


    def print_settings_autocomplete_set(self, new_value):
        print(f"Set autocomplete to '{new_value}'.")


    def print_settings_descriptiveness_get(self):
        print(f"Allowed values are 'descriptive', 'moderate', and 'minimal'. The current value of this setting is '{state['settings']['descriptiveness']}'.")


    def print_settings_descriptiveness_set(self, new_value):
        print(f"Set descriptiveness to '{new_value}'.")


    def print_settings_flavor_text_get(self):
        print(f"Allowed values are 'always', 'once', and 'never'. The current value of this setting is '{state['settings']['show_flavor_text']}'.")


    def print_settings_flavor_text_set(self, new_value):
        print(f"Set show_flavor_text to '{new_value}'.")


    def print_var_value(self, var_value):
        print(var_value)
    

    def print_vars_defined(self):
        var_names = {}

        curr_addr = addressing.get_block_part(state["last_address"])
        for ind in range(len(curr_addr) + 1):
            addr_to_check = curr_addr[:ind]

            for var_name in state["vars"][addr_to_check].keys():
                var_names[var_name] = True
        
        for name in sorted(var_names):
            print(name)


    def get_input(self):
        old_print() # Add a new line
        command_string = input("> ")
        old_print()
        state["displayed_text"] += "\n> " + command_string + "\n\n"

        command = command_string.split()
        return command


class ViewForTesting:
    def __init__(self, choice_list=[]):
        self.num_choices_made = 0
        self.choice_list = choice_list
        self.commands_called = []


    def update_choice_list(self, choice_list):
        self.num_choices_made = 0
        self.choice_list = choice_list
        self.commands_called = []


    def get_sub_commands_called(self, id):
        sub_commands_called = []
        for command in self.commands_called:
            if command["id"] == id:
                sub_commands_called.append(command)
        return sub_commands_called


    def get_text_commands_called(self):
        text_commands_called = []
        for command in self.commands_called:
            if command["id"] == "print_text":
                text_commands_called.append(command["text"])
        return text_commands_called


    def clear(self):
        self.commands_called.append({"id": "clear"})


    def clear_var_view(self):
        self.commands_called.append({"id": "clear_var_view"})


    def print_choices(self, display_actions = False):
        self.commands_called.append({"id": "print_choices"})


    def print_feedback_message(self, msg_type):
        self.commands_called.append({"id": "print_feedback_message", "msg": msg_type})


    def print_flavor_text(self, text, dont_save_print=False):
        self.commands_called.append({"id": "print_flavor_text", "text": text})


    def print_settings(self):
        self.commands_called.append({"id": "print_settings"})


    def print_settings_flavor_text_get(self):
        self.commands_called.append({"id": "print_settings_flavor_text_get"})


    def print_settings_flavor_text_set(self, new_value):
        self.commands_called.append({"id": "print_settings_flavor_text_set", "new_value": new_value})


    def print_shown_vars(self, shown_vars, vars_address):
        self.commands_called.append({"id": "print_shown_vars", "shown_vars": shown_vars, "vars_address": vars_address})


    def print_stat_change(self, text):
        self.commands_called.append({"id": "print_stat_change", "text": text})


    def print_table(self, tbl_to_display, dont_save_print=False):
        self.commands_called.append({"id": "print_table", "tbl": tbl_to_display})


    def print_text(self, text, style, dont_save_print=False):
        self.commands_called.append({"id": "print_text", "text": utility.format.vformat(text, (), utility.collect_vars(state)), "style": style})


    def print_var_modification(self, text_to_show_spec, dont_save_print=False):
        self.commands_called.append({"id": "print_var_modifications", "text": text_to_show_spec})


    def print_var_value(self, var_value):
        self.commands_called.append({"id": "print_var_value", "var_value": var_value})


    def get_input(self):
        if self.num_choices_made >= len(self.choice_list):
            return "exit".split()

        self.num_choices_made += 1
        return self.choice_list[self.num_choices_made - 1].split()


# TODO: Storing text for save/load for WebView
class WebView:
    def __init__(self):
        self.app = Flask(__name__)
        # TODO: Figure out what the secret key is needed for
        # Having this was suggested by ChatGPT
        self.app.config["SECRET_KEY"] = "password"
        self.socketio = SocketIO(self.app, async_mode="eventlet", manage_session=True)
        self.setup_routes()
        self.sid_to_uid = {}

        try:
            self.web_state = pickle.loads((config.saves / "_web_state").with_suffix(".pkl").read_bytes())
        except FileNotFoundError:
            self.web_state = {}
    

    def setup_routes(self):
        @self.app.route('/')
        def index():
            session.setdefault("uid", str(uuid4()))
            return render_template("index.html")
        

        @self.socketio.on("make_choice")
        def handle_choice(data):
            state["command_buffer"].append([data["choice_id"]])


    def save_game_state(self, uid, game_obj, state_obj):
        entry = self.web_state.setdefault(uid, {})
        entry["game"] = copy.deepcopy(game_obj)
        entry["state"] = copy.deepcopy(state_obj)
        entry["client_side"] = {} # TODO

        # Save across server restarts
        (config.saves / "_web_state").with_suffix(".pkl").write_bytes(pickle.dumps(self.web_state))


    ######################################################################
    # Miscellaneous
    ######################################################################


    # Clears console and story view
    def clear(self, dont_reset_displayed_text = False):
        # TODO: Saving displayed text
        self.socketio.emit("clear", {})


    # Reprints displayed text for save/loads
    def print_displayed_text(self):
        pass # TODO
    

    ######################################################################
    # Story board
    ######################################################################


    def print_flavor_text(self, text, dont_save_print=False):
        pass # TODO


    def print_separator(self, dont_save_print=False):
        self.socketio.emit("separator", {})


    def print_table(self, tbl_to_display, dont_save_print=False):
        pass # TODO


    def print_text(self, text, style="", dont_save_print=False):
        self.socketio.emit("print", {"text": text})


    ######################################################################
    # Stats board
    ######################################################################


    def clear_var_view(self):
        self.socketio.emit("clear_var_view", {})


    def print_shown_vars(self, shown_vars, vars_address):
        var_dict_vals = utility.collect_vars(state, vars_address)
        for var_group in shown_vars:
            if isinstance(var_group, str):
                self.socketio.emit("print_var", {"text": utility.localize(var_group, vars_address) + ":\t" + str(var_dict_vals[var_group])})
            elif isinstance(var_group, dict):
                label = next(iter(var_group))
                for var in var_group[label]:
                    self.socketio.emit("print_var", {"group": label, "name": utility.localize(var, vars_address), "value": str(var_dict_vals[var])})
                # Close the group if needed, or by default
                #is_open = False
                #if label in state["view"]["stats_dropdowns_open"] and state["view"]["stats_dropdowns_open"][label]:
                #    is_open = True
                #self.socketio.emit("set_dropdown_state", {"group": label, "open": is_open})


    def print_var(self, text):
        self.socketio.emit("print_var", {"text": text})


    def print_var_modification(self, text_to_show_spec, dont_save_print=False):
        pass # TODO


    ######################################################################
    # Console
    ######################################################################


    def print_choices(self, display_actions=False):
        effects_texts = {}

        # Fill effects texts (can't eval the python in the javascript)
        # TODO: Un-duplicate this text
        for choice_id, choice in state["choices"].items():
            var_dict_vals = utility.collect_vars(state, choice["choice_address"])

            def parse_modification_spec(choice, spec, spec_type):
                effects_text = ""
                if spec_type == "cost_spec":
                    effects_text = " [Cost: "
                if spec_type == "req_spec":
                    effects_text = " [Required: "
                if spec_type == "shown_spec":
                    effects_text = " [Effects: "
                for modification in spec:
                    expr_val = eval(modification["amount"], {}, var_dict_vals)
                    sign = ""
                    if expr_val >= 0:
                        sign = "+"
                    if spec_type == "req_spec" or spec_type == "cost_spec":
                        sign = ""
                    effects_text += f"{sign}{expr_val} {utility.localize(modification["var"], choice["choice_address"])}, "
                effects_text = effects_text[:-2]
                effects_text += "]"
                return effects_text
            
            effects_text = ""
            if "cost_spec" in choice and len(choice["cost_spec"]) > 0:
                effects_text += parse_modification_spec(choice, choice["cost_spec"], "cost_spec")
            if "req_spec" in choice and len(choice["req_spec"]) > 0:
                effects_text += parse_modification_spec(choice, choice["req_spec"], "req_spec")
            if "shown_spec" in choice and len(choice["shown_spec"]) > 0:
                effects_text += parse_modification_spec(choice, choice["shown_spec"], "shown_spec")

            effects_texts[choice_id] = effects_text

        self.socketio.emit("print_choices", {"choices": state["choices"], "effects_texts": effects_texts})


    def print_feedback_message(self, msg_type, dont_save=True):
        self.socketio.emit("print_feedback_message", {"text": feedback_msg[msg_type]})


    def print_settings(self):
        pass # TODO


    def print_settings_flavor_text_get(self):
        pass # TODO


    def print_settings_flavor_text_set(self, new_value):
        pass # TODO


    def print_var_value(self, var_value):
        pass # TODO


    def get_input(self):
        # TODO?
        return []