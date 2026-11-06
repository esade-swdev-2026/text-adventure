"""Models for the escape: items, doors, containers, rooms, the player and inventory."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

CAPACITY = 4
DOOR = "door"  # reserved name: `open door` always means the room's door

# State names. A container is closed or open, the door locked, unlocked or open. A `use` can
# give an item or a container a story state instead, such as "power on".
OPEN = "open"
CLOSED = "closed"
LOCKED = "locked"
UNLOCKED = "unlocked"


@dataclass(frozen=True)
class Use:
    """What happens when an item is used on an object (or, on an item's own rule, by itself).

    If an object named in `needs` is not in the state given, the player reads `refusal` and
    nothing changes. Otherwise the player reads `text`, the object takes the story `state` (if
    any), each name in `reveal` comes out of hiding, and a `consume`d item is used up.
    """

    item: str | None  # the item used; None on an item's own rule (`use flashbulb`)
    text: str
    needs: Mapping[str, str] = field(default_factory=dict)
    refusal: str = ""
    state: str | None = None
    reveal: tuple[str, ...] = ()
    consume: bool = False


def pick_text(texts: Mapping[str, str], state: str | None) -> str:
    """The text for this state, or the first text if the state has none of its own."""
    if state is not None and state in texts:
        return texts[state]
    return next(iter(texts.values()), "")


class Item:
    """Something the player can find, and maybe carry."""

    def __init__(
        self,
        name: str,
        description: str = "",
        portable: bool = True,
        floor_text: str = "",
        *,
        details: Mapping[str, str] | None = None,
        uses: list[Use] | None = None,
        refusal: str = "",
    ) -> None:
        self.name = name
        self.description = description
        self.portable = portable
        self.floor_text = floor_text  # sentence used while the item lies on the floor
        self.details = details or {}  # what `inspect` shows, by state; the first is the default
        self.uses = uses or []  # what happens when an item is used on this one
        self.refusal = refusal  # said when this item is used where it does nothing
        self.story: str | None = None  # story state set by a `use`, if any

    @property
    def state(self) -> str | None:
        """The item's story state, or None while it has none."""
        return self.story

    def describe(self) -> str:
        """Return the item's description, or just its name if it has none."""
        return self.description or f"A {self.name}"


class Door:
    """The exit of a room. Its required item unlocks it and is used up; then it opens."""

    def __init__(
        self,
        next_room: Room | None,
        required_item: str | None = None,
        *,
        needs: Mapping[str, str] | None = None,
        refusal: str = "",
        unlock_text: str = "",
        room_texts: Mapping[str, str] | None = None,
        details: Mapping[str, str] | None = None,
        uses: list[Use] | None = None,
    ) -> None:
        self.next_room = next_room  # Room it leads to, or None for the final exit
        self.required_item = required_item  # name of the Item that unlocks it
        self.needs = needs or {}  # states of other objects the lock waits for, e.g. power
        self.refusal = refusal  # said when the key is tried before `needs` are met
        self.unlock_text = unlock_text  # said when the key turns
        self.room_texts = room_texts or {}  # its sentence in the room description, by state
        self.details = details or {}  # what `inspect` shows, by state
        self.uses = uses or []
        self.is_unlocked = required_item is None
        self.is_open = False

    @property
    def state(self) -> str:
        """ "locked", "unlocked" or "open"."""
        if self.is_open:
            return OPEN
        return UNLOCKED if self.is_unlocked else LOCKED

    def room_sentence(self) -> str:
        """Its sentence in the room description for the current state, or "" if it has none."""
        return self.room_texts.get(self.state, "")

    def is_exit(self) -> bool:
        """Return True if opening this door wins the game."""
        return self.next_room is None

    def unlock(self, inventory: Inventory) -> bool:
        """Unlock the door with its required item, which is used up. Return True if unlocked."""
        if not self.is_unlocked:
            if self.required_item is None or not inventory.has_item(self.required_item):
                return False
            inventory.use_item(self.required_item)
            self.is_unlocked = True
        return True

    def open(self) -> bool:
        """Open the door if it is unlocked. Return True if it opened."""
        if self.is_unlocked:
            self.is_open = True
        return self.is_open


class Container:
    """A desk, chest or box that starts closed and reveals its items when opened."""

    def __init__(
        self,
        name: str,
        contents: list[Item] | None = None,
        required_item: str | None = None,
        closed_text: str = "",
        open_text: str = "",
        *,
        hidden: list[Item] | None = None,
        needs: Mapping[str, str] | None = None,
        refusal: str = "",
        room_texts: Mapping[str, str] | None = None,
        details: Mapping[str, str] | None = None,
        uses: list[Use] | None = None,
    ) -> None:
        self.name = name
        self.contents = contents or []  # list of Item inside
        self.hidden = hidden or []  # items inside that no one sees until a `use` reveals them
        self.required_item = required_item  # name of the Item that unlocks it, or None
        self.needs = needs or {}  # states of other objects the lock waits for
        self.refusal = refusal  # said when the tool is tried before `needs` are met
        self.closed_text = closed_text  # sentence used while it is closed
        self.open_text = open_text  # sentence used once it is open
        self.room_texts = room_texts or {}  # sentence for a state, used instead of the two above
        self.details = details or {}  # what `inspect` shows, by state
        self.uses = uses or []  # what happens when an item is used on it
        self.is_open = False
        self.story: str | None = None  # story state set by a `use`, if any

    @property
    def state(self) -> str:
        """Its story state if it has one, else "open" or "closed"."""
        return self.story or (OPEN if self.is_open else CLOSED)

    def room_sentence(self) -> str:
        """Its sentence in the room description for the current state, or "" if it has none."""
        if self.state in self.room_texts:
            return self.room_texts[self.state]
        return self.open_text if self.is_open else self.closed_text

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


type Thing = Item | Container | Door  # anything `inspect` and `use` can name


class Room:
    """A room: containers, loose items and a single door."""

    def __init__(
        self,
        name: str,
        description: str,
        door: Door,
        containers: list[Container] | None = None,
        items: list[Item] | None = None,
        hidden: list[Item] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.door = door
        self.containers = containers or []  # list of Container
        self.items = items or []  # loose items lying in the room
        self.hidden = hidden or []  # loose items no one sees until a `use` reveals them

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

    def reveal(self, name: str) -> None:
        """Bring a hidden item out of hiding: onto the floor, or into its container."""
        for found, hidden in [(self.items, self.hidden)] + [
            (c.contents, c.hidden) for c in self.containers
        ]:
            for item in [item for item in hidden if item.name == name]:
                hidden.remove(item)
                found.append(item)

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
    """The player: which room they are in, what they carry, and how many moves they've made."""

    def __init__(self, current_room: Room, inventory: Inventory) -> None:
        self.current_room = current_room
        self.inventory = inventory  # an Inventory (max CAPACITY items)
        self.moves = 0  # commands that changed the game (game.py decides which)

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
