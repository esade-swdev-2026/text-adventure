"""Models for the three-room escape: items, doors, containers, rooms, the player and inventory."""


class Item:
    """Something the player can find, and maybe carry."""

    def __init__(self, name, description="", portable=True):
        self.name = name
        self.description = description
        self.portable = portable

    def describe(self):
        return f"A {self.name}"


class Door:
    """The exit of a room, opened only if the player holds the required item."""

    def __init__(self, next_room, required_item=None):
        self.next_room = next_room          # Room it leads to, or None for the final exit
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
        self.contents = contents or []      # list of Item inside
        self.required_item = required_item  # name of the Item that unlocks it, or None
        self.is_open = False

    def is_locked(self):
        """Return True if the player needs an item before this can be opened."""
        return self.required_item is not None


class Room:
    """One of the three rooms: containers, loose items and a single door."""

    def __init__(self, name, description, door, containers=None, items=None):
        self.name = name
        self.description = description
        self.door = door
        self.containers = containers or []  # list of Container
        self.items = items or []            # loose items lying in the room


class Player:
    """The player: which room they are in and what they carry."""

    def __init__(self, current_room, inventory):
        self.current_room = current_room
        self.inventory = inventory  # an Inventory (max 4 items)

    def drop_item(self, item):
        """Drop an item from the inventory onto the floor of the current room."""
        self.current_room.items.append(self.inventory.drop_item(item))


Capacity = 4


class Inventory:
    """Holds the items the player carries, up to a fixed capacity."""

    def __init__(self, inventory=None, capacity=Capacity):
        self.inventory = inventory or []  # list of Item
        self.capacity = capacity

    def is_full(self):
        """True when no more items can be carried."""
        return len(self.inventory) >= self.capacity

    def pick_up_item(self, item):
        """Add an item to the inventory."""
        if not isinstance(item, Item):
            raise TypeError(f"Expected an Item, got {type(item).__name__}")
        if self.is_full():
            raise ValueError(f"Inventory is full. Drop an item to pick up {item.name}.")
        self.inventory.append(item)
        print(f"{item.name} has been added, you now have {self.capacity_check()} items in inventory")

    def has_item(self, name):
        """True if an item with this name is being carried."""
        return any(item.name == name for item in self.inventory)

    def use_item(self, name):
        """Remove the item with this name (e.g. a key used on a door) and return it."""
        for item in self.inventory:
            if item.name == name:
                self.inventory.remove(item)
                return item
        raise ValueError(f"{name} not in inventory")

    def capacity_check(self):
        return len(self.inventory)

    def show_inventory(self):
        return self.inventory

    def drop_item(self, item):
        if item not in self.inventory:
            raise ValueError(f"{item.name} not in inventory, please enter item you want to drop")
        else:
            self.inventory.remove(item)
            print(f"{item.name} has been removed, you now have {self.capacity_check()} items in inventory")
            return item
