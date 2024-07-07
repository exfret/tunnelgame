from flask import Flask, render_template
import os
from pathlib import Path # TODO: Move this back into config, currently hotfix to prevent circular dependency
import subprocess # TODO: Add to dependencies?
import textwrap
from tunnelvision import utility

feedback_msg = {
    "could_not_load_autosave": "Could not revert to autosave",
    "exec_no_story_given": "Must give path to story to execute.",
    "exec_invalid_file_given": "Invalid story given for exec.",
    "goto_invalid_address_given": "Incorrect address given.",
    "goto_no_address_given": "Must give an address.",
    "help": "Valid commands are 'actions', 'choices', 'exit', 'goto', 'help', 'inspect', 'load', 'save', 'set', and 'settings'.",
    "inspect_invalid_variable_given": "That's not a valid variable.",
    "inspect_no_variable_given": "Must give a variable to print the value of.",
    "load_invalid_file_given": "File to be loaded not found.",
    "load_no_file_given": "Must supply file to load.",
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
    "settings_flavor_invalid_val": "That's not an allowed value of show_flavor_text. Allowed values are 'always', 'once', and 'never'",
    "choice_missing_requirements": "Missing requirements.",
    "unrecognized_command": "Unrecognized command/choice. Type 'help' for commands or 'choices' for a list of choices.",
    "default": "Error: Invalid feedback message key.",
}


old_print = print

def print(text = ""):
    state["displayed_text"] += str(text) + "\n"
    old_print(text)


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
    def clear(self, dont_reset_displayed_text = False):
        if not dont_reset_displayed_text:
            state["displayed_text"] = ""
        os.system("clear")

    # Reprints displayed text for save/loads
    def print_displayed_text(self):
        old_print(state["displayed_text"], end="")
    
    ######################################################################
    # Story board
    ######################################################################

    def print_flavor_text(self, text):
        self.print_text(text)

    def print_separator(self):
        print("-" * 90)
        print()

    def print_table(self, tbl_to_display):
        border = f"+-{'-' * len(tbl_to_display[0])}-+"
        print(border)
        for row in tbl_to_display:
            row = map(str, row)
            print(f"| {''.join(row)} |")
        print(border)

    def print_text(self, text, style=""):
        ansi_code = "\033[0m"
        if style == "bold":
            ansi_code = "\033[1m"

        string_to_print = utility.format.vformat(text, (), utility.collect_vars(state))  # TODO: Exceptions in case of syntax errors
        print(ansi_code + textwrap.fill(string_to_print, 100) + "\033[0m")
        print()

    ######################################################################
    # Stats board
    ######################################################################

    def print_stat_change(self, text):
        displayed_text = text + "\n"
        state["displayed_text"] += displayed_text + "\n"
        print(displayed_text)

    def print_var_modification(self, text_to_show_spec):
        operation_text = None
        new_text = ""
        if text_to_show_spec["op"] == "add":
            print(f"[+{text_to_show_spec['amount']} {text_to_show_spec['var']['locale']}]")
        elif text_to_show_spec["op"] == "subtract":
            print(f"[-{text_to_show_spec['amount']} {text_to_show_spec['var']['locale']}]")
        elif text_to_show_spec["op"] == "set":
            print(f"[Set {text_to_show_spec['var']['locale']} to {text_to_show_spec['amount']}]")
        print()  # Print newline

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
            if choice["text"]:
                text_for_choice = f" {choice['text']}"
            print(f"        {text_color} * {new_text}{choice_color}{choice_id}{text_color}{text_for_choice}{effects_text}")
            if len(choice["missing"]) > 0:
                missing_text = "\033[90m              Missing: "
                for missing in choice["missing"]:
                    if isinstance(missing, dict):
                        if missing["type_missing"] == "bag":
                            missing_text += f"{missing['item']} in {missing['bag_name']}, "
                        else:  # The only special missing type right now is a bag
                            raise Exception()
                    else:
                        missing_text += missing + ", "
                missing_text = missing_text[:-2]
                print(missing_text + "\033[0m")

    def print_feedback_message(self, msg_type, dont_save = False):
        if dont_save:
            if not (msg_type in feedback_msg):
                old_print(feedback_msg["default"])
            else:
                old_print(feedback_msg[msg_type])
        else:
            if not (msg_type in feedback_msg):
                print(feedback_msg["default"])
            else:
                print(feedback_msg[msg_type])

    def print_settings(self):
        displayed_text = ""
        for key in state["settings"].keys():
            print(f" * {key}")

    def print_settings_flavor_text_get(self):
        print(f"Allowed values are 'always', 'once', and 'never'. The current value of this setting is '{state['settings']['show_flavor_text']}'")

    def print_settings_flavor_text_set(self, new_value):
        print(f"Set show_flavor_text to '{new_value}'")

    def print_var_value(self, var_value):
        print(var_value)

    def get_input(self) -> str:
        old_print()
        command_string = input("> ")
        old_print()  # Add a new line
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

    def print_choices(self, display_actions = False):
        self.commands_called.append({"id": "print_choices"})

    def print_feedback_message(self, msg_type):
        self.commands_called.append({"id": "print_feedback_message", "msg": msg_type})

    def print_flavor_text(self, text):
        self.commands_called.append({"id": "print_flavor_text", "text": text})

    def print_settings(self):
        self.commands_called.append({"id": "print_settings"})

    def print_settings_flavor_text_get(self):
        self.commands_called.append({"id": "print_settings_flavor_text_get"})

    def print_settings_flavor_text_set(self, new_value):
        self.commands_called.append({"id": "print_settings_flavor_text_set", "new_value": new_value})

    def print_stat_change(self, text):
        self.commands_called.append({"id": "print_stat_change", "text": text})

    def print_table(self, tbl_to_display):
        self.commands_called.append({"id": "print_table", "tbl": tbl_to_display})

    def print_text(self, text, style):
        self.commands_called.append({"id": "print_text", "text": utility.format.vformat(text, (), utility.collect_vars(state)), "style": style})

    def print_var_modification(self, text_to_show_spec):
        self.commands_called.append({"id": "print_var_modifications", "text": text_to_show_spec})

    def print_var_value(self, var_value):
        self.commands_called.append({"id": "print_var_value", "var_value": var_value})

    def get_input(self) -> str:
        if self.num_choices_made >= len(self.choice_list):
            return "exit".split()

        self.num_choices_made += 1
        return self.choice_list[self.num_choices_made - 1].split()

