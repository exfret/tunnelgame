import math
import random
import yaml

from utility import *

import addressing

# TODO: Check addresses in program are valid

class InvalidDisjunctError(Exception):
    pass

class InvalidTagError(Exception):
    pass

class IncorrectTypeError(Exception):
    pass

class GrammarParsingError(Exception):
    pass

class MissingReferenceError(Exception):
    pass

class MissingRequiredTagError(Exception):
    pass

class WrongFormattingError(Exception):
    pass

def add_vars_with_address(game, state, node, address): # TODO: Finish up so that it has the other extra features of vars too
    if isinstance(node, list): # In this case, the inner part of the node is just content
        return

    if not ("vars" in state):
        state["vars"] = {}
    # Run this once
    if address == ():
        # Initialize special vars
        # TODO: _args overhaul, and make it NoneType by default
        state["vars"]["_args"] = [0] * 10000 # TODO: Remove this hardcap on number arguments, and it's also a little silly
    state["vars"][address] = {}

    if "_vars" in node:
        for var in node["_vars"]:
            # Find the var_name/value declaration
            var_name = None
            var_value = None
            locale = None

            num_var_keys = 0
            for key, val in var.items():
                if key[0] != "_":
                    var_name = key
                    var_value = val
                    num_var_keys += 1
                elif "_locale" in var:
                    if not isinstance(var["_locale"], str):
                        raise IncorrectTypeError()
                    locale = var["_locale"]
                elif "_type" in var:
                    if not isinstance(var["_type"], str):
                        raise IncorrectTypeError()
                    if val != "bag": # Bag is the only allowed special type for now
                        raise IncorrectTypeError()
                else:
                    raise InvalidTagError()

            if num_var_keys != 1:
                raise InvalidTagError()

            if locale is None:
                locale = var_name
            
            state["vars"][address][var_name] = {"address": address, "locale": locale, "value": var_value}
    
    # Recurse into all sub-blocks
    for tag, subnode in node.items():
        # Anything that's not a keyword must be a block right now
        if tag[0] != "_":
            add_vars_with_address(game, state, subnode, address + (tag,))

def add_vars(game, state):
    if not ("_vars" in game):
        game["_vars"] = []
        return
    
    if not isinstance(game["_vars"], list):
        raise IncorrectTypeError("VARS is not a list.")

    for var in game["_vars"]:
        if not isinstance(var, dict):
            raise IncorrectTypeError("VAR not a dict")

        var_name = ""
        num_var_keys = 0
        for key, val in var.items(): # TODO: Check that vars have valid names (no leading underscores/name conflicts)
            if key[0] != "_":
                var_name = key
                var_val = val
                num_var_keys += 1
            elif key == "_locale":
                if not isinstance(val, str):
                    raise IncorrectTypeError()
            elif key == "_type":
                if val != "bag": # Bag is the only allowed special type for now
                    raise IncorrectTypeError()
            else:
                raise InvalidTagError()
        if num_var_keys != 1:
            raise InvalidTagError("Extra tags in VAR specification.")
        state["vars"][var_name] = var_val
        # Initialize bags as dicts
        if ("_type" in var) and var["_type"] == "bag" and var_val == None:
            state["vars"][var_name] = {}
    
    # Extra vars
    state["vars"]["_visits"] = 0

def add_module_vars(state):
    # Add special variables
    state["vars"]["random"] = random
    state["vars"]["rand"] = lambda num: random.randint(1, num)
    state["vars"]["math"] = math
    state["vars"]["floor"] = math.floor
    state["vars"]["ceil"] = math.ceil
    state["vars"]["pow"] = math.pow

def remove_module_vars(state):
    del state["vars"]["random"]
    del state["vars"]["rand"]
    del state["vars"]["math"]
    del state["vars"]["floor"]
    del state["vars"]["ceil"]
    del state["vars"]["pow"]

