import yaml
import random

from tunnelvision import addressing, gameparser, utility
from tunnelvision.config import stories


class ErrorNode(Exception):
    pass


class UnrecognizedInstruction(Exception):
    pass


def add_stack(game, state, address, partial_address):
    curr_node = get_instr(game, partial_address)

    if isinstance(curr_node, dict) and "_header" in curr_node:
        state["bookmark"] = state["bookmark"] + ((partial_address + ("_header", 0),),)


def make_bookmark(game, state, address, injections = []):
    partial_address = ()
    add_stack(game, state, address, partial_address)
    for tag in address:
        partial_address = partial_address + (tag,)
        add_stack(game, state, address, partial_address)

    for inj in injections:
        state["bookmark"] = state["bookmark"] + ((inj,),)

    # Add the actual instruction we're going to
    state["bookmark"] = state["bookmark"] + ((address,),)


# TODO: Change to "get_node"
def get_instr(curr_node, addr):
    if addr == ():
        return curr_node

    if isinstance(curr_node, list) and addr[0] >= len(curr_node):
        return False  # TODO: Instead throw/catch error

    return get_instr(curr_node[addr[0]], addr[1:])  # TODO: Check map/address compatibility


def set_curr_addr(state, new_addr):
    new_first_stack = state["bookmark"][0][:-1] + (new_addr,)
    new_bookmark = (new_first_stack,) + state["bookmark"][1:]

    state["bookmark"] = new_bookmark


def get_next_addr(game, addr):
    if addr == ():
        return False

    # If it's a string key, it's not an incrementable address piece
    if isinstance(addr[-1], str):
        if addr[-1] == "effects":  # If it's a choice effects section, don't spill over into the remaining block
            return False
        return get_next_addr(game, addr[:-1])

    new_addr = addr[:-1] + ((addr[-1] + 1),)  # TODO: Error check that last element is indeed an int

    if get_instr(game, new_addr) == False:
        return get_next_addr(game, addr[:-1])
    else:
        return new_addr


def trim_footer(addr):
    if addr == ():
        return True

    if addr[-1] == "_footer":
        if len(addr) == 1:
            return False

        return addr[:-2]
    else:
        return trim_footer(addr[:-1])


def search_for_footers(game, call_stack):
    curr_node = get_instr(game, call_stack[0])

    if isinstance(curr_node, dict) and "_footer" in curr_node:
        return (call_stack[0] + ("_footer", 0),)
    else:
        if call_stack[0] == ():
            return ()

        return search_for_footers(game, (call_stack[0][:-1],))


def get_next_call_stack(game, call_stack):
    if call_stack == ():
        return False

    if get_next_addr(game, call_stack[-1]) == False:
        # If this is the last part of the call stack, check for footers to execute
        if len(call_stack) == 1:
            trimmed = trim_footer(call_stack[0])
            if trimmed == True:
                trimmed = call_stack[0]
            elif trimmed == False:
                return False

            return search_for_footers(game, (trimmed,))

        return get_next_call_stack(game, call_stack[:-1])
    else:
        return call_stack[:-1] + (get_next_addr(game, call_stack[-1]),)


def get_next_bookmark(game, bookmark):
    if bookmark == ():
        return False

    if get_next_call_stack(game, bookmark[0]) == False:
        return bookmark[1:]  # We don't need to increment because in the queue this hasn't been touched at all
    else:
        return bookmark[1:] + (get_next_call_stack(game, bookmark[0]),)