class JavaView:
    def __init__(self):
        local_dir = Path(__file__).parent
        compile_result = subprocess.run(["javac", local_dir / "tunnelvision" / "src" / "main" / "java" / "com" / "example" / "tunnelvision" / "JavaView.java"])

        # Check that it compiled
        if compile_result.returncode != 0:
            raise Exception

        self.process = subprocess.Popen(
            ['java', 'com.example.tunnelvision.JavaView'],
            cwd=str(local_dir / "tunnelvision" / "src" / "main" / "java"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # Ensures text mode for stdin/stdout
        )

    def send_message(self, text):
        self.process.stdin.write(text)
        self.process.stdin.flush()

    ######################################################################
    # Miscellaneous
    ######################################################################

    # Clears console and story view
    def clear(self, dont_reset_displayed_text = False):
        self.send_message("clear:")

    # Reprints displayed text for save/loads
    def print_displayed_text(self):
        pass # TODO
    
    ######################################################################
    # Story board
    ######################################################################

    def print_flavor_text(self, text):
        pass # TODO

    def print_separator(self):
        pass # TODO

    def print_table(self, tbl_to_display):
        pass # TODO

    def print_text(self, text, style=""):
        self.send_message(f"print:{text}")

    ######################################################################
    # Stats board
    ######################################################################

    def print_stat_change(self, text):
        pass # TODO

    def print_var_modification(self, text_to_show_spec):
        pass # TODO

    ######################################################################
    # Console
    ######################################################################

    def print_choices(self, display_actions=False):
        choice_string = "choice:"
        for choice_id in state["choices"].keys():
            choice_string += choice_id + " "

        self.send_message(f"choice:{choice_string[:-1]}")

    def print_feedback_message(self, msg_type, dont_save = False):
        pass # TODO

    def print_settings(self):
        pass # TODO

    def print_settings_flavor_text_get(self):
        pass # TODO

    def print_settings_flavor_text_set(self, new_value):
        pass # TODO

    def print_var_value(self, var_value):
        pass # TODO

    def get_input(self) -> str:
        while True:
            try:
                response = self.process.stdout.readline()
                if not response.strip() == "":
                    return response.split(" ")
            except Exception:
                pass

class WebView:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_routes()
        self.app.run(port=5001, debug=True)
    
    def setup_routes(self):
        @self.app.route('/')
        def create_webpage():
            return render_template("index.html")

    ######################################################################
    # Miscellaneous
    ######################################################################

    # Clears console and story view
    def clear(self, dont_reset_displayed_text = False):
        pass # TODO

    # Reprints displayed text for save/loads
    def print_displayed_text(self):
        pass # TODO
    
    ######################################################################
    # Story board
    ######################################################################

    def print_flavor_text(self, text):
        pass # TODO

    def print_separator(self):
        pass # TODO

    def print_table(self, tbl_to_display):
        pass # TODO

    def print_text(self, text, style=""):
        pass # TODO

    ######################################################################
    # Stats board
    ######################################################################

    def print_stat_change(self, text):
        pass # TODO

    def print_var_modification(self, text_to_show_spec):
        pass # TODO

    ######################################################################
    # Console
    ######################################################################

    def print_choices(self, display_actions=False):
        pass # TODO

    def print_feedback_message(self, msg_type, dont_save = False):
        pass # TODO

    def print_settings(self):
        pass # TODO

    def print_settings_flavor_text_get(self):
        pass # TODO

    def print_settings_flavor_text_set(self, new_value):
        pass # TODO

    def print_var_value(self, var_value):
        pass # TODO

    def get_input(self) -> str:
        pass # TODO