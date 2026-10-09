import pytest

from text_adventure.models import CAPACITY, Container, Door, Inventory, Item, Player, Room


def make_room(door=None, containers=None, items=None) -> Room:
    return Room("Lab", "A dark lab.", door or Door(None), containers, items)


# Door


def test_door_without_next_room_is_exit() -> None:
    assert Door(None).is_exit() is True
    assert Door(make_room()).is_exit() is False


def test_locked_door_stays_shut_without_key() -> None:
    assert Door(None, "key").open(Inventory()) is False


def test_locked_door_opens_and_uses_up_key() -> None:
    inventory = Inventory([Item("key")])
    assert Door(None, "key").open(inventory) is True
    assert not inventory.has_item("key")


# Container


def test_locked_container_stays_shut_without_item() -> None:
    container = Container("chest", required_item="key")
    assert container.open(Inventory()) is False
    assert container.is_open is False


def test_locked_container_opens_and_keeps_item() -> None:
    container = Container("chest", required_item="key")
    inventory = Inventory([Item("key")])
    assert container.open(inventory) is True
    assert container.is_open is True
    assert inventory.has_item("key")


# Room


def test_room_remove_item_from_open_container() -> None:
    item = Item("torch")
    container = Container("desk", [item])
    container.open(Inventory())
    room = make_room(containers=[container])
    assert room.remove_item(item) is item
    assert container.contents == []


def test_room_cannot_remove_item_from_closed_container() -> None:
    item = Item("torch")
    room = make_room(containers=[Container("desk", [item])])
    with pytest.raises(ValueError):
        room.remove_item(item)


# Inventory


def test_inventory_full_at_capacity() -> None:
    inventory = Inventory([Item(str(n)) for n in range(CAPACITY)])
    assert inventory.is_full()
    with pytest.raises(ValueError):
        inventory.pick_up_item(Item("one too many"))


def test_inventory_use_item_removes_and_returns_it() -> None:
    key = Item("key")
    inventory = Inventory([key])
    assert inventory.use_item("key") is key
    assert inventory.items == []


# Player


def test_player_take_item_moves_it_to_inventory() -> None:
    item = Item("torch")
    room = make_room(items=[item])
    player = Player(room, Inventory())
    player.take_item(item)
    assert player.inventory.items == [item]
    assert room.items == []


def test_player_cannot_take_non_portable_item() -> None:
    statue = Item("statue", portable=False)
    room = make_room(items=[statue])
    player = Player(room, Inventory())
    with pytest.raises(ValueError):
        player.take_item(statue)
    assert room.items == [statue]


def test_player_drop_item_puts_it_on_floor() -> None:
    item = Item("torch")
    room = make_room()
    player = Player(room, Inventory([item]))
    player.drop_item(item)
    assert room.items == [item]
    assert player.inventory.items == []
