"""The rules: apply one command to the player and say what happened. Never prints."""

from dataclasses import dataclass

from .commands import Command, CommandError, Verb, parse
from .models import DOOR, Player

NBSP = " "  # keeps a command and its short form on one line when the text wraps
HELP_TEXT = (
    f"Commands: look, open{NBSP}<thing>, take{NBSP}<thing>, drop{NBSP}<thing>, "
    f"inventory{NBSP}(i), help{NBSP}(?), quit{NBSP}(q)."
)


@dataclass(frozen=True)
class Outcome:
    """What one command did: the message for the player, and whether the game goes on."""

    message: str
    error: bool = False
    won: bool = False
    quit: bool = False
    subject: str | None = None  # the object this command changed, if any


def _names(names: list[str]) -> str:
    return ", ".join(names)


def _open(player: Player, name: str) -> Outcome:
    room, inventory = player.current_room, player.inventory
    if name == DOOR:
        door = room.door
        if not door.open(inventory):
            return Outcome("The door is locked.", error=True)
        if door.next_room is None:
            return Outcome("The door swings open. You're out.", won=True, subject=DOOR)
        player.current_room = door.next_room
        return Outcome(f"The door opens. You step into the {door.next_room.name}.")

    container = room.find_container(name)
    if container is None:
        return Outcome(f"There is no {name} here.", error=True)
    if container.is_open:
        return Outcome(f"The {name} is already open.")
    if not container.open(inventory):
        return Outcome(f"The {name} is locked.", error=True)
    inside = [item.name for item in container.contents]
    found = f"Inside: {_names(inside)}." if inside else "It's empty."
    tool = f" with the {container.required_item}" if container.required_item else ""
    return Outcome(f"You open the {name}{tool}. {found}", subject=name)


def _take(player: Player, name: str) -> Outcome:
    item = player.current_room.find_visible_item(name)
    if item is None:
        return Outcome(f"There is no {name} here.", error=True)
    try:
        player.take_item(item)
    except ValueError as refused:
        return Outcome(str(refused), error=True)
    return Outcome(f"You take the {name}.", subject=name)


def _drop(player: Player, name: str) -> Outcome:
    item = player.inventory.find(name)
    if item is None:
        return Outcome(f"You aren't carrying a {name}.", error=True)
    player.drop_item(item)
    return Outcome(f"You drop the {name}.", subject=name)


def _inventory(player: Player) -> Outcome:
    items = player.inventory.show_inventory()
    if not items:
        return Outcome("You are carrying nothing.")
    listed = [f"{item.name} ({item.describe()})" for item in items]
    return Outcome(f"You carry: {_names(listed)}.")


def apply_command(player: Player, command: Command) -> Outcome:
    """Change the game state for one command and return what the player should be told."""
    name = command.name or ""
    match command.verb:
        case Verb.OPEN:
            return _open(player, name)
        case Verb.TAKE:
            return _take(player, name)
        case Verb.DROP:
            return _drop(player, name)
        case Verb.INVENTORY:
            return _inventory(player)
        case Verb.LOOK:
            return Outcome("You look around.")
        case Verb.HELP:
            return Outcome(HELP_TEXT)
        case Verb.QUIT:
            return Outcome("Goodbye.", quit=True)


def play_turn(player: Player, text: str) -> Outcome | None:
    """Parse and apply one typed line. Return None for an empty line."""
    try:
        command = parse(text)
    except CommandError as error:
        return Outcome(str(error), error=True)
    return None if command is None else apply_command(player, command)
