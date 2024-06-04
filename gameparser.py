import math
import random
import yaml

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

def story_verify(node, context, state):
    if context == "ADD":
        if not isinstance(node["add"], str):
            raise IncorrectTypeError("Node of type ADD_SPECIFICATION is not a string.")
        # TODO: Check that the add specification value is correctly formatted
        for tag, val in node.items():
            if tag == "add":
                new_var = val.split()[1]
                if not (new_var in state["vars"]):
                    state["vars"][new_var] = 0 # Initialize to 0
            else:
                raise InvalidTagError("Unrecognized tag.")
    elif context == "BLOCK":
        # If this is a list, this is actually just a _content
        if isinstance(node, list):
            story_verify(node, "CONTENT", state)

            return

        if not isinstance(node, dict):
            raise IncorrectTypeError("Node of type BLOCK is not a dict.")
        for tag, val in node.items():
            if tag == "_actions": # TODO: Remove
                story_verify(val, "ACTIONS", state)
            elif tag == "_content":
                story_verify(val, "CONTENT", state)
            elif tag == "_footer":
                story_verify(val, "CONTENT", state)
            elif tag == "_header":
                story_verify(val, "CONTENT", state)
            elif len(tag) > 0 and tag[0] != "_":
                story_verify(val, "BLOCK", state)
            else:
                raise InvalidTagError("Invalid tag " + tag + " in BLOCK type.")
        
        # Add block type decorator
        node["_type"] = "BLOCK"
    elif context == "CHOICE":
        if not isinstance(node, dict):
            raise IncorrectTypeError("Node of type CHOICE is not a dict.")
        
        # Fill in effects tag if there is none
        if not ("effects" in node):
            node["effects"] = node["choice"]
        
        # Verify all tags are valid
        for tag, val in node.items():
            if tag == "choice":
                if not isinstance(val, str): # TODO: Make sure no spaces and such
                    raise IncorrectTypeError("Node of type CHOICE_ID is of incorrect type.")
            elif tag == "effects":
                if isinstance(val, str): # TODO: Check that this is a valid goto address
                    pass
                else:
                    story_verify(val, "CONTENT", state)
            elif tag == "cost":
                if not isinstance(val, str):
                    raise IncorrectTypeError("Node of type COST_EFFECT is of incorrect type.")
                # TODO: Check that this is a valid int - var combination list
            elif tag == "text":
                if not isinstance(val, str):
                    raise IncorrectTypeError("Node of type TEXT is of incorrect type.")
            else:
                raise InvalidTagError("Urecognized tag in node of type CHOICE.")
    elif context == "CONTENT":
        if not isinstance(node, list):
            raise IncorrectTypeError("Node of type CONTENT is not a list.")
        for instr in node:
            if isinstance(instr, str):
                continue # Allow plain strings as print statements

            if not isinstance(instr, dict):
                raise IncorrectTypeError("Node of type INSTRUCTION is not a dict.")
            
            if "add" in instr:
                story_verify(instr, "ADD", state)
            elif "choice" in instr:
                story_verify(instr, "CHOICE", state)
            elif "error" in instr:
                story_verify(instr, "ERROR", state)
            elif "flavor" in instr:
                # Do flavor verification here since it's simple

                if isinstance(instr["flavor"], list):
                    story_verify(instr["flavor"], "CONTENT", state)
                elif isinstance(instr["flavor"], str):
                    pass
                else:
                    IncorrectTypeError("Node of type FLAVOR_VAL is not of type CONTENT or STRING.")
                
                for tag, val in instr.items():
                    if tag != "flavor":
                        raise InvalidTagError("Tag other than 'flavor' in node of type FLAVOR")
            elif "goto" in instr:
                story_verify(instr, "GOTO", state)
            elif "if" in instr:
                story_verify(instr, "IF", state)
            elif "lose" in instr:
                story_verify(instr, "LOSE", state)
            elif "once" in instr:
                # Do once verification here since it's simple

                if isinstance(instr["once"], list):
                    story_verify(instr["once"], "CONTENT", state)
                elif isinstance(instr["once"], str):
                    pass
                else:
                    raise IncorrectTypeError("Node of type ONCE_VAL is not of type CONTENT or STRING.")
                
                for tag, val in instr.items():
                    if tag != "once":
                        raise InvalidTagError("Tag other than 'once' in node of type ONCE")
            elif "pass" in instr:
                story_verify(instr, "PASS", state)
            elif "print" in instr:
                story_verify(instr, "PRINT", state)
            elif "random" in instr:
                # Do random verification here since it's simple

                if not isinstance(instr["random"], dict):
                    raise IncorrectTypeError("Node of type RANDOM_EVENTS is not of type DICT.")
                
                for val in instr["random"].values():
                    story_verify(val, "CONTENT", state)
            elif "set" in instr:
                story_verify(instr, "SET", state)
            else:
                raise InvalidTagError("Node of type INSTRUCTION with unrecognized tags: " + str(instr)) # TODO: Probably should be an InvalidDisjunctError not InvalidTagError?
    elif context == "IF":
        # TODO: Finish this
        if "then" in node:
            story_verify(node["then"], "CONTENT", state)
        if "else" in node:
            story_verify(node["else"], "CONTENT", state)
    elif context == "LOSE":
        # TODO: Un-duplicate this code from 'ADD' case

        if not isinstance(node["lose"], str):
            raise IncorrectTypeError("Node of type LOSE_SPECIFICATION is not a string.")
        # TODO: Check that the lose specification value is correctly formatted
        for tag, val in node.items():
            if tag == "lose":
                new_var = val.split()[1]
                if not (new_var in state["vars"]):
                    state["vars"][new_var] = 0 # Initialize to 0
            else:
                raise InvalidTagError("Unrecognized tag.")
    elif context == "PASS":
        if not isinstance(node, dict):
            raise IncorrectTypeError("Node of type PASS is not a dict.")
        
        for tag, val in node.items():
            if tag == "pass":
                if not (val is None):
                    raise IncorrectTypeError("Node of type PASS_VAL is not of type None.")
            else:
                raise InvalidTagError("Node of type PASS with unrecognized tags: " + str(node))
    # TODO: Finish

