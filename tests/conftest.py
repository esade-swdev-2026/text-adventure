import json
from importlib.resources import files

import pytest

from text_adventure.art import Art, parse_art
from text_adventure.models import Inventory, Player
from text_adventure.world import World, art_paths, build_world


@pytest.fixture
def world() -> World:
    """A fresh copy of the built-in world, read from package data like the real game."""
    package = files("text_adventure")
    world_json = json.loads((package / "world.json").read_text(encoding="utf-8"))
    art: dict[str, Art] = {
        path: parse_art(package.joinpath(*path.split("/")).read_text("utf-8"))
        for path in art_paths(world_json)
    }
    return build_world(world_json, art)


@pytest.fixture
def player(world: World) -> Player:
    return Player(world.first_room, Inventory())
