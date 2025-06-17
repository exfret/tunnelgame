from engine.gamestate import GameState


class InvalidAddressError(Exception):
    pass


class Addressing:
    gamestate : GameState


    def __init__(self, gamestate):
        self.gamestate = gamestate
    

    def get_node(self, addr, curr_node=None):
        if curr_node is None:
            curr_node = self.gamestate.game
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
            raise InvalidAddressError("Attempt to index into nonexistent key of address.")

        return self.get_node(addr[1:], curr_node[addr[0]])
    

    def get_curr_addr(self, bookmark=None):
        if bookmark is None:
            bookmark = self.gamestate.light.bookmark

        # If queue is empty, we're done
        if bookmark is False or len(bookmark) == 0:
            return False

        return bookmark[0]
    

    # Remove current address and add new address
    def set_curr_addr(self, addr):
        self.gamestate.light.bookmark = (addr,) + self.gamestate.light.bookmark[1:]


    # Get's next instruction's address; returns False if there is no next instruction (i.e.- we're at the end of a block)
    def get_next_addr(self, addr):
        if addr == ():
            return False
        
        # If it's a string key, it's not an incrementable address piece
        if isinstance(addr[-1], str):
            # If it's a choice effects section, don't spill over into the remaining block
            if addr[-1] == "effects":
                return False
            return self.get_next_addr(addr[:-1])

        if not isinstance(addr[-1], int):
            raise InvalidAddressError("Expected numeric index at end of address.")
        new_addr = addr[:-1] + (addr[-1] + 1,)

        # Check to see if we spill out of this numerical block
        # TODO: Check manually that the only issue is iterating past the end of a numerical section
        try:
            self.get_node(new_addr)
        except InvalidAddressError:
            return self.get_next_addr(addr[:-1])
        else:
            return new_addr
    

    # Goes a block up if this is a footer so we don't loop inside a footer
    def trim_footer(self, addr):
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
            return self.trim_footer(addr[:-1])
        
    
    # Searches for footer as a child of the current address, if not goes up a block
    def search_for_footers(self, addr):
        curr_node = self.get_node(addr)

        if isinstance(curr_node, dict) and "_footer" in curr_node:
            return addr + ("_footer", 0)
        else:
            # No footers found
            if addr == ():
                return False

            # Try next higher block
            return self.search_for_footers(addr[:-1])
    

    def get_next_bookmark(self, bookmark):
        # Case where there's no addresses in the queue left
        if bookmark == ():
            return False
        
        curr_addr = self.get_curr_addr(bookmark)
        next_addr = self.get_next_addr(curr_addr)
        
        # Check if we reached the end of execution for this queue entry
        if next_addr is False:
            # If this is the last part of the address queue, check for footers to execute
            if len(bookmark) == 1:
                # Ignore any footers that we currently are in
                trimmed = self.trim_footer(curr_addr)
                if trimmed is True:
                    trimmed = curr_addr
                elif trimmed is False:
                    return False

                footer = self.search_for_footers(trimmed)
                if footer is False:
                    return False
                else:
                    return (self.search_for_footers(trimmed),)

            return bookmark[1:]
        else:
            return (next_addr,) + bookmark[1:]
    

    def add_header(self, addr, bookmark):
        curr_node = self.get_node(addr)

        if isinstance(curr_node, dict) and "_header" in curr_node:
            # TODO: Check during parse-time that headers are lists with at least one instruction
            bookmark = bookmark + (addr + ("_header", 0),)
        
        return bookmark
    

    def add_injections(self, addr, position="before", bookmark=None):
        if bookmark is None:
            bookmark = self.get_curr_addr()
        
        curr_node = self.get_node(addr)

        if "_injections" in curr_node:
            for inj in curr_node["_injections"]:
                if position in inj:
                    bookmark = bookmark + (self.parse_addr(addr, inj[position]),)
        
        return bookmark


    def make_bookmark(self, bookmark, addr, injections = []):
        # Classic headers (backwards compatibility)
        partial_addr = ()
        bookmark = self.add_header(partial_addr, bookmark)
        for tag in addr:
            partial_addr = partial_addr + (tag,)
            bookmark = self.add_header(partial_addr, bookmark)
        
        # Block based injections
        partial_addr_inj = ()
        bookmark = self.add_injections(partial_addr_inj, position="before", bookmark=bookmark)
        for tag in addr:
            partial_addr_inj = partial_addr_inj + (tag,)
            bookmark = self.add_injections(partial_addr_inj, position="before", bookmark=bookmark)

        # Choice-based "before" injections
        for inj in injections:
            if inj["position"] == "before":
                bookmark = bookmark + (inj["address"],)
        
        bookmark = bookmark + (addr,)

        # After injections
        for inj in injections:
            if inj["position"] == "after":
                bookmark = bookmark + (inj["address"],)

        return bookmark
    

    def get_block_part(self, curr_addr, index=0):
        if index >= len(curr_addr):
            return curr_addr

        if isinstance(curr_addr[index], int) or curr_addr[index][0] == "_":
            return curr_addr[:index]
        else:
            return self.get_block_part(curr_addr, index + 1)
        

    def parse_addr_from_block(self, block_addr, path):
        if len(path) == 0:
            return block_addr

        index = path[0]
        path = path[1:]

        if index == "":  # Corresponds to instance of a root /
            return self.parse_addr_from_block((), path)
        elif index == ".":
            return self.parse_addr_from_block(block_addr, path)
        elif index == "..":
            if len(block_addr) == 0:
                raise InvalidAddressError("Attempt to index out of root node in an address ID.")

            return self.parse_addr_from_block(block_addr[:-1], path)
        elif index[0] == "_":
            raise InvalidAddressError("Attempt to index into non-block address.")
        elif index[0] == "~": # Corresponds to root of a given file
            while True:
                if block_addr in self.gamestate.game_data.file_homes or len(block_addr) == 0:
                    break
                else:
                    block_addr = block_addr[:-1]

            return self.parse_addr_from_block(block_addr, path)
        else:
            return self.parse_addr_from_block(block_addr + (index,), path)


    
    def parse_addr(self, curr_addr, addr_id, only_block_part=False):
        # Blocks are simply children of the root node with purely string addresses having no leading underscores
        curr_addr = self.get_block_part(curr_addr, 0)
        path = tuple(addr_id.split("/"))

        new_addr = None
        try:
            new_addr = self.parse_addr_from_block(curr_addr, path)

            node = self.get_node(new_addr)
        except InvalidAddressError:
            if len(curr_addr) > 0:
                # If this block is a list block and not the root content, it can't contain other blocks anyways, so just allow it to goto sibling blocks
                # TODO: More "block searching" functionality to find blocks with similar names
                try:
                    new_addr = self.parse_addr_from_block(curr_addr[:-1], path)

                    node = self.get_node(new_addr)
                except InvalidAddressError:
                    print(f"Invalid address {path} at address {curr_addr}")
                    raise InvalidAddressError()
            else:
                raise InvalidAddressError("Non-existent block address")

        curr_addr = new_addr

        # If we're just trying to get a block, we can return that now
        if only_block_part:
            return curr_addr

        # Otherwise, get the start of the instructions to execute
        if isinstance(node, list): # Note: this if statement is now defunct because all blocks are converted into dict blocks at parsetime
            return curr_addr + (0,)
        elif isinstance(node, dict) and ("_content" in node):
            return curr_addr + ("_content", 0)
        else:
            raise InvalidAddressError("Attempt to goto block without content.")