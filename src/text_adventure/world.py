"""Build and check the world from already-parsed JSON data. Never reads files itself."""

import re
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from .art import (
    CLOSEUP,
    ICON,
    Art,
    Picture,
    PictureSize,
    Position,
    floor_key,
    sprite_key,
)
from .commands import ON_WORDS
from .models import (
    CLOSED,
    DOOR,
    LOCKED,
    OPEN,
    UNLOCKED,
    Container,
    Door,
    Item,
    Room,
    Thing,
    Use,
)

STATE_NAME = re.compile(r"^[a-z0-9]+( [a-z0-9]+)*$")  # also a valid picture frame name
BUILT_IN_STATES = frozenset({OPEN, CLOSED, LOCKED, UNLOCKED})


class WorldError(ValueError):
    """The world data breaks a rule. The message says which one, for the person writing it."""


@dataclass(frozen=True)
class World:
    first_room: Room
    intro: str
    ending: str
    art: Mapping[str, Art]  # keyed by room name
    icons: Mapping[str, Picture] = field(default_factory=dict)  # keyed by item name
    closeups: Mapping[str, Picture] = field(default_factory=dict)  # keyed by item/container name
    door_closeups: Mapping[str, Picture] = field(default_factory=dict)  # keyed by room name
    par: int | None = None  # moves a sharp player needs to win; None if the world sets none

    def art_for(self, room: Room) -> Art:
        """The drawing for this room, with its object placements."""
        return self.art[room.name]

    def icon_for(self, item_name: str) -> Picture | None:
        """The item's inventory icon, or None if it has none yet."""
        return self.icons.get(item_name)

    def closeup_for(self, room: Room, name: str) -> Picture | None:
        """The close-up of an item, a container or this room's door, or None if it has none."""
        if name == DOOR:
            return self.door_closeups.get(room.name)
        return self.closeups.get(name)

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


def missing_pictures(world: World) -> list[str]:
    """Each portable item without an icon and each object without a close-up.

    `check` shows these as warnings: the game runs without them, but E2 will draw them.
    """
    warnings: list[str] = []
    for room in world.rooms():
        for item in _all_items([room]):
            if item.portable and item.name not in world.icons:
                warnings.append(f'item "{item.name}" has no icon')
            if item.name not in world.closeups:
                warnings.append(f'item "{item.name}" has no close-up')
        warnings += [
            f'container "{container.name}" has no close-up'
            for container in room.containers
            if container.name not in world.closeups
        ]
        if room.name not in world.door_closeups:
            warnings.append(f'room "{room.name}": the door has no close-up')
    return warnings


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
    if ON_WORDS & set(name.split()):
        raise WorldError(
            f'{where}: name "{name}" can\'t contain "on", "in" or "with" (see `use … on …`)'
        )


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


@dataclass
class _Pictures:
    """The icons and close-ups loaded from disk, and which object uses which."""

    loaded: Mapping[str, Picture]
    icons: dict[str, Picture] = field(default_factory=dict)
    closeups: dict[str, Picture] = field(default_factory=dict)
    door_closeups: dict[str, Picture] = field(default_factory=dict)

    def find(self, json_object: Any, key: str, size: PictureSize, where: str) -> Picture | None:
        """The picture named by `key` ("icon" or "closeup"), checked to be the right kind."""
        path = _optional_str(json_object, key, where)
        if path is None:
            return None
        if path not in self.loaded:
            raise WorldError(f'{where}: no picture loaded for "{path}"')
        picture = self.loaded[path]
        if picture.size != size:
            raise WorldError(
                f'{where}: "{key}" needs {size.kind} size ({size.width}x{size.height}), '
                f"but {path} is {picture.size.kind} size"
            )
        return picture

    def add(self, found: dict[str, Picture], name: str, picture: Picture | None) -> None:
        if picture is not None:
            found[name] = picture


@dataclass(frozen=True)
class _BuiltRoom:
    room: Room
    next_id: str | None  # the id of the room the door leads to; None for the way out
    art: Art  # the room's art, with its placements filled in


def _both_states(name: str) -> list[str]:
    return [sprite_key(name, OPEN), sprite_key(name, CLOSED)]


