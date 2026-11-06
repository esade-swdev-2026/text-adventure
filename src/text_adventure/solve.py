"""Find the shortest way to win a world, for `check`. Plays copies of the game; never prints."""

from collections import deque
from copy import deepcopy

from .commands import Command, Verb
from .game import apply_command
from .models import DOOR, Inventory, Item, Player
from .world import World

type StateKey = tuple[object, ...]


def _items(items: list[Item]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((item.name, item.story or "") for item in items))


def _key(player: Player) -> StateKey:
    """Everything that can change during play, so two equal keys are the same game."""
    room = player.current_room
    containers = tuple(
        (c.name, c.state, c.is_open, _items(c.contents), _items(c.hidden)) for c in room.containers
    )
    return (
        room.name,
        room.door.state,
        _items(room.items),
        _items(room.hidden),
        _items(player.inventory.items),
        containers,
    )


def _candidates(player: Player) -> list[Command]:
    """Every command worth trying right now: each verb on each thing the player can see."""
    room = player.current_room
    carried = [item.name for item in player.inventory.items]
    visible = [item.name for item in room.items]
    for container in room.containers:
        if container.is_open:
            visible += [item.name for item in container.contents]
    targets = [DOOR, *(c.name for c in room.containers), *visible, *carried]

    commands = [Command(Verb.OPEN, DOOR)]
    commands += [Command(Verb.OPEN, c.name) for c in room.containers if not c.is_open]
    commands += [Command(Verb.TAKE, name) for name in visible]
    commands += [Command(Verb.DROP, name) for name in carried]
    for item in carried:
        commands.append(Command(Verb.USE, item))
        commands += [Command(Verb.USE, item, target) for target in targets if target != item]
    return commands


def command_text(command: Command) -> str:
    """The command as a player would type it: "use fuse on fuse box"."""
    text = f"{command.verb.value} {command.name}"
    return f"{text} on {command.target}" if command.target else text


def reachable(world: World) -> list[Player]:
    """One copy of the game in every state the player can reach before winning."""
    start = deepcopy(Player(world.first_room, Inventory()))
    found, seen = [start], {_key(start)}
    for player in found:  # grows while it is walked: a breadth-first search
        for command in _candidates(player):
            after = deepcopy(player)
            outcome = apply_command(after, command)
            if outcome.moved and not outcome.won and _key(after) not in seen:
                seen.add(_key(after))
                found.append(after)
    return found


def shortest_win(world: World) -> list[str] | None:
    """The fewest commands that win, as typed, or None if the world can't be won.

    A breadth-first search over game states: every command that counts as a move is tried
    on a copy of the game, and states already seen are skipped.
    """
    start = deepcopy(Player(world.first_room, Inventory()))
    queue: deque[tuple[Player, list[str]]] = deque([(start, [])])
    seen = {_key(start)}
    while queue:
        player, route = queue.popleft()
        for command in _candidates(player):
            after = deepcopy(player)
            outcome = apply_command(after, command)
            if not outcome.moved:
                continue
            steps = [*route, command_text(command)]
            if outcome.won:
                return steps
            key = _key(after)
            if key not in seen:
                seen.add(key)
                queue.append((after, steps))
    return None
