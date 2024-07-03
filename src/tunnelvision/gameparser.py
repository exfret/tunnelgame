import ast
import copy
import math
import random
import yaml

from tunnelvision import addressing
from tunnelvision.config import grammar, stories
from tunnelvision.utility import *  # TODO: Make it not import *, use proper namespace

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


class UndefinedVariableChecker(ast.NodeVisitor):
    def visit_Name(self, node):
        if node.id not in self.var_dict and node.id not in __builtins__:
            raise MissingReferenceError(f"{node.id} not in var_dict: {self.var_dict}")
        self.generic_visit(node)

    def check(self, expression, var_dict):
        try:
            tree = ast.parse(expression, mode="eval")
        except Exception:
            print(f"\033[31mError:\033[0m Parsing error at for expression {expression}")
            raise WrongFormattingError()
        self.var_dict = var_dict
        self.visit(tree)


expr_checker = UndefinedVariableChecker()


def open_game(game_name):
    game.clear()
    state.clear()
    contents = yaml.safe_load((stories / game_name).read_text())
    game.update(contents)

    starting_state = {
        "bookmark": (),  # bookmark is a queue (tuple) of call stacks (tuples) containing addresses (tuples)
        "call_stack": [],  # List of dicts with bookmarks and vars (TODO: Maybe do last_address_list and choices here too?)
        "command_buffer": [],
        "choices": {
            "start": {"text": "Start the game", "address": ("_content", 0)},
        },  # Dict of choice ID's to new locations and descriptions
        "displayed_text": "",
        "file_data": {
            "filename": "",
        },  # TODO: Include some sort of hash or name of game
        "last_address": (),
        "last_address_list": [],
        "macros": {},
        "map": {},  # TODO: What was map again? I think it was the game object, probably need to implement this
        "metadata": {
            "node_types": {},
        },  # TODO: Rename to 'story_data' or something such, maybe remove after parsing overhaul
        "msg": {},  # Hacky way for things to communicate to gameloop
        "settings": {
            "show_flavor_text": "once",
        },
        "vars": {},
        "visits": {},
    }
    state.update(copy.deepcopy(starting_state))


def construct_game(node):
    if "_include" in node:
        for block_name, file_name in node["_include"].items():
            subgame = yaml.safe_load((stories / file_name).read_text())
            node[block_name] = copy.deepcopy(subgame)
    if not "_meta" in node:
        node["_meta"] = {}

    for key, subnode in node.items():
        if isinstance(subnode, dict) and not key[0] == "_":  # Only recurse into sub-blocks
            construct_game(subnode)  # Note: This can result in exponentially long games with the right setups...
            # TODO: Smarter stitching that does not just duplicate everything


def expand_macros(node):
    def add_footers(node, footer):
        for key, subnode in node.items():
            # If this is a terminal block or _content node
            if (key == "_content" or key[0] != "_") and isinstance(subnode, list):
                subnode.extend(footer)
            if isinstance(subnode, dict):
                add_footers(subnode, footer)

    if isinstance(node, list):
        for subnode in node:
            expand_macros(subnode)
    elif isinstance(node, dict):
        for key, subnode in node.items():
            if key == "_footer":
                add_footers(node, subnode)
            else:
                expand_macros(subnode)
        if "_footer" in node:
            del node["_footer"]


def add_flags(node):
    if not "flags" in state["vars"]:
        state["vars"]["flags"] = {}

    if isinstance(node, list):
        for subnode in node:
            add_flags(subnode)
    elif isinstance(node, dict):
        for key, subnode in node.items():
            if key == "flag":
                state["vars"]["flags"][subnode] = False

            add_flags(subnode)


