"""The rules: apply one command to the player and say what happened. Never prints."""

from collections.abc import Mapping
from dataclasses import dataclass, replace

from .commands import Command, CommandError, Verb, parse
from .models import DOOR, Container, Door, Item, Player, Room, Thing, Use, pick_text

NBSP = " "  # keeps a command and its short form on one line when the text wraps
HELP_TEXT = (
    f"Verbs: look{NBSP}(l), inspect{NBSP}(x), open, take{NBSP}(get), drop, "
    f"use{NBSP}…{NBSP}on{NBSP}…, inventory{NBSP}(i), help{NBSP}(?), quit{NBSP}(q). "
    "Tab completes names."
)

# What `Inspection.kind` can be.
ITEM = "item"
CONTAINER = "container"


@dataclass(frozen=True)
class Inspection:
    """What `inspect` looked at, for the close-up view (docs/SCREEN-SPEC.md §4)."""

    name: str  # as typed in commands: "fuse box", "door"
    kind: str  # ITEM, CONTAINER or DOOR
    state: str | None  # picks the close-up frame; None for an item without a story state
    text: str  # the thing's detailed description in that state


@dataclass(frozen=True)
class Outcome:
    """What one command did: the message for the player, and whether the game goes on."""

    message: str
    error: bool = False
    won: bool = False
    quit: bool = False
    subject: str | None = None  # the object this command changed, if any
    moved: bool = False  # the command changed the game, so it counts as a move
    inspected: Inspection | None = None  # set by `inspect`
    flash: bool = False  # the room lights up white for an instant before it is drawn


def win_message(moves: int, par: int | None) -> str:
    """ "Escaped in 11 moves. Par is 8." with " Sharp." added at or under par."""
    message = f"Escaped in {moves} move{'' if moves == 1 else 's'}."
    if par is None:
        return message
    return f"{message} Par is {par}." + (" Sharp." if moves <= par else "")


def _names(names: list[str]) -> str:
    return ", ".join(names)


def _sentence(text: str) -> str:
    """Capitalise the first letter and end with a full stop: "a worn flathead." → "A worn…"."""
    text = text[:1].upper() + text[1:]
    return text if text.endswith((".", "!", "?", '"')) else text + "."


def _visible(player: Player, name: str) -> Thing | None:
    """The thing with this name that the player can see right now: the door, a container, an
    item on the floor or in an open container, or a carried item."""
    room = player.current_room
    if name == DOOR:
        return room.door
    return room.find_container(name) or room.find_visible_item(name) or player.inventory.find(name)


def _anywhere(room: Room, player: Player, name: str) -> Thing | None:
    """The thing with this name in the room or carried, even if hidden or shut away."""
    if name == DOOR:
        return room.door
    items = room.items + room.hidden + player.inventory.items
    for container in room.containers:
        if container.name == name:
            return container
        items += container.contents + container.hidden
    return next((item for item in items if item.name == name), None)


def _needs_met(player: Player, needs: Mapping[str, str]) -> bool:
    """True if every object named is in the state given."""
    room = player.current_room
    for name, state in needs.items():
        thing = _anywhere(room, player, name)
        if thing is None or thing.state != state:
            return False
    return True


def _open_container(player: Player, container: Container) -> Outcome:
    """Open a container, with its tool if it is locked; the tool is kept."""
    name = container.name
    if container.is_locked() and not player.inventory.has_item(container.required_item or ""):
        return Outcome(f"The {name} is locked.", error=True)
    if not _needs_met(player, container.needs):
        return Outcome(container.refusal, error=True)
    container.open(player.inventory)
    inside = [item.name for item in container.contents]
    if inside:
        found = f"Inside: {_names(inside)}."
    else:
        found = "You can't make anything out." if container.hidden else "It's empty."
    tool = f" with the {container.required_item}" if container.required_item else ""
    return Outcome(f"You open the {name}{tool}. {found}", subject=name, moved=True)


def _unlock_door(player: Player, door: Door) -> Outcome:
    """Unlock the door with its key, once whatever it waits for (e.g. power) is ready."""
    if door.is_unlocked:
        return Outcome("The door is already unlocked.")
    if not player.inventory.has_item(door.required_item or ""):
        return Outcome("The door is locked.", error=True)
    if not _needs_met(player, door.needs):
        return Outcome(door.refusal, error=True)
    door.unlock(player.inventory)
    text = door.unlock_text or f"You unlock the door with the {door.required_item}."
    return Outcome(text, subject=DOOR, moved=True)


def _open(player: Player, name: str) -> Outcome:
    room = player.current_room
    if name == DOOR:
        door = room.door
        if not door.open():
            return Outcome("The door is locked.", error=True)
        if door.next_room is None:
            return Outcome("The door swings open. You're out.", won=True, subject=DOOR, moved=True)
        player.current_room = door.next_room
        return Outcome(f"The door opens. You step into the {door.next_room.name}.", moved=True)

    container = room.find_container(name)
    if container is None:
        return Outcome(f"There is no {name} here.", error=True)
    if container.is_open:
        return Outcome(f"The {name} is already open.")
    return _open_container(player, container)


