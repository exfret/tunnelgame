import ast
import copy
import math
import random
import yaml


from engine.gamestate import GameState, LineData
from engine.config import Config
from engine.addressing import Addressing
from engine.utility import Utility


# TODO: Check addresses in program are valid


class InvalidDisjunctError(Exception):
    pass


class InvalidTagError(Exception):
    pass


class InvalidValueError(Exception):
    pass


class IncorrectStructureError(Exception):
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
    def __init__(self):
        self.curr_address = ()

    def visit_Name(self, node):
        if node.id not in self.var_dict and node.id not in __builtins__:
            print(f"\033[31mError:\033[0m Missing reference for var \"{node.id}\" at address {self.curr_address}")
            raise MissingReferenceError()
        self.generic_visit(node)

    def check(self, expression, var_dict, address):
        self.curr_address = address
        try:
            tree = ast.parse(expression, mode="eval")
        except Exception:
            print(f"\033[31mError:\033[0m Parsing error for expression at address {address} with value {expression}")
            raise WrongFormattingError()
        self.var_dict = var_dict
        self.visit(tree)


class GameParser:
    gamestate : GameState
    config : Config
    addressing : Addressing
    utility : Utility


    def __init__(self, gamestate, config, addressing, utility, grammar):
        self.gamestate = gamestate
        self.config = config
        self.addressing = addressing
        self.utility = utility

        self.expr_checker = UndefinedVariableChecker()
        self.grammar = grammar
    

    def open_game(self, story_path):
        self.gamestate.reset()
        contents = yaml.safe_load(story_path.read_text())
        self.gamestate.game = contents
    

    def construct_game(self, node, story_path, address=()):
        if "_include" in node:
            for block_name, file_name in node["_include"].items():
                subgame = yaml.safe_load((story_path.parent / file_name).read_text())
                node[block_name] = copy.deepcopy(subgame)
                self.gamestate.game_data.file_homes[address + (block_name,)] = True
        if not "_meta" in node:
            node["_meta"] = {}

        # Need to do manual world checking since we populate state["world"] at parsetime
        # TODO: Finish implementing object system... not sure where to go with this, currently just parses
        if "_world" in node:
            if not isinstance(node["_world"], list):
                print(f"\033[31mError:\033[0m _world is not instance of list at {address} node {node}")
                raise IncorrectTypeError()
            for detail in node["_world"]:
                if not isinstance(detail, dict):
                    print(f"\033[31mError:\033[0m DETAIL is not instance of dict at {address} node {node}")
                    raise IncorrectTypeError()
                if "object" in detail:
                    if not isinstance(detail["object"], str):
                        print(f"\033[31mError:\033[0m OBJECT_ID is not instance of str at {address} node {node}")
                        raise IncorrectTypeError()
                    # TODO: World in gamestate
                    #self.gamestate.state["world"]["objects"][detail["object"]] = {"notes": [], "descriptors": [], "relationships": []}
                    #curr = self.gamestate.state["world"]["objects"][detail["object"]]

                    # Don't check for extraneous tags here when it's too much hassle, we can have the grammar do that
                    if "_notes" in detail:
                        if not isinstance(detail["_notes"], list):
                            print(f"\033[31mError:\033[0m OBJECT_NOTES is not instance of list at {address} node {node}")
                            raise IncorrectTypeError()
                        for note in detail["_notes"]:
                            if not isinstance(note, str):
                                print(f"\033[31mError:\033[0m OBJECT_NOTE is not instance of str at {address} node {node}")
                                raise IncorrectTypeError()
                            #curr["notes"].append(note)
                    if "_descriptors" in detail:
                        if not isinstance(detail["_descriptors"], list):
                            print(f"\033[31mError:\033[0m OBJECT_DESCRIPTORS is not instance of list at {address} node {node}")
                            raise IncorrectTypeError()
                        for descriptor in detail["_descriptors"]:
                            if not isinstance(descriptor, str):
                                print(f"\033[31mError:\033[0m OBJECT_DESCRIPTOR is not instance of str at {address} node {node}")
                                raise IncorrectTypeError()
                            #curr["descriptors"].append(descriptor)
                    if "_relationships" in detail:
                        if not isinstance(detail["_relationships"], list):
                            print(f"\033[31mError:\033[0m OBJECT_RELATIONSHIP is not instance of list at {address} node {node}")
                            raise IncorrectTypeError()
                        for relationship in detail["_relationships"]:
                            if not isinstance(relationship, dict):
                                print(f"\033[31mError:\033[0m OBJECT_RELATIONSHIP is not instance of dict at {address} node {node}")
                                raise IncorrectTypeError()
                            if not "by" in relationship or not "to" in relationship:
                                print(f"\033[31mError:\033[0m OBJECT_RELATIONSHIP has missing tags {address} node {node}")
                                raise MissingRequiredTagError()
                            if len(relationship) > 2:
                                print(f"\033[31mError:\033[0m OBJECT_RELATIONSHIP has invalid tags at {address} node {node}")
                                raise InvalidTagError()
                            if not isinstance(relationship["by"], str) or not isinstance(relationship["to"], str):
                                print(f"\033[31mError:\033[0m Incorrect type for 'by' or 'to' tag in RELATIONSHIP at {address} node {node}")
                                raise IncorrectTypeError()
                            #curr["relationships"].append({"by": relationship["by"], "to": relationship["to"]})
                elif "descriptor" in detail:
                    if not isinstance(detail["descriptor"], str):
                        print(f"\033[31mError:\033[0m DESCRIPTOR is not instance of str at {address} node {node}")
                        raise IncorrectTypeError()
                    # TODO: World in gamestate
                    #self.gamestate.state["world"]["objects"][detail["descriptor"]] = {}
                elif "relationship" in detail:
                    if not isinstance(detail["relationship"], str):
                        print(f"\033[31mError:\033[0m RELATIONSHIP is not instance of str at {address} node {node}")
                        raise IncorrectTypeError()
                    # TODO: World in gamestate
                    #self.gamestate.state["world"]["objects"][detail["relationship"]] = {}
                else:
                    print(f"\033[31mError:\033[0m Invalid DETAIL disjunct at {address} node {node}")
                    raise InvalidDisjunctError()

        for key, subnode in node.items():
            if not key[0] == "_":  # Only recurse into sub-blocks
                # Turn this block into a dict block if it isn't already
                if isinstance(subnode, list):
                    node[key] = {"_content": subnode}
                else:
                    self.construct_game(subnode, story_path, address + (key,))  # Note: This can result in exponentially long games with the right setups...
                    # TODO: Smarter stitching that does not just duplicate everything
    

    def expand_macros(self, node):
        def add_footers(node, footer):
            for key, subnode in node.items():
                # If this is a terminal block or _content node
                if (key == "_content" or key[0] != "_") and isinstance(subnode, list):
                    subnode.extend(footer)
                if isinstance(subnode, dict):
                    add_footers(subnode, footer)

        if isinstance(node, list):
            for subnode in node:
                self.expand_macros(subnode)
        elif isinstance(node, dict):
            for key, subnode in node.items():
                if key == "_footer":
                    add_footers(node, subnode)
                else:
                    self.expand_macros(subnode)
            if "_footer" in node:
                del node["_footer"]

    
    def add_flags(self, node):
        if not "flags" in self.gamestate.bulk.vars:
            self.gamestate.bulk.vars["flags"] = {}

        if isinstance(node, list):
            for subnode in node:
                self.add_flags(subnode)
        elif isinstance(node, dict):
            for key, subnode in node.items():
                if key == "flag":
                    self.gamestate.bulk.vars["flags"][subnode] = False

                self.add_flags(subnode)
    
    def add_vars_with_address(self, node, address, default_hide=False):  # TODO: Finish up so that it has the other extra features of vars too
        if isinstance(node, list):  # In this case, the inner part of the node is just content
            return

        # Run this once
        if address == ():
            # Initialize special vars
            self.gamestate.bulk.vars["_args"] = self.utility.get_args_list()
        if not address in self.gamestate.bulk.vars:
            self.gamestate.bulk.vars[address] = {}

        # Change the value of default_hide if needed
        if "_meta" in node and "hidden_by_default" in node["_meta"]:
            if not isinstance(node["_meta"]["hidden_by_default"], bool):
                print(f"\033[31mError:\033[0m hidden_by_default is not of type bool at {address} node {node}")
                raise IncorrectTypeError()
            default_hide = node["_meta"]["hidden_by_default"]

        if not isinstance(node, dict):
            print("\033[31mError:\033[0m Block is not of type dict at {address} node {node}")
            raise IncorrectTypeError()
        if "_vars" in node:
            for var in node["_vars"]:
                # Find the var_name/value declaration
                var_name = None
                var_value = None
                global_value = False
                hidden_value = default_hide
                locale = None
                possible_values = None

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
                    elif key == "_hidden":
                        if var["_hidden"] is not None and not var["_hidden"] in {True, False, "nonzero"}:
                            print(f"\033[31mError:\033[0m _hidden is not a valid value at {address} node {node}")
                            raise IncorrectTypeError()
                        if var["_hidden"] == None:
                            hidden_value = True
                        else:
                            hidden_value = var["_hidden"]
                    elif key == "_locale":
                        if not isinstance(var["_locale"], str) and not isinstance(var["_locale"], dict):
                            print(f"\033[31mError:\033[0m _locale is not of type string or dict at {address} node {node}")
                            raise IncorrectTypeError()
                        locale = var["_locale"]
                    elif key == "_possible_values":
                        if not isinstance(var["_possible_values"], list):
                            print(f"\033[31mError:\033[0m _possible_values is not of type list at {address} node {node}")
                            raise IncorrectTypeError()
                        for value in var["_possible_values"]:
                            # Check that values are terminal nodes
                            if not isinstance(value, str) and not isinstance(value, bool) and not isinstance(value, int) and not isinstance(value, str):
                                print(f"\033[31mError:\033[0m A possible value is not of terminal type at {address} node {node}")
                                raise IncorrectTypeError()
                            possible_values = var["_possible_values"]
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
                    # TODO: Figure out what's missing for grid type now
                    var_value = get_arrs(curr_ind, dims)

                # TODO: When adding properties to vars, need to also update the default var for ArgsList in utility.py
                self.gamestate.bulk.vars[address][var_name] = {"address": address, "locale": locale, "possible_values": possible_values, "value": var_value, "global": global_value, "hidden": hidden_value}

        # Recurse into all sub-blocks
        for tag, subnode in node.items():
            # Anything that's not a keyword must be a block right now
            if tag[0] != "_":
                self.add_vars_with_address(subnode, address + (tag,))
    
    def add_module_vars(self):
        # Add special variables
        self.gamestate.bulk.vars["random"] = random
        self.gamestate.bulk.vars["rand"] = lambda num: random.randint(1, num)
        self.gamestate.bulk.vars["math"] = math
        self.gamestate.bulk.vars["floor"] = math.floor
        self.gamestate.bulk.vars["ceil"] = math.ceil
        self.gamestate.bulk.vars["pow"] = math.pow


    def remove_module_vars(self):
        del self.gamestate.bulk.vars["random"]
        del self.gamestate.bulk.vars["rand"]
        del self.gamestate.bulk.vars["math"]
        del self.gamestate.bulk.vars["floor"]
        del self.gamestate.bulk.vars["ceil"]
        del self.gamestate.bulk.vars["pow"]


    def parse_node(self, node, context, address):
        if not (address in self.gamestate.game_data.node_contexts):
            self.gamestate.game_data.node_contexts[address] = {}
        self.gamestate.game_data.node_contexts[address][context] = True

        if not (address in self.gamestate.bulk.per_line):
            self.gamestate.bulk.per_line[address] = LineData(address)

        if context == "_addr":
            # TODO: Make local _meta tags respected here too
            if not "no_addr_eval" in self.gamestate.game["_meta"]:
                # Try to access this address to ensure it's valid
                self.addressing.parse_addr(address, node)
        elif context == "_addr_list":
            if not isinstance(node, str):
                print(f"\033[31mError:\033[0m _addr_list is not of type string at {address} node {node}")
                raise IncorrectTypeError()
            else:
                for id in node.split(","):
                    self.parse_node(id.strip(), "_addr", address)
        elif context == "_bool":
            if not isinstance(node, bool):
                print(f"\033[31mError:\033[0m _bool is not of type bool at {address} node {node}")
                raise IncorrectTypeError()
        elif context == "_complex_value":
            # Any value is possible here, just don't need to recurse deeper
            pass
        elif context == "_expr":
            if isinstance(node, str):
                # Try to eval the node to make sure it works
                # TODO: Add variable sensing
                if not "no_parse_eval" in self.gamestate.game["_meta"]: # TODO: Make local _meta tags repected
                    self.expr_checker.check(node, self.utility.collect_vars(address), address)
            elif isinstance(node, (int, float)):
                return  # Plain numerical expression
            else:
                print(f"\033[31mError:\033[0m _expr is neither a numerical or string type at {address} node {node}")
                raise IncorrectTypeError()
        elif context == "_hidden_config":
            if node is not None and not isinstance(node, str | bool):
                print(f"\033[31mError:\033[0m _hidden_config is not of type bool or string at {address} node {node}")
                raise IncorrectTypeError()
            
            if node not in {None, True, False, "nonzero"}:
                print(f"\033[31mError:\033[0m _hidden_config has invalid value at {address} node {node}")
                raise WrongFormattingError()
        elif context == "_id":
            if not isinstance(node, str):
                print(f"\033[31mError:\033[0m _id is not of type string at {address} node {node}")
                raise IncorrectTypeError()

            # Id's can't start with an underscore or have whitespace
            if node[0] == "_" or len(node.split()) != 1:
                print(f"\033[31mError:\033[0m Id's can't start with an underscore or have whitespace at {address} node {node}")
                raise WrongFormattingError()
        elif context == "_inject_position":
            if not isinstance(node, str):
                print(f"\033[31mError:\033[0m _inject_position is not of type string at {address} node {node}")
                raise IncorrectTypeError()
            
            if node not in {"before", "after"}:
                print(f"\033[31mError:\033[0m _inject_position is not a valid value at {address} node {node}")
                raise InvalidValueError()
        elif context == "_num_expr":  # TODO: Is there a difference between this and _expr?
            if isinstance(node, (int, float)):
                pass
            elif isinstance(node, str):
                self.parse_node(node, "_expr", address)
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
                        self.parse_node(real_spec, "_expr", address)
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
                        if not real_spec.split(" from ")[-1] in self.utility.collect_vars(address):
                            print(f"\033[31mError:\033[0m Undefined variable {real_spec.split(' from ')[-1]} at {address} node {node}")
                            raise MissingReferenceError()  # Here, just check for bag's existence
                    elif not (real_spec in self.utility.collect_vars(address)):
                        print(f"\033[31mError:\033[0m Undefined variable {real_spec} at {address} node {node}")
                        raise MissingReferenceError()
        elif context == "_set_expr":
            if not isinstance(node, str):
                print(f"\033[31mError:\033[0m Expected string for _set_expression at {address} node {node}")
                raise IncorrectTypeError()  # TODO: Convert IncorrectTypeError exceptions to more useful format

            var_expr_pair = node.split("=")

            if len(var_expr_pair) == 1 and (var_expr_pair[0] in self.utility.collect_vars(address)):
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

            if not (var_name_indices[0] in self.utility.collect_vars(address)):
                print(f"\033[31mError:\033[0m Undefined variable {var_name_indices[0]} at {address} node {node}")
                raise MissingReferenceError()

            # NOTE: No checking for array length yet!

            self.parse_node(var_expr_pair[1].strip(), "_expr", address)
        elif context == "_story_point":
            if node is None:
                # Don't include the storypoint part of the address
                self.gamestate.light.storypoints[address[:-1]] = False
            else:
                if not isinstance(node, str):
                    print(f"\033[31mError:\033[0m Non-string story point at {address} node {node}")
                    raise IncorrectTypeError()

                self.gamestate.light.storypoints[node] = False
        elif context == "_table_id":
            # First check it's a valid variable reference
            self.parse_node(node, "_var_id", address)

            var_referenced = self.utility.collect_vars_with_dicts(address)[node]["value"]
            if not isinstance(var_referenced, list):
                print(f"\033[31mError:\033[0m Non-list table specified at {address} node {node}")
                raise IncorrectTypeError()
            for row in var_referenced:
                if not isinstance(row, list):
                    print(f"\033[31mError:\033[0m Non-list table row specified at {address} node {node}")
                    raise IncorrectTypeError()
                for col in row:
                    # Check that this is a valid (non-list) value
                    self.parse_node(col, "_value", address)
        elif context == "_text":
            if not isinstance(node, str):
                print(f"\033[31mError:\033[0m String expected for _text value at {address} node {node}")
                raise IncorrectTypeError()
            try:
                string_to_print = self.utility.format.vformat(node, (), self.utility.collect_vars(address))
            except:
                print(f"\033[31mError:\033[0m Missing reference (or incorrect formatting) for text at {address} node {node}")
                raise MissingReferenceError()
        elif context == "_value":
            if not isinstance(node, (str, int, bool, float)):
                print(f"\033[31mError:\033[0m Expected string/numerical/bool value at {address} node {node}")
                raise IncorrectTypeError(f"Node with context {context} is of incorrect type.")
        elif context == "_var_id":
            if not isinstance(node, str):
                print(f"\033[31mError:\033[0m Expected string value at {address} node {node}")
                raise IncorrectTypeError()
            if not node in self.utility.collect_vars(address):
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
        
        # Special handling for SPILL
        if context == "SPILL":
            partial_addr = address
            while True:
                partial_node = self.addressing.get_node(partial_addr)
                if "choice" in partial_node:
                    break
                
                if partial_addr == ():
                    print(f"\033[31mError:\033[0m SPILL context not within a choice at {address} node {node}")
                    raise IncorrectStructureError()
                else:
                    partial_addr = partial_addr[:-1]

        if not (context in self.grammar):
            print(f"\033[31mError:\033[0m Undefined context {context} at {address} node {node}")
            raise GrammarParsingError()

        curr_rule = self.grammar[context]

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
            
            def parse_key():
                if "mandatory" in curr_rule and key in curr_rule["mandatory"]:
                    self.parse_node(node[key], curr_rule["mandatory"][key], address + (key,))
                elif "optional" in curr_rule and key in curr_rule["optional"]:
                    self.parse_node(node[key], curr_rule["optional"][key], address + (key,))
                elif "other" in curr_rule:
                    self.parse_node(node[key], curr_rule["other"], address + (key,))
                else:
                    print(f"\033[31mError:\033[0m Invalid tag {key} at address {address} node {node}")
                    raise InvalidTagError()

            # Parse priority keys in order
            priority_keys = {}
            if "priority" in curr_rule:
                if not isinstance(curr_rule["priority"], list):
                    print(f"\033[31mError:\033[0m The value for the 'priority' key of grammar rule {context} is not of type list")
                    raise GrammarParsingError()
                for key in curr_rule["priority"]:
                    if key in node:
                        priority_keys[key] = True
                        parse_key()

            # Parse other keys
            for key in node.keys():
                if key not in priority_keys:
                    parse_key()
        elif curr_rule["type"] == "list":
            if not isinstance(node, list):
                print(f"\033[31mError:\033[0m Expected list node at {address} node {node}")
                raise IncorrectTypeError()

            for index, element in enumerate(node):
                self.parse_node(element, curr_rule["elements"], address + (index,))
        elif curr_rule["type"] == "union":
            could_be_parsed = False
            for member in curr_rule["members"]:
                try:
                    self.parse_node(node, member, address)
                    could_be_parsed = True
                    break
                except Exception as e:
                    continue
            if not could_be_parsed:
                print(f"\033[31mError:\033[0m Invalid Disjunct at address {address} node {node}")
                raise InvalidDisjunctError()
        elif curr_rule["type"] == "union_with_keys":
            could_be_parsed = False
            for key, context in curr_rule["contexts"].items():
                if key in node:
                    # In this case, we've parsed it as multiple different things
                    if could_be_parsed:
                        print(f"\033[31mError:\033[0m Ambiguous Disjunct at address {address} node {node}")
                        raise InvalidDisjunctError()

                    self.parse_node(node, context, address)
                    could_be_parsed = True

            # In this case, it couldn't be parsed as anything
            if not could_be_parsed:
                print(f"\033[31mError:\033[0m Invalid Disjunct at address {address} node {node}")
                raise InvalidDisjunctError()
        elif curr_rule["type"] == "union_with_types":
            if "list" in curr_rule and isinstance(node, list):
                self.parse_node(node, curr_rule["list"], address)
            elif "dict" in curr_rule and isinstance(node, dict):
                self.parse_node(node, curr_rule["dict"], address)
            elif "str" in curr_rule and isinstance(node, str):
                self.parse_node(node, curr_rule["str"], address)
            elif "num" in curr_rule and isinstance(node, (int, float)):
                self.parse_node(node, curr_rule["num"], address)
            elif "none" in curr_rule and node is None:
                self.parse_node(node, curr_rule["none"], address)
            else:
                print(f"\033[31mError:\033[0m Invalid Disjunct at address {address} node {node}")
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
                    self.parse_node(node["effects"], "CONTENT", address + ("effects",))
                else:
                    self.parse_node(node["choice"], "_addr", address)
        # TODO: Special checking for SET to check that if the set is just a single var name we need a TO


    def parse_game(self):
        self.parse_node(self.gamestate.game, "START", ())
