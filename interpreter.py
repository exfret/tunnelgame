import random
import string
import textwrap

class ErrorNode(Exception):
    pass

class UnrecognizedInstruction(Exception):
    pass

def add_stack(game, state, address, partial_address):
    curr_node = get_instr(game["story"], partial_address)

    if isinstance(curr_node, dict) and "_header" in curr_node:
        state["bookmark"] = state["bookmark"] + ((partial_address + ("_header", 0),),)

def make_bookmark(game, state, address):
    partial_address = ()
    add_stack(game, state, address, partial_address)
    for tag in address:
        partial_address = partial_address + (tag,)
        add_stack(game, state, address, partial_address)

    # Add the _content node
    state["bookmark"] = state["bookmark"] + ((address,),)

# TODO: Change to "get_node"
def get_instr(curr_node, addr):
    if addr == ():
        return curr_node
    
    if isinstance(curr_node, list) and addr[0] >= len(curr_node):
        return False # TODO: Instead throw/catch error

    return get_instr(curr_node[addr[0]], addr[1:]) # TODO: Check map/address compatibility

def get_curr_addr(state):
    # If queue is empty, we're done
    if len(state["bookmark"]) == 0:
        return False
    
    if len(state["bookmark"][0]) == 0:
        state["bookmark"] = state["bookmark"][1:]
        return get_curr_addr(state)

    return state["bookmark"][0][-1]

def set_curr_addr(state, new_addr):
    new_first_stack = state["bookmark"][0][:-1] + (new_addr,)
    new_bookmark = (new_first_stack,) + state["bookmark"][1:]

    state["bookmark"] = new_bookmark

def get_next_addr(game, addr):
    if addr == ():
        return False
    
    # If it's a string key, it's not an incrementable address piece
    if isinstance(addr[-1], str):
        return get_next_addr(game, addr[:-1])

    new_addr = addr[:-1] + ((addr[-1] + 1),) # TODO: Error check that last element is indeed an int

    if get_instr(game["story"], new_addr) == False:
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
    curr_node = get_instr(game["story"], call_stack[0])

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
        return bookmark[1:] # We don't need to increment because in the queue this hasn't been touched at all
    else:
        return bookmark[1:] + (get_next_call_stack(game, bookmark[0]),)

def get_parent_block(game, addr):
    node = get_instr(game["story"], addr)

    is_content = False
    if addr != ():
        parent = get_instr(game["story"], addr[:-1])
        if isinstance(parent, dict):
            for key, val in parent.items():
                if val == node and key == "_content":
                    is_content = True

    if "_type" in node and node["_type"] == "BLOCK":
        return addr
    # Check for list blocks
    # TODO: Make this more elegant, maybe metadate for what's a list and not
    elif (not is_content) and addr != () and isinstance(get_instr(game["story"], addr[:-1]), dict) and ("_type" in get_instr(game["story"], addr[:-1])) and isinstance(node, list):
        return addr
    else:
        return get_parent_block(game, addr[:-1])

def parse_addr(game, curr_addr, addr_id):
    curr_path = tuple(addr_id.split("/"))

    curr_addr = get_parent_block(game, curr_addr)

    for index in curr_path:
        # This usually happens when there is an initial / so go to root
        if index == "":
            curr_addr = ()
        elif index == ".":
            pass
        elif index == "..":
            curr_addr = get_parent_block(game, curr_addr)[:-1]
        else:
            curr_addr = curr_addr + (index,)
    
    if isinstance(get_instr(game["story"], curr_addr), list):
        return curr_addr + (0,)
    
    return curr_addr + ("_content", 0)

def do_print(text, state):
    string_to_print = string.Formatter().vformat(text, (), state["vars"]) # TODO: Exceptions in case of syntax errors
    print(textwrap.fill(string_to_print, 100))
    print()

def do_shown_var_modification(modification, state, symbol):
    amount_to_modify = 0
    modification_var = ""
    if modification.find('(') != -1 and modification.rfind(')') != -1:
        modification_amount_spec = modification[modification.find('(') + 1:modification.rfind(')')]

        amount_to_modify = eval(modification_amount_spec, {}, state["vars"])
        modification_var = modification[modification.rfind(')') + 2:]
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
        symbol = "" # The negative sign already shows up by virtue of it being a negative number
    state["vars"][modification_var] += amount_to_modify
    print("[" + symbol + str(amount_to_modify) + " " + modification_var + "]") # TODO: Add localization

