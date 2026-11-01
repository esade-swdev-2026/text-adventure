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
