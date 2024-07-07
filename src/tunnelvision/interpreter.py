import yaml
import random

from tunnelvision import addressing, gameparser, utility
from tunnelvision.config import stories


class ErrorNode(Exception):
    pass


class UnrecognizedInstruction(Exception):
    pass


def do_print(text, state, style={}):  # TODO: Move ansi code handling to view as well
    view.print_text(text, style)


def do_shown_var_modification(modification, state, symbol, game):  # TODO: Remove... Only used for "add" and "lose", which are defunct
    amount_to_modify = 0
    modification_var = ""
    if modification.find("(") != -1 and modification.rfind(")") != -1:
        modification_amount_spec = modification[modification.find("(") + 1 : modification.rfind(")")]

        amount_to_modify = eval(modification_amount_spec, {}, utility.collect_vars(state))
        modification_var = modification[modification.rfind(")") + 2 :]
    else:
        modification_specification = modification.split()
        modification_amount_spec = modification_specification[0].split("-")
        if len(modification_amount_spec) == 1:
            amount_to_modify = int(modification_amount_spec[0])
        else:
            amount_to_modify = random.randint(int(modification_amount_spec[0]), int(modification_amount_spec[1]))
        modification_var = modification_specification[1]

    # Check if we're actually losing this amount
    if symbol == "-":
        amount_to_modify *= -1
        symbol = ""  # The negative sign already shows up by virtue of it being a negative number

    vars_by_name = utility.collect_vars_with_dicts(state)
    vars_by_name[modification_var]["value"] += amount_to_modify
    print(f"[{symbol}{amount_to_modify} {utility.localize(modification_var)}]")


def eval_conditional(game, state, node):
    vars_by_name = utility.collect_vars_with_dicts(state)

    if isinstance(node, str):
        return eval(node, {}, utility.collect_vars(state))
    elif isinstance(node, list):  # Lists are automatically ANDS, unless they're part of an OR tag covered later
        condition = True
        for subnode in node:
            if not eval_conditional(game, state, subnode):
                return False
        return True
    elif isinstance(node, dict):
        if "has" in node:
            bag = vars_by_name[node["in"]]["value"]
            amount = 1
            if "amount" in node:
                amount = node["amount"]

            if node["has"] in bag and bag[node["has"]] >= amount:
                return True
            else:
                return False
        elif "or" in node:
            for subnode in node["or"]:
                if eval_conditional(game, state, subnode):
                    return True
            return False


def step(game, state):
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

    if isinstance(curr_node, str):
        do_print(curr_node, state)

        state["bookmark"] = addressing.get_next_bookmark(state["bookmark"])

        return True

    # Since this is an instruction, it must be a map
    # TODO: Verify this part of stories
    if False and "add" in curr_node: # TODO: Remove
        try:
            do_shown_var_modification(curr_node["add"], state, "+", game)
        except Exception:
            # Just move on and do nothing if we get an exception, and print warning
            print(f"WARNING: Exception occurred evaluating 'ADD' node at address {curr_addr}")
    elif "back" in curr_node:
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
        addressing.make_bookmark(addressing.parse_addr(curr_addr, curr_node["call"]))

        state["vars"] = {}
        gameparser.add_flags(game)
        gameparser.add_vars_with_address(game, state, game, ())
        gameparser.add_module_vars(state)

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

            effect_address = ""
            if not "effects" in curr_node:
                effect_address = addressing.parse_addr(curr_addr, curr_node["choice"])
            else:
                effect_address = curr_addr + ("effects", 0)
                if isinstance(curr_node["effects"], str):
                    effect_address = addressing.parse_addr(curr_addr, curr_node["effects"])

            is_action = False
            if "action" in curr_node:
                is_action = True

            state["choices"][curr_node["choice"]]["text"] = text
            state["choices"][curr_node["choice"]]["address"] = effect_address
            state["choices"][curr_node["choice"]]["missing"] = missing_list
            state["choices"][curr_node["choice"]]["modifications"] = modify_list
            state["choices"][curr_node["choice"]]["choice_address"] = curr_addr
            state["choices"][curr_node["choice"]]["action"] = is_action
    elif "command" in curr_node:
        commands = curr_node["command"].split(";")
        for subcommand in commands:
            state["command_buffer"].append(subcommand.split())
    elif "error" in curr_node:
        raise ErrorNode("Error raised.")
    elif "flag" in curr_node:
        state["vars"]["flags"][curr_node["flag"]] = True
    elif "flavor" in curr_node:
        if state["settings"]["show_flavor_text"] != "never" and (state["visits"][curr_addr] <= 1 or state["settings"]["show_flavor_text"] == "always"):
            if isinstance(curr_node["flavor"], str):  # TODO: Allow style spec tag with flavor text
                view.print_flavor_text(curr_node["flavor"])
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
            condition_value = eval_conditional(game, state, curr_node["if"])
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
            choices_to_inject_into = curr_node["into_choices"].split()
            for choice_id in choices_to_inject_into:
                if choice_id in state["choices"]:
                    if not "injections" in state["choices"][choice_id]:
                        state["choices"][choice_id]["injections"] = []
                    state["choices"][choice_id]["injections"].append(addressing.parse_addr(curr_addr, curr_node["inject"]))
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
    elif False and "lose" in curr_node: # TODO: Remove!
        try:
            do_shown_var_modification(curr_node["lose"], state, "-", game)
        except Exception:
            print(f"WARNING: Exception occurred evaluating 'LOSE' node at address {curr_addr}")
    elif "modify" in curr_node:
        # TODO: Parse-time checks that this is a variable that can be modified (i.e.- it has a value)
        var_to_change = utility.eval_vars(curr_node["modify"])
        old_val = utility.eval_values(curr_node["modify"])
        new_val = None
        if "add" in curr_node:
            new_val = old_val + utility.eval_values(curr_node["add"])
        utility.set_value(var_to_change, new_val)
    elif "once" in curr_node:
        if state["visits"][curr_addr] <= 1:
            if isinstance(curr_node["once"], str):
                do_print(curr_node["once"], state)
            else:
                addressing.set_curr_addr(curr_addr + ("once", 0))

                return True
    elif "pass" in curr_node:
        pass
    elif "print" in curr_node:
        style = None
        if "style" in curr_node:
            style = curr_node["style"]

        do_print(curr_node["print"], state, style)
    elif "print_table" in curr_node:
        vars_by_name = utility.collect_vars_with_dicts(state)

        tbl_to_display = vars_by_name[curr_node["print_table"]]["value"]

        view.print_table(tbl_to_display)
    elif "random" in curr_node:
        possibilities_list = []

        if isinstance(curr_node["random"], str):
            for id in curr_node["random"].split(","):
                possibilities_list.append(id.strip())

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
        temp_yaml = stories / "temp.yaml"
        temp_yaml.write_bytes(yaml.dump(contents).encode('utf-8'))

        state["msg"]["signal_run_statement"] = True

        state["bookmark"] = addressing.get_next_bookmark(state["bookmark"])

        return False
    elif "separator" in curr_node:
        view.print_separator()
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
            view.print_var_modification(text_to_show_spec)
    elif "stop" in curr_node:
        # Need to remove this address now from the queue
        state["bookmark"] = state["bookmark"][1:]

        return False
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
    elif "unflag" in curr_node:
        state["vars"]["flags"][curr_node["unflag"]] = False
    else:
        raise UnrecognizedInstruction(f"Unrecognized instruction: {curr_node}")

    state["bookmark"] = addressing.get_next_bookmark(state["bookmark"])

    return True
