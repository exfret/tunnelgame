from config import game, state

class View:
    def __init__(self):
            pass
    
    def print_choices(self):
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
    
    def print_text(self, text):
        print(text)
    
    def print_stat_change(self, text):
        print(text)

    def print_flavor_text(self, text):
        print(text)
    
    def print_table(self, table):
        print(table)
    
    def get_input(self) -> str:
        return input("> ")