def add_vars_with_address(game, state, node, address):  # TODO: Finish up so that it has the other extra features of vars too
    if isinstance(node, list):  # In this case, the inner part of the node is just content
        return

    # Run this once
    if address == ():
        # Initialize special vars
        # TODO: _args overhaul, and make it NoneType by default
        state["vars"]["_args"] = [0] * 10000  # TODO: Remove this hardcap on number arguments, and it's also a little silly
    if not address in state["vars"]:
        state["vars"][address] = {}

    if not isinstance(node, dict):
        print("\033[31mError:\033[0m Block is not of type dict at {address} node {node}")
        raise IncorrectTypeError()
    if "_vars" in node:
        for var in node["_vars"]:
            # Find the var_name/value declaration
            var_name = None
            var_value = None
            global_value = False
            locale = None

            num_var_keys = 0
            for key, val in var.items():
                if key[0] != "_":
                    var_name = key
                    var_value = val
                    num_var_keys += 1
                elif key == "_global":
                    if not var["_global"] is None:
                        print(f"\033[31mError:\033[0m _global is not of type null at {address} node {node}")
                        raise IncorrectTypeError()
                    global_value = True
                elif key == "_locale":
                    if not isinstance(var["_locale"], str):
                        print(f"\033[31mError:\033[0m _locale is not of type string at {address} node {node}")
                        raise IncorrectTypeError()
                    locale = var["_locale"]
                elif key == "_type":
                    if not isinstance(var["_type"], str):
                        print(f"\033[31mError:\033[0m _type is not of type string at {address} node {node}")
                        raise IncorrectTypeError()
                    if val != "bag" and val != "map" and val != "grid":  # These are the only allowed special types for now
                        print(f"\033[31mError:\033[0m _type has invalid value at {address} node {node}")
                        raise IncorrectTypeError()
                elif key in ["_fill", "_dims"]:  # Extra keys
                    pass
                else:
                    print(f"\033[31mError:\033[0m Invalid special var tag address {address} node {node}")
                    raise InvalidTagError()

            if num_var_keys != 1:
                print(f"\033[31mError:\033[0m More than one var specified at {address} node {node}")
                raise InvalidTagError()

            if locale is None:
                locale = var_name

            # Initialize bags as dicts
            if ("_type" in var) and var["_type"] == "bag" and var_value == None:
                var_value = {}
            elif ("_type" in var) and var["_type"] == "map":
                pass  # TODO: Any special parsing to be done?
            elif ("_type" in var) and var["_type"] == "grid":
                if not "_dims" in var:
                    print(f"\033[31mError:\033[0m Missing required tag _dims at {address} node {node}")
                    raise MissingRequiredTagError()
                elif not "_fill" in var:
                    print(f"\033[31mError:\033[0m Missing required tag _fill at {address} node {node}")
                    raise MissingRequiredTagError()  # TODO: Have a default fill?

                dims = var["_dims"].split()
                for ind, dim in enumerate(dims):
                    dims[ind] = int(dim)

                def get_arrs(curr_ind, dims):
                    if len(curr_ind) == len(dims):
                        return var["_fill"]

                    curr_arr = []
                    for i in range(dims[len(curr_ind)]):
                        curr_arr.append(get_arrs(curr_ind + (i,), dims))

                    return curr_arr

                curr_ind = () * len(dims)
                arr = get_arrs(curr_ind, dims)

            state["vars"][address][var_name] = {"address": address, "locale": locale, "value": var_value, "global": global_value}

    # Recurse into all sub-blocks
    for tag, subnode in node.items():
        # Anything that's not a keyword must be a block right now
        if tag[0] != "_":
            add_vars_with_address(game, state, subnode, address + (tag,))


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


