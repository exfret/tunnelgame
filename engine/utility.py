from string import Formatter


from engine.gamestate import GameState
from engine.addressing import Addressing


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


# TODO: Use this for custom indexing (make sure to index into value)
class Var():
    pass


class VarDict(dict):
    def __contains__(self, key: object) -> bool:
        if isinstance(key, str) and len(key.split("__")) == 2:
            bag_name = key.split("__")[0]
            if super().__contains__(bag_name):
                return True  # Never raise missing reference for items as long as the bag exists
            else:
                return False
        else:
            return super().__contains__(key)

    def __getitem__(self, key):
        if isinstance(key, str) and len(key.split("__")) == 2:
            bag_var = super().__getitem__(key.split("__")[0])

            if not key.split("__")[1] in bag_var["value"]:
                # TODO: Remove this duplicate "default var creation" code
                bag_var["value"][key.split("__")[1]] = {"address": bag_var["address"], "value": 0, "locale": key.split("__")[1]}  # TODO: locale support

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


def localize_from_var(var_name, var):
    if "locale" in var:
        if isinstance(var["locale"], str):
            return var["locale"]
        
        if "value" not in var:
            return var["locale"]["default"]

        if "singular" in var["locale"] and var["value"] == 1:
            return var["locale"]["singular"]
        elif "plural" in var["locale"] and isinstance(var["value"], float | int):
            return var["locale"]["plural"]
        
        return var["locale"]["default"]
    else:
        return var_name


class VarDictValues(VarDict):
    def __getitem__(self, key):
        # First, check if this is a localization variable
        if len(key) > 2 and key[:2] == "__":
            var = super().__getitem__(key[2:])
            return localize_from_var(key[2:], var)

        var = super().__getitem__(key)

        if isinstance(var, dict) and "value" in var:
            return var["value"]
        else:
            return var
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)


class ArgsList(list):
    def __getitem__(self, index):
        try:
            return super().__getitem__(index)
        except IndexError:
            return None


