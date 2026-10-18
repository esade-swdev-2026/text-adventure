"""Build and check the world from already-parsed JSON data. Never reads files itself."""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from .art import CLOSED, OPEN, Art, Position, floor_key, sprite_key
from .models import DOOR, Container, Door, Item, Room


class WorldError(ValueError):
    """The world data breaks a rule. The message says which one, for the person writing it."""


@dataclass(frozen=True)
class World:
    first_room: Room
    intro: str
    ending: str
    art: Mapping[str, Art]  # keyed by room name

    def art_for(self, room: Room) -> Art:
        """The drawing for this room, with its object placements."""
        return self.art[room.name]

    def rooms(self) -> list[Room]:
        """Every room, in the order the doors lead through them."""
        rooms = [self.first_room]
        while (next_room := rooms[-1].door.next_room) is not None:
            rooms.append(next_room)
        return rooms


@dataclass(frozen=True)
class WorldSummary:
    """How much a world contains, for the `check` command."""

    rooms: int
    containers: int
    items: int
    first_room: str


def summarize(world: World) -> WorldSummary:
    """Count the rooms, containers and items (loose or inside containers) in a world."""
    rooms = world.rooms()
    return WorldSummary(
        rooms=len(rooms),
        containers=sum(len(room.containers) for room in rooms),
        items=len(_all_items(rooms)),
        first_room=world.first_room.name,
    )


def _get[T](json_object: Any, key: str, kind: type[T], where: str, default: T | None = None) -> T:
    """Read `key` from a JSON object and check its type, or raise WorldError naming `where`."""
    if not isinstance(json_object, dict):
        raise WorldError(f"{where} must be an object")
    value = json_object.get(key, default)
    if not isinstance(value, kind):
        raise WorldError(f'{where} needs "{key}" ({kind.__name__})')
    return value


def _optional_str(json_object: dict[str, Any], key: str, where: str) -> str | None:
    value = json_object.get(key)
    if value is not None and not isinstance(value, str):
        raise WorldError(f'{where}: "{key}" must be a string or null')
    return value


def _check_name(name: str, where: str) -> None:
    if name != name.lower() or name != " ".join(name.split()) or not name:
        raise WorldError(f'{where}: name "{name}" must be lower case with single spaces')
    if name == DOOR:
        raise WorldError(f'{where}: "door" is reserved for the room\'s door')


def _placement(json_object: dict[str, Any], where: str, key: str = "sprite") -> Position | None:
    value = json_object.get(key)
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(n, int) and n >= 0 for n in value)
    ):
        raise WorldError(f'{where}: "{key}" must be [row, column] with numbers >= 0')
    return Position(value[0], value[1])


@dataclass
class _RoomDrawing:
    """Where each object in a room is drawn, and the art sections that needs."""

    placements: dict[str, Position] = field(default_factory=dict)
    needed_sprites: list[str] = field(default_factory=list)

    def place(self, key: str, position: Position | None, sprites: list[str]) -> None:
        if position is not None:
            self.placements[key] = position
            self.needed_sprites += sprites


@dataclass(frozen=True)
class _BuiltRoom:
    room: Room
    next_id: str | None  # the id of the room the door leads to; None for the way out
    art: Art  # the room's art, with its placements filled in


def _both_states(name: str) -> list[str]:
    return [sprite_key(name, OPEN), sprite_key(name, CLOSED)]


def _build_item(item_json: Any, where: str, drawing: _RoomDrawing) -> Item:
    """Build an item, recording where it is drawn ("sprite") and where it lies once dropped."""
    name = _get(item_json, "name", str, where)
    _check_name(name, where)
    where = f"{where} {name}"
    drawing.place(name, _placement(item_json, where), [sprite_key(name)])
    drawing.place(floor_key(name), _placement(item_json, where, "floor"), [sprite_key(name)])
    return Item(
        name,
        _get(item_json, "description", str, where, ""),
        _get(item_json, "portable", bool, where, True),
        _get(item_json, "floor_text", str, where, ""),
    )


def _build_container(container_json: Any, where: str, drawing: _RoomDrawing) -> Container:
    name = _get(container_json, "name", str, where)
    _check_name(name, where)
    where = f'container "{name}"'
    contents = [
        _build_item(item_json, f"{where} item", drawing)
        for item_json in _get(container_json, "contents", list, where, [])
    ]
    drawing.place(name, _placement(container_json, where), _both_states(name))
    return Container(
        name,
        contents,
        _optional_str(container_json, "required_item", where),
        _get(container_json, "closed_text", str, where, ""),
        _get(container_json, "open_text", str, where, ""),
    )