def parse_node(node, context, address):
    if not (address in state["metadata"]["node_types"]):
        state["metadata"]["node_types"][address] = {}
    state["metadata"]["node_types"][address][context] = True

    if not (address in state["visits"]):
        state["visits"][address] = 0

    if context == "_addr":
        # Try to access this address to ensure it's valid
        addressing.parse_addr(address, node)
    elif context == "_addr_list":
        if not isinstance(node, str):
            print(f"\033[31mError:\033[0m _addr_list is not of type string at {address} node {node}")
            raise IncorrectTypeError()
        else:
            for id in node.split(","):
                parse_node(id.strip(), "_addr", address)
    elif context == "_complex_value":
        # Any value is possible here, just don't need to recurse deeper
        pass
    elif context == "_expr":
        if isinstance(node, str):
            # Try to eval the node to make sure it works
            # TODO: Add variable sensing
            if not "no_parse_eval" in game["_meta"]:  # TODO: Local _meta tags repected
                expr_checker.check(node, collect_vars(state, address))
        elif isinstance(node, (int, float)):
            return  # Plain numerical expression
        else:
            print(f"\033[31mError:\033[0m _expr is neither a numerical or string type at {address} node {node}")
            raise IncorrectTypeError()
    elif context == "_id":
        if not isinstance(node, str):
            print(f"\033[31mError:\033[0m _id is not of type string at {address} node {node}")
            raise IncorrectTypeError()

        # Id's can't start with an underscore or have whitespace
        if node[0] == "_" or len(node.split()) != 1:
            print(f"\033[31mError:\033[0m Id's can't start with an underscore or have whitespace at {address} node {node}")
            raise WrongFormattingError()
    elif context == "_num_expr":  # TODO: Is there a difference between this and _expr?
        if isinstance(node, (int, float)):
            pass
        elif isinstance(node, str):
            parse_node(node, "_expr", address)
        else:
            print(f"\033[31mError:\033[0m _num_expr is neither of type numerical or string at {address} node {node}")
            raise IncorrectTypeError()
    elif context == "_null":
        if not (node is None):
            print(f"\033[31mError:\033[0m Null type expected at {address} node {node}")
            raise IncorrectTypeError()
    elif context == "_requirement_specification":  # TODO: Rename to '_amount_specification' or something similar
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
                    specs.append(node[last_index : index + 1])
                    last_index = index + 1
        specs.append(node[last_index:])

        real_specs = []
        for spec in specs:
            if len(spec) > 0:
                if spec[-1] != ")":
                    for substring in spec.split(","):
                        if len(substring.split("from")) == 2:
                            # Case of a 'from' statement, keep the part with the "from", i.e. - the last 3 "words"
                            real_specs.append(substring.split(" ", 1)[0])
                            real_specs.append(substring.split(" ", 1)[1])
                        else:
                            for subsubstring in substring.split():
                                real_specs.append(subsubstring)
                else:
                    real_specs.append(spec)

        for index, real_spec in enumerate(real_specs):
            if index % 2 == 0:
                if real_spec[-1] == ")":
                    parse_node(real_spec, "_expr", address)
                else:
                    real_spec_split = real_spec.split("-")

                    if len(real_spec_split) == 1:
                        try:
                            float(real_spec_split[0])
                        except ValueError:
                            print(f"\033[31mError:\033[0m Non numerical string for requirement amount at {address} node {node}")
                            raise IncorrectTypeError()
                    elif len(real_spec_split) == 2:  # TODO: Error on requirements/costs
                        try:
                            float(real_spec_split[0])
                            float(real_spec_split[1])
                        except ValueError:
                            print(f"\033[31mError:\033[0m Non numerical string for requirement amount at {address} node {node}")
                            raise IncorrectTypeError()
                    else:
                        print(f"\033[31mError:\033[0m Wrong number of -'s in requirement amount at {address} node {node}")
                        raise WrongFormattingError()
            elif index % 2 == 1:
                if len(real_spec.split("from")) > 1:
                    if not real_spec.split(" from ")[-1] in collect_vars(state, address):
                        print(f"\033[31mError:\033[0m Undefined variable {real_spec.split(' from ')[-1]} at {address} node {node}")
                        raise MissingReferenceError()  # Here, just check for bag's existence
                elif not (real_spec in collect_vars(state, address)):
                    print(f"\033[31mError:\033[0m Undefined variable {real_spec} at {address} node {node}")
                    raise MissingReferenceError()
    elif context == "_set_expr":
        if not isinstance(node, str):
            print(f"\033[31mError:\033[0m Expected string for _set_expression at {address} node {node}")
            raise IncorrectTypeError()  # TODO: Convert IncorrectTypeError exceptions to more useful format

        var_expr_pair = node.split("=")

        if len(var_expr_pair) == 1 and (var_expr_pair[0] in collect_vars(state, address)):
            return
        elif len(var_expr_pair) != 2:
            print(f"\033[31mError:\033[0m Incorrect formatting of _set_expr at {address} node {node}")
            raise WrongFormattingError()

        var_name_indices = var_expr_pair[0]
        if var_name_indices[-1] == "+":
            var_name_indices = var_name_indices[:-1].strip().split("[")
        elif var_name_indices[-1] == "-":
            var_name_indices = var_name_indices[:-1].strip().split("[")
        else:
            var_name_indices = var_name_indices.strip().split("[")

        if not (var_name_indices[0] in collect_vars(state, address)):
            print(f"\033[31mError:\033[0m Undefined variable {var_name_indices[0]} at {address} node {node}")
            raise MissingReferenceError()

        # NOTE: No checking for array length yet!

        parse_node(var_expr_pair[1].strip(), "_expr", address)
    elif context == "_table_id":
        # First check it's a valid variable reference
        parse_node(node, "_var_id", address)

        var_referenced = collect_vars_with_dicts(state, address)[node]["value"]
        if not isinstance(var_referenced, list):
            print(f"\033[31mError:\033[0m Non-list table specified at {address} node {node}")
            raise IncorrectTypeError()
        for row in var_referenced:
            if not isinstance(row, list):
                print(f"\033[31mError:\033[0m Non-list table row specified at {address} node {node}")
                raise IncorrectTypeError()
            for col in row:
                # Check that this is a valid (non-list) value
                parse_node(col, "_value", address)
    elif context == "_text":
        if not isinstance(node, str):
            print(f"\033[31mError:\033[0m String expected for _text value at {address} node {node}")
            raise IncorrectTypeError()
    elif context == "_value":
        if not isinstance(node, (str, int, bool, float)):
            print(f"\033[31mError:\033[0m Expected string/numerical/bool value at {address} node {node}")
            raise IncorrectTypeError(f"Node with context {context} is of incorrect type.")
    elif context == "_var_id":
        if not isinstance(node, str):
            print(f"\033[31mError:\033[0m Expected string value at {address} node {node}")
            raise IncorrectTypeError()
        if not node in collect_vars(state, address):
            print(f"\033[31mError:\033[0m Undefined variable {node} at {address} node {node}")
            raise MissingReferenceError()
    elif context == "_var_type":
        if node != "bag" and node != "map" and node != "grid":  # Bag, map, and grid are the only current var types
            # TODO: Unify this code with the checking in var creation
            print(f"\033[31mError:\033[0m Disallowed value of _var_type at {address} node {node}")
            raise IncorrectTypeError()
    elif context[0] == "_":
        print(f"\033[31mError:\033[0m Specification of incorrect terminal context {context} at {address} node {node}")
        raise GrammarParsingError()

    # Return if this is just a terminal node
    if context[0] == "_":
        return

    if not (context in grammar):
        print(f"\033[31mError:\033[0m Undefined context {context} at {address} node {node}")
        raise GrammarParsingError()

    curr_rule = grammar[context]

    # First, check the type of the node
    if curr_rule["type"] == "dict":
        if not isinstance(node, dict):
            print(f"\033[31mError:\033[0m Expected dict node at {address} node {node}")
            raise IncorrectTypeError()

        if "mandatory" in curr_rule:
            for mandatory_key in curr_rule["mandatory"].keys():
                if not mandatory_key in node:
                    print(f"\033[31mError:\033[0m Missing required tag {mandatory_key} at {address} node {node}")
                    raise MissingRequiredTagError()
        for key, val in node.items():
            if "mandatory" in curr_rule and key in curr_rule["mandatory"]:
                parse_node(
                    node[key],
                    curr_rule["mandatory"][key],
                    address + (key,),
                )
            elif "optional" in curr_rule and key in curr_rule["optional"]:
                parse_node(
                    node[key],
                    curr_rule["optional"][key],
                    address + (key,),
                )
            elif "other" in curr_rule:
                parse_node(node[key], curr_rule["other"], address + (key,))
            else:
                print(f"\033[31mError:\033[0m Invalid tag {key} at address {address} node {node}")
                raise InvalidTagError()
    elif curr_rule["type"] == "list":
        if not isinstance(node, list):
            print(f"\033[31mError:\033[0m Expected list node at {address} node {node}")
            raise IncorrectTypeError()

        for index, element in enumerate(node):
            parse_node(element, curr_rule["elements"], address + (index,))
    elif curr_rule["type"] == "union":
        could_be_parsed = False
        for member in curr_rule["members"]:
            try:
                parse_node(node, member, address)
                could_be_parsed = True
                break
            except Exception as e:
                continue
        if not could_be_parsed:
            print(f"\033[31mError:\033[0m Invalid Disjunct at address {address} node {node}")
            raise InvalidDisjunctError(f"Could not instantiate union node of type {context} as any of its member types.")
    elif curr_rule["type"] == "union_with_keys":
        could_be_parsed = False
        for key, context in curr_rule["contexts"].items():
            if key in node:
                # In this case, we've parsed it as multiple different things
                if could_be_parsed:
                    print(f"\033[31mError:\033[0m Ambiguous Disjunct at address {address} node {node}")
                    raise InvalidDisjunctError()

                parse_node(node, context, address)
                could_be_parsed = True

        # In this case, it couldn't be parsed as anything
        if not could_be_parsed:
            print(f"\033[31mError:\033[0m Invalid Disjunct at address {address} node {node}")
            raise InvalidDisjunctError()
    elif curr_rule["type"] == "union_with_types":
        if "list" in curr_rule and isinstance(node, list):
            parse_node(node, curr_rule["list"], address)
        elif "dict" in curr_rule and isinstance(node, dict):
            parse_node(node, curr_rule["dict"], address)
        elif "str" in curr_rule and isinstance(node, str):
            parse_node(node, curr_rule["str"], address)
        elif "num" in curr_rule and isinstance(node, (int, float)):
            parse_node(node, curr_rule["num"], address)
        elif "null" in curr_rule and node is None:
            parse_node(node, curr_rule["null"], address)
        else:
            raise InvalidDisjunctError()
    else:
        print(f"\033[31mError:\033[0m Invalid 'type' key for grammar rule {context} while parsing at {address} node {node}")
        raise GrammarParsingError()

    # Special checking
    if context == "CHOICE":
        if not ("effects" in node):  # If effects doesn't exist, this should be an address
            if node["choice"] == "_back":
                # Special indicator for "back" choice, fill in the syntactic sugar
                # TODO: Maybe figure out a way to do this without modifying game?
                node["choice"] = "back"
                node["effects"] = [{"back": None}]
                parse_node(node["effects"], "CONTENT", address + ("effects",))
            else:
                parse_node(node["choice"], "_addr", address)
    # TODO: Special checking for SET to check that if the set is just a single var name we need a TO


def parse_game():
    parse_node(game, "START", ())
