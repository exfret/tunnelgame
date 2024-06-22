from config import game, state

class InvalidAddressError(Exception):
    pass

def get_node(addr, curr_node = game):
    if addr == ():
        return curr_node
    
    if not isinstance(addr[0], (int, str)):
        raise InvalidAddressError("Address has index of type neither int or str.")
    if isinstance(addr[0], int) and not isinstance(curr_node, list):
        raise InvalidAddressError("Address has numerical index for non-list node.")
    if isinstance(addr[0], str) and not isinstance(curr_node, dict):
        raise InvalidAddressError("Address has string index for non-dict node.")
    if isinstance(curr_node, list) and (addr[0] >= len(curr_node) or addr[0] < -len(curr_node)):
        raise InvalidAddressError("Address has numerical index that is out of range.")
    if isinstance(curr_node, dict) and not addr[0] in curr_node:
        raise InvalidAddressError("Attempt to index into nonexistent key of address")

    return get_node(addr[1:], curr_node[addr[0]])

def make_bookmark(address):
    return (address,)

def get_block_part(curr_addr, index):
    if index >= len(curr_addr):
        return curr_addr
    
    if isinstance(curr_addr[index], int) or curr_addr[index][0] == "_":
        return curr_addr[:index]
    else:
        return get_block_part(curr_addr, index + 1)

def parse_addr(curr_addr, addr_id):
    # Blocks are simply children of the root node with purely string addresses having leading underscores
    curr_addr = get_block_part(curr_addr, 0)
    path = tuple(addr_id.split("/"))

    def parse_addr_from_block(block_addr, path):
        if len(path) == 0:
            return block_addr
        
        index = path[0]
        path = path[1:]

        if index == "": # Corresponds to instance of a root /
            return parse_addr_from_block((), path)
        elif index == ".":
            return parse_addr_from_block(block_addr, path)
        elif index == "..":
            if len(block_addr) == 0:
                raise InvalidAddressError("Attempt to index out of root node in an address ID.")

            return parse_addr_from_block(block_addr[:-1], path)
        elif index[0] == "_":
            raise InvalidAddressError("Attempt to index into non-block address.")
        else:
            return parse_addr_from_block(block_addr + (index,), path)

    new_addr = None
    try:
        new_addr = parse_addr_from_block(curr_addr, path)

        node = get_node(new_addr)
    except InvalidAddressError:
        if len(curr_addr) > 0:
            # If this block is a list block and not the root content, it can't contain other blocks anyways, so just allow it to goto sibling blocks
            # TODO: More "block searching" functionality to find blocks with similar names
            new_addr = parse_addr_from_block(curr_addr[:-1], path)

            node = get_node(new_addr)
        else:
            raise InvalidAddressError("Non-existent block address")

    curr_addr = new_addr

    if isinstance(node, list):
        return curr_addr + (0,)
    elif isinstance(node, dict) and ("_content" in node):
        return curr_addr + ("_content", 0)
    else:
        raise InvalidAddressError("Attempt to goto block without content.")