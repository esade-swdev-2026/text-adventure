"""Room art: parse the art file, compose sprites onto the background by object state, turn
shade and light into tone characters, and plan the lamp's flicker (docs/SCREEN-SPEC.md §5)."""

import math
import random
import re
from bisect import insort
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from rich.cells import cell_len

from .models import CLOSED, DOOR, OPEN, Room

SCREEN_WIDTH = 92  # cells, the picture area inside the room panel
ART_HEIGHT = 24  # rows
BACKGROUND = "background"
SHADE = "shade"  # the surface's shade per cell, digits 0-9; also the suffix of a sprite's map
LIGHT = "light"  # the light falling on each cell, digits 0-9 or a colour letter
LIGHT_STATE = "light:"  # prefix of a light map used while an object is in a state
LIT = "#"
FLOOR = "@floor"  # placement suffix for where an item lies once dropped

DIGITS = frozenset("0123456789")
LIGHT_LETTERS = frozenset("nrf*")  # cells of a light map with a fixed colour role
DEFAULT_LIGHT = "6"  # a room without a [light] section is lit evenly, in the LIT band
FULL_LIGHT = 9

# Tone (docs/SCREEN-SPEC.md §5.1): t = shade × light / 81, black below BLACK, otherwise a
# ramp character picked with an ordered dither, so a smooth fall-off reads as a gradient.
RAMP = " ░▒▓█"
BLACK = 0.24
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

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
    light: tuple[str, ...] = ()  # ART_HEIGHT rows of SCREEN_WIDTH cells: a digit or a letter
    shade: tuple[str, ...] = ()  # ART_HEIGHT rows of SCREEN_WIDTH digits
    lights: Mapping[str, tuple[str, ...]] = field(default_factory=dict)  # by object state
    sprite_shades: Mapping[str, tuple[str, ...]] = field(default_factory=dict)  # by sprite key


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


def _check_allowed(section: str, lines: list[str], allowed: frozenset[str], what: str) -> None:
    """Reject any cell that is not a space or one of `allowed`, e.g. a letter in a shade map."""
    for line in lines:
        wrong = set(line) - allowed - {" "}
        if wrong:
            raise ArtError(f"[{section}] uses {min(wrong)!r}, which is not {what}")


def _levels(rows: tuple[str, ...]) -> tuple[str, ...]:
    """A padded digit map with its blank cells as "0"."""
    return tuple(row.replace(" ", "0") for row in rows)


def parse_art(text: str) -> Art:
    """Parse an art file into an Art (no placements): "[background]", the "[shade]" and
    "[light]" maps, light maps by state ("[light:power on]"), sprites ("[toolbox:open]") and
    their shade maps ("[toolbox:open:shade]")."""
    sections = _split_sections(text)
    if BACKGROUND not in sections:
        raise ArtError("art file has no [background] section")
    for name, lines in sections.items():
        _check_cells(name, lines)
    background = _full_size(BACKGROUND, sections.pop(BACKGROUND))

    shade = sections.pop(SHADE, None)
    if shade is not None:
        _check_allowed(SHADE, shade, DIGITS, "a digit")
    shade_map = _levels(_full_size(SHADE, shade or []))

    lights: dict[str, tuple[str, ...]] = {}
    for name in [name for name in sections if name.startswith(LIGHT_STATE)]:
        lines = sections.pop(name)
        _check_allowed(name, lines, DIGITS | LIGHT_LETTERS, "a light level or a colour letter")
        lights[name.removeprefix(LIGHT_STATE)] = _levels(_full_size(name, lines))
    light = sections.pop(LIGHT, None)
    if light is not None:
        _check_allowed(LIGHT, light, DIGITS | LIGHT_LETTERS, "a light level or a colour letter")
        light_map = _levels(_full_size(LIGHT, light))
    else:
        light_map = (DEFAULT_LIGHT * SCREEN_WIDTH,) * ART_HEIGHT

    suffix = ":" + SHADE
    shade_sections = {name: sections.pop(name) for name in list(sections) if name.endswith(suffix)}
    sprites = {
        name: _pad(lines, max((cell_len(line) for line in lines), default=0))
        for name, lines in sections.items()
    }
    sprite_shades: dict[str, tuple[str, ...]] = {}
    for name, lines in shade_sections.items():
        key = name.removesuffix(suffix)
        if key not in sprites:
            raise ArtError(f"[{name}] has no [{key}] sprite")
        _check_allowed(name, lines, DIGITS, "a digit")
        sprite_shades[key] = _levels(_fit_to(name, lines, sprites[key]))
    return Art(
        background,
        sprites,
        light=light_map,
        shade=shade_map,
        lights=lights,
        sprite_shades=sprite_shades,
    )


