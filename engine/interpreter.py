import yaml
import random

from engine import addressing, config, gameparser, utility


game = config.game
state = config.state


class ErrorNode(Exception):
    pass


class UnrecognizedInstruction(Exception):
    pass


def do_print(text, state, style={}, dont_save_print=False):  # TODO: Move ansi code handling to view as well
    config.view.print_text(text, style, dont_save_print=dont_save_print)


def step():
    curr_view = config.view
    
    curr_addr = addressing.get_curr_addr()
    
    if curr_addr == False:
        return False

    parent_block = addressing.get_block_part(curr_addr)
    # Don't save footer addresses
    if len(parent_block) == 0 or parent_block[-1] != "_footer":
        state["last_address"] = curr_addr

    curr_node = addressing.get_node(curr_addr)
    # Mark that we've visited this node (again)
    if not (curr_addr in state["visits"]):
        state["visits"][curr_addr] = 0
    state["visits"][curr_addr] += 1

    # Figure out if we are in a dont_save_print block
    dont_save_print = False
    for ind in range(len(parent_block)):
        parent_block_node = addressing.get_node(parent_block[:ind+1])
        if "_meta" in parent_block_node and "dont_save_print" in parent_block_node["_meta"]:
            dont_save_print = True

    if isinstance(curr_node, str):
        do_print(curr_node, state, dont_save_print=dont_save_print)

        state["bookmark"] = addressing.get_next_bookmark(state["bookmark"])

        return True

    # Since this is an instruction, it must be a map
    # TODO: Verify this part of stories
    if "back" in curr_node:
        while True:
            if len(state["last_address_list"]) == 0:
                break

            new_addr = addressing.get_block_part(state["last_address_list"].pop())

            # Don't count footers
            if addressing.get_block_part(state["last_address"]) != new_addr:
                parent_node = addressing.get_node(new_addr)

                if isinstance(parent_node, list):
                    new_addr = new_addr + (0,)
                else:
                    new_addr = new_addr + ("_content", 0)

                addressing.set_curr_addr(new_addr)

                return True
    elif "call" in curr_node:
        # TODO: Implement global/local vars that persist or don't persist after calls
        # Right now no variables persist after calls
        state["call_stack"].append({"bookmark": state["bookmark"], "vars": state["vars"]})

        state["bookmark"] = ()
        addressing.make_bookmark(state["bookmark"], addressing.parse_addr(curr_addr, curr_node["call"]))

        state["vars"] = {}
        gameparser.add_flags(game)
        gameparser.add_vars_with_address(game, ())
        gameparser.add_module_vars()

        # Add back "global" vars values
        for key, val in state["call_stack"][-1]["vars"].items():
            if isinstance(key, tuple):
                for var_name, var in val.items():
                    if "global" in var and var["global"]:
                        state["vars"][key][var_name] = var

        return True
    elif "choice" in curr_node:
        if not "selectable_once" in curr_node or not curr_addr in state["visits_choices"] or state["visits_choices"][curr_addr] == 0:
            vars_by_name = utility.collect_vars_with_dicts(state)

            state["choices"][curr_node["choice"]] = {}

            choice_args = []
            if "args" in curr_node:
                for arg in curr_node["args"]:
                    pass # TODO: Remove this sort of args checking
            
            # By default there is nothing enforced
            state["choices"][curr_node["choice"]]["enforce"] = "True"
            if "enforce" in curr_node:
                state["choices"][curr_node["choice"]]["enforce"] = curr_node["enforce"]

            missing_list = []
            modify_list = []
            text = ""
            if "text" in curr_node:
                text = curr_node["text"]
            if "cost" in curr_node:
                state["choices"][curr_node["choice"]]["cost_spec"] = utility.parse_requirement_spec(curr_node["cost"])
            if "require" in curr_node:
                state["choices"][curr_node["choice"]]["req_spec"] = utility.parse_requirement_spec(curr_node["require"])
            if "shown" in curr_node:
                state["choices"][curr_node["choice"]]["shown_spec"] = utility.parse_requirement_spec(curr_node["shown"])
            if "per_cost" in curr_node:
                state["choices"][curr_node["choice"]]["per_cost_spec"] = utility.parse_requirement_spec(curr_node["per_cost"])
            if "per_require" in curr_node:
                state["choices"][curr_node["choice"]]["per_req_spec"] = utility.parse_requirement_spec(curr_node["per_require"])
            if "per_shown" in curr_node:
                state["choices"][curr_node["choice"]]["per_shown_spec"] = utility.parse_requirement_spec(curr_node["per_shown"])

            def get_effect_address(key):
                effect_address = ""
                if not key in curr_node:
                    if key == "effects":
                        effect_address = addressing.parse_addr(curr_addr, curr_node["choice"])
                    elif key == "alt_effects":
                        effect_address = None
                else:
                    effect_address = curr_addr + (key, 0)
                    if isinstance(curr_node[key], str):
                        effect_address = addressing.parse_addr(curr_addr, curr_node[key])
                return effect_address
            effect_address = get_effect_address("effects")
            alt_effect_address = get_effect_address("alt_effects")

            is_action = False
            if "action" in curr_node:
                is_action = True

            state["choices"][curr_node["choice"]]["text"] = text
            state["choices"][curr_node["choice"]]["address"] = effect_address
            state["choices"][curr_node["choice"]]["alt_address"] = alt_effect_address
            state["choices"][curr_node["choice"]]["missing"] = missing_list
            state["choices"][curr_node["choice"]]["modifications"] = modify_list
            state["choices"][curr_node["choice"]]["choice_address"] = curr_addr
            state["choices"][curr_node["choice"]]["action"] = is_action
    elif "command" in curr_node:
        commands = curr_node["command"].split(";")
        for subcommand in commands:
            state["command_buffer"].append(subcommand.split())
    elif "descriptive" in curr_node:
        # Default to setting that's at least as descriptive
        if state["settings"]["descriptiveness"] == "descriptive":
            if not curr_node["descriptive"] is None:
                do_print(curr_node["descriptive"], state, dont_save_print=dont_save_print)
        elif state["settings"]["descriptiveness"] == "moderate":
            if "moderate" in curr_node:
                if not curr_node["moderate"] is None:
                    do_print(curr_node["moderate"], state, dont_save_print=dont_save_print)
            else:
                if not curr_node["descriptive"] is None:
                    do_print(curr_node["descriptive"], state, dont_save_print=dont_save_print)
        elif state["settings"]["descriptiveness"] == "minimal":
            if "minimal" in curr_node:
                if not curr_node["minimal"] is None:
                    do_print(curr_node["minimal"], state, dont_save_print=dont_save_print)
            elif "moderate" in curr_node:
                if not curr_node["moderate"] is None:
                    do_print(curr_node["moderate"], state, dont_save_print=dont_save_print)
            else:
                if not curr_node["descriptive"] is None:
                    do_print(curr_node["descriptive"], state, dont_save_print=dont_save_print)
    elif "error" in curr_node:
        raise ErrorNode("Error raised.")
    elif "flag" in curr_node:
        state["vars"]["flags"][curr_node["flag"]] = True
    elif "flavor" in curr_node:
        if state["settings"]["show_flavor_text"] != "never" and (state["visits"][curr_addr] <= 1 or state["settings"]["show_flavor_text"] == "always"):
            if isinstance(curr_node["flavor"], str):  # TODO: Allow style spec tag with flavor text
                curr_view.print_flavor_text(curr_node["flavor"], dont_save_print=dont_save_print)
            else:
                addressing.set_curr_addr(curr_addr + ("flavor", 0))

                return True
    elif "gosub" in curr_node:
        sub_address = addressing.parse_addr(curr_addr, curr_node["gosub"])

        # Increment current address so that when we return we don't just go back to the gosub
        state["bookmark"] = addressing.get_next_bookmark(state["bookmark"])

        state["bookmark"] = (sub_address,) + state["bookmark"]

        return True
    elif "goto" in curr_node:
        addressing.set_curr_addr(addressing.parse_addr(curr_addr, curr_node["goto"]))

        return True
    elif "if" in curr_node:
        exception_occurred = False
        condition_value = None  # Bool representing the end condition value
        try:
            condition_value = utility.eval_conditional(curr_node["if"])
        except Exception as e:
            exception_occurred = True
            print(f'Warning, exception "{e}" occurred while evaluating if condition. Skipping if statement.')

        if not exception_occurred:
            if condition_value:
                addressing.set_curr_addr(curr_addr + ("then", 0))

                return True
            elif "else" in curr_node:
                addressing.set_curr_addr(curr_addr + ("else", 0))

                return True
    elif "inject" in curr_node:
        if "into_choices" in curr_node:
            # Check for dict version of into_choices specification first
            choices_to_inject_into = None
            if isinstance(curr_node["into_choices"], dict):
                # Right now, just except is valid, which put it into all choices except the given ones
                if "except" in curr_node["into_choices"]:
                    choices_to_inject_into = list(state["choices"].keys())

                    choices_not_to_inject_into = curr_node["into_choices"]["except"].split()
                    for choice_id in choices_not_to_inject_into:
                        if choice_id in choices_to_inject_into:
                            choices_to_inject_into.remove(choice_id)
            elif isinstance(curr_node["into_choices"], str):
                if curr_node["into_choices"] == "_all":
                    choices_to_inject_into = list(state["choices"].keys())
                else:
                    choices_to_inject_into = curr_node["into_choices"].split()

            position = "before"
            if "position" in curr_node:
                position = curr_node["position"]

            for choice_id in choices_to_inject_into:
                # TODO: Warning when trying to inject into a choice that doesn't exist
                if choice_id in state["choices"]:
                    if not "injections" in state["choices"][choice_id]:
                        state["choices"][choice_id]["injections"] = []
                    state["choices"][choice_id]["injections"].append({"address": addressing.parse_addr(curr_addr, curr_node["inject"]), "position": position})
    elif "insert" in curr_node:
        vars_by_name = utility.collect_vars_with_dicts(state)

        amount = 1
        if "amount" in curr_node and isinstance(curr_node["amount"], (int, float)):
            amount = curr_node["amount"]
        elif "amount" in curr_node and isinstance(curr_node["amount"], str):
            amount = eval(curr_node["amount"], {}, utility.collect_vars(state))

        if not (curr_node["insert"] in vars_by_name[curr_node["into"]]["value"]):
            vars_by_name[curr_node["into"]]["value"][curr_node["insert"]] = {
                "address": vars_by_name[curr_node["into"]]["address"],
                # TODO: Locale!
                "value": 0,
            }
        vars_by_name[curr_node["into"]]["value"][curr_node["insert"]]["value"] += amount
    elif "modify" in curr_node:
        # TODO: Parse-time checks that this is a variable that can be modified (i.e.- it has a value)
        var_to_change = utility.eval_vars(curr_node["modify"])
        old_val = utility.eval_values(curr_node["modify"])
        new_val = None
        if "add" in curr_node:
            new_val = old_val + utility.eval_values(curr_node["add"])
        utility.set_value(var_to_change, new_val)
    elif "move" in curr_node:
        # Make sure to only get the block's address, not its inside instructions
        block_to_move_addr = addressing.parse_addr(curr_addr, curr_node["move"], only_block_part=True)
        # Make sure we're not trying to move the root block
        # TODO: Throw some sort of warning if we try to move the root block
        if block_to_move_addr != ():
            block_to_move = addressing.get_node(block_to_move_addr)
            # Move the block
            new_block_addr = addressing.parse_addr(curr_addr, curr_node["to"], only_block_part=True)
            new_block = addressing.get_node(new_block_addr)
            parent_block = addressing.get_node(block_to_move_addr[:-1])
            del parent_block[block_to_move_addr[-1]]
            new_block[block_to_move_addr[-1]] = block_to_move

            # Update block address stuff
            def reset_node_info(block, old_addr):
                new_addr = new_block_addr + old_addr[len(block_to_move_addr)-1:]
                if old_addr in state["story_data"]["file_homes"]:
                    state["story_data"]["file_homes"].add(new_addr)
                    state["story_data"]["file_homes"].remove(old_addr)
                if old_addr in state["story_data"]["node_types"]:
                    state["story_data"]["node_types"][new_addr] = state["story_data"]["node_types"][old_addr]
                    del state["story_data"]["node_types"][old_addr]

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
                addressing.set_curr_addr(curr_addr)
                # Don't return anything because we actually still need to increment the address            
    elif "once" in curr_node:
        if state["visits"][curr_addr] <= 1:
            if isinstance(curr_node["once"], str):
                do_print(curr_node["once"], state, dont_save_print=dont_save_print)
            else:
                addressing.set_curr_addr(curr_addr + ("once", 0))

                return True
    elif "pass" in curr_node:
        pass
    elif "pop_queue" in curr_node:
        # Pop the first element of the queue that's not the current stack element
        # Useful for injections
        # TODO: Label what parts of the bookmark queue represent (subroutine, injection, header, etc.) and use this to more easily manipulate it
        try:
            state["bookmark"] = state["bookmark"][:1] + state["bookmark"][2:]
        except Exception:
            # If there was out of index error, do nothing
            pass
    elif "print" in curr_node:
        style = None
        if "style" in curr_node:
            style = curr_node["style"]

        do_print(curr_node["print"], state, style, dont_save_print=dont_save_print)
    elif "print_table" in curr_node:
        vars_by_name = utility.collect_vars_with_dicts(state)

        tbl_to_display = vars_by_name[curr_node["print_table"]]["value"]

        curr_view.print_table(tbl_to_display, dont_save_print=dont_save_print)
    elif "print_var" in curr_node:
        curr_view.print_var(curr_node["print_var"])
    elif "random" in curr_node:
        possibilities_list = []

        if isinstance(curr_node["random"], str):
            for id in curr_node["random"].split(","):
                possibilities_list.append(id.strip())

            if len(state["seed"]) > 0:
                # Check if the seed is in the possibilities list
                seed = state["seed"].pop(0)
                if seed in possibilities_list:
                    addressing.set_curr_addr(addressing.parse_addr(curr_addr, seed))
                else:
                    # Feedback messages should already not save
                    curr_view.print_feedback_message("runtime_error_invalid_seed")

                    return False
            else:
                addressing.set_curr_addr(addressing.parse_addr(curr_addr, possibilities_list[random.randint(0, len(possibilities_list) - 1)]))

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
        if len(state["seed"]) > 0:
            seed = state["seed"].pop(0)

            # Can't just use "in" here since possibilities_list is more complex
            is_possible = False
            for possibility in possibilities_list:
                if seed == possibility[1]:
                    is_possible = True
            
            if is_possible:
                if curr_node["random"][seed] is None:
                    addressing.set_curr_addr(addressing.parse_addr(curr_addr, seed))
                else:
                    addressing.set_curr_addr(curr_addr + ("random", seed, 0))

                return True
            else:
                # Feedback messages should already not save
                curr_view.print_feedback_message("runtime_error_invalid_seed")

                return False

        curr_weight = 0
        target_weight = random.uniform(0, total_weight)
        for possibility in possibilities_list:
            curr_weight += possibility[0]
            if curr_weight >= target_weight:
                if curr_node["random"][possibility[1]] is None:
                    addressing.set_curr_addr(addressing.parse_addr(curr_addr, possibility[1].split()[-1]))
                else:
                    addressing.set_curr_addr(curr_addr + ("random", possibility[1], 0))

                return True
    elif "return" in curr_node:
        # TODO: Give warning if call stack is empty
        if len(state["call_stack"]) >= 1:
            stack_state = state["call_stack"].pop()

            state["vars"] = stack_state["vars"]
            state["bookmark"] = stack_state["bookmark"]

            # Don't return true since we need to increment past the call instruction
    elif "run" in curr_node:
        contents = utility.get_var(state["vars"], curr_node["run"], curr_addr)["value"]
        temp_yaml = config.stories / "_temp.yaml"
        temp_yaml.write_bytes(yaml.dump(contents).encode('utf-8'))

        state["msg"]["signal_run_statement"] = True

        state["bookmark"] = addressing.get_next_bookmark(state["bookmark"])

        return False
    elif "seed" in curr_node:
        state["seed"].append(curr_node["seed"])
    elif "send" in curr_node:
        # Just trigger child blocks and current block for now by default
        parent_block_addr = addressing.get_block_part(curr_addr)
        parent_block = addressing.get_node(parent_block_addr)
        for child_block_name, child_block in list(parent_block.items()) + [((), parent_block)]:
            if "_listeners" in child_block:
                for index, listener in enumerate(child_block["_listeners"]):
                    # TODO: Parse listeners beforehand into a dict that's easier/faster to access
                    if "on_receive" in listener and listener["on_receive"] == curr_node["send"]:
                        child_block_addr_name = (child_block_name,)
                        if child_block_name == ():
                            child_block_addr_name = ()
                        state["bookmark"] = state["bookmark"] + (parent_block_addr + child_block_addr_name + ("_listeners", index, "handler", 0),)
    elif "separator" in curr_node:
        curr_view.print_separator(dont_save_print=dont_save_print)
    elif "set" in curr_node:
        text_to_show_spec = {}
        vars_by_name = utility.collect_vars_with_dicts(state)

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

            if modifier == "+":
                if not (last_index is None):
                    last_var_to_modify[last_index] += eval(var_expr_pair[1], {}, utility.collect_vars(state))
                    # TODO: Show some text (in this case it doesn't quite make sense how to refer to the variable
                else:
                    vars_by_name[var_name_indices[0]]["value"] += eval(var_expr_pair[1], {}, utility.collect_vars(state))
                    text_to_show_spec = {"op": "add", "amount": eval(var_expr_pair[1], {}, utility.collect_vars(state)), "var": vars_by_name[var_name_indices[0]]}
            elif modifier == "-":
                if not (last_index is None):
                    last_var_to_modify[last_index] -= eval(var_expr_pair[1], {}, utility.collect_vars(state))
                else:
                    vars_by_name[var_name_indices[0]]["value"] -= eval(var_expr_pair[1], {}, utility.collect_vars(state))
                    text_to_show_spec = {"op": "subtract", "amount": eval(var_expr_pair[1], {}, utility.collect_vars(state)), "var": vars_by_name[var_name_indices[0]]}
            else:
                if not (last_index is None):
                    last_var_to_modify[last_index] = eval(var_expr_pair[1], {}, utility.collect_vars(state))
                else:
                    vars_by_name[var_name_indices[0]]["value"] = eval(var_expr_pair[1], {}, utility.collect_vars(state))
                    text_to_show_spec = {"op": "set", "amount": eval(var_expr_pair[1], {}, utility.collect_vars(state)), "var": vars_by_name[var_name_indices[0]]}
        else:
            if isinstance(curr_node["to"], (int, float)):
                vars_by_name[curr_node["set"]]["value"] = curr_node["to"]  # TODO: Allow setting to string literal values
            else:
                vars_by_name[curr_node["set"]]["value"] = eval(curr_node["to"], {}, utility.collect_vars(state))  # TODO: Catch exceptions in case of syntax errors

        if "show" in curr_node:
            curr_view.print_var_modification(text_to_show_spec, dont_save_print=dont_save_print)
    elif "stop" in curr_node:
        # Need to remove this address now from the queue
        state["bookmark"] = state["bookmark"][1:]

        return False
    elif "storypoint" in curr_node:
        if curr_node["storypoint"] is None:
            state["story_points"][curr_addr] = True
        else:
            state["story_points"][curr_node["storypoint"]] = True
    elif "sub" in curr_node:
        # TODO: Make this interact better with "call"
        # (Right now, they each have their own call stacks that interact noncommutatively with each other)
        
        # Need to get next bookmark so after return we increment past the sub command
        state["sub_stack"] = (addressing.get_next_bookmark(state["bookmark"]),) + state["sub_stack"]
        state["bookmark"] = addressing.make_bookmark((), addressing.parse_addr(curr_addr, curr_node["sub"]))

        return True
    elif "subreturn" in curr_node:
        if len(state["sub_stack"]) == 0:
            # TODO: Throw error in this case, this is where we try to return from a subroutine but we're not in one
            pass
        else:
            state["bookmark"] = state["sub_stack"][0]
            state["sub_stack"] = state["sub_stack"][1:]

            return True
    elif "switch" in curr_node:
        switch_value = eval(curr_node["switch"], {}, utility.collect_vars(state))
        if str(switch_value) in curr_node:
            if isinstance(curr_node[str(switch_value)], str):
                addressing.set_curr_addr(addressing.parse_addr(curr_addr, curr_node[str(switch_value)]))
            else:
                addressing.set_curr_addr(curr_addr + (str(switch_value), 0))

            return True
        elif "_default" in curr_node:
            if isinstance(curr_node["_default"], str):
                addressing.set_curr_addr(curr_node[str(switch_value)])
            else:
                addressing.set_curr_addr(curr_addr + ("_default", 0))

            return True
    elif "tag" in curr_node:
        pass # Tags currently do nothing
    elif "unflag" in curr_node:
        state["vars"]["flags"][curr_node["unflag"]] = False
    else:
        raise UnrecognizedInstruction(f"Unrecognized instruction: {curr_node}")

    state["bookmark"] = addressing.get_next_bookmark(state["bookmark"])

    return True