def _take(player: Player, name: str) -> Outcome:
    item = player.current_room.find_visible_item(name)
    if item is None:
        return Outcome(f"There is no {name} here.", error=True)
    try:
        player.take_item(item)
    except ValueError as refused:
        return Outcome(str(refused), error=True)
    return Outcome(f"You take the {name}.", subject=name, moved=True)


def _drop(player: Player, name: str) -> Outcome:
    item = player.inventory.find(name)
    if item is None:
        return Outcome(f"You aren't carrying a {name}.", error=True)
    player.drop_item(item)
    return Outcome(f"You drop the {name}.", subject=name, moved=True)


def _inventory(player: Player) -> Outcome:
    items = player.inventory.show_inventory()
    if not items:
        return Outcome("You are carrying nothing.")
    listed = [f"{item.name} ({item.describe()})" for item in items]
    return Outcome(f"You carry: {_names(listed)}.")


def _plain_details(thing: Thing, name: str) -> str:
    """What `inspect` says about a thing that has no detailed description of its own."""
    if isinstance(thing, Item):
        return _sentence(thing.describe())
    if isinstance(thing, Container):
        text = thing.open_text if thing.is_open else thing.closed_text
        return text or f"The {name} is {thing.state}."
    return f"The door is {thing.state}."


def _inspect(player: Player, name: str) -> Outcome:
    thing = _visible(player, name)
    if thing is None:
        return Outcome(f"There is no {name} here.", error=True)
    kind = ITEM if isinstance(thing, Item) else CONTAINER if isinstance(thing, Container) else DOOR
    text = pick_text(thing.details, thing.state) or _plain_details(thing, name)
    return Outcome(text, inspected=Inspection(name, kind, thing.state, text))


def _apply_use(player: Player, rule: Use, item: Item, target: Thing, target_name: str) -> Outcome:
    """Carry out one `use` rule from world.json."""
    if not _needs_met(player, rule.needs):
        return Outcome(rule.refusal, error=True)
    if rule.consume:
        player.inventory.use_item(item.name)
    if rule.state is not None and not isinstance(target, Door):
        target.story = rule.state
    for name in rule.reveal:
        player.current_room.reveal(name)
    return Outcome(rule.text, subject=target_name, moved=True, flash=rule.flash)


def _find_rule(uses: list[Use], item: str | None) -> Use | None:
    return next((rule for rule in uses if rule.item == item), None)


def _use(player: Player, item_name: str, target_name: str | None) -> Outcome:
    item = player.inventory.find(item_name)
    if item is None:
        return Outcome(f"You aren't carrying a {item_name}.", error=True)
    if target_name is None:
        own = _find_rule(item.uses, None)
        if own is None:
            return Outcome(f"Use the {item_name} on what?", error=True)
        return _apply_use(player, own, item, item, item_name)

    target = _visible(player, target_name)
    if target is None:
        return Outcome(f"There is no {target_name} here.", error=True)
    rule = _find_rule(target.uses, item_name)
    if rule is not None:
        return _apply_use(player, rule, item, target, target_name)
    # The tool for a lock works like opening (a container) or unlocking (the door).
    if isinstance(target, Door) and target.required_item == item_name:
        return _unlock_door(player, target)
    if isinstance(target, Container) and target.required_item == item_name:
        return _open(player, target_name)
    return Outcome(item.refusal or f"The {item_name} is no use on the {target_name}.", error=True)


def _apply_verb(player: Player, command: Command) -> Outcome:
    name = command.name or ""
    match command.verb:
        case Verb.INSPECT:
            return _inspect(player, name)
        case Verb.OPEN:
            return _open(player, name)
        case Verb.TAKE:
            return _take(player, name)
        case Verb.DROP:
            return _drop(player, name)
        case Verb.USE:
            return _use(player, name, command.target)
        case Verb.INVENTORY:
            return _inventory(player)
        case Verb.LOOK:
            return Outcome("You look around.")
        case Verb.HELP:
            return Outcome(HELP_TEXT)
        case Verb.QUIT:
            return Outcome("Goodbye.", quit=True)


def apply_command(player: Player, command: Command, par: int | None = None) -> Outcome:
    """Change the game state for one command and return what the player should be told.

    A command that changes the game counts as a move. Winning says how many moves it took,
    against `par` if the world sets one.
    """
    outcome = _apply_verb(player, command)
    if outcome.moved:
        player.moves += 1
    if outcome.won:
        outcome = replace(outcome, message=win_message(player.moves, par))
    return outcome


def play_turn(player: Player, text: str, par: int | None = None) -> Outcome | None:
    """Parse and apply one typed line. Return None for an empty line."""
    try:
        command = parse(text)
    except CommandError as error:
        return Outcome(str(error), error=True)
    return None if command is None else apply_command(player, command, par)
