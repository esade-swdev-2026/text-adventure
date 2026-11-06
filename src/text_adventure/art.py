"""Room art: parse the art file and compose sprites onto the background by object state."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from rich.cells import cell_len

from .models import CLOSED, DOOR, OPEN, Room

SCREEN_WIDTH = 92  # cells, the picture area inside the room panel
ART_HEIGHT = 11  # rows
BACKGROUND = "background"
LIGHT = "light"  # optional map: "#" where the light falls, anything else is shadow
LIT = "#"
FLOOR = "@floor"  # placement suffix for where an item lies once dropped

_HEADER = re.compile(r"^\[([a-z0-9 :]+)\]$")


class ArtError(ValueError):
    """The art file is malformed."""


@dataclass(frozen=True)
class Position:
    """A cell in the art panel, counted from the top-left corner."""

    row: int
    column: int


@dataclass(frozen=True)
class Box:
    """The rectangle of cells an object's sprite covers right now."""

    top: int
    left: int
    height: int
    width: int

    def contains(self, row: int, column: int) -> bool:
        """True if the cell at (row, column) lies inside the box."""
        return (
            self.top <= row < self.top + self.height
            and self.left <= column < self.left + self.width
        )


@dataclass(frozen=True)
class DrawnObject:
    """An object that is visible right now: its name, its sprite section and where it goes."""

    name: str
    sprite: str
    position: Position


@dataclass(frozen=True)
class Art:
    """A background plus named sprites, and where each object's sprite goes (row, column)."""

    background: tuple[str, ...]
    sprites: Mapping[str, tuple[str, ...]]
    placements: Mapping[str, Position] = field(default_factory=dict)
    light: tuple[str, ...] = ()  # ART_HEIGHT rows of SCREEN_WIDTH cells; LIT where light falls


def sprite_key(name: str, state: str | None = None) -> str:
    """Return the section name for an object in a state, e.g. "toolbox:open"."""
    return f"{name}:{state}" if state else name


def floor_key(name: str) -> str:
    """The placement name for where a dropped item lies, e.g. "wrench@floor"."""
    return name + FLOOR


def _pad(lines: list[str], width: int) -> tuple[str, ...]:
    """Pad every line with spaces to exactly `width` cells."""
    return tuple(line + " " * (width - cell_len(line)) for line in lines)


def _check_cells(section: str, lines: list[str]) -> None:
    """Reject any character wider than one cell, which would shift the rest of the row."""
    for line in lines:
        for char in line:
            if cell_len(char) != 1:
                raise ArtError(f"[{section}] uses {char!r}, which is not one cell wide")


def _split_sections(text: str) -> dict[str, list[str]]:
    """Group the file's lines under their "[name]" headers, without trailing blank lines."""
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        header = _HEADER.match(line)
        if header:
            name = header.group(1)
            if name in sections:
                raise ArtError(f"section [{name}] appears twice")
            current = sections[name] = []
        elif current is not None:
            current.append(line)
        elif line:
            raise ArtError("art file must start with a [section] header")
    for lines in sections.values():
        while lines and not lines[-1]:
            lines.pop()
    return sections


def parse_art(text: str) -> Art:
    """Parse sections like "[background]" and "[toolbox:open]" into an Art (no placements)."""
    sprites: dict[str, tuple[str, ...]] = {}
    for name, lines in _split_sections(text).items():
        _check_cells(name, lines)
        width = max((cell_len(line) for line in lines), default=0)
        sprites[name] = _pad(lines, width)

    if BACKGROUND not in sprites:
        raise ArtError("art file has no [background] section")
    background = _full_size(BACKGROUND, sprites.pop(BACKGROUND))
    light = sprites.pop(LIGHT, None)
    light_map = (
        _full_size(LIGHT, light) if light is not None else (LIT * SCREEN_WIDTH,) * ART_HEIGHT
    )
    return Art(background, sprites, light=light_map)


def _full_size(section: str, rows: tuple[str, ...]) -> tuple[str, ...]:
    """Pad a section to the whole art panel, or raise ArtError if it is too big."""
    if len(rows) > ART_HEIGHT or any(cell_len(row) > SCREEN_WIDTH for row in rows):
        raise ArtError(f"[{section}] must fit in {SCREEN_WIDTH}x{ART_HEIGHT} cells")
    return _pad(list(rows) + [""] * (ART_HEIGHT - len(rows)), SCREEN_WIDTH)


COLORS = ":colors"  # suffix of a frame's optional colour map, e.g. "[open:colors]"
# One letter per cell in a colour map (docs/SCREEN-SPEC.md §7). A space or "." is shadow.
COLOR_LETTERS = frozenset(" .s#*nrf")


@dataclass(frozen=True)
class PictureSize:
    """The fixed size of one kind of picture, in terminal cells."""

    kind: str
    width: int
    height: int


ICON = PictureSize("icon", 8, 3)  # an inventory slot's picture
CLOSEUP = PictureSize("close-up", 92, 11)  # fills the room panel while inspecting