def step(game, state):
    if get_curr_addr(state) == False:
        return False

    curr_node = get_instr(game["story"], get_curr_addr(state))
    # Mark that we've visited this node (again)
    if not (get_curr_addr(state) in state["visits"]):
        state["visits"][get_curr_addr(state)] = 0
    state["visits"][get_curr_addr(state)] += 1

    if isinstance(curr_node, str):
        do_print(curr_node, state)

        state["bookmark"] = get_next_bookmark(game, state["bookmark"])

        return True

    # Since this is an instruction, it must be a map
    # TODO: Verify this part of stories
    if "add" in curr_node:
        do_shown_var_modification(curr_node["add"], state, "+")
    elif "choice" in curr_node:
        missing_list = []
        modify_list = []
        text = ""
        if "text" in curr_node:
            text = curr_node["text"]
        if "cost" in curr_node:
            if text != "":
                text += " "
            text += "\033[0m[\033[31mCost:\033[0m "

            cost_list = curr_node["cost"].split(",")
            for cost in cost_list:
                parsed_cost = cost.split()

                text += parsed_cost[0] + " " + parsed_cost[1] + ", " # TODO: Use localised name of variables

                if state["vars"][parsed_cost[1]] < int(parsed_cost[0]):
                    missing_list.append(parsed_cost[1])
                
                modify_list.append({"var": parsed_cost[1], "amount": -1 * int(parsed_cost[0])})
            # Remove the last comma and space
            text = text[:-2]
            text += "]"

        effect_address = get_curr_addr(state) + ("effects", 0)
        if isinstance(curr_node["effects"], str):
            effect_address = parse_addr(game, get_curr_addr(state), curr_node["effects"])

        state["choices"][curr_node["choice"]] = {"text": text, "address": effect_address, "missing": missing_list, "modifications": modify_list, "choice_address": get_curr_addr(state)}
    elif "error" in curr_node:
        raise ErrorNode("Error raised.")
    elif "flavor" in curr_node:
        if state["settings"]["show_flavor_text"] != "never" and (state["visits"][get_curr_addr(state)] <= 1 or state["settings"]["show_flavor_text"] == "always"):
            if isinstance(curr_node["flavor"], str):
                do_print(curr_node["flavor"], state)
            else:
                set_curr_addr(state, get_curr_addr(state) + ("flavor", 0))

                return True
    elif "goto" in curr_node:
        set_curr_addr(state, parse_addr(game, get_curr_addr(state), curr_node["goto"]))

        return True
    elif "if" in curr_node:
        exception_occurred = False
        try:
            condition = eval(curr_node["if"], {}, state["vars"])
        except Exception as e:
            exception_occurred = True
            print(f"Warning, exception \"{e}\" occurred while evaluating if condition. Skipping if statement.")

        if not exception_occurred:
            if condition:
                set_curr_addr(state, get_curr_addr(state) + ("then", 0))

                return True
            elif "else" in curr_node:
                set_curr_addr(state, get_curr_addr(state) + ("else", 0))

                return True
    elif "lose" in curr_node:
        do_shown_var_modification(curr_node["lose"], state, "-")
    elif "once" in curr_node:
        if state["visits"][get_curr_addr(state)] <= 1:
            if isinstance(curr_node["once"], str):
                do_print(curr_node["once"], state)
            else:
                set_curr_addr(state, get_curr_addr(state) + ("once", 0))

                return True
    elif "pass" in curr_node:
        pass
    elif "print" in curr_node:
        do_print(curr_node["print"], state)

        return True
    elif "random" in curr_node:
        possibilities_list = []
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
                set_curr_addr(state, get_curr_addr(state) + ("random", possibility[1], 0))
                
                return True
    elif "set" in curr_node:
        if isinstance(curr_node["to"], (int, float)):
            state["vars"][curr_node["set"]] = curr_node["to"]
        else:
            state["vars"][curr_node["set"]] = eval(curr_node["to"], {}, state["vars"]) # TODO: Catch exceptions in case of syntax errors
    else:
        raise UnrecognizedInstruction("Unrecognized instruction: " + str(curr_node))

    state["bookmark"] = get_next_bookmark(game, state["bookmark"])

    return True