import importlib.util
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path
from types import ModuleType

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
    """The shortest way out of the built-in world, room by room: as many moves as its par."""
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
        # Darkroom
        "open camera bag",
        "take lens",
        "use lens on enlarger",
        "take negatives",
        "use negatives on enlarger",
        "open tray",
        "use wrench on cabinet",
        "take tongs",
        "use tongs on safelight",
        "take padlock key",
        "use padlock key on door",
        "open door",
        # Night Office: the inventory is full by the letter opener, so a spent tool goes
        "use tongs on radiator",
        "take matchbook",
        "use matchbook on lantern",
        "take shutter key",
        "open coat",
        "take desk key",
        "open desk",
        "drop wrench",
        "take letter opener",
        "use letter opener on alarm panel",
        "use shutter key on door",
        "open door",
    ]


SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


@pytest.fixture(scope="session")
def load_script() -> Callable[[str], ModuleType]:
    """Load a development script from scripts/ by name. It is not a package, so it is read
    from its file, the way `python scripts/<name>.py` would run it."""

    def load(name: str) -> ModuleType:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load