def _check_state(state: str, where: str) -> None:
    """A story state set by a `use`: lower case words, and not one of the built-in states."""
    if not STATE_NAME.match(state) or state in BUILT_IN_STATES:
        raise WorldError(
            f'{where}: state "{state}" must be lower case words other than '
            f"{', '.join(sorted(BUILT_IN_STATES))}"
        )


def _details(json_object: dict[str, Any], where: str) -> dict[str, str]:
    """The "inspect" text: one text, or an object of texts by state (the first is the default)."""
    value = json_object.get("inspect")
    if value is None:
        return {}
    if isinstance(value, str):
        return {"": value}
    if (
        isinstance(value, dict)
        and value
        and all(isinstance(text, str) and text for text in value.values())
    ):
        return dict(value)
    raise WorldError(f'{where}: "inspect" must be a text, or an object of texts by state')


def _room_texts(json_object: dict[str, Any], where: str) -> dict[str, str]:
    """The "room_text": the object's sentence in the room description, by state."""
    value = _get(json_object, "room_text", dict, where, {})
    if not all(isinstance(text, str) and text for text in value.values()):
        raise WorldError(f'{where}: "room_text" must be an object of sentences by state')
    return value


def _needs(json_object: dict[str, Any], where: str) -> tuple[dict[str, str], str]:
    """The "needs" (object name → state) and the "refusal" said while one isn't met."""
    needs = _get(json_object, "needs", dict, where, {})
    if not all(isinstance(state, str) for state in needs.values()):
        raise WorldError(f'{where}: "needs" must map names to states')
    refusal = _get(json_object, "refusal", str, where, "")
    if needs and not refusal:
        raise WorldError(f'{where}: "needs" must come with a "refusal" text')
    return needs, refusal


def _build_use(use_json: Any, where: str, own: bool) -> Use:
    """One rule from a "uses" list. An item's own rules may leave out "item"."""
    item = _optional_str(use_json, "item", where)
    if item is None and not own:
        raise WorldError(f'{where}: each use needs an "item"')
    where = f'{where} use of "{item}"' if item else f"{where} own use"
    needs, refusal = _needs(use_json, where)
    state = _optional_str(use_json, "state", where)
    if state is not None:
        _check_state(state, where)
    reveal = _get(use_json, "reveal", list, where, [])
    if not all(isinstance(name, str) for name in reveal):
        raise WorldError(f'{where}: "reveal" must be a list of names')
    return Use(
        item,
        _get(use_json, "text", str, where),
        needs,
        refusal,
        state,
        tuple(reveal),
        _get(use_json, "consume", bool, where, False),
    )


def _build_uses(json_object: dict[str, Any], where: str, own: bool = False) -> list[Use]:
    uses = [
        _build_use(use_json, where, own) for use_json in _get(json_object, "uses", list, where, [])
    ]
    items = [use.item for use in uses]
    if len(set(items)) != len(items):
        raise WorldError(f"{where}: two uses for the same item")
    return uses


def _build_item(item_json: Any, where: str, drawing: _RoomDrawing, pictures: _Pictures) -> Item:
    """Build an item, recording where it is drawn ("sprite"), where it lies once dropped,
    and its icon and close-up."""
    name = _get(item_json, "name", str, where)
    _check_name(name, where)
    where = f"{where} {name}"
    drawing.place(name, _placement(item_json, where), [sprite_key(name)])
    drawing.place(floor_key(name), _placement(item_json, where, "floor"), [sprite_key(name)])
    pictures.add(pictures.icons, name, pictures.find(item_json, "icon", ICON, where))
    pictures.add(pictures.closeups, name, pictures.find(item_json, "closeup", CLOSEUP, where))
    return Item(
        name,
        _get(item_json, "description", str, where, ""),
        _get(item_json, "portable", bool, where, True),
        _get(item_json, "floor_text", str, where, ""),
        details=_details(item_json, where),
        uses=_build_uses(item_json, where, own=True),
        refusal=_get(item_json, "refusal", str, where, ""),
    )


def _build_items(
    items_json: list[Any], where: str, drawing: _RoomDrawing, pictures: _Pictures
) -> tuple[list[Item], list[Item]]:
    """Build a list of items, split into those in plain sight and those marked "hidden"."""
    shown: list[Item] = []
    hidden: list[Item] = []
    for item_json in items_json:
        item = _build_item(item_json, where, drawing, pictures)
        is_hidden = _get(item_json, "hidden", bool, f"{where} {item.name}", False)
        (hidden if is_hidden else shown).append(item)
    return shown, hidden


