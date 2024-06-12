def get_var(var_dict, var_name, curr_address):
    if (curr_address in var_dict) and (var_name in var_dict[curr_address]):
        return var_dict[curr_address][var_name]
    else:
        if curr_address == ():
            raise Exception() # TODO: Make exception more specific (missing reference)

        return get_var(var_dict, var_name, curr_address[:-1])

# TODO: Make this not duplicate code and move all into addressing (it's also in interpreter.py right now)
def get_curr_addr(state):
    # If queue is empty, we're done
    if len(state["bookmark"]) == 0:
        return False
    
    if len(state["bookmark"][0]) == 0:
        state["bookmark"] = state["bookmark"][1:]
        return get_curr_addr(state)

    return state["bookmark"][0][-1]

def collect_vars_with_dicts(state, address = None):
    var_dict = {}

    if address is None:
        address = get_curr_addr(state)

    for ind in range(len(address)):
        addr_to_check = address[:ind]
        if addr_to_check in state["vars"]:
            new_vars_dict = state["vars"][addr_to_check]

            for var_name, var_spec in new_vars_dict.items():
                var_dict[var_name] = var_spec
    
    # Add module vars/other special vars
    for ind, val in state["vars"].items():
        if not isinstance(ind, tuple):
            var_dict[ind] = val
    
    var_dict["_visits"] = state["visits"][address]
    return var_dict

def collect_vars(state, address = None):
    var_dict = collect_vars_with_dicts(state, address)
    new_var_dict = var_dict

    for key, val in var_dict.items():
        # Hacky way to test if this is actually an addressed var
        # TODO: Make this less hacky
        if isinstance(val, dict) and ("value" in val):
            new_var_dict[key] = val["value"]

    return new_var_dict