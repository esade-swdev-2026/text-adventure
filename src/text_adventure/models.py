"""Models for the escape: items, doors, containers, rooms, the player and inventory."""

from __future__ import annotations

CAPACITY = 4
DOOR = "door"  # reserved name: `open door` always means the room's door


class Item:
    """Something the player can find, and maybe carry."""

    def __init__(
        self, name: str, description: str = "", portable: bool = True, floor_text: str = ""
    ) -> None:
        self.name = name
        self.description = description
        self.portable = portable
        self.floor_text = floor_text  # sentence used while the item lies on the floor

    def describe(self) -> str:
        """Return the item's description, or just its name if it has none."""
        return self.description or f"A {self.name}"


class Door:
    """The exit of a room, opened only if the player holds the required item."""

    def __init__(self, next_room: Room | None, required_item: str | None = None) -> None:
        self.next_room = next_room  # Room it leads to, or None for the final exit
        self.required_item = required_item  # name of the Item that opens it
        self.is_open = False

    def is_exit(self) -> bool:
        """Return True if opening this door wins the game."""
        return self.next_room is None

    def open(self, inventory: Inventory) -> bool:
        """Try to open the door; the key is used up. Return True if it opened."""
        if self.required_item is not None:
            if not inventory.has_item(self.required_item):
                return False
            inventory.use_item(self.required_item)
        self.is_open = True
        return True


class Container:
    """A desk, chest or box that starts closed and reveals its items when opened."""

    def __init__(
        self,
        name: str,
        contents: list[Item] | None = None,
        required_item: str | None = None,
        closed_text: str = "",
        open_text: str = "",
    ) -> None:
        self.name = name
        self.contents = contents or []  # list of Item inside
        self.required_item = required_item  # name of the Item that unlocks it, or None
        self.closed_text = closed_text  # sentence used while it is closed
        self.open_text = open_text  # sentence used once it is open
        self.is_open = False

    def is_locked(self) -> bool:
        """Return True if the player still needs an item before this can be opened."""
        return self.required_item is not None and not self.is_open

    def open(self, inventory: Inventory) -> bool:
        """Try to open the container; the required item is kept. Return True if it opened."""
        if (
            self.is_locked()
            and self.required_item is not None
            and not inventory.has_item(self.required_item)
        ):
            return False
        self.is_open = True
        return True


class Room:
    """A room: containers, loose items and a single door."""

    def __init__(
        self,
        name: str,
        description: str,
        door: Door,
        containers: list[Container] | None = None,
        items: list[Item] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.door = door
        self.containers = containers or []  # list of Container
        self.items = items or []  # loose items lying in the room

    def find_container(self, name: str) -> Container | None:
        """Return the container with this name, or None."""
        return next((c for c in self.containers if c.name == name), None)

    def find_visible_item(self, name: str) -> Item | None:
        """Return the item with this name on the floor or in an open container, or None."""
        for item in self.items:
            if item.name == name:
                return item
        for container in self.containers:
            if container.is_open:
                for item in container.contents:
                    if item.name == name:
                        return item
        return None

    def remove_item(self, item: Item) -> Item:
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

    def __init__(self, current_room: Room, inventory: Inventory) -> None:
        self.current_room = current_room
        self.inventory = inventory  # an Inventory (max CAPACITY items)

    def take_item(self, item: Item) -> None:
        """Move an item from the current room into the inventory."""
        if not item.portable:
            raise ValueError(f"The {item.name} can't be carried.")
        if self.inventory.is_full():
            raise ValueError(f"Your hands are full. Drop something to take the {item.name}.")
        self.inventory.pick_up_item(self.current_room.remove_item(item))

    def drop_item(self, item: Item) -> None:
        """Drop an item from the inventory onto the floor of the current room."""
        self.current_room.items.append(self.inventory.drop_item(item))


class Inventory:
    """Holds the items the player carries, up to a fixed capacity."""

    def __init__(self, items: list[Item] | None = None, capacity: int = CAPACITY) -> None:
        self.items = items or []  # list of Item
        self.capacity = capacity

    def is_full(self) -> bool:
        """True when no more items can be carried."""
        return len(self.items) >= self.capacity

    def pick_up_item(self, item: Item) -> None:
        """Add an item to the inventory."""
        if not isinstance(item, Item):
            raise TypeError(f"Expected an Item, got {type(item).__name__}")
        if self.is_full():
            raise ValueError(f"Your hands are full. Drop something to take the {item.name}.")
        self.items.append(item)

    def has_item(self, name: str) -> bool:
        """True if an item with this name is being carried."""
        return any(item.name == name for item in self.items)

    def find(self, name: str) -> Item | None:
        """Return the carried item with this name, or None."""
        return next((item for item in self.items if item.name == name), None)

    def use_item(self, name: str) -> Item:
        """Remove the item with this name (e.g. a key used on a door) and return it."""
        for item in self.items:
            if item.name == name:
                self.items.remove(item)
                return item
        raise ValueError(f"{name} not in inventory")

    def count(self) -> int:
        """Return how many items are being carried."""
        return len(self.items)

    def show_inventory(self) -> list[Item]:
        """Return a copy of the carried items, so callers can't change the inventory by accident."""
        return list(self.items)

    def drop_item(self, item: Item) -> Item:
        """Remove an item from the inventory and return it."""
        if item not in self.items:
            raise ValueError(f"{item.name} not in inventory")
        self.items.remove(item)
        return item
