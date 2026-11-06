from importlib.resources import files

import pytest

from text_adventure.cli import load_world
from text_adventure.models import Inventory, Player
from text_adventure.world import World


@pytest.fixture
def world() -> World:
    """A fresh copy of the built-in world, read from package data like the real game."""
    package = files("text_adventure")
    return load_world(package / "world.json", package)


@pytest.fixture
def player(world: World) -> Player:
    return Player(world.first_room, Inventory())


@pytest.fixture
def win_script() -> list[str]:
    """The shortest way out of the built-in world: 12 moves, its par."""
    return [
        "open toolbox",
        "take wrench",
        "open vent",
        "take flashbulb",
        "use flashbulb on vent",
        "take fuse",
        "take screwdriver",
        "open fuse box",
        "take key",
        "use fuse on fuse box",
        "use key on door",
        "open door",
    ]