def _build_door(door_json: Any, where: str, drawing: _RoomDrawing) -> Door:
    where = f"{where} door"
    required = _optional_str(door_json, "required_item", where)
    if required is None:
        raise WorldError(f"{where} needs a required_item")
    drawing.place(DOOR, _placement(door_json, where), _both_states(DOOR))
    return Door(None, required)  # linked to the next room once every room is built


def _room_art(room_json: Any, where: str, art: Mapping[str, Art], drawing: _RoomDrawing) -> Art:
    """The room's art with its placements, after checking it has every section needed."""
    art_path = _get(room_json, "art", str, where)
    if art_path not in art:
        raise WorldError(f'{where}: no art loaded for "{art_path}"')
    room_art = art[art_path]
    for key in drawing.needed_sprites:
        if key not in room_art.sprites:
            raise WorldError(f"{where}: {art_path} has no [{key}] section")
    return replace(room_art, placements=drawing.placements)


def _build_room(room_json: Any, where: str, art: Mapping[str, Art]) -> _BuiltRoom:
    name = _get(room_json, "name", str, where)
    where = f'room "{name}"'
    drawing = _RoomDrawing()
    items = [
        _build_item(item_json, f"{where} item", drawing)
        for item_json in _get(room_json, "items", list, where, [])
    ]
    containers = [
        _build_container(container_json, f"{where} container", drawing)
        for container_json in _get(room_json, "containers", list, where, [])
    ]
    door_json = _get(room_json, "door", dict, where)
    door = _build_door(door_json, where, drawing)
    room = Room(name, _get(room_json, "description", str, where), door, containers, items)
    return _BuiltRoom(
        room,
        _optional_str(door_json, "next_room", f"{where} door"),
        _room_art(room_json, where, art, drawing),
    )


def _check_names_unique(rooms: Collection[Room]) -> None:
    names = [item.name for item in _all_items(rooms)]
    names += [container.name for room in rooms for container in room.containers]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise WorldError(f"names must be unique, but these repeat: {', '.join(duplicates)}")


def _check_required_items_exist(rooms: Collection[Room]) -> None:
    item_names = {item.name for item in _all_items(rooms)}
    for room in rooms:
        for required in [room.door.required_item] + [c.required_item for c in room.containers]:
            if required is not None and required not in item_names:
                raise WorldError(f'room "{room.name}": required_item "{required}" doesn\'t exist')


def _link_doors(rooms: dict[str, Room], next_ids: dict[str, str | None]) -> None:
    """Point each door at its next room. Only the last room's door may lead out."""
    for room_id, next_id in next_ids.items():
        if next_id is not None:
            if next_id not in rooms:
                raise WorldError(f'room {room_id}: next_room "{next_id}" doesn\'t exist')
            rooms[room_id].door.next_room = rooms[next_id]
    last_id = list(rooms)[-1]
    exits = [room_id for room_id, next_id in next_ids.items() if next_id is None]
    if exits != [last_id]:
        raise WorldError("exactly one door, the last room's, must lead out (next_room: null)")


def art_paths(world_json: Any) -> list[str]:
    """The art file named by each room, skipping anything malformed (build_world reports it)."""
    rooms = world_json.get("rooms") if isinstance(world_json, dict) else None
    if not isinstance(rooms, list):
        return []
    return [
        room["art"] for room in rooms if isinstance(room, dict) and isinstance(room.get("art"), str)
    ]


def build_world(world_json: Any, art: Mapping[str, Art]) -> World:
    """Turn parsed world.json data into linked rooms. Raise WorldError on any broken rule."""
    rooms_json = _get(world_json, "rooms", list, "world")
    if not rooms_json:
        raise WorldError("world needs at least one room")

    rooms: dict[str, Room] = {}
    next_ids: dict[str, str | None] = {}
    room_art: dict[str, Art] = {}
    for index, room_json in enumerate(rooms_json):
        room_id = _get(room_json, "id", str, f"room {index + 1}")
        if room_id in rooms:
            raise WorldError(f'two rooms have the id "{room_id}"')
        built = _build_room(room_json, f"room {room_id}", art)
        if built.room.name in room_art:
            raise WorldError(f'two rooms are called "{built.room.name}"')
        rooms[room_id], next_ids[room_id] = built.room, built.next_id
        room_art[built.room.name] = built.art

    _check_names_unique(rooms.values())
    _check_required_items_exist(rooms.values())
    _link_doors(rooms, next_ids)
    return World(
        rooms[next(iter(rooms))],
        _get(world_json, "intro", str, "world", ""),
        _get(world_json, "ending", str, "world", ""),
        room_art,
    )


def _all_items(rooms: Iterable[Room]) -> list[Item]:
    """Every item in these rooms, whether on the floor or inside a container."""
    items: list[Item] = []
    for room in rooms:
        items += room.items
        for container in room.containers:
            items += container.contents
    return items
