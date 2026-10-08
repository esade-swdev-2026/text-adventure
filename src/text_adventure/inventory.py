"""Item and Inventory classes for the text adventure."""

from dataclasses import dataclass, field

CAPACITY = 4


@dataclass(frozen=True)
class Item:
    """Something the player can find, and maybe carry."""

    name: str
    description: str = ""
    portable: bool = True

    def describe(self) -> str:
        """Short text description of the item."""
        return f"A {self.name}"


@dataclass
class Inventory:
    """The items the player is carrying (at most `capacity`)."""

    items: list[Item] = field(default_factory=list)
    capacity: int = CAPACITY

    def count(self) -> int:
        """Number of items currently carried."""
        return len(self.items)

    def is_full(self) -> bool:
        """True when no more items can be carried."""
        return self.count() >= self.capacity

    def pick_up_item(self, item: Item) -> None:
        """Add an item to the inventory."""
        if not isinstance(item, Item):
            raise TypeError(f"Expected an Item, got {type(item).__name__}")
        if not item.portable:
            raise ValueError(f"You can't pick up the {item.name}.")
        if self.is_full():
            raise ValueError(f"Inventory is full. Drop an item to pick up {item.name}.")
        self.items.append(item)

    def drop_item(self, name: str) -> Item:
        """Remove an item by name and return it."""
        for item in self.items:
            if item.name == name:
                self.items.remove(item)
                return item
        raise ValueError(f"You aren't carrying '{name}'.")
