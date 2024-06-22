from config import game, state
import os
import string
import textwrap
import utility

feedback_msg = {
    "goto_invalid_address_given": "Incorrect address given.",
    "goto_no_address_given": "Must give an address.",
    "help": "Valid commands are 'exit', 'goto', 'help', 'inspect', 'load', 'save', and 'settings'.",
    "inspect_invalid_variable_given": "That's not a valid variable.",
    "inspect_no_variable_given": "Must give a variable to print the value of.",
    "load_invalid_file_given": "File to be loaded not found.",
    "load_no_file_given": "Must supply file to load.",
    "save_no_default_name_given": "Must supply default save name.",
    "settings_no_setting_given": "Must give a setting to give a new value to or test the current value of. Here is a list of settings:",
    "settings_flavor_invalid_val": "That's not an allowed value of show_flavor_text. Allowed values are 'always', 'once', and 'never'",
    "choice_missing_requirements": "Missing requirements.",
    "unrecognized_command": "Unrecognized command/choice. Type 'help' for commands or 'choices' for a list of choices.",
    "default": "Error: Invalid feedback message key."
}

class View:
    def __init__(self):
        pass

    def clear(self):
        os.system("clear")
    
    def print_choices(self):
        print("\n        Choices...")
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

    def print_flavor_text(self, text):
        self.print_text(text)
    
    def print_settings(self):
        for key in state["settings"].keys():
            print(" * " + key)

    def print_settings_flavor_text_get(self):
        print("Allowed values are 'always', 'once', and 'never'. The current value of this setting is '" + state["settings"]["show_flavor_text"] + "'")

    def print_settings_flavor_text_set(self, new_value):
        print("Set show_flavor_text to '" + new_value + "'")

    def print_stat_change(self, text):
        print(text)

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
    
    def print_var_modification(self, text_to_show_spec):
        operation_text = None
        if text_to_show_spec["op"] == "add":
            print("[+" + str(text_to_show_spec["amount"]) + " " + text_to_show_spec["var"]["locale"] + "]")
        elif text_to_show_spec["op"] == "subtract":
            print("[-" + str(text_to_show_spec["amount"]) + " " + text_to_show_spec["var"]["locale"] + "]")
        elif text_to_show_spec["op"] == "set":
            print("[Set " + text_to_show_spec["var"]["locale"] + " to " + str(text_to_show_spec["amount"]) + "]")
    
    def print_var_value(self, var_value):
        print(var_value)
    
    def get_input(self) -> str:
        command_string = input("\n> ")
        print() # Add a new line
        command = command_string.split()
        return command

class TestView:
    def __init__(self, choice_list):
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

view = View()

#view = TestView([])