def _build_container(
    container_json: Any, where: str, drawing: _RoomDrawing, pictures: _Pictures
) -> Container:
    name = _get(container_json, "name", str, where)
    _check_name(name, where)
    where = f'container "{name}"'
    contents, hidden = _build_items(
        _get(container_json, "contents", list, where, []), f"{where} item", drawing, pictures
    )
    drawing.place(name, _placement(container_json, where), _both_states(name))
    pictures.add(pictures.closeups, name, pictures.find(container_json, "closeup", CLOSEUP, where))
    needs, refusal = _needs(container_json, where)
    return Container(
        name,
        contents,
        _optional_str(container_json, "required_item", where),
        _get(container_json, "closed_text", str, where, ""),
        _get(container_json, "open_text", str, where, ""),
        hidden=hidden,
        needs=needs,
        refusal=refusal,
        room_texts=_room_texts(container_json, where),
        details=_details(container_json, where),
        uses=_build_uses(container_json, where),
    )


def _build_door(door_json: Any, where: str, drawing: _RoomDrawing) -> Door:
    where = f"{where} door"
    required = _optional_str(door_json, "required_item", where)
    if required is None:
        raise WorldError(f"{where} needs a required_item")
    door_sprites = [sprite_key(DOOR, state) for state in (LOCKED, UNLOCKED, OPEN)]
    drawing.place(DOOR, _placement(door_json, where), door_sprites)
    needs, refusal = _needs(door_json, where)
    return Door(  # linked to the next room once every room is built
        None,
        required,
        needs=needs,
        refusal=refusal,
        unlock_text=_get(door_json, "unlock_text", str, where, ""),
        room_texts=_room_texts(door_json, where),
        details=_details(door_json, where),
        uses=_build_uses(door_json, where),
    )


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


def _build_room(
    room_json: Any, where: str, art: Mapping[str, Art], pictures: _Pictures
) -> _BuiltRoom:
    name = _get(room_json, "name", str, where)
    where = f'room "{name}"'
    drawing = _RoomDrawing()
    items, hidden = _build_items(
        _get(room_json, "items", list, where, []), f"{where} item", drawing, pictures
    )
    containers = [
        _build_container(container_json, f"{where} container", drawing, pictures)
        for container_json in _get(room_json, "containers", list, where, [])
    ]
    door_json = _get(room_json, "door", dict, where)
    door = _build_door(door_json, where, drawing)
    door_closeup = pictures.find(door_json, "closeup", CLOSEUP, f"{where} door")
    pictures.add(pictures.door_closeups, name, door_closeup)
    description = _get(room_json, "description", str, where)
    room = Room(name, description, door, containers, items, hidden)
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


def _room_things(room: Room) -> dict[str, Thing]:
    """Every object in a room by name: the door, the containers and every item, even hidden."""
    things: dict[str, Thing] = {DOOR: room.door}
    things.update((container.name, container) for container in room.containers)
    things.update((item.name, item) for item in _all_items([room]))
    return things


def _states(thing: Thing, stories: set[str]) -> set[str]:
    """Every state a thing can be in: its built-in ones and the story states uses give it."""
    if isinstance(thing, Door):
        return {LOCKED, UNLOCKED, OPEN}
    if isinstance(thing, Container):
        return {CLOSED, OPEN} | stories
    return stories


def _check_needs(needs: Mapping[str, str], where: str, states: dict[str, set[str]]) -> None:
    for name, state in needs.items():
        if name not in states:
            raise WorldError(f'{where}: needs "{name}", which isn\'t in this room')
        if state not in states[name]:
            raise WorldError(f'{where}: "{name}" is never "{state}"')


