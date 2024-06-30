import os
import string
import textwrap
from tunnelvision import utility

feedback_msg = {
    "goto_invalid_address_given": "Incorrect address given.",
    "goto_no_address_given": "Must give an address.",
    "help": "Valid commands are 'exit', 'goto', 'help', 'inspect', 'load', 'save', and 'settings'.",
    "inspect_invalid_variable_given": "That's not a valid variable.",
    "inspect_no_variable_given": "Must give a variable to print the value of.",
    "load_invalid_file_given": "File to be loaded not found.",
    "load_no_file_given": "Must supply file to load.",
    "save_no_default_name_given": "Must supply default save name.",
    "set_no_variable_given": "Must supply a variable to set the value of.",
    "set_no_value_given": "Must supply a new value for the variable.",
    "set_invalid_variable_given": "Invalid variable given to set value of.",
    "set_command_successful": "Successfully set variable to new value.",
    "settings_no_setting_given": "Must give a setting to give a new value to or test the current value of. Here is a list of settings:",
    "settings_flavor_invalid_val": "That's not an allowed value of show_flavor_text. Allowed values are 'always', 'once', and 'never'",
    "choice_missing_requirements": "Missing requirements.",
    "unrecognized_command": "Unrecognized command/choice. Type 'help' for commands or 'choices' for a list of choices.",
    "default": "Error: Invalid feedback message key."
}

# Story board (Left up) - Supports different views, currently just story view which displays story and flavor-related text
# Stats board (Right up) - Will support buttons to change views of story board, currently just var changes
# Console (bottom) - Prints feedback and takes input

class View:
    def __init__(self):
        pass

    ######################################################################
    # Miscellaneous
    ######################################################################

    # Clears console and story view
    def clear(self):
        os.system("clear")
    
    ######################################################################
    # Story board
    ######################################################################
    
    def print_flavor_text(self, text):
        self.print_text(text)
    
    def print_table(self, tbl_to_display):
        print("+" + "-" * (len(tbl_to_display[0]) + 2) + "+")
        for row in tbl_to_display:
            row_str = "| "
            for col in row:
                row_str += col
            row_str += " |"
            print(row_str)
        print("+" + "-" * (len(tbl_to_display[0]) + 2) + "+")
    
    def print_text(self, text, style = ""):
        ansi_code = "\033[0m"
        if style == "bold":
            ansi_code = "\033[1m"

        string_to_print = utility.format.vformat(text, (), utility.collect_vars(state)) # TODO: Exceptions in case of syntax errors
        print(ansi_code + textwrap.fill(string_to_print, 100) + "\033[0m")
        print()
    
    ######################################################################
    # Stats board
    ######################################################################

    def print_stat_change(self, text):
        print(text)

    def print_var_modification(self, text_to_show_spec):
        operation_text = None
        if text_to_show_spec["op"] == "add":
            print("[+" + str(text_to_show_spec["amount"]) + " " + text_to_show_spec["var"]["locale"] + "]")
        elif text_to_show_spec["op"] == "subtract":
            print("[-" + str(text_to_show_spec["amount"]) + " " + text_to_show_spec["var"]["locale"] + "]")
        elif text_to_show_spec["op"] == "set":
            print("[Set " + text_to_show_spec["var"]["locale"] + " to " + str(text_to_show_spec["amount"]) + "]")
        print() # Print newline
    
    ######################################################################
    # Console
    ######################################################################

    def print_choices(self):
        # Choices now have cost_spec, req_spec, and shown_spec
        # TODO: Evaluate missing at choice printing (here)

        print("\n        Choices...")
        for choice_id, choice in state["choices"].items():
            # Evaluate costs/requirements/shown
            if not "missing" in choice:
                choice["missing"] = []
            if not "modifications" in choice:
                choice["modifications"] = []
            var_dict_vals = utility.collect_vars(state, choice["choice_address"])
            effects_text = ""
            if "cost_spec" in choice and len(choice["cost_spec"]) > 0:
                effects_text += "\033[0m [\033[31mCost:\033[0m "
                for cost in choice["cost_spec"]:
                    localized_var = utility.localize(cost["var"], choice["choice_address"])
                    expr_val = eval(cost["amount"], {}, var_dict_vals)
                    var_val = var_dict_vals[cost["var"]]

                    effects_text += str(expr_val) + " " + localized_var + ", "
                    if var_val < expr_val:
                        choice["missing"].append(localized_var)
                    choice["modifications"].append({"var": cost["var"], "amount": -expr_val})
                effects_text = effects_text[:-2]
                effects_text += "]"
            if "req_spec" in choice and len(choice["req_spec"]) > 0:
                effects_text += "\033[0m [\033[38;2;255;165;0mRequired:\033[0m "
                for req in choice["req_spec"]:
                    localized_var = utility.localize(req["var"], choice["choice_address"])
                    expr_val = eval(req["amount"], {}, var_dict_vals)
                    var_val = var_dict_vals[req["var"]]

                    effects_text += str(expr_val) + " " + localized_var + ", "
                    if var_val < expr_val:
                        choice["missing"].append(localized_var)
                effects_text = effects_text[:-2]
                effects_text += "]"
            if "shown_spec" in choice and len(choice["shown_spec"]) > 0:
                effects_text += "\033[0m [\033[34mEffects:\033[0m "
                for shown in choice["shown_spec"]:
                    localized_var = utility.localize(shown["var"], choice["choice_address"])
                    expr_val = eval(shown["amount"], {}, var_dict_vals)
                    var_val = var_dict_vals[shown["var"]]

                    sign = ""
                    if expr_val > 0:
                        sign = "+"
                    effects_text += sign + str(expr_val) + " " + localized_var + ", "
                    choice["modifications"].append({"var": shown["var"], "amount": expr_val})
                effects_text = effects_text[:-2]
                effects_text += "]"

            choice_color = "\033[32m"
            text_color = "\033[0m"
            if len(choice["missing"]) > 0:
                choice_color = "\033[90m"
                text_color = "\033[90m"
            new_text = ""
            if state["visits"][choice["choice_address"]] <= 1:
                new_text = "\033[33m(New) "
            
            text_for_choice = ""
            if choice["text"]:
                text_for_choice = " " + choice["text"]
            print("        " + text_color + " * " + new_text + choice_color + choice_id + text_color + text_for_choice + effects_text)
            if len(choice["missing"]) > 0:
                missing_text = "              Missing: "
                for missing in choice["missing"]:
                    if isinstance(missing, dict):
                        if missing["type_missing"] == "bag":
                            missing_text += missing["item"] + " in " + missing["bag_name"] + ", "
                        else: # The only special missing type right now is a bag
                            raise Exception()
                    else:
                        missing_text += missing + ", "
                missing_text = missing_text[:-2]
                print(missing_text)
    
    def print_feedback_message(self, msg_type):
        if not (msg_type in feedback_msg):
            print(feedback_msg["default"])
        print(feedback_msg[msg_type])

    def print_settings(self):
        for key in state["settings"].keys():
            print(" * " + key)

    def print_settings_flavor_text_get(self):
        print("Allowed values are 'always', 'once', and 'never'. The current value of this setting is '" + state["settings"]["show_flavor_text"] + "'")

    def print_settings_flavor_text_set(self, new_value):
        print("Set show_flavor_text to '" + new_value + "'")

    def print_var_value(self, var_value):
        print(var_value)
    
    def get_input(self) -> str:
        command_string = input("\n> ")
        print() # Add a new line
        command = command_string.split()
        return command

class TestView:

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

    def print_choices(self):
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
