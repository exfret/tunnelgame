class InvalidAddressError(Exception):
    pass

def get_instr(curr_node, addr):
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

    return get_instr(curr_node[addr[0]], addr[1:]) # TODO: Check map/address compatibility

def get_block_part(curr_addr, index):
    if curr_addr == () or curr_addr[0] != "story":
        raise InvalidAddressError("Attempt to get block part of non-story address.")
    
    if index >= len(curr_addr):
        return curr_addr
    
    if isinstance(curr_addr[index], int) or curr_addr[index][0] == "_":
        return curr_addr[:index]
    else:
        return get_block_part(curr_addr, index + 1)

def parse_addr(game, curr_addr, addr_id):
    # Blocks are simply children of story (including story) with numerical addresses and no leading underscores
    curr_addr = get_block_part(curr_addr, 0)

    path = tuple(addr_id.split("/"))

    for index in path:
        if index == "": # Corresponds to instance of a root /
            curr_addr = ("story",)
        elif index == ".":
            pass
        elif index == "..":
            if len(curr_addr) == 1:
                raise InvalidAddressError("Attempt to index out of story in an address ID.")

            curr_addr = curr_addr[:-1]
        elif index[0] == "_":
            raise InvalidAddressError("Attempt to index into non-block address.")
        else:
            curr_addr = curr_addr + (index,)

    node = get_instr(game, curr_addr)

    if isinstance(node, list):
        return curr_addr + (0,)
    elif isinstance(node, dict) and ("_content" in node):
        return curr_addr + ("_content",)
    else:
        raise InvalidAddressError("Attempt to goto block without content.")