@dataclass(frozen=True)
class Frame:
    """One drawing of a picture, padded to its full size, with a colour letter per cell."""

    rows: tuple[str, ...]
    colors: tuple[str, ...]


@dataclass(frozen=True)
class Picture:
    """An icon or close-up: one frame per state. The first frame is the default."""

    size: PictureSize
    frames: Mapping[str, Frame]

    def frame(self, state: str | None = None) -> Frame:
        """The frame for this state, or the first frame if the state has none of its own."""
        if state is not None and state in self.frames:
            return self.frames[state]
        return next(iter(self.frames.values()))


def parse_picture(text: str, size: PictureSize) -> Picture:
    """Parse a picture file: "[state]" frames, each with an optional "[state:colors]" map.

    Every frame and map must fit in `size` and is padded to exactly that size.
    """
    sections = _split_sections(text)
    frames: dict[str, Frame] = {}
    for name, lines in sections.items():
        if name.endswith(COLORS):
            if name.removesuffix(COLORS) not in sections:
                raise ArtError(f"[{name}] has no [{name.removesuffix(COLORS)}] frame")
            continue
        colors = sections.get(name + COLORS, [])
        for line in colors:
            wrong = set(line) - COLOR_LETTERS
            if wrong:
                raise ArtError(f"[{name}{COLORS}] uses {min(wrong)!r}, which is not a colour")
        _check_cells(name, lines)
        frames[name] = Frame(_fit(name, lines, size), _fit(name + COLORS, colors, size))
    if not frames:
        raise ArtError(f"{size.kind} has no [state] frame")
    return Picture(size, frames)


def _fit(section: str, lines: list[str], size: PictureSize) -> tuple[str, ...]:
    """Pad a frame to exactly the picture's size, or raise ArtError if it is too big."""
    if len(lines) > size.height or any(cell_len(line) > size.width for line in lines):
        raise ArtError(f"[{section}] must fit in {size.width}x{size.height} cells ({size.kind})")
    return _pad(lines + [""] * (size.height - len(lines)), size.width)


def _state_sprite(art: Art, name: str, state: str, fallback: str) -> str:
    """The sprite for an object's state, e.g. "vent:flashed", or its open/closed one if the
    art has no sprite for that story state."""
    key = sprite_key(name, state)
    return key if key in art.sprites else sprite_key(name, fallback)


def drawn(art: Art, room: Room) -> list[DrawnObject]:
    """Each object drawn right now, in drawing order.

    Containers show the sprite for their state, items show inside an open container or on the
    floor (a dropped item at its "@floor" place), and the door comes last, locked, unlocked or
    open. Objects without a sprite or a place are not drawn.
    """
    found: list[DrawnObject] = []

    def add(name: str, key: str, place: str) -> None:
        if key in art.sprites and place in art.placements:
            found.append(DrawnObject(name, key, art.placements[place]))

    for container in room.containers:
        fallback = OPEN if container.is_open else CLOSED
        add(
            container.name,
            _state_sprite(art, container.name, container.state, fallback),
            container.name,
        )
        if container.is_open:
            for item in container.contents:
                add(item.name, sprite_key(item.name), item.name)
    for item in room.items:
        place = floor_key(item.name)
        add(item.name, sprite_key(item.name), place if place in art.placements else item.name)
    add(DOOR, sprite_key(DOOR, room.door.state), DOOR)
    return found


def sprite_box(art: Art, room: Room, name: str) -> Box | None:
    """The cells `name` covers right now, ignoring blank sprite rows, or None if not drawn."""
    for shown in drawn(art, room):
        if shown.name == name:
            sprite = art.sprites[shown.sprite]
            drawn_rows = [index for index, line in enumerate(sprite) if line.strip()]
            if not drawn_rows:
                return None
            width = max(cell_len(row.rstrip()) for row in sprite)
            top = shown.position.row + drawn_rows[0]
            return Box(top, shown.position.column, drawn_rows[-1] - drawn_rows[0] + 1, width)
    return None


def compose(art: Art, room: Room) -> list[str]:
    """Draw every visible object's sprite for its current state onto the background.

    Spaces before and after a sprite row's outline are transparent, so the background shows
    around the object's shape. Spaces inside the outline are opaque.
    """
    canvas = [list(row) for row in art.background]
    for shown in drawn(art, room):
        for sprite_row_index, sprite_row in enumerate(art.sprites[shown.sprite]):
            row = shown.position.row + sprite_row_index
            if not 0 <= row < len(canvas):
                continue
            outline = sprite_row.strip(" ")
            first_drawn = len(sprite_row) - len(sprite_row.lstrip(" "))
            for offset, char in enumerate(outline, first_drawn):
                column = shown.position.column + offset
                if 0 <= column < len(canvas[row]):
                    canvas[row][column] = char
    return ["".join(row) for row in canvas]