def _fit_to(section: str, lines: list[str], sprite: tuple[str, ...]) -> tuple[str, ...]:
    """Pad a sprite's shade map to exactly the sprite's size, or raise if it is bigger."""
    width = max((cell_len(row) for row in sprite), default=0)
    if len(lines) > len(sprite) or any(cell_len(line) > width for line in lines):
        raise ArtError(f"[{section}] must fit in its sprite ({width}x{len(sprite)} cells)")
    return _pad(lines + [""] * (len(sprite) - len(lines)), width)


def _full_size(section: str, rows: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Pad a section to the whole art panel, or raise ArtError if it is too big."""
    if len(rows) > ART_HEIGHT or any(cell_len(row) > SCREEN_WIDTH for row in rows):
        raise ArtError(f"[{section}] must fit in {SCREEN_WIDTH}x{ART_HEIGHT} cells")
    return _pad(list(rows) + [""] * (ART_HEIGHT - len(rows)), SCREEN_WIDTH)


def level(cell: str) -> int:
    """A light or shade cell as a number: its digit, 0 for a blank, full light for a letter."""
    if cell in DIGITS:
        return int(cell)
    return 0 if cell == " " else FULL_LIGHT


def tone(shade: int, light: int, row: int, column: int) -> str:
    """The tone character for a surface of `shade` under `light` (both 0-9) at this cell.

    Black below BLACK, otherwise ░▒▓█ with a 4 × 4 Bayer dither. The dither depends only on
    the position, so the same picture always draws the same characters.
    """
    strength = shade * light / (FULL_LIGHT * FULL_LIGHT)
    if strength < BLACK:
        return RAMP[0]
    dither = (BAYER[row % 4][column % 4] + 0.5) / 16
    step = math.floor(strength * (len(RAMP) - 1) + dither)
    return RAMP[min(len(RAMP) - 1, max(1, step))]


COLORS = ":colors"  # suffix of a frame's optional colour map, e.g. "[open:colors]"
SHADES = ":" + SHADE  # suffix of a frame's optional shade map, e.g. "[open:shade]"
# One letter per cell in a colour map (docs/SCREEN-SPEC.md §7.2). A space or "." is shadow;
# a digit is a light level, on the same scale as the room's light map.
COLOR_LETTERS = frozenset(" .s#*nrf") | DIGITS


@dataclass(frozen=True)
class PictureSize:
    """The fixed size of one kind of picture, in terminal cells."""

    kind: str
    width: int
    height: int


ICON = PictureSize("icon", 10, 4)  # an inventory slot's picture
CLOSEUP = PictureSize("close-up", SCREEN_WIDTH, ART_HEIGHT)  # fills the room panel


@dataclass(frozen=True)
class Frame:
    """One drawing of a picture, padded to its full size, with a colour letter per cell and,
    optionally, a shade digit per cell for its blank cells (drawn as tone)."""

    rows: tuple[str, ...]
    colors: tuple[str, ...]
    shade: tuple[str, ...] = ()


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
    """Parse a picture file: "[state]" frames, each with an optional "[state:colors]" map and
    an optional "[state:shade]" map.

    Every frame and map must fit in `size` and is padded to exactly that size.
    """
    sections = _split_sections(text)
    frames: dict[str, Frame] = {}
    for name, lines in sections.items():
        suffix = next((s for s in (COLORS, SHADES) if name.endswith(s)), None)
        if suffix is not None:
            if name.removesuffix(suffix) not in sections:
                raise ArtError(f"[{name}] has no [{name.removesuffix(suffix)}] frame")
            continue
        colors = sections.get(name + COLORS, [])
        _check_allowed(name + COLORS, colors, COLOR_LETTERS, "a colour")
        shade = sections.get(name + SHADES)
        if shade is not None:
            _check_allowed(name + SHADES, shade, DIGITS, "a digit")
        _check_cells(name, lines)
        frames[name] = Frame(
            _fit(name, lines, size),
            _fit(name + COLORS, colors, size),
            _levels(_fit(name + SHADES, shade, size)) if shade is not None else (),
        )
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


def _overlay(
    art: Art, room: Room, base: tuple[str, ...], cells: Callable[[str], tuple[str, ...]]
) -> list[str]:
    """Paint each visible object onto `base`, taking its cells from `cells(sprite key)`.

    Only cells inside a sprite row's outline are painted: spaces before and after it are
    transparent, so the background shows around the object's shape. Spaces inside are opaque.
    """
    canvas = [list(row) for row in base]
    for shown in drawn(art, room):
        sprite, source = art.sprites[shown.sprite], cells(shown.sprite)
        for sprite_row_index, sprite_row in enumerate(sprite):
            row = shown.position.row + sprite_row_index
            if not 0 <= row < len(canvas):
                continue
            first_drawn = len(sprite_row) - len(sprite_row.lstrip(" "))
            last_drawn = len(sprite_row.rstrip(" "))
            for offset in range(first_drawn, last_drawn):
                column = shown.position.column + offset
                if 0 <= column < len(canvas[row]):
                    canvas[row][column] = source[sprite_row_index][offset]
    return ["".join(row) for row in canvas]


def compose(art: Art, room: Room) -> list[str]:
    """Draw every visible object's sprite for its current state onto the background."""
    return _overlay(art, room, art.background, lambda key: art.sprites[key])


def compose_shade(art: Art, room: Room) -> list[str]:
    """The shade digit of every cell: the room's [shade] map, with each visible object's own
    shade map inside its outline (black where it has none)."""

    def cells(key: str) -> tuple[str, ...]:
        sprite = art.sprites[key]
        return art.sprite_shades.get(key) or tuple("0" * len(row) for row in sprite)

    base = art.shade or (("0" * SCREEN_WIDTH,) * len(art.background))
    return _overlay(art, room, base, cells)


def light_state(art: Art, room: Room) -> str | None:
    """The state whose "[light:<state>]" map is in use, or None for "[light]". If objects in
    different states each have a map, the first container in world.json order wins, then the
    door; items never pick one (docs/SCREEN-SPEC.md §5.2)."""
    states = [container.state for container in room.containers] + [room.door.state]
    return next((state for state in states if state in art.lights), None)


def light_for(art: Art, room: Room) -> tuple[str, ...]:
    """The light map in use: "[light:<state>]" while an object in the room is in that state
    (power-on lighting), otherwise "[light]"."""
    state = light_state(art, room)
    return art.light if state is None else art.lights[state]


# Lamp flicker (docs/SCREEN-SPEC.md §5.6). Everything that can be decided without a clock or a
# terminal is here, so tests can check it: how far a dip lowers the light, whether to flicker
# at all, and when the next flicker comes. terminal.py only runs the timer.
DIP = 2  # light levels a dip takes off
DIP_SECONDS = 0.07  # a dip lasts 70 ms
DIP_GAP = 0.07  # the light is normal for 70 ms between the two dips of a flicker
FLICKER_WAIT = (3.0, 8.0)  # seconds from one flicker to the next
POWER_ON = "power on"  # the light state that stops the flicker: the ceiling tube is on
MAX_DIPS = 3  # never more than this many dips in any WINDOW seconds: not a strobe
WINDOW = 10.0


def dimmed(light: Sequence[str], by: int) -> tuple[str, ...]:
    """A light map with every digit lowered by `by`, never below 0. Colour letters and blanks
    stay as they are, so the door's night and the red light do not dip."""
    lowered = str.maketrans({str(n): str(max(0, n - by)) for n in range(FULL_LIGHT + 1)})
    return tuple(row.translate(lowered) for row in light)


def flicker_wanted(
    art: Art,
    room: Room,
    *,
    inspecting: bool,
    color: bool,
    is_terminal: bool,
    term: str,
    motion: bool,
) -> bool:
    """Should the lamp flicker while the player thinks? Only in the room view (a close-up is
    still), in a room whose light flickers (`"flicker"`, §5.7), while the power is off
    (`[light:power on]` is not in use; other state maps don't stop it), and when the terminal
    can take it: colour on, stdout a terminal, TERM not dumb, and no `play --no-motion`.
    Whether the screen fits is left to the terminal, which checks it at every redraw, so the
    flicker starts once a small window is made big enough."""
    return (
        not inspecting
        and room.flicker
        and light_state(art, room) != POWER_ON
        and color
        and is_terminal
        and term != "dumb"
        and motion
    )


@dataclass(frozen=True)
class Flicker:
    """One flicker: one dip, or two with a gap between them. `start` is when the first dip
    begins, in seconds on whatever clock the caller keeps."""

    start: float
    dips: int

    def times(self) -> tuple[float, ...]:
        """When each of its dips begins."""
        return tuple(self.start + n * (DIP_SECONDS + DIP_GAP) for n in range(self.dips))


class FlickerSchedule:
    """Picks when the lamp flickers next, and keeps it from ever becoming a strobe.

    A flicker is one or two dips, 3 to 8 seconds after the one before. That alone allows 8 dips
    in 10 seconds (four flickers 3 seconds apart, two dips each), so the schedule remembers
    every dip it has planned: a flicker that would make a fourth dip within WINDOW seconds
    loses its second dip, and if that is not enough it waits until the oldest dip has left the
    window. Take a seeded `random.Random` and a test can plan ten minutes and check every window.
    """

    def __init__(
        self, rng: random.Random | None = None, wait: tuple[float, float] = FLICKER_WAIT
    ) -> None:
        self._random = rng or random.Random()
        self._wait = wait
        self._dips: list[float] = []  # when every planned dip begins, in order

    def _crowded(self, times: Sequence[float]) -> bool:
        """Would these dips, with the ones already planned, put more than MAX_DIPS in a window?"""
        merged = sorted([*self._dips, *times])
        return any(
            merged[index + MAX_DIPS] < merged[index] + WINDOW
            for index in range(len(merged) - MAX_DIPS)
        )

    def next(self, after: float) -> Flicker:
        """The next flicker, 3 to 8 seconds after `after` unless the cap pushes it later."""
        start = after + self._random.uniform(*self._wait)
        dips = self._random.choice((1, 2))
        while self._crowded(Flicker(start, dips).times()):
            if dips > 1:
                dips = 1
            else:
                leaving = [dip + WINDOW for dip in self._dips if dip + WINDOW > start]
                start = min(leaving)
        flicker = Flicker(start, dips)
        for time in flicker.times():
            insort(self._dips, time)
        return flicker

    def cancel_after(self, now: float) -> None:
        """Forget the planned dips that begin after `now`: the flicker thread stopped (the
        player pressed Enter) before they ran, so they must not count against the cap."""
        self._dips = [dip for dip in self._dips if dip <= now]