class Utility:
    gamestate : GameState
    addressing : Addressing


    def __init__(self, gamestate, addressing):
        self.gamestate = gamestate
        self.addressing = addressing

        self.format = CustomFormatter()


    def get_args_list(self):
        return ArgsList()


    # Was going to be used for args but then I realized I needed something else, so currently unused
    def create_default_var(self, value=None, locale=None):
        return {"address": (), "locale": locale, "possible_values": None, "value": value, "global": False, "hidden": False}


    def get_var(self, var_dict, var_name, curr_address):
        if (curr_address in var_dict) and (var_name in var_dict[curr_address]):
            return var_dict[curr_address][var_name]
        else:
            if curr_address == ():
                raise Exception()  # TODO: Make exception more specific (missing reference)

            return self.get_var(var_dict, var_name, curr_address[:-1])
    

    def collect_vars_with_dicts(self, address=None):
        var_dict = VarDict()

        if address is None:
            address = self.addressing.get_curr_addr()
        if address is False:
            address = self.gamestate.light.last_address

        for ind in range(len(address)):
            addr_to_check = address[:ind]
            if addr_to_check in self.gamestate.bulk.vars:
                new_vars_dict = self.gamestate.bulk.vars[addr_to_check]

                for var_name, var_spec in new_vars_dict.items():
                    var_dict[var_name] = var_spec
        
        # Add module vars/other special vars
        for ind, val in self.gamestate.bulk.vars.items():
            if not isinstance(ind, tuple):
                var_dict[ind] = val
        for flag in self.gamestate.bulk.vars["flags"]:
            if self.gamestate.bulk.vars["flags"][flag]:
                var_dict[flag] = True
            else:
                var_dict[flag] = False

        var_dict["_visits"] = self.gamestate.bulk.per_line[address].visits
        var_dict["_num_choices"] = len(self.gamestate.light.choices)
        var_dict["_address"] = self.addressing.get_block_part(self.gamestate.light.last_address)
        if len(self.gamestate.light.last_address_list) >= 1:
            var_dict["_previous_address"] = self.addressing.get_block_part(self.gamestate.light.last_address_list[-1])
        else:
            var_dict["_previous_address"] = ()

        return var_dict
    

    def collect_vars(self, address=None):
        var_dict = VarDictValues(self.collect_vars_with_dicts(address))

        return var_dict
    

    # Dereferences things in {}, can handle recursive nesting like {{foo}} where foo = "blop" and blop = "bar"
    def dereference_text(self, text):
        # Keep formatting until we've stabilized
        while True:
            new_text = self.format.vformat(text, (), self.collect_vars())
            if text == new_text:
                break
            else:
                text = new_text
        return text
    

    def eval_values(self, text):
        return eval(self.dereference_text(text), {}, self.collect_vars())
    

    def eval_vars(self, text):
        return eval(self.dereference_text(text), {}, self.collect_vars_with_dicts())


    def eval_conditional(self, node, address=None):
        vars_by_name = self.collect_vars_with_dicts(address)

        if isinstance(node, str):
            return eval(node, {}, self.collect_vars(address))
        elif isinstance(node, list):  # Lists are automatically ANDS, unless they're part of an OR tag covered later
            for subnode in node:
                if not self.eval_conditional(subnode, address):
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
                    if self.eval_conditional(subnode, address):
                        return True
                return False


    def set_val(self, var, new_val):
        # TODO: Throw exceptions if we try to set a var without value
        if "value" in var:
            var["value"] = new_val


    def localize(self, var_name, address=None, var_to_use=None):
        var = None
        if var_to_use is not None:
            var = var_to_use
        else:
            if address is None:
                address = self.addressing.get_curr_addr()
            var_dict = self.collect_vars_with_dicts(address)
            var = var_dict[var_name]

        return localize_from_var(var_name, var)

    
    def create_choice(self, text, address):
        return {"text": text, "address": address, "choice_address": (), "action": False, "missing": [], "modifications": []}
    

    def parse_requirement_spec(self, text_spec):
        vars_by_name = self.collect_vars_with_dicts()  # I don't think this is used because we don't actually do the eval here

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
                    paren_splits.append(text_spec[last_index : index + 1])
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
            if index % 2 == 0:  # Case of an eval part
                grouped_specs.append({})
                grouped_specs[int(index / 2)]["amount"] = non_grouped_spec
            else:  # Case of a var part
                # TODO: Use collect_vars?
                grouped_specs[int(index / 2)]["var"] = non_grouped_spec

        return grouped_specs
    

    # Not used yet; for when I get around to per_cost_specs
    def parse_modification_spec(self, choice, amount=1):
        vars_to_amounts_cost = {}
        vars_to_amounts_req = {}
        vars_to_amounts_shown = {}

        for spec_type in ["cost_spec", "req_spec", "shown_spec", "per_cost_spec", "per_req_spec", "per_shown_spec"]:
            if spec_type in choice and len(choice[spec_type]) > 0:
                for modification in choice[spec_type]:
                    var_dict_vals = self.collect_vars(choice["choice_address"])
                    expr_val = eval(modification["amount"], {}, var_dict_vals)

                    def dict_add(dict, key, val):
                        if not key in dict:
                            dict[key] = 0
                        dict[key] += val

                    if spec_type == "cost_spec":
                        dict_add(vars_to_amounts_cost, modification["var"], expr_val)
                    elif spec_type == "per_cost_spec":
                        dict_add(vars_to_amounts_cost, modification["var"], amount * expr_val)
                    elif spec_type == "req_spec":
                        dict_add(vars_to_amounts_req, modification["var"], expr_val)
                    elif spec_type == "per_req_spec":
                        dict_add(vars_to_amounts_req, modification["var"], amount * expr_val)
                    elif spec_type == "shown_spec":
                        dict_add(vars_to_amounts_shown, modification["var"], expr_val)
                    elif spec_type == "per_shown_spec":
                        dict_add(vars_to_amounts_shown, modification["var"], amount * expr_val)
    

    # Used in word counting commands
    def count_words(self, node, only_count_visited=False, address=()):
        count_node = True
        if only_count_visited and self.gamestate.bulk.per_line[address].visits == 0:
            count_node = False

        num_words = 0

        if isinstance(node, str):
            if count_node:
                num_words += len(node.split())
        elif isinstance(node, (int, float)):
            if count_node:
                num_words += 1
        elif isinstance(node, list):
            for ind, subnode in enumerate(node):
                num_words += self.count_words(subnode, only_count_visited, address + (ind,))
        elif isinstance(node, dict):
            for key, subnode in node.items():
                if count_node:
                    num_words += 1
                    #num_words += len(key.split())
                num_words += self.count_words(subnode, only_count_visited, address + (key,))
        
        return num_words