def parse_node(game, node, state, grammar, context, address):
    if not (address in state["metadata"]["node_types"]):
        state["metadata"]["node_types"][address] = {}
    state["metadata"]["node_types"][address][context] = True

    if not (address in state["visits"]):
        state["visits"][address] = 0

    if context == "_addr":
        # Try to access this address to ensure it's valid
        addressing.parse_addr(game, address, node)
    elif context == "_addr_list":
        if not isinstance(node, str):
            raise IncorrectTypeError("Node with context " + context + " is of incorrect type.")
        else:
            for id in node.split(","):
                parse_node(game, id.strip(), state, grammar, "_addr", address)
    elif context == "_complex_value":
        # Any value is possible here, just don't need to recurse deeper
        pass
    elif context == "_expr":
        if isinstance(node, str):
            # Try to eval the node to make sure it works
            # TODO: Add variable sensing
            eval(node, {}, collect_vars(state, address))
        elif isinstance(node, (int, float)):
            return # Plain numerical set
        else:
            raise IncorrectTypeError("Node with context " + context + " is of incorrect type.")
    elif context == "_id":
        if not isinstance(node, str):
            raise IncorrectTypeError()
        
        # Id's can't start with an underscore or have whitespace
        if node[0] == "_" or len(node.split()) != 1:
            raise WrongFormattingError()
    elif context == "_num_expr":
        if isinstance(node, (int, float)):
            pass
        elif isinstance(node, str):
            parse_node(game, node, state, grammar, "_expr", address)
        else:
            raise IncorrectTypeError()
    elif context == "_null":
        if not (node is None):
            raise IncorrectTypeError("Node with context " + context + " is of incorrect type.")
    elif context == "_requirement_specification": # TODO: Rename to '_amount_specification' or something similar
        specs = []
        paren_state = 0
        last_index = 0
        for index, char in enumerate(node):
            if char == "(":
                if paren_state == 0:
                    specs.append(node[last_index:index])
                    last_index = index

                paren_state += 1
            elif char == ")":
                paren_state -= 1
                if paren_state == 0:
                    specs.append(node[last_index:index + 1])
                    last_index = index + 1
        specs.append(node[last_index:])

        real_specs = []
        for spec in specs:
            if len(spec) > 0:
                if spec[-1] != ")":
                    for substring in spec.split(","):
                        for subsubstring in substring.split():
                            real_specs.append(subsubstring)
                else:
                    real_specs.append(spec)
        
        for index, real_spec in enumerate(real_specs):
            if index % 2 == 0:
                if real_spec[-1] == ")":
                    parse_node(game, real_spec, state, grammar, "_expr", address)
                else:
                    real_spec_split = real_spec.split("-")

                    if len(real_spec_split) == 1:
                        try:
                            float(real_spec_split[0])
                        except ValueError:
                            raise IncorrectTypeError("Non-numerical string for requirement amount.")
                    elif len(real_spec_split) == 2: # TODO: Error on requirements/costs
                        try:
                            float(real_spec_split[0])
                            float(real_spec_split[1])
                        except ValueError:
                            raise IncorrectTypeError("Non-numerical string for requirement amount.")
                    else:
                        raise WrongFormattingError("Wrong number of -'s in requirement amount.")
            elif index % 2 == 1:
                if not (real_spec in collect_vars(state, address)):
                    raise MissingReferenceError("Referenced variable not declared.")
    elif context == "_set_expr":
        if not isinstance(node, str):
            raise IncorrectTypeError() # TODO: Convert IncorrectTypeError exceptions to more useful format
        
        var_expr_pair = node.split("=")

        if len(var_expr_pair) == 1 and (var_expr_pair[0] in collect_vars(state, address)):
            return
        elif len(var_expr_pair) != 2:
            print(address)
            raise WrongFormattingError()

        var_name_indices = var_expr_pair[0]
        if var_name_indices[-1] == "+":
            var_name_indices = var_name_indices[:-1].strip().split("[")
        elif var_name_indices[-1] == "-":
            var_name_indices = var_name_indices[:-1].strip().split("[")
        else:
            var_name_indices = var_name_indices.split("[")
        
        if not (var_name_indices[0] in collect_vars(state, address)):
            raise MissingReferenceError()
        
        # NOTE: No checking for array length yet!
        
        parse_node(game, var_expr_pair[1], state, grammar, "_expr", address)
    elif context == "_table_id":
        # First check it's a valid variable reference
        parse_node(game, node, state, grammar, "_var_id", address)

        var_referenced = collect_vars(state, address)[node]["value"]
        if not isinstance(var_referenced, list):
            raise IncorrectTypeError()
        for row in var_referenced:
            if not isinstance(row, list):
                raise IncorrectTypeError
            for col in row:
                # Check that this is a valid (non-list) value
                parse_node(game, col, state, grammar, "_value", address)
    elif context == "_text":
        if not isinstance(node, str):
            print(address)
            raise IncorrectTypeError()
    elif context == "_value":
        if not isinstance(node, (str, int, bool, float)):
            raise IncorrectTypeError("Node with context " + context + " is of incorrect type.")
    elif context == "_var_id":
        if not isinstance(node, str):
            raise IncorrectTypeError()
        if not node in collect_vars(state, address):
            raise MissingReferenceError()
    elif context == "_var_type":
        if node != "bag": # Bag is the only current var type
            # TODO: Unify this code with the checking in var creation
            raise IncorrectTypeError()
    elif context[0] == "_":
        raise GrammarParsingError("Node with incorrect terminal context " + context)
    
    # Return if this is just a terminal node
    if context[0] == "_":
        return

    if not (context in grammar):
        GrammarParsingError("Undefined context " + context)

    curr_rule = grammar[context]

    # First, check the type of the node
    if curr_rule["type"] == "dict":
        if not isinstance(node, dict):
            raise IncorrectTypeError("Node with context " + context + " is of incorrect type.")
        
        if "mandatory" in curr_rule:
            for mandatory_key in curr_rule["mandatory"].keys():
                if not mandatory_key in node:
                    raise MissingRequiredTagError("Node with context " + context + " is missing required tag: " + mandatory_key)
        for key, val in node.items():
            if "mandatory" in curr_rule and key in curr_rule["mandatory"]:
                parse_node(game, node[key], state, grammar, curr_rule["mandatory"][key], address + (key,))
            elif "optional" in curr_rule and key in curr_rule["optional"]:
                parse_node(game, node[key], state, grammar, curr_rule["optional"][key], address + (key,))
            elif "other" in curr_rule:
                parse_node(game, node[key], state, grammar, curr_rule["other"], address + (key,))
            else:
                print(address)
                raise InvalidTagError("Node with context " + context + " has invalid tag: " + key)
    elif curr_rule["type"] == "list":
        if not isinstance(node, list):
            raise IncorrectTypeError("Node with context " + context + " is of incorrect type.")
        
        for index, element in enumerate(node):
            parse_node(game, element, state, grammar, curr_rule["elements"], address + (index,))
    elif curr_rule["type"] == "union":
        could_be_parsed = False
        for member in curr_rule["members"]:
            try:
                parse_node(game, node, state, grammar, member, address)
                could_be_parsed = True
                break
            except Exception as e:
                continue
        if not could_be_parsed:
            raise InvalidDisjunctError("Could not instantiate union node of type " + context + " as any of its member types.")
    elif curr_rule["type"] == "union_with_keys":
        could_be_parsed = False
        for key, context in curr_rule["contexts"].items():
            if key in node:
                # In this case, we've parsed it as multiple different things
                if could_be_parsed:
                    raise InvalidDisjunctError()
                
                parse_node(game, node, state, grammar, context, address)
                could_be_parsed = True

        # In this case, it couldn't be parsed as anything
        if not could_be_parsed:
            print(address)
            raise InvalidDisjunctError()
    elif curr_rule["type"] == "union_with_types":
        if "list" in curr_rule and isinstance(node, list):
            parse_node(game, node, state, grammar, curr_rule["list"], address)
        elif "dict" in curr_rule and isinstance(node, dict):
            parse_node(game, node, state, grammar, curr_rule["dict"], address)
        elif "str" in curr_rule and isinstance(node, str):
            parse_node(game, node, state, grammar, curr_rule["str"], address)
        elif "num" in curr_rule and isinstance(node, (int, float)):
            parse_node(game, node, state, grammar, curr_rule["num"], address)
        elif "null" in curr_rule and node is None:
            parse_node(game, node, state, grammar, curr_rule["null"], address)
        else:
            raise InvalidDisjunctError()
    else:
        GrammarParsingError("Invalid type key for grammar rule.")
    
    # Special checking
    if context == "CHOICE":
        if not ("effects" in node): # If effects doesn't exist, this should be an address
            parse_node(game, node["choice"], state, grammar, "_addr", address)
    # TODO: Special checking for SET to check that if the set is just a single var name we need a TO

def parse(game, state):
    with open(
        "/Users/kylehess/Documents/programs/tunnelgame/grammar.yaml", "r"
    ) as file:
        grammar = yaml.safe_load(file)
    
    parse_node(game, game, state, grammar, "START", ())
