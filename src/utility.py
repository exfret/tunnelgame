from string import Formatter

import addressing
from config import state, game

class CustomFormatter(Formatter):
    def get_value(self, key, args, kwargs):
        # TODO: Support nested bags
        if isinstance(key, str) and len(key.split("/")) == 2:
            bag_var = kwargs[key.split("/")[0]]
            var_val = None
            if not key.split("/")[1] in bag_var:
                var_val = 0
            else:
                var_val = bag_var[key.split("/")[1]]["value"]
            return var_val
        else:
            return Formatter.get_value(self, key, args, kwargs)
format = CustomFormatter()

class VarDict(dict):
    def __contains__(self, key: object) -> bool:
        if isinstance(key, str) and len(key.split("__")) == 2:
            bag_name = key.split("__")[0]
            if super().__contains__(bag_name):
                return True # Never raise missing reference for items as long as the bag exists
            else:
                return False
        else:
            return super().__contains__(key)

    def __getitem__(self, key):
        if isinstance(key, str) and len(key.split("__")) == 2:
            bag_var = super().__getitem__(key.split("__")[0])

            if not key.split("__")[1] in bag_var["value"]:
                # TODO: Remove this duplicate "default var creation" code
                bag_var["value"][key.split("__")[1]] = {"address": bag_var["address"], "value": 0, "locale": key.split("__")[1]} # TODO: locale support
            
            return bag_var["value"][key.split("__")[1]]
        else:
            return super().__getitem__(key)
    
    def __setitem__(self, key, value):
        if isinstance(key, str) and len(key.split("__")) == 2:
            bag_var = super().__getitem__(key.split("__")[0])

            if not key.split("__")[1] in bag_var["value"]:
                # TODO: Remove this duplicate "default var creation" code
                bag_var["value"][key.split("__")[1]] = {"address": bag_var["address"], "value": 0, "locale": key.split("__")[1]}
            
            bag_var["value"][key.split("__")[1]]["value"] = value
        else:
            super().__setitem__(key, value)

class VarDictValues(VarDict):
    def __getitem__(self, key):
        var = super().__getitem__(key)

        if isinstance(var, dict) and "value" in var:
            return var["value"]
        else:
            return var

def get_var(var_dict, var_name, curr_address):
    if (curr_address in var_dict) and (var_name in var_dict[curr_address]):
        return var_dict[curr_address][var_name]
    else:
        if curr_address == ():
            raise Exception() # TODO: Make exception more specific (missing reference)

        return get_var(var_dict, var_name, curr_address[:-1])

def collect_vars_with_dicts(state, address = None):
    var_dict = VarDict()

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
    for flag in state["vars"]["flags"]:
        if state["vars"]["flags"][flag]:
            var_dict[flag] = True
        else:
            var_dict[flag] = False
    
    var_dict["_visits"] = state["visits"][address]
    var_dict["_num_choices"] = len(state["choices"])
    var_dict["_address"] = addressing.get_block_part(state["last_address"])
    if len(state["last_address_list"]) >= 1:
        var_dict["_previous_address"] = addressing.get_block_part(state["last_address_list"][-1])
    else:
        var_dict["_previous_address"] = ()
    return var_dict

def collect_vars(state, address = None):
    var_dict = VarDictValues(collect_vars_with_dicts(state, address))

    return var_dict

# TODO: Move to addressing
def get_curr_addr(state):
    # If queue is empty, we're done
    if len(state["bookmark"]) == 0:
        return False
    
    if len(state["bookmark"][0]) == 0:
        state["bookmark"] = state["bookmark"][1:]
        return get_curr_addr(state)

    return state["bookmark"][0][-1]

def localize(var_name, address = None):
    if address is None:
        address = get_curr_addr(state)
    var_dict = collect_vars_with_dicts(state, address)
    var = var_dict[var_name]

    if "locale" in var:
        return var["locale"]
    else:
        return var_name

def parse_requirement_spec(text_spec):
    vars_by_name = collect_vars_with_dicts(state) # I don't think this is used because we don't actually do the eval here

    paren_splits = []
    paren_state = 0
    last_index = 0
    for index, char in enumerate(text_spec):
        if char == "(":
            if paren_state == 0:
                paren_splits.append(text_spec[last_index:index])
                last_index = index
            paren_state += 1
        elif char == ")":
            paren_state -= 1
            if paren_state == 0:
                paren_splits.append(text_spec[last_index:index + 1])
                last_index = index + 1
    paren_splits.append(text_spec[last_index:])

    # Now split by spaces and remove trailing commas
    non_grouped_specs = []
    for paren_split in paren_splits:
        if len(paren_split) > 0 and paren_split[-1] != ")":
            # TODO: From statements for backwards compatibility?
            for substring in paren_split.split():
                if substring[-1] == ",":
                    substring = substring[:-1]
                non_grouped_specs.append(substring)
        else:
            non_grouped_specs.append(paren_split)
    
    # Remove possible initial paren issue
    if non_grouped_specs[0] == "":
        non_grouped_specs = non_grouped_specs[1:]

    grouped_specs = []
    for index, non_grouped_spec in enumerate(non_grouped_specs):
        if index % 2 == 0: # Case of an eval part
            grouped_specs.append({})
            grouped_specs[int(index / 2)]["amount"] = non_grouped_spec
        else: # Case of a var part
            # TODO: Use collect_vars?
            grouped_specs[int(index / 2)]["var"] = non_grouped_spec
    
    return grouped_specs