# Note: Duplicate code, also in addressing
def get_parent_block(game, addr, state):
    node = get_instr(game, addr)

    is_content = False
    if addr != ():
        parent = get_instr(game, addr[:-1])
        if isinstance(parent, dict):
            for key, val in parent.items():
                if val == node and key == "_content":
                    is_content = True

    node_types = state["metadata"]["node_types"][addr]  # TODO: Remove backwards compatibility quirk (need to add "story" to address)
    if "START" in node_types or "BLOCK" in node_types:
        return addr
    # Check for list blocks
    # TODO: Make this more elegant, maybe metadate for what's a list and not
    elif (not is_content) and addr != () and isinstance(get_instr(game, addr[:-1]), dict) and ("_type" in get_instr(game, addr[:-1])) and isinstance(node, list):
        return addr
    else:
        return get_parent_block(game, addr[:-1], state)


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
    if utility.get_curr_addr(state) == False:
        return False

    parent_block = get_parent_block(game, utility.get_curr_addr(state), state)
    # Don't save footer addresses
    if len(parent_block) == 0 or parent_block[-1] != "_footer":
        state["last_address"] = utility.get_curr_addr(state)

    curr_node = get_instr(game, utility.get_curr_addr(state))
    # Mark that we've visited this node (again)
    if not (utility.get_curr_addr(state) in state["visits"]):
        state["visits"][utility.get_curr_addr(state)] = 0
    state["visits"][utility.get_curr_addr(state)] += 1

    if isinstance(curr_node, str):
        do_print(curr_node, state)

        state["bookmark"] = get_next_bookmark(game, state["bookmark"])

        return True

    # Since this is an instruction, it must be a map
    # TODO: Verify this part of stories
    if "add" in curr_node:
        try:
            do_shown_var_modification(curr_node["add"], state, "+", game)
        except Exception:
            # Just move on and do nothing if we get an exception, and print warning
            print(f"WARNING: Exception occurred evaluating 'ADD' node at address {utility.get_curr_addr(state)}")
    elif "back" in curr_node:
        while True:
            if len(state["last_address_list"]) == 0:
                break

            new_addr = get_parent_block(game, state["last_address_list"].pop(), state)

            # Don't count footers
            if get_parent_block(game, state["last_address"], state) != new_addr:
                parent_node = get_instr(game, new_addr)

                if isinstance(parent_node, list):
                    new_addr = new_addr + (0,)
                else:
                    new_addr = new_addr + ("_content", 0)

                set_curr_addr(state, new_addr)

                return True
    elif "call" in curr_node:
        # TODO: Implement global/local vars that persist or don't persist after calls
        # Right now no variables persist after calls
        state["call_stack"].append({"bookmark": state["bookmark"], "vars": state["vars"]})

        curr_addr = utility.get_curr_addr(state)
        state["bookmark"] = ()
        make_bookmark(game, state, addressing.parse_addr(curr_addr, curr_node["call"]))

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
        if not "selectable_once" in curr_node or not utility.get_curr_addr(state) in state["visits_choices"] or state["visits_choices"][utility.get_curr_addr(state)] == 0:
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
                effect_address = addressing.parse_addr(utility.get_curr_addr(state), curr_node["choice"])
            else:
                effect_address = utility.get_curr_addr(state) + ("effects", 0)
                if isinstance(curr_node["effects"], str):
                    effect_address = addressing.parse_addr(utility.get_curr_addr(state), curr_node["effects"])

            is_action = False
            if "action" in curr_node:
                is_action = True

            state["choices"][curr_node["choice"]]["text"] = text
            state["choices"][curr_node["choice"]]["address"] = effect_address
            state["choices"][curr_node["choice"]]["missing"] = missing_list
            state["choices"][curr_node["choice"]]["modifications"] = modify_list
            state["choices"][curr_node["choice"]]["choice_address"] = utility.get_curr_addr(state)
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
        if state["settings"]["show_flavor_text"] != "never" and (state["visits"][utility.get_curr_addr(state)] <= 1 or state["settings"]["show_flavor_text"] == "always"):
            if isinstance(curr_node["flavor"], str):  # TODO: Allow style spec tag with flavor text
                view.print_flavor_text(curr_node["flavor"])
            else:
                set_curr_addr(state, utility.get_curr_addr(state) + ("flavor", 0))

                return True
    elif "gosub" in curr_node:
        sub_address = addressing.parse_addr(utility.get_curr_addr(state), curr_node["gosub"])

        new_first_stack = state["bookmark"][0] + (sub_address,)
        new_bookmark = (new_first_stack,) + state["bookmark"][1:]

        state["bookmark"] = new_bookmark

        return True
    elif "goto" in curr_node:
        set_curr_addr(state, addressing.parse_addr(utility.get_curr_addr(state), curr_node["goto"]))

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
                set_curr_addr(state, utility.get_curr_addr(state) + ("then", 0))

                return True
            elif "else" in curr_node:
                set_curr_addr(state, utility.get_curr_addr(state) + ("else", 0))

                return True
    elif "inject" in curr_node:
        if "into_choices" in curr_node:
            choices_to_inject_into = curr_node["into_choices"].split()
            for choice_id in choices_to_inject_into:
                if choice_id in state["choices"]:
                    if not "injections" in state["choices"][choice_id]:
                        state["choices"][choice_id]["injections"] = []
                    state["choices"][choice_id]["injections"].append(addressing.parse_addr(utility.get_curr_addr(state), curr_node["inject"]))
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
    elif "lose" in curr_node:
        try:
            do_shown_var_modification(curr_node["lose"], state, "-", game)
        except Exception:
            print(f"WARNING: Exception occurred evaluating 'LOSE' node at address {utility.get_curr_addr(state)}")
    elif "once" in curr_node:
        if state["visits"][utility.get_curr_addr(state)] <= 1:
            if isinstance(curr_node["once"], str):
                do_print(curr_node["once"], state)
            else:
                set_curr_addr(state, utility.get_curr_addr(state) + ("once", 0))

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

            set_curr_addr(state, addressing.parse_addr(utility.get_curr_addr(state), possibilities_list[random.randint(0, len(possibilities_list) - 1)]))

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
                    set_curr_addr(state, addressing.parse_addr(utility.get_curr_addr(state), possibility[1].split()[-1]))
                else:
                    set_curr_addr(state, utility.get_curr_addr(state) + ("random", possibility[1], 0))

                return True
    elif "return" in curr_node:
        # TODO: Give warning if call stack is empty
        if len(state["call_stack"]) >= 1:
            stack_state = state["call_stack"].pop()

            state["vars"] = stack_state["vars"]
            state["bookmark"] = stack_state["bookmark"]

            # Don't return true since we need to increment past the call instruction
    elif "run" in curr_node:
        addr = utility.get_curr_addr(state)
        contents = utility.get_var(state["vars"], curr_node["run"], addr)["value"]
        temp_yaml = stories / "temp.yaml"
        temp_yaml.write_bytes(yaml.dump(contents).encode('utf-8'))

        state["msg"]["signal_run_statement"] = True

        state["bookmark"] = get_next_bookmark(game, state["bookmark"])

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
        return False
    elif "switch" in curr_node:
        switch_value = eval(curr_node["switch"], {}, utility.collect_vars(state))
        if str(switch_value) in curr_node:
            if isinstance(curr_node[str(switch_value)], str):
                set_curr_addr(state, addressing.parse_addr(utility.get_curr_addr(state), curr_node[str(switch_value)]))
            else:
                set_curr_addr(state, utility.get_curr_addr(state) + (str(switch_value), 0))

            return True
        elif "_default" in curr_node:
            if isinstance(curr_node["_default"], str):
                set_curr_addr(state, addressing.parse_addr(utility.get_curr_addr(state), curr_node[str(switch_value)]))
            else:
                set_curr_addr(state, utility.get_curr_addr(state) + ("_default", 0))

            return True
    else:
        raise UnrecognizedInstruction(f"Unrecognized instruction: {curr_node}")

    state["bookmark"] = get_next_bookmark(game, state["bookmark"])

    return True