def _check_room_uses(room: Room, item_names: set[str]) -> None:
    """Every `use` names real things, every hidden item can be revealed, and every state named
    in "needs" or "inspect" is one the object can really be in."""
    where = f'room "{room.name}"'
    things = _room_things(room)
    hidden = {item.name for item in room.hidden}
    hidden |= {item.name for container in room.containers for item in container.hidden}
    stories: dict[str, set[str]] = {name: set() for name in things}
    revealed: set[str] = set()
    for name, thing in things.items():
        for use in thing.uses:
            at = f'{where}: using "{use.item}" on "{name}"' if use.item else f'{where}: "{name}"'
            if use.item is not None and use.item not in item_names:
                raise WorldError(f'{at}: there is no item "{use.item}"')
            if not isinstance(thing, Item) and use.item == thing.required_item:
                raise WorldError(f"{at}: it is already the required_item, so it needs no use")
            if use.state is not None:
                if isinstance(thing, Door):
                    raise WorldError(f"{at}: the door has no story states")
                stories[name].add(use.state)
            for secret in use.reveal:
                if secret not in hidden:
                    raise WorldError(f'{at}: "{secret}" is not a hidden item in this room')
            revealed.update(use.reveal)
    for secret in sorted(hidden - revealed):
        raise WorldError(f'{where}: hidden item "{secret}" is never revealed')

    states = {name: _states(thing, stories[name]) for name, thing in things.items()}
    for name, thing in things.items():
        for use in thing.uses:
            _check_needs(use.needs, f'{where}: using "{use.item}" on "{name}"', states)
        texts = [("inspect", state) for state in thing.details if state]
        if not isinstance(thing, Item):
            _check_needs(thing.needs, f'{where}: "{name}"', states)
            texts += [("room_text", state) for state in thing.room_texts]
        for key, state in texts:
            if state not in states[name]:
                raise WorldError(
                    f'{where}: "{name}" has a {key} for "{state}", a state it is never in'
                )


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


def picture_paths(world_json: Any) -> dict[str, PictureSize]:
    """Every icon and close-up file the world names, with the size it must be drawn at.

    Malformed data is skipped here; build_world reports it.
    """
    paths: dict[str, PictureSize] = {}

    def note(json_object: Any, kinds: dict[str, PictureSize]) -> None:
        if isinstance(json_object, dict):
            for key, size in kinds.items():
                if isinstance(json_object.get(key), str):
                    paths.setdefault(json_object[key], size)

    item_kinds = {"icon": ICON, "closeup": CLOSEUP}
    object_kinds = {"closeup": CLOSEUP}
    for room in _list(world_json, "rooms"):
        for item in _list(room, "items"):
            note(item, item_kinds)
        for container in _list(room, "containers"):
            note(container, object_kinds)
            for item in _list(container, "contents"):
                note(item, item_kinds)
        if isinstance(room, dict):
            note(room.get("door"), object_kinds)
    return paths


def _list(json_object: Any, key: str) -> list[Any]:
    """`key` of a JSON object if it is a list, else an empty list."""
    value = json_object.get(key) if isinstance(json_object, dict) else None
    return value if isinstance(value, list) else []


def build_world(
    world_json: Any, art: Mapping[str, Art], pictures: Mapping[str, Picture] | None = None
) -> World:
    """Turn parsed world.json data into linked rooms. Raise WorldError on any broken rule.

    `art` holds each room's parsed art file and `pictures` each icon and close-up file,
    both keyed by the path world.json uses.
    """
    found = _Pictures(pictures or {})
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
        built = _build_room(room_json, f"room {room_id}", art, found)
        if built.room.name in room_art:
            raise WorldError(f'two rooms are called "{built.room.name}"')
        rooms[room_id], next_ids[room_id] = built.room, built.next_id
        room_art[built.room.name] = built.art

    _check_names_unique(rooms.values())
    _check_required_items_exist(rooms.values())
    item_names = {item.name for item in _all_items(rooms.values())}
    for room in rooms.values():
        _check_room_uses(room, item_names)
    _link_doors(rooms, next_ids)
    return World(
        rooms[next(iter(rooms))],
        _get(world_json, "intro", str, "world", ""),
        _get(world_json, "ending", str, "world", ""),
        room_art,
        found.icons,
        found.closeups,
        found.door_closeups,
        _par(world_json),
    )


def _par(world_json: dict[str, Any]) -> int | None:
    """The optional "par": the number of moves a sharp player needs to win."""
    par = world_json.get("par")
    if par is not None and (not isinstance(par, int) or isinstance(par, bool) or par < 1):
        raise WorldError('world: "par" must be a whole number of moves, 1 or more')
    return par


def _all_items(rooms: Iterable[Room]) -> list[Item]:
    """Every item in these rooms, whether on the floor or inside a container."""
    items: list[Item] = []
    for room in rooms:
        items += room.items + room.hidden
        for container in room.containers:
            items += container.contents + container.hidden
    return items
