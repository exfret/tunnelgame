import yaml
import random
import time


from engine.gamestate import GameState
from engine.config import Config
from engine.addressing import Addressing
from engine.utility import Utility
from engine.view import View
from engine.gameparser import GameParser


class ErrorNode(Exception):
    pass


class UnrecognizedInstruction(Exception):
    pass


class Interpreter:
    gamestate : GameState
    config : Config
    addressing : Addressing
    utility : Utility
    view : View
    gameparser : GameParser


    def __init__(self, gamestate, config, addressing, utility, view, gameparser):
        self.gamestate = gamestate
        self.config = config
        self.addressing = addressing
        self.utility = utility
        self.view = view
        self.gameparser = gameparser


    def do_print(self, text, style="", dont_save_print=False):
        self.view.print_text(text, style, dont_save_print=dont_save_print)


    def do_profiling(self, start_time):
        if self.config.profiling:
            self.config.last_instr_time = time.time() - start_time
            self.config.total_instr_time += time.time() - start_time
            self.config.total_num_instrs += 1


    def instr_choice(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        if not "selectable_once" in curr_node or self.gamestate.bulk.per_line[curr_addr].choice_visits == 0:
            self.gamestate.light.choices[curr_node["choice"]] = {}
            
            # By default there is nothing enforced
            self.gamestate.light.choices[curr_node["choice"]]["enforce"] = "True"
            if "enforce" in curr_node:
                self.gamestate.light.choices[curr_node["choice"]]["enforce"] = curr_node["enforce"]

            missing_list = []
            modify_list = []
            text = ""
            if "text" in curr_node:
                text = curr_node["text"]
            if "cost" in curr_node:
                self.gamestate.light.choices[curr_node["choice"]]["cost_spec"] = self.utility.parse_requirement_spec(curr_node["cost"])
            if "require" in curr_node:
                self.gamestate.light.choices[curr_node["choice"]]["req_spec"] = self.utility.parse_requirement_spec(curr_node["require"])
            if "shown" in curr_node:
                self.gamestate.light.choices[curr_node["choice"]]["shown_spec"] = self.utility.parse_requirement_spec(curr_node["shown"])

            def get_effect_address(key):
                effect_address = ""
                if not key in curr_node:
                    if key == "effects":
                        effect_address = self.addressing.parse_addr(curr_addr, curr_node["choice"])
                    elif key == "alt_effects":
                        effect_address = None
                else:
                    effect_address = curr_addr + (key, 0)
                    if isinstance(curr_node[key], str):
                        effect_address = self.addressing.parse_addr(curr_addr, curr_node[key])
                return effect_address
            effect_address = get_effect_address("effects")
            alt_effect_address = get_effect_address("alt_effects")

            is_action = False
            if "action" in curr_node:
                is_action = True

            self.gamestate.light.choices[curr_node["choice"]]["text"] = text
            self.gamestate.light.choices[curr_node["choice"]]["address"] = effect_address
            self.gamestate.light.choices[curr_node["choice"]]["alt_address"] = alt_effect_address
            self.gamestate.light.choices[curr_node["choice"]]["missing"] = missing_list
            self.gamestate.light.choices[curr_node["choice"]]["modifications"] = modify_list
            self.gamestate.light.choices[curr_node["choice"]]["choice_address"] = curr_addr
            self.gamestate.light.choices[curr_node["choice"]]["action"] = is_action
    
    
    def instr_command(self, **kwargs):
        curr_node = kwargs["curr_node"]

        commands = curr_node["command"].split(";")
        for subcommand in commands:
            self.gamestate.light.command_buffer.append(subcommand.split())
    

    def instr_error(self, **kwargs):
        raise ErrorNode("Error raised.")


    def instr_flag(self, **kwargs):
        curr_node = kwargs["curr_node"]

        self.gamestate.modify_flag(curr_node["flag"], True)

    
    def instr_goto(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, curr_node["goto"]))

        return True
    

    def instr_if(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        exception_occurred = False
        condition_value = None  # Bool representing the end condition value
        try:
            condition_value = self.utility.eval_conditional(curr_node["if"])
        except Exception as e:
            exception_occurred = True
            print(f'Warning, exception "{e}" occurred while evaluating if condition. Skipping if statement.')

        if not exception_occurred:
            if condition_value:
                self.addressing.set_curr_addr(curr_addr + ("then", 0))

                return True
            elif "else" in curr_node:
                self.addressing.set_curr_addr(curr_addr + ("else", 0))

                return True


    def instr_inject(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        if "into_choices" in curr_node:
            # Check for dict version of into_choices specification first
            choices_to_inject_into = None
            if isinstance(curr_node["into_choices"], dict):
                # Right now, just except is valid, which put it into all choices except the given ones
                if "except" in curr_node["into_choices"]:
                    choices_to_inject_into = list(self.gamestate.light.choices.keys())

                    choices_not_to_inject_into = curr_node["into_choices"]["except"].split()
                    for choice_id in choices_not_to_inject_into:
                        if choice_id in choices_to_inject_into:
                            choices_to_inject_into.remove(choice_id)
            elif isinstance(curr_node["into_choices"], str):
                if curr_node["into_choices"] == "_all":
                    choices_to_inject_into = list(self.gamestate.light.choices.keys())
                else:
                    choices_to_inject_into = curr_node["into_choices"].split()

            position = "before"
            if "position" in curr_node:
                position = curr_node["position"]

            for choice_id in choices_to_inject_into:
                # TODO: Warning when trying to inject into a choice that doesn't exist
                if choice_id in self.gamestate.light.choices:
                    if not "injections" in self.gamestate.light.choices[choice_id]:
                        self.gamestate.light.choices[choice_id]["injections"] = []
                    self.gamestate.light.choices[choice_id]["injections"].append({"address": self.addressing.parse_addr(curr_addr, curr_node["inject"]), "position": position})


    def instr_pass(self, **kwargs):
        pass


    def instr_print_var(self, **kwargs):
        curr_node = kwargs["curr_node"]
        dont_save_print = kwargs["dont_save_print"]

        self.view.print_var(curr_node["print_var"], dont_save_print=dont_save_print)
    

    def instr_random(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        possibilities_dict = {}
        total_weight = 0
        if isinstance(curr_node["random"], str):
            for id in curr_node["random"].split(","):
                possibilities_dict[id.strip()] = 1
                total_weight += 1
        else:
            for key in curr_node["random"].keys():
                spec = key.split()
                weight = 1
                if len(spec) > 1:
                    weight = float(spec[0])
                total_weight += weight

                possibilities_dict[key] = weight
            
        if len(self.gamestate.light.random_buffer) > 0:
            next_choice = self.gamestate.light.random_buffer.pop(0)
            if next_choice in possibilities_dict:
                if isinstance(curr_node["random"], str):
                    self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, next_choice))
                else:
                    self.addressing.set_curr_addr(curr_addr + ("random", next_choice, 0))
                return True
            else:
                # Feedback messages should already not save
                # TODO: Check if this is true??
                self.view.print_feedback_message("runtime_error_invalid_seed")

                return False
                
        curr_weight = 0
        target_weight = random.uniform(0, total_weight)
        for possibility in possibilities_dict.keys():
            curr_weight += possibilities_dict[possibility]
            if curr_weight >= target_weight:
                if isinstance(curr_node["random"], str):
                    self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, possibility))
                else: 
                    if curr_node["random"][possibility] is None:
                        self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, possibility.split()[1]))
                    else:
                        self.addressing.set_curr_addr(curr_addr + ("random", possibility, 0))

                return True
    

    def instr_remove_choice(self, **kwargs):
        curr_node = kwargs["curr_node"]

        # TODO: Warning if this choice was not in the story?
        if curr_node["remove_choice"] in self.gamestate.light.choices:
            del self.gamestate.light.choices[curr_node["remove_choice"]]
    

    def instr_reveal(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        var_dict = self.utility.collect_vars_with_dicts(curr_addr)

        var_dict[curr_node["reveal"]]["hidden"] = False
    

    def instr_seed(self, **kwargs):
        curr_node = kwargs["curr_node"]

        self.gamestate.light.random_buffer.append(curr_node["seed"])

    
    def instr_send(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        # Just trigger child blocks and current block for now by default
        parent_block_addr = self.addressing.get_block_part(curr_addr)
        parent_block = self.addressing.get_node(parent_block_addr)
        for child_block_name, child_block in list(parent_block.items()) + [((), parent_block)]:
            if "_listeners" in child_block:
                for index, listener in enumerate(child_block["_listeners"]):
                    # TODO: Parse listeners beforehand into a dict that's easier/faster to access
                    if "on_receive" in listener and listener["on_receive"] == curr_node["send"]:
                        child_block_addr_name = (child_block_name,)
                        if child_block_name == ():
                            child_block_addr_name = ()
                        self.gamestate.light.bookmark = self.gamestate.light.bookmark + (parent_block_addr + child_block_addr_name + ("_listeners", index, "handler", 0),)


    def instr_separator(self, **kwargs):
        dont_save_print = kwargs["dont_save_print"]

        self.view.print_separator(dont_save_print=dont_save_print)
    

    def instr_set(self, **kwargs):
        curr_node = kwargs["curr_node"]
        dont_save_print = kwargs["dont_save_print"]

        text_to_show_spec = {}
        vars_by_name = self.utility.collect_vars_with_dicts()

        var_expr_pair = curr_node["set"].split("=")

        var_name = var_expr_pair[0].strip()
        modifier = None
        if var_name[-1] == "+" or var_name[-1] == "-":
            modifier = var_name[-1]
            var_name = var_name[:-1].strip()

        var_name_indices = var_name.split("[")
        last_var_to_modify = None  # list
        var_to_modify = vars_by_name[var_name_indices[0]]
        last_index = None  # int
        for index in var_name_indices[1:]:
            last_index = int(index[:-1])
            last_var_to_modify = var_to_modify
            var_to_modify = var_to_modify[int(index[:-1])]

        # TODO: Show some text (in this case it doesn't quite make sense how to refer to the variable
        if modifier == "+":
            if not (last_index is None):
                # TODO: BROKEN
                last_var_to_modify[last_index] += eval(var_expr_pair[1], {}, self.utility.collect_vars())
            else:
                var = vars_by_name[var_name_indices[0]]
                self.gamestate.modify_var(var["address"], var_name_indices[0], var["value"] + eval(var_expr_pair[1], {}, self.utility.collect_vars()))
                text_to_show_spec = {"var_name": var_name_indices[0], "op": "add", "amount": eval(var_expr_pair[1], {}, self.utility.collect_vars()), "var": vars_by_name[var_name_indices[0]]}
        elif modifier == "-":
            if not (last_index is None):
                # TODO: BROKEN
                last_var_to_modify[last_index] -= eval(var_expr_pair[1], {}, self.utility.collect_vars())
            else:
                var = vars_by_name[var_name_indices[0]]
                self.gamestate.modify_var(var["address"], var_name_indices[0], var["value"] - eval(var_expr_pair[1], {}, self.utility.collect_vars()))
                text_to_show_spec = {"var_name": var_name_indices[0], "op": "subtract", "amount": eval(var_expr_pair[1], {}, self.utility.collect_vars()), "var": vars_by_name[var_name_indices[0]]}
        else:
            if not (last_index is None):
                # TODO: BROKEN
                last_var_to_modify[last_index] = eval(var_expr_pair[1], {}, self.utility.collect_vars())
            else:
                var = vars_by_name[var_name_indices[0]]
                self.gamestate.modify_var(var["address"], var_name_indices[0], eval(var_expr_pair[1], {}, self.utility.collect_vars()))
                text_to_show_spec = {"var_name": var_name_indices[0], "op": "set", "amount": eval(var_expr_pair[1], {}, self.utility.collect_vars()), "var": vars_by_name[var_name_indices[0]]}

        if "show" in curr_node:
            self.view.print_var_modification(text_to_show_spec, dont_save_print=dont_save_print)


    def instr_spill(self, **kwargs):
        curr_addr = kwargs["curr_addr"]

        partial_addr = curr_addr

        while partial_addr != ():
            partial_node = self.addressing.get_node(partial_addr)
            if "choice" in partial_node:
                break
            else:
                partial_addr = partial_addr[:-1]
        
        self.addressing.set_curr_addr(partial_addr)

    
    def instr_stop(self, **kwargs):
        # Need to remove this address now from the queue
        self.gamestate.light.bookmark = self.gamestate.light.bookmark[1:]

        return False
    

    def instr_storypoint(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        if curr_node["storypoint"] is None:
            self.gamestate.light.storypoints[curr_addr] = True
        else:
            self.gamestate.light.storypoints[curr_node["storypoint"]] = True
    

    def instr_sub(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        # TODO: Make this interact better with "call"
        # (Right now, they each have their own call stacks that interact noncommutatively with each other)
        
        # Need to get next bookmark so after return we increment past the sub command
        self.gamestate.light.sub_stack = (self.addressing.get_next_bookmark(self.gamestate.light.bookmark),) + self.gamestate.light.sub_stack
        self.gamestate.light.bookmark = self.addressing.make_bookmark((), self.addressing.parse_addr(curr_addr, curr_node["sub"]))

        return True


    def instr_unflag(self, **kwargs):
        curr_node = kwargs["curr_node"]

        self.gamestate.modify_flag(curr_node["unflag"], False)


    def instr_subreturn(self, **kwargs):
        if len(self.gamestate.light.sub_stack) == 0:
            # TODO: Throw error in this case, this is where we try to return from a subroutine but we're not in one
            pass
        else:
            self.gamestate.light.bookmark = self.gamestate.light.sub_stack[0]
            self.gamestate.light.sub_stack = self.gamestate.light.sub_stack[1:]

            return True
    

    def instr_switch(self, **kwargs):
        curr_addr = kwargs["curr_addr"]
        curr_node = kwargs["curr_node"]

        switch_value = eval(curr_node["switch"], {}, self.utility.collect_vars())
        if str(switch_value) in curr_node:
            if isinstance(curr_node[str(switch_value)], str):
                self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, curr_node[str(switch_value)]))
            else:
                self.addressing.set_curr_addr(curr_addr + (str(switch_value), 0))

            return True
        elif "_default" in curr_node:
            if isinstance(curr_node["_default"], str):
                self.addressing.set_curr_addr(curr_node[str(switch_value)])
            else:
                self.addressing.set_curr_addr(curr_addr + ("_default", 0))

            return True


    def step(self):
        start_time = None
        if self.config.profiling:
            start_time = time.time()

        curr_addr = self.addressing.get_curr_addr()

        if curr_addr == False:
            self.do_profiling(start_time)
            return False

        parent_block = self.addressing.get_block_part(curr_addr)
        # Don't save footer addresses
        if len(parent_block) == 0 or parent_block[-1] != "_footer":
            self.gamestate.light.last_address = curr_addr

        curr_node = self.addressing.get_node(curr_addr)

        # Mark that we've visited this node (again)
        self.gamestate.inc_visits(curr_addr)

        # Figure out if we are in a dont_save_print block
        dont_save_print = False
        for ind in range(len(parent_block)):
            parent_block_node = self.addressing.get_node(parent_block[:ind+1])
            if "_meta" in parent_block_node and "dont_save_print" in parent_block_node["_meta"]:
                dont_save_print = True
        
        to_print = None
        style = ""
        if isinstance(curr_node, str):
            to_print = curr_node
        else:
            if "print" in curr_node:
                if "style" in curr_node:
                    style = curr_node["style"]
                to_print = curr_node["print"]
        if to_print is not None:
            self.do_print(to_print, style=style, dont_save_print=dont_save_print)

            self.gamestate.light.bookmark = self.addressing.get_next_bookmark(self.gamestate.light.bookmark)

            self.do_profiling(start_time)
            return True

        instr_to_handler = {
            "choice": self.instr_choice,
            "command": self.instr_command,
            "error": self.instr_error,
            "flag": self.instr_flag,
            "goto": self.instr_goto,
            "if": self.instr_if,
            "inject": self.instr_inject,
            "pass": self.instr_pass,
            "print_var": self.instr_print_var,
            "random": self.instr_random,
            "remove_choice": self.instr_remove_choice,
            "reveal": self.instr_reveal,
            "seed": self.instr_seed,
            "send": self.instr_send,
            "separator": self.instr_separator,
            "set": self.instr_set,
            "spill": self.instr_spill,
            "stop": self.instr_stop,
            "storypoint": self.instr_storypoint,
            "sub": self.instr_sub,
            "subreturn": self.instr_subreturn,
            "switch": self.instr_switch,
            "unflag": self.instr_unflag
        }

        # Find the "primary" key
        primary_key = None
        for key in curr_node.keys():
            if key in instr_to_handler:
                primary_key = key
                break
        if primary_key is None:
            raise UnrecognizedInstruction(f"Unrecognized instruction: {curr_node}")
        return_val = instr_to_handler[primary_key](**{"curr_addr": curr_addr, "curr_node": curr_node, "dont_save_print": dont_save_print})
        self.do_profiling(start_time)
        if return_val is not None:
            return return_val

        # Go to the next instruction
        self.gamestate.light.bookmark = self.addressing.get_next_bookmark(self.gamestate.light.bookmark)
        return True