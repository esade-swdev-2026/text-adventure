"""Find the shortest way to win a world, for `check`. Plays a copy of the game; never prints."""

from collections import deque
from copy import deepcopy
from dataclasses import dataclass

from .commands import Command, Verb
from .game import Outcome, apply_command
from .models import DOOR, Inventory, Item, Player, Room
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


@dataclass(frozen=True)
class _Snapshot:
    """Everything play can change, saved so the game can be put back exactly."""

    room: Room
    moves: int
    lists: tuple[tuple[list[Item], tuple[Item, ...]], ...]  # each item list and what was in it
    flags: tuple[tuple[object, str, object], ...]  # (object, attribute, value)


class _Game:
    """One live copy of the world that the search plays on, saving and restoring its state.

    Copying the whole game for every try was nearly all of the search's work. Play only moves
    items between lists, sets a few flags and gives objects story states, so those are what
    `save` keeps and `restore` puts back; the texts and rules are never touched.
    """

    def __init__(self, world: World) -> None:
        self.player = deepcopy(Player(world.first_room, Inventory()))
        self.rooms: list[Room] = []
        room: Room | None = self.player.current_room
        while room is not None and room not in self.rooms:
            self.rooms.append(room)
            room = room.door.next_room
        self.lists = [self.player.inventory.items]
        self.switches: list[tuple[object, str]] = []
        for room in self.rooms:
            self.lists += [room.items, room.hidden]
            self.switches += [(room.door, "is_unlocked"), (room.door, "is_open")]
            for container in room.containers:
                self.lists += [container.contents, container.hidden]
                self.switches += [(container, "is_open"), (container, "story")]
        items = {id(item): item for items in self.lists for item in items}
        self.switches += [(item, "story") for item in items.values()]

    def save(self) -> _Snapshot:
        return _Snapshot(
            self.player.current_room,
            self.player.moves,
            tuple((items, tuple(items)) for items in self.lists),
            tuple((thing, name, getattr(thing, name)) for thing, name in self.switches),
        )

    def restore(self, snapshot: _Snapshot) -> None:
        self.player.current_room = snapshot.room
        self.player.moves = snapshot.moves
        for items, saved in snapshot.lists:
            items[:] = saved
        for thing, name, value in snapshot.flags:
            setattr(thing, name, value)

    def try_command(self, snapshot: _Snapshot, command: Command) -> Outcome:
        """Play the command from the saved state. `save` keeps the state it leads to."""
        self.restore(snapshot)
        return apply_command(self.player, command)


def command_text(command: Command) -> str:
    """The command as a player would type it: "use fuse on fuse box"."""
    text = f"{command.verb.value} {command.name}"
    return f"{text} on {command.target}" if command.target else text


def reachable(world: World) -> list[Player]:
    """One copy of the game in every state the player can reach before winning."""
    game = _Game(world)
    found, seen = [game.save()], {_key(game.player)}
    for snapshot in found:  # grows while it is walked: a breadth-first search
        game.restore(snapshot)
        for command in _candidates(game.player):
            outcome = game.try_command(snapshot, command)
            if outcome.moved and not outcome.won and _key(game.player) not in seen:
                seen.add(_key(game.player))
                found.append(game.save())
    players = []
    for snapshot in found:
        game.restore(snapshot)
        players.append(deepcopy(game.player))
    return players


def shortest_win(world: World) -> list[str] | None:
    """The fewest commands that win, as typed, or None if the world can't be won.

    A breadth-first search over game states: every command that counts as a move is tried
    from a saved state, and states already seen are skipped.
    """
    game = _Game(world)
    start = game.save()
    queue: deque[tuple[_Snapshot, list[str]]] = deque([(start, [])])
    seen = {_key(game.player)}
    while queue:
        snapshot, route = queue.popleft()
        game.restore(snapshot)
        for command in _candidates(game.player):
            outcome = game.try_command(snapshot, command)
            if not outcome.moved:
                continue
            steps = [*route, command_text(command)]
            if outcome.won:
                return steps
            key = _key(game.player)
            if key not in seen:
                seen.add(key)
                queue.append((game.save(), steps))
    return None
