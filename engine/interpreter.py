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

        if isinstance(curr_node, str):
            self.do_print(curr_node, dont_save_print=dont_save_print)

            self.gamestate.light.bookmark = self.addressing.get_next_bookmark(self.gamestate.light.bookmark)

            self.do_profiling(start_time)
            return True


        # Since this is an instruction, it must be a map
        # TODO: Verify this part of stories
        if "back" in curr_node:
            while True:
                if len(self.gamestate.light.last_address_list) == 0:
                    break

                new_addr = self.addressing.get_block_part(self.gamestate.light.last_address_list.pop())

                # Don't count footers
                if self.addressing.get_block_part(self.gamestate.light.last_address) != new_addr:
                    parent_node = self.addressing.get_node(new_addr)

                    if isinstance(parent_node, list):
                        new_addr = new_addr + (0,)
                    else:
                        new_addr = new_addr + ("_content", 0)

                    self.addressing.set_curr_addr(new_addr)

                    self.do_profiling(start_time)
                    return True
        elif "call" in curr_node:
            # TODO: Currently borken!!!

            # TODO: Implement global/local vars that persist or don't persist after calls
            # Right now no variables persist after calls
            self.gamestate.state["call_stack"].append({"bookmark": self.gamestate.state["bookmark"], "vars": self.gamestate.state["vars"]})

            self.gamestate.state["bookmark"] = ()
            self.addressing.make_bookmark(self.gamestate.state["bookmark"], self.addressing.parse_addr(curr_addr, curr_node["call"]))

            self.gamestate.state["vars"] = {}
            self.gameparser.add_flags(self.gameobject.game)
            self.gameparser.add_vars_with_address(self.gameobject.game, ())
            self.gameparser.add_module_vars()

            # Add back "global" vars values
            for key, val in self.gamestate.state["call_stack"][-1]["vars"].items():
                if isinstance(key, tuple):
                    for var_name, var in val.items():
                        if "global" in var and var["global"]:
                            self.gamestate.state["vars"][key][var_name] = var

            self.do_profiling(start_time)
            return True
        elif "choice" in curr_node:
            if not "selectable_once" in curr_node or self.gamestate.bulk.per_line[curr_addr].choice_visits == 0:
                vars_by_name = self.utility.collect_vars_with_dicts()

                self.gamestate.light.choices[curr_node["choice"]] = {}

                choice_args = []
                if "args" in curr_node:
                    for arg in curr_node["args"]:
                        pass # TODO: Remove this sort of args checking
                
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
                if "per_cost" in curr_node:
                    self.gamestate.light.choices[curr_node["choice"]]["per_cost_spec"] = self.utility.parse_requirement_spec(curr_node["per_cost"])
                if "per_require" in curr_node:
                    self.gamestate.light.choices[curr_node["choice"]]["per_req_spec"] = self.utility.parse_requirement_spec(curr_node["per_require"])
                if "per_shown" in curr_node:
                    self.gamestate.light.choices[curr_node["choice"]]["per_shown_spec"] = self.utility.parse_requirement_spec(curr_node["per_shown"])

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
        elif "command" in curr_node:
            commands = curr_node["command"].split(";")
            for subcommand in commands:
                self.gamestate.light.command_buffer.append(subcommand.split())
        elif "descriptive" in curr_node:
            # TODO: Currently BROKEN!!

            # Default to setting that's at least as descriptive
            if self.gamestate.state["settings"]["descriptiveness"] == "descriptive":
                if not curr_node["descriptive"] is None:
                    self.do_print(curr_node["descriptive"], dont_save_print=dont_save_print)
            elif self.gamestate.state["settings"]["descriptiveness"] == "moderate":
                if "moderate" in curr_node:
                    if not curr_node["moderate"] is None:
                        self.do_print(curr_node["moderate"], dont_save_print=dont_save_print)
                else:
                    if not curr_node["descriptive"] is None:
                        self.do_print(curr_node["descriptive"], dont_save_print=dont_save_print)
            elif self.gamestate.state["settings"]["descriptiveness"] == "minimal":
                if "minimal" in curr_node:
                    if not curr_node["minimal"] is None:
                        self.do_print(curr_node["minimal"], dont_save_print=dont_save_print)
                elif "moderate" in curr_node:
                    if not curr_node["moderate"] is None:
                        self.do_print(curr_node["moderate"], dont_save_print=dont_save_print)
                else:
                    if not curr_node["descriptive"] is None:
                        self.do_print(curr_node["descriptive"], dont_save_print=dont_save_print)
        elif "error" in curr_node:
            raise ErrorNode("Error raised.")
        elif "flag" in curr_node:
            self.gamestate.modify_flag(curr_node["flag"], True)
        elif "flavor" in curr_node:
            # TODO: CURRENTLY BROKEN!!!

            if self.gamestate.state["settings"]["show_flavor_text"] != "never" and (self.gamestate.state["visits"][curr_addr] <= 1 or self.gamestate.state["settings"]["show_flavor_text"] == "always"):
                if isinstance(curr_node["flavor"], str):  # TODO: Allow style spec tag with flavor text
                    self.view.print_flavor_text(curr_node["flavor"], dont_save_print=dont_save_print)
                else:
                    self.addressing.set_curr_addr(curr_addr + ("flavor", 0))

                    self.do_profiling(start_time)
                    return True
        elif "gosub" in curr_node:
            sub_address = self.addressing.parse_addr(curr_addr, curr_node["gosub"])

            # Increment current address so that when we return we don't just go back to the gosub
            self.gamestate.light.bookmark = self.addressing.get_next_bookmark(self.gamestate.light.bookmark)

            self.gamestate.light.bookmark = (sub_address,) + self.gamestate.light.bookmark

            self.do_profiling(start_time)
            return True
        elif "goto" in curr_node:
            self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, curr_node["goto"]))

            self.do_profiling(start_time)
            return True
        elif "if" in curr_node:
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

                    self.do_profiling(start_time)
                    return True
                elif "else" in curr_node:
                    self.addressing.set_curr_addr(curr_addr + ("else", 0))

                    self.do_profiling(start_time)
                    return True
        elif "inject" in curr_node:
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
        elif "insert" in curr_node:
            vars_by_name = self.utility.collect_vars_with_dicts()

            amount = 1
            if "amount" in curr_node and isinstance(curr_node["amount"], (int, float)):
                amount = curr_node["amount"]
            elif "amount" in curr_node and isinstance(curr_node["amount"], str):
                amount = eval(curr_node["amount"], {}, self.utility.collect_vars())

            if not (curr_node["insert"] in vars_by_name[curr_node["into"]]["value"]):
                vars_by_name[curr_node["into"]]["value"][curr_node["insert"]] = {
                    "address": vars_by_name[curr_node["into"]]["address"],
                    # TODO: Locale!
                    "value": 0,
                }
            vars_by_name[curr_node["into"]]["value"][curr_node["insert"]]["value"] += amount
        elif "modify" in curr_node:
            # TODO: Parse-time checks that this is a variable that can be modified (i.e.- it has a value)
            var_to_change = self.utility.eval_vars(curr_node["modify"])
            old_val = self.utility.eval_values(curr_node["modify"])
            new_val = None
            if "add" in curr_node:
                new_val = old_val + self.utility.eval_values(curr_node["add"])
            self.utility.set_val(var_to_change, new_val)
        elif "move" in curr_node:
            # TODO: CURRENTLY BROKEN

            # Make sure to only get the block's address, not its inside instructions
            block_to_move_addr = self.addressing.parse_addr(curr_addr, curr_node["move"], only_block_part=True)
            # Make sure we're not trying to move the root block
            # TODO: Throw some sort of warning if we try to move the root block
            if block_to_move_addr != ():
                block_to_move = self.addressing.get_node(block_to_move_addr)
                # Move the block
                new_block_addr = self.addressing.parse_addr(curr_addr, curr_node["to"], only_block_part=True)
                new_block = self.addressing.get_node(new_block_addr)
                parent_block = self.addressing.get_node(block_to_move_addr[:-1])
                del parent_block[block_to_move_addr[-1]]
                new_block[block_to_move_addr[-1]] = block_to_move

                # Update block address stuff
                def reset_node_info(block, old_addr):
                    new_addr = new_block_addr + old_addr[len(block_to_move_addr)-1:]
                    if old_addr in self.gamestate.state["story_data"]["file_homes"]:
                        self.gamestate.state["story_data"]["file_homes"].add(new_addr)
                        self.gamestate.state["story_data"]["file_homes"].remove(old_addr)
                    if old_addr in self.gamestate.state["story_data"]["node_types"]:
                        self.gamestate.state["story_data"]["node_types"][new_addr] = self.gamestate.state["story_data"]["node_types"][old_addr]
                        del self.gamestate.state["story_data"]["node_types"][old_addr]

                    for key, val in block.items():
                        if key[0] != "_":
                            reset_node_info(val, old_addr + (key,))
                reset_node_info(block_to_move, block_to_move_addr)

                # If our address is now invalid, update it
                # Check if our initial part of the address matches the moved block
                if curr_addr[:len(block_to_move_addr)] == block_to_move_addr:
                    # Remove part that was previously the block
                    curr_addr = curr_addr[len(block_to_move_addr):]
                    # Add the new block part
                    curr_addr = new_block_addr + (block_to_move_addr[-1],) + curr_addr
                    # Set the address
                    self.addressing.set_curr_addr(curr_addr)
                    # Don't return anything because we actually still need to increment the address            
        elif "once" in curr_node:
            if self.gamestate.bulk.per_line[curr_addr].visits <= 1:
                if isinstance(curr_node["once"], str):
                    self.do_print(curr_node["once"], dont_save_print=dont_save_print)
                else:
                    self.addressing.set_curr_addr(curr_addr + ("once", 0))

                    self.do_profiling(start_time)
                    return True
        elif "pass" in curr_node:
            pass
        elif "pop_queue" in curr_node:
            # Pop the first element of the queue that's not the current stack element
            # Useful for injections
            # TODO: Label what parts of the bookmark queue represent (subroutine, injection, header, etc.) and use this to more easily manipulate it
            try:
                self.gamestate.light.bookmark = self.gamestate.light.bookmark[:1] + self.gamestate.light.bookmark[2:]
            except Exception:
                # If there was out of index error, do nothing
                pass
        elif "print" in curr_node:
            style = None
            if "style" in curr_node:
                style = curr_node["style"]

            self.do_print(curr_node["print"], style, dont_save_print=dont_save_print)
        elif "print_table" in curr_node:
            vars_by_name = self.utility.collect_vars_with_dicts()

            tbl_to_display = vars_by_name[curr_node["print_table"]]["value"]

            self.view.print_table(tbl_to_display, dont_save_print=dont_save_print)
        elif "print_var" in curr_node:
            self.view.print_var(curr_node["print_var"])
        elif "random" in curr_node:
            possibilities_list = []

            if isinstance(curr_node["random"], str):
                for id in curr_node["random"].split(","):
                    possibilities_list.append(id.strip())

                if len(self.gamestate.light.random_buffer) > 0:
                    # Check if the seed is in the possibilities list
                    seed = self.gamestate.light.random_buffer.pop(0)
                    if seed in possibilities_list:
                        self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, seed))
                    else:
                        # Feedback messages should already not save
                        self.view.print_feedback_message("runtime_error_invalid_seed")

                        self.do_profiling(start_time)
                        return False
                else:
                    self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, possibilities_list[random.randint(0, len(possibilities_list) - 1)]))

                self.do_profiling(start_time)
                return True

            total_weight = 0
            for key in curr_node["random"].keys():
                spec = key.split()
                weight = 1
                if len(spec) > 1:
                    weight = float(spec[0])
                total_weight += weight

                possibilities_list.append((weight, key))
            
            # Check if the seed exists and is in the possibilities list
            if len(self.gamestate.light.random_buffer) > 0:
                seed = self.gamestate.light.random_buffer.pop(0)

                # Can't just use "in" here since possibilities_list is more complex
                is_possible = False
                for possibility in possibilities_list:
                    if seed == possibility[1]:
                        is_possible = True
                
                if is_possible:
                    if curr_node["random"][seed] is None:
                        self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, seed))
                    else:
                        self.addressing.set_curr_addr(curr_addr + ("random", seed, 0))

                    self.do_profiling(start_time)
                    return True
                else:
                    # Feedback messages should already not save
                    self.view.print_feedback_message("runtime_error_invalid_seed")

                    self.do_profiling(start_time)
                    return False

            curr_weight = 0
            target_weight = random.uniform(0, total_weight)
            for possibility in possibilities_list:
                curr_weight += possibility[0]
                if curr_weight >= target_weight:
                    if curr_node["random"][possibility[1]] is None:
                        self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, possibility[1].split()[-1]))
                    else:
                        self.addressing.set_curr_addr(curr_addr + ("random", possibility[1], 0))

                    self.do_profiling(start_time)
                    return True
        elif "remove_choice" in curr_node:
            # TODO: Warning if this choice was not in the story?
            if curr_node["remove_choice"] in self.gamestate.light.choices:
                del self.gamestate.light.choices[curr_node["remove_choice"]]
        elif "return" in curr_node:
            # TODO: CURRENTLY BROKEN

            # TODO: Give warning if call stack is empty
            if len(self.gamestate.state["call_stack"]) >= 1:
                stack_state = self.gamestate.state["call_stack"].pop()

                self.gamestate.state["vars"] = stack_state["vars"]
                self.gamestate.state["bookmark"] = stack_state["bookmark"]

                # Don't return true since we need to increment past the call instruction
        elif "reveal" in curr_node:
            var_dict = self.utility.collect_vars_with_dicts(curr_addr)

            var_dict[curr_node["reveal"]]["hidden"] = False
        elif "run" in curr_node:
            # TODO: CURRENTLY BROKEN

            contents = self.utility.get_var(self.gamestate.state["vars"], curr_node["run"], curr_addr)["value"]
            temp_yaml = self.config.story_dir / "_temp.yaml"
            temp_yaml.write_bytes(yaml.dump(contents).encode('utf-8'))

            self.gamestate.state["msg"]["signal_run_statement"] = True

            self.gamestate.state["bookmark"] = self.addressing.get_next_bookmark(self.gamestate.state["bookmark"])

            self.do_profiling(start_time)
            return False
        elif "seed" in curr_node:
            self.gamestate.light.random_buffer.append(curr_node["seed"])
        elif "send" in curr_node:
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
        elif "separator" in curr_node:
            self.view.print_separator(dont_save_print=dont_save_print)
        elif "set" in curr_node:
            text_to_show_spec = {}
            vars_by_name = self.utility.collect_vars_with_dicts()

            if not ("to" in curr_node):
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

                # TODO: Make show compatible with "to" set statements!
                if "show" in curr_node:
                    self.view.print_var_modification(text_to_show_spec, dont_save_print=dont_save_print)
            else:
                # TODO: BROKEN
                if isinstance(curr_node["to"], (int, float)):
                    vars_by_name[curr_node["set"]]["value"] = curr_node["to"]  # TODO: Allow setting to string literal values
                else:
                    vars_by_name[curr_node["set"]]["value"] = eval(curr_node["to"], {}, self.utility.collect_vars())  # TODO: Catch exceptions in case of syntax errors
        # Currently only spills out of choices
        elif "spill" in curr_node:
            partial_addr = curr_addr

            while partial_addr != ():
                partial_node = self.addressing.get_node(partial_addr)
                if "choice" in partial_node:
                    break
                else:
                    partial_addr = partial_addr[:-1]
            
            self.addressing.set_curr_addr(partial_addr)
        elif "stop" in curr_node:
            # Need to remove this address now from the queue
            self.gamestate.light.bookmark = self.gamestate.light.bookmark[1:]

            self.do_profiling(start_time)
            return False
        elif "storypoint" in curr_node:
            if curr_node["storypoint"] is None:
                self.gamestate.light.storypoints[curr_addr] = True
            else:
                self.gamestate.light.storypoints[curr_node["storypoint"]] = True
        elif "sub" in curr_node:
            # TODO: Make this interact better with "call"
            # (Right now, they each have their own call stacks that interact noncommutatively with each other)
            
            # Need to get next bookmark so after return we increment past the sub command
            self.gamestate.light.sub_stack = (self.addressing.get_next_bookmark(self.gamestate.light.bookmark),) + self.gamestate.light.sub_stack
            self.gamestate.light.bookmark = self.addressing.make_bookmark((), self.addressing.parse_addr(curr_addr, curr_node["sub"]))

            self.do_profiling(start_time)
            return True
        elif "subreturn" in curr_node:
            if len(self.gamestate.light.sub_stack) == 0:
                # TODO: Throw error in this case, this is where we try to return from a subroutine but we're not in one
                pass
            else:
                self.gamestate.light.bookmark = self.gamestate.light.sub_stack[0]
                self.gamestate.light.sub_stack = self.gamestate.light.sub_stack[1:]

                self.do_profiling(start_time)
                return True
        elif "switch" in curr_node:
            switch_value = eval(curr_node["switch"], {}, self.utility.collect_vars())
            if str(switch_value) in curr_node:
                if isinstance(curr_node[str(switch_value)], str):
                    self.addressing.set_curr_addr(self.addressing.parse_addr(curr_addr, curr_node[str(switch_value)]))
                else:
                    self.addressing.set_curr_addr(curr_addr + (str(switch_value), 0))

                self.do_profiling(start_time)
                return True
            elif "_default" in curr_node:
                if isinstance(curr_node["_default"], str):
                    self.addressing.set_curr_addr(curr_node[str(switch_value)])
                else:
                    self.addressing.set_curr_addr(curr_addr + ("_default", 0))

                self.do_profiling(start_time)
                return True
        elif "tag" in curr_node:
            pass # Tags currently do nothing
        elif "unflag" in curr_node:
            self.gamestate.modify_flag(curr_node["unflag"], False)
        else:
            raise UnrecognizedInstruction(f"Unrecognized instruction: {curr_node}")

        self.gamestate.light.bookmark = self.addressing.get_next_bookmark(self.gamestate.light.bookmark)

        self.do_profiling(start_time)
        return True