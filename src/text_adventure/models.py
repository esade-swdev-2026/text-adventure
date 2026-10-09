"""Models for the three-room escape: items, doors, containers, rooms, the player and inventory."""


class Item:
    """Something the player can find, and maybe carry."""

    def __init__(self, name, description="", portable=True):
        self.name = name
        self.description = description
        self.portable = portable

    def describe(self):
        """Return the item's description, or just its name if it has none."""
        return self.description or f"A {self.name}"


class Door:
    """The exit of a room, opened only if the player holds the required item."""

    def __init__(self, next_room, required_item=None):
        self.next_room = next_room  # Room it leads to, or None for the final exit
        self.required_item = required_item  # name of the Item that opens it

    def is_exit(self):
        """Return True if opening this door wins the game."""
        return self.next_room is None

    def open(self, inventory):
        """Try to open the door; the key is used up. Return True if it opened."""
        if self.required_item is None:
            return True
        if not inventory.has_item(self.required_item):
            return False
        inventory.use_item(self.required_item)
        return True


class Container:
    """A desk, chest or box that starts closed and reveals its items when opened."""

    def __init__(self, name, contents=None, required_item=None):
        self.name = name
        self.contents = contents or []  # list of Item inside
        self.required_item = required_item  # name of the Item that unlocks it, or None
        self.is_open = False

    def is_locked(self):
        """Return True if the player still needs an item before this can be opened."""
        return self.required_item is not None and not self.is_open

    def open(self, inventory):
        """Try to open the container; the required item is kept. Return True if it opened."""
        if self.is_locked() and not inventory.has_item(self.required_item):
            return False
        self.is_open = True
        return True


class Room:
    """One of the three rooms: containers, loose items and a single door."""

    def __init__(self, name, description, door, containers=None, items=None):
        self.name = name
        self.description = description
        self.door = door
        self.containers = containers or []  # list of Container
        self.items = items or []  # loose items lying in the room

    def remove_item(self, item):
        """Take an item off the floor or out of an open container and return it."""
        if item in self.items:
            self.items.remove(item)
            return item
        for container in self.containers:
            if container.is_open and item in container.contents:
                container.contents.remove(item)
                return item
        raise ValueError(f"There is no {item.name} here")


class Player:
    """The player: which room they are in and what they carry."""

    def __init__(self, current_room, inventory):
        self.current_room = current_room
        self.inventory = inventory  # an Inventory (max 4 items)

    def take_item(self, item):
        """Move an item from the current room into the inventory."""
        if not item.portable:
            raise ValueError(f"The {item.name} can't be carried")
        if self.inventory.is_full():
            raise ValueError(f"Inventory is full. Drop an item to pick up {item.name}.")
        self.inventory.pick_up_item(self.current_room.remove_item(item))

    def drop_item(self, item):
        """Drop an item from the inventory onto the floor of the current room."""
        self.current_room.items.append(self.inventory.drop_item(item))


CAPACITY = 4


class Inventory:
    """Holds the items the player carries, up to a fixed capacity."""

    def __init__(self, items=None, capacity=CAPACITY):
        self.items = items or []  # list of Item
        self.capacity = capacity

    def is_full(self):
        """True when no more items can be carried."""
        return len(self.items) >= self.capacity

    def pick_up_item(self, item):
        """Add an item to the inventory."""
        if not isinstance(item, Item):
            raise TypeError(f"Expected an Item, got {type(item).__name__}")
        if self.is_full():
            raise ValueError(f"Inventory is full. Drop an item to pick up {item.name}.")
        self.items.append(item)

    def has_item(self, name):
        """True if an item with this name is being carried."""
        return any(item.name == name for item in self.items)

    def use_item(self, name):
        """Remove the item with this name (e.g. a key used on a door) and return it."""
        for item in self.items:
            if item.name == name:
                self.items.remove(item)
                return item
        raise ValueError(f"{name} not in inventory")

    def capacity_check(self):
        """Return how many items are being carried."""
        return len(self.items)

    def show_inventory(self):
        """Return the list of carried items."""
        return self.items

    def drop_item(self, item):
        """Remove an item from the inventory and return it."""
        if item not in self.items:
            raise ValueError(f"{item.name} not in inventory, please enter item you want to drop")
        self.items.remove(item)
        return item
