from engine import config


game = config.game
state = config.state


class InvalidAddressError(Exception):
    pass


def get_node(addr, curr_node=None):
    if curr_node is None:
        curr_node = game
    if addr == ():
        return curr_node

    # We can't do print statements here because these exceptions can be caught
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


def get_curr_addr(bookmark=None):
    if bookmark is None:
        bookmark = state["bookmark"]

    # If queue is empty, we're done
    if bookmark == False or len(bookmark) == 0:
        return False

    return bookmark[0]


# Remove current address and add new address
def set_curr_addr(addr):
    state["bookmark"] = (addr,) + state["bookmark"][1:]


# Get's next instruction's address; returns False if there is no next instruction (i.e.- we're at the end of a block)
def get_next_addr(addr):
    if addr == ():
        return False
    
    # If it's a string key, it's not an incrementable address piece
    if isinstance(addr[-1], str):
        # If it's a choice effects section, don't spill over into the remaining block
        if addr[-1] == "effects":
            return False
        return get_next_addr(addr[:-1])

    new_addr = addr[:-1] + (addr[-1] + 1,)  # TODO: Error check that last element is indeed an int and not something weird

    # Check to see if we spill out of this numerical block
    # TODO: Check manually that the only issue is iterating past the end of a numerical section
    try:
        get_node(new_addr)
    except InvalidAddressError:
        return get_next_addr(addr[:-1])
    else:
        return new_addr


# Goes a block up if this is a footer so we don't loop inside a footer
def trim_footer(addr):
    # Case where we weren't in a footer
    if addr == ():
        return True

    # If this is a footer of the root block, we're done and stop
    if addr[-1] == "_footer":
        # Case where we were in the root footer (thus we're done executing)
        if len(addr) == 1:
            return False

        return addr[:-2]
    else:
        return trim_footer(addr[:-1])
    

# Searches for footer as a child of the current address, if not goes up a block
def search_for_footers(addr):
    curr_node = get_node(addr)

    if isinstance(curr_node, dict) and "_footer" in curr_node:
        return addr + ("_footer", 0)
    else:
        # No footers found
        if addr == ():
            return False

        # Try next higher block
        return search_for_footers(addr[:-1])


def get_next_bookmark(bookmark):
    # Case where there's no addresses in the queue left
    if bookmark == ():
        return False
    
    curr_addr = get_curr_addr(bookmark)
    next_addr = get_next_addr(curr_addr)
    
    # Check if we reached the end of execution for this queue entry
    if next_addr == False:
        # If this is the last part of the call stack, check for footers to execute
        if len(bookmark) == 1:
            # Ignore any footers that we currently are in
            trimmed = trim_footer(curr_addr)
            if trimmed == True:
                trimmed = curr_addr
            elif trimmed == False:
                return False

            footer = search_for_footers(trimmed)
            if footer == False:
                return False
            else:
                return (search_for_footers(trimmed),)

        return bookmark[1:]
    else:
        return (next_addr,) + bookmark[1:]


def add_header(addr):
    curr_node = get_node(addr)

    if isinstance(curr_node, dict) and "_header" in curr_node:
        # TODO: Check during parse-time that headers are lists with at least one instruction
        state["bookmark"] = state["bookmark"] + (addr + ("_header", 0),)


def make_bookmark(bookmark, addr, injections = []):
    partial_addr = ()

    add_header(partial_addr)
    for tag in addr:
        partial_addr = partial_addr + (tag,)
        add_header(partial_addr)

    for inj in injections:
        bookmark = bookmark + (inj,)
    
    bookmark = bookmark + (addr,)

    return bookmark


def get_block_part(curr_addr, index=0):
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

    new_addr = None
    try:
        new_addr = parse_addr_from_block(curr_addr, path)

        node = get_node(new_addr)
    except InvalidAddressError:
        if len(curr_addr) > 0:
            # If this block is a list block and not the root content, it can't contain other blocks anyways, so just allow it to goto sibling blocks
            # TODO: More "block searching" functionality to find blocks with similar names
            try:
                new_addr = parse_addr_from_block(curr_addr[:-1], path)

                node = get_node(new_addr)
            except InvalidAddressError:
                print(f"Invalid address {path} at address {curr_addr}")
                raise InvalidAddressError()
        else:
            raise InvalidAddressError("Non-existent block address")

    curr_addr = new_addr

    if isinstance(node, list):
        return curr_addr + (0,)
    elif isinstance(node, dict) and ("_content" in node):
        return curr_addr + ("_content", 0)
    else:
        raise InvalidAddressError("Attempt to goto block without content.")


def parse_addr_from_block(block_addr, path):
    if len(path) == 0:
        return block_addr

    index = path[0]
    path = path[1:]

    if index == "":  # Corresponds to instance of a root /
        return parse_addr_from_block((), path)
    elif index == ".":
        return parse_addr_from_block(block_addr, path)
    elif index == "..":
        if len(block_addr) == 0:
            raise InvalidAddressError("Attempt to index out of root node in an address ID.")

        return parse_addr_from_block(block_addr[:-1], path)
    elif index[0] == "_":
        raise InvalidAddressError("Attempt to index into non-block address.")
    elif index[0] == "~": # Corresponds to root of a given file
        while True:
            if block_addr in state["story_data"]["file_homes"] or len(block_addr) == 0:
                break
            else:
                block_addr = block_addr[:-1]

        return parse_addr_from_block(block_addr, path)
    else:
        return parse_addr_from_block(block_addr + (index,), path)