def add_vars(game, state):
    if not ("vars" in game):
        game["vars"] = []
        return
    
    if not isinstance(game["vars"], list):
        raise IncorrectTypeError("VARS is not a list.")

    for var in game["vars"]:
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
            else:
                raise InvalidTagError()
        if num_var_keys != 1:
            raise InvalidTagError("Extra tags in VAR specification.")
        state["vars"][var_name] = var_val
    
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
            eval(node, {}, state["vars"])
        else:
            raise IncorrectTypeError("Node with context " + context + " is of incorrect type.")
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
                if not (real_spec in state["vars"]):
                    raise MissingReferenceError("Referenced variable not declared.")
    elif context == "_set_expr":
        if not isinstance(node, str):
            raise IncorrectTypeError() # TODO: Convert IncorrectTypeError exceptions to more useful format
        
        var_expr_pair = node.split("=")

        if len(var_expr_pair) != 2:
            raise WrongFormattingError()

        var_name_indices = var_expr_pair[0]
        if var_name_indices[-1] == "+":
            var_name_indices = var_name_indices[:-1].strip().split("[")
        elif var_name_indices[-1] == "-":
            var_name_indices = var_name_indices[:-1].strip().split("[")
        else:
            var_name_indices = var_name_indices.split("[")
        
        if not (var_name_indices[0] in state["vars"]):
            print(state["vars"])

            raise MissingReferenceError()
        
        # NOTE: No checking for array length yet!
        
        parse_node(game, var_expr_pair[1], state, grammar, "_expr", address)
    elif context == "_table_id":
        # First check it's a valid variable reference
        parse_node(game, node, state, grammar, "_var_id", address)

        var_referenced = state["vars"][node]
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
        if not node in state["vars"]:
            raise MissingReferenceError()
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

def parse(game, state):
    with open(
        "/Users/kylehess/Documents/programs/tunnelgame/grammar.yaml", "r"
    ) as file:
        grammar = yaml.safe_load(file)
    
    parse_node(game, game, state, grammar, "START", ())

def verify(game, state):
    # Check for story tag
    if not ("story" in game):
        raise MissingRequiredTagError("'story' tag missing at game root.")
    # For compatibility reasons, change any root "_start" to "_content"
    if "_start" in game["story"]:
        if "_content" in game["story"]:
            raise InvalidTagError("Can only have one of _start or _content in story root.")
        game["story"]["_content"] = game["story"]["_start"]
        del game["story"]["_start"]
    if not ("_content" in game["story"]):
        raise MissingRequiredTagError("Story has no root content.")
    
    # Check nodes via depth-first search
    story_verify(game["story"], "BLOCK", state)

def init_vars(game, state):
    if not ("vars" in game):
        game["vars"] = {}
    
    for var in game["vars"]:
        unique_item = {}
        for key, val in var.items():
            unique_item = {"key": key, "val": val}
        state["vars"][unique_item["key"]] = unique_item["val"]
    
    # Add libraries (TODO: exception/warning if any of these are attempted to be overriden by a var)
    state["vars"]["random"] = random
    state["vars"]["math"] = math

    # Initialize _args
    state["vars"]["_args"] = []