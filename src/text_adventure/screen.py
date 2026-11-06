"""Build the screen as rows of text tagged with roles. terminal.py only adds style and prints.

The layout follows docs/SCREEN-SPEC.md: a 96 × 29 block where every region has a fixed number
of rows, so the screen never changes shape between turns.
"""

import textwrap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum, auto

from rich.cells import cell_len

from .art import (
    ART_HEIGHT,
    ICON,
    LIT,
    SCREEN_WIDTH,
    Art,
    Box,
    Frame,
    Picture,
    compose,
    sprite_box,
)
from .models import DOOR, Container, Inventory, Room

MIN_COLUMNS = 100
MIN_ROWS = 30
BLOCK_WIDTH = SCREEN_WIDTH + 4  # picture + one cell of padding and one of border on each side
BLOCK_HEIGHT = MIN_ROWS - 1  # the last terminal row stays spare, so Enter never scrolls
PANEL_INNER_WIDTH = BLOCK_WIDTH - 2  # cells between the room panel's two side borders
INDENT = "  "
TEXT_WIDTH = SCREEN_WIDTH
DESCRIPTION_LINES = 3
HISTORY_LINES = 3
NEWEST_LINES = 2  # the newest history entry may wrap onto a second row
TITLE_MAX = 60
ELLIPSIS = "…"

# Where each region starts, counted from 0 (docs/SCREEN-SPEC.md §3 counts from 1).
DESCRIPTION_ROW = ART_HEIGHT + 2
PANELS_ROW = DESCRIPTION_ROW + DESCRIPTION_LINES + 1
HISTORY_ROW = PANELS_ROW + 7

DOOR_CLOSED_TEXT = "The door is shut tight."
DOOR_OPEN_TEXT = "The door stands open."
FIRST_HINT = "Type a verb and a thing, like  look  or  inspect door. Tab completes."
INSPECT_HINT = "Enter returns to the room"
WIN_FOOTER = "Thanks for playing."


class Tone(Enum):
    """How a history entry reads: story text, a result, a mistake, or the win."""

    NARRATION = auto()
    RESULT = auto()
    ERROR = auto()
    WIN = auto()


MARKERS = {Tone.NARRATION: "", Tone.RESULT: "» ", Tone.ERROR: "✗ ", Tone.WIN: "✓ "}


class Role(Enum):
    """What a piece of text is, so terminal.py can pick its style (docs/SCREEN-SPEC.md §6)."""

    TITLE = auto()
    BORDER = auto()
    SHADOW = auto()  # art outside the light
    LIT = auto()  # art in the lamp's light
    LIGHT = auto()  # light sources in the light
    NIGHT = auto()
    DANGER = auto()
    PLAIN = auto()  # art in the terminal's own colour, e.g. clue text
    FOCUS = auto()  # the object or slot the last command changed
    TEXT = auto()
    VERB = auto()
    LABEL = auto()
    RESULT = auto()
    ERROR = auto()
    WIN = auto()
    HISTORY = auto()
    NARRATION = auto()
    PROMPT = auto()


TONE_ROLES = {
    Tone.NARRATION: Role.NARRATION,
    Tone.RESULT: Role.RESULT,
    Tone.ERROR: Role.ERROR,
    Tone.WIN: Role.WIN,
}

# A picture's colour letters (docs/SCREEN-SPEC.md §7.2).
COLOR_ROLES = {
    " ": Role.SHADOW,
    ".": Role.SHADOW,
    "s": Role.SHADOW,
    LIT: Role.LIT,
    "*": Role.LIGHT,
    "n": Role.NIGHT,
    "r": Role.DANGER,
    "f": Role.PLAIN,
}

# Characters drawn as light sources (bold) where the room's light falls.
LIGHT_SOURCES = frozenset("▗▟█▙▖●*ϟ")

# The verb panel: (verb, short form). Help and Quit are about the game, so they sit back.
VERBS = [
    ("Look", "l"),
    ("Inspect", "x"),
    ("Open", ""),
    ("Take", "get"),
    ("Drop", ""),
    ("Use", ""),
    ("Help", "?"),
    ("Quit", "q"),
]
GAME_VERBS = frozenset({"Help", "Quit"})
VERB_WIDTH = 8
CELL_WIDTH = 14
VERB_PANEL_WIDTH = 32
PANEL_GAP = "  "
SLOTS = 4
SLOT_WIDTH = 14
SLOT_INNER = SLOT_WIDTH - 2
ICON_PAD = "  "

# Tab completion: verbs first, then a name for the verbs that take one.
TAB_VERBS = ["look", "inspect", "open", "take", "drop", "use", "inventory", "help", "quit"]
NAMED_VERBS = frozenset({"inspect", "x", "open", "take", "get", "drop", "use"})
USE = "use"
ON = "on"

type Segment = tuple[str, Role]
type Line = list[Segment]


@dataclass(frozen=True)
class Message:
    """One entry in the message history: what a command said, and how it reads."""

    text: str
    tone: Tone = Tone.RESULT


@dataclass(frozen=True)
class Inspected:
    """The thing shown in the inspect view: its name, description and close-up (if drawn).

    `state` picks the close-up frame; None means its first frame.
    """

    name: str
    description: str
    picture: Picture | None = None
    state: str | None = None


@dataclass(frozen=True)
class Screen:
    """One whole screen: every row above the prompt, the prompt, and the names Tab offers."""

    rows: list[Line]  # exactly BLOCK_HEIGHT - 1 rows
    prompt: str  # empty when the game is over
    names: list[str] = field(default_factory=list)
    footer: str = ""  # shown in place of the prompt when the game is over


def _cut(text: str, width: int) -> str:
    """Shorten text to `width` cells ending in …, cutting at a word boundary."""
    if len(text) + len(ELLIPSIS) <= width:
        return text.rstrip(" .,") + ELLIPSIS
    head = text[: width - len(ELLIPSIS)]
    if " " in head.strip():
        head = head[: head.rstrip().rindex(" ")]
    return head.rstrip(" .,") + ELLIPSIS


def fit(text: str, rows: int, first: str = "", rest: str = "") -> list[str]:
    """Wrap text to TEXT_WIDTH in exactly `rows` lines: pad short text, cut long text with …."""
    lines = textwrap.wrap(text, TEXT_WIDTH, initial_indent=first, subsequent_indent=rest)
    if len(lines) > rows:
        lines = lines[:rows]
        lines[-1] = _cut(lines[-1], TEXT_WIDTH)
    return lines + [""] * (rows - len(lines))


def _open_sentence(text: str, contents: list[str], say_empty: bool = True) -> str:
    """An open container's sentence, followed by what is inside it, or ", empty"."""
    if contents:
        return f"{text} Inside: {', '.join(contents)}."
    return text.removesuffix(".") + ", empty." if say_empty else text


def container_sentence(container: Container) -> str:
    """A container's sentence in its current state."""
    text = container.room_sentence()
    if not container.is_open:
        return text or f"There is a {container.name}."
    names = [item.name for item in container.contents]
    # Not "empty" while something hides inside, or when world.json words the state.
    say_empty = not container.hidden and container.state not in container.room_texts
    return _open_sentence(text or f"The {container.name} is open.", names, say_empty)


def object_sentences(room: Room) -> list[str]:
    """One sentence per object in its current state, then the door."""
    sentences = [container_sentence(container) for container in room.containers]
    sentences += [item.floor_text for item in room.items if item.floor_text]
    dropped = [item.name for item in room.items if not item.floor_text]
    if dropped:
        sentences.append(f"On the floor: {', '.join(dropped)}.")
    door_text = DOOR_OPEN_TEXT if room.door.is_open else DOOR_CLOSED_TEXT
    sentences.append(room.door.room_sentence() or door_text)
    return sentences


def describe_room(room: Room) -> str:
    """The room's mood text plus one sentence for each object in its current state."""
    return " ".join([room.description, *object_sentences(room)])


def description_rows(room: Room) -> list[str]:
    """The description in DESCRIPTION_LINES rows. The mood goes first when space runs out,
    so the state of every object, and the door, is always shown."""
    full = describe_room(room)
    if len(textwrap.wrap(full, TEXT_WIDTH)) <= DESCRIPTION_LINES:
        return fit(full, DESCRIPTION_LINES)
    return fit(" ".join(object_sentences(room)), DESCRIPTION_LINES)


def visible_names(room: Room, inventory: Inventory) -> list[str]:
    """Names Tab may offer: what can be seen in the room, what is carried, and the door.
    Items inside a closed container are never listed, so completion gives nothing away."""
    names = [container.name for container in room.containers]
    names += [item.name for item in room.items]
    for container in room.containers:
        if container.is_open:
            names += [item.name for item in container.contents]
    names += [item.name for item in inventory.items]
    names.append(DOOR)
    return list(dict.fromkeys(names))


def complete(typed: str, names: Sequence[str]) -> list[str]:
    """Whole-line completions for Tab: a verb first, then one of `names`.

    `ins` → `inspect `, `inspect fu` → `inspect fuse box`, `use scr` → `use screwdriver `,
    then `use screwdriver o` → `use screwdriver on `.
    """
    words = typed.lower().split()
    ends_with_space = typed.endswith(" ")
    if len(words) <= 1 and not ends_with_space:
        start = words[0] if words else ""
        return [v + (" " if v in NAMED_VERBS else "") for v in TAB_VERBS if v.startswith(start)]
    verb = words[0]
    if verb not in NAMED_VERBS:
        return []
    rest = " ".join(words[1:]) + (" " if ends_with_space and len(words) > 1 else "")
    if verb != USE:
        return [f"{verb} {name}" for name in names if name.startswith(rest)]
    matches = [f"{USE} {name} " for name in names if name.startswith(rest)]
    for name in names:
        if not rest.startswith(name + " "):
            continue
        tail = rest[len(name) + 1 :]
        if f"{ON} ".startswith(tail):
            matches.append(f"{USE} {name} {ON} ")
        elif tail.startswith(f"{ON} "):
            target = tail[len(ON) + 1 :]
            matches += [f"{USE} {name} {ON} {t}" for t in names if t.startswith(target)]
    return list(dict.fromkeys(matches))


def _runs(chars: str, roles: Sequence[Role]) -> Line:
    """Join neighbouring cells with the same role into one segment."""
    line: Line = []
    for char, role in zip(chars, roles, strict=True):
        if line and line[-1][1] is role:
            line[-1] = (line[-1][0] + char, role)
        else:
            line.append((char, role))
    return line


def room_picture(art: Art, room: Room, focus: Box | None = None) -> list[Line]:
    """The room composed for its current state, each cell in shadow, light or the spotlight."""
    lines = []
    for row, cells in enumerate(compose(art, room)):

        def role(column: int, char: str, row: int = row) -> Role:
            if focus and focus.contains(row, column):
                return Role.FOCUS
            if art.light[row][column] == LIT:
                return Role.LIGHT if char in LIGHT_SOURCES else Role.LIT
            return Role.SHADOW

        lines.append(_runs(cells, [role(column, char) for column, char in enumerate(cells)]))
    return lines


def frame_lines(frame: Frame, focus: bool = False) -> list[Line]:
    """A picture frame (close-up or icon) with each cell in its colour letter's role."""
    return [
        _runs(row, [Role.FOCUS if focus else COLOR_ROLES.get(c, Role.SHADOW) for c in colors])
        for row, colors in zip(frame.rows, frame.colors, strict=True)
    ]


def moves_label(moves: int) -> str:
    """The move counter in the border: `1 move`, `11 moves`."""
    return f"{moves} move" if moves == 1 else f"{moves} moves"


def top_border(title: str, moves: int) -> Line:
    """The room panel's top border: the title centred, the move counter near the right corner."""
    if len(title) > TITLE_MAX:
        title = title[: TITLE_MAX - len(ELLIPSIS)] + ELLIPSIS
    label = f" {title} "
    counter = f" {moves_label(moves)} "
    left = (PANEL_INNER_WIDTH - cell_len(label)) // 2  # as the spec mocks: odd column goes right
    right = PANEL_INNER_WIDTH - left - cell_len(label) - len(counter) - 1
    return [
        ("╭" + "─" * left, Role.BORDER),
        (label, Role.TITLE),
        ("─" * right, Role.BORDER),
        (counter, Role.LABEL),
        ("─╮", Role.BORDER),
    ]


def bottom_border(hint: str = "") -> Line:
    """The room panel's bottom border, with an optional hint near the left corner."""
    if not hint:
        return [("╰" + "─" * PANEL_INNER_WIDTH + "╯", Role.BORDER)]
    label = f" {hint} "
    rest = PANEL_INNER_WIDTH - 1 - len(label)
    return [("╰─", Role.BORDER), (label, Role.LABEL), ("─" * rest + "╯", Role.BORDER)]


def _framed(picture: list[Line]) -> list[Line]:
    return [[("│ ", Role.BORDER), *row, (" │", Role.BORDER)] for row in picture]


def _text(text: str, role: Role) -> Line:
    return [(INDENT + text, role)] if text else []


def verb_panel() -> list[Line]:
    """The fixed verb panel: 4 rows of 2 cells, each a verb padded to 8 and its short form."""
    rows: list[Line] = [[("╭" + "─" * (VERB_PANEL_WIDTH - 2) + "╮", Role.BORDER)]]
    for index in range(0, len(VERBS), 2):
        line: Line = [("│ ", Role.BORDER)]
        for verb, short in VERBS[index : index + 2]:
            verb_role = Role.LABEL if verb in GAME_VERBS else Role.VERB
            line += [
                (verb.ljust(VERB_WIDTH), verb_role),
                (short.ljust(CELL_WIDTH - VERB_WIDTH), Role.LABEL),
            ]
        line.append((" │", Role.BORDER))
        rows.append(line)
    rows.append([("╰" + "─" * (VERB_PANEL_WIDTH - 2) + "╯", Role.BORDER)])
    return rows


def slot(name: str | None, icon: Picture | None = None, focus: bool = False) -> list[Line]:
    """One inventory slot, 14 × 6: a frame, the icon centred, the name under it."""
    border = Role.FOCUS if focus else Role.BORDER
    rows: list[Line] = [[("╭" + "─" * SLOT_INNER + "╮", border)]]
    icon_rows = frame_lines(icon.frame(), focus) if icon is not None else []
    for index in range(ICON.height):
        if index < len(icon_rows):
            inside: Line = [(ICON_PAD, border), *icon_rows[index], (ICON_PAD, border)]
        else:
            inside = [(" " * SLOT_INNER, border)]
        rows.append([("│", border), *inside, ("│", border)])
    label = name or ""
    if len(label) > SLOT_INNER:
        label = label[: SLOT_INNER - len(ELLIPSIS)] + ELLIPSIS
    left = (SLOT_INNER - len(label)) // 2  # the odd space goes right
    centred = " " * left + label + " " * (SLOT_INNER - left - len(label))
    rows.append([("│", border), (centred, Role.VERB), ("│", border)])
    rows.append([("╰" + "─" * SLOT_INNER + "╯", border)])
    return rows


def panels(
    inventory: Inventory, icons: Mapping[str, Picture], focus: str | None = None
) -> list[Line]:
    """The verb panel and the four inventory slots side by side (rows 18-23)."""
    items = inventory.items[:SLOTS]
    slots = [slot(item.name, icons.get(item.name), focus == item.name) for item in items] + [
        slot(None) for _ in range(SLOTS - len(items))
    ]
    rows = []
    for index, verb_row in enumerate(verb_panel()):
        line: Line = [*verb_row]
        for column in slots:
            line += [(PANEL_GAP, Role.BORDER), *column[index]]
        rows.append(line)
    return rows


def history_rows(history: Sequence[Message]) -> list[Line]:
    """The last results, newest at the bottom. The newest is in its tone's role and may take
    two rows; older ones are dim and take one row each.

    Before the first command, the story so far (narration) sits above a one-line hint.
    """
    if all(message.tone is Tone.NARRATION for message in history):
        story = [row for message in history for row in fit(message.text, NEWEST_LINES) if row]
        rows = [_text(row, Role.NARRATION) for row in story[-(HISTORY_LINES - 1) :]]
        rows.append(_text(FIRST_HINT, Role.LABEL))
        return [[] for _ in range(HISTORY_LINES - len(rows))] + rows
    newest = history[-1]
    marker = MARKERS[newest.tone]
    newest_rows = [row for row in fit(newest.text, NEWEST_LINES, marker, " " * len(marker)) if row]
    rows = [_text(row, TONE_ROLES[newest.tone]) for row in newest_rows]
    room_left = HISTORY_LINES - len(rows)
    older = list(history[:-1])[-room_left:] if room_left else []
    for message in reversed(older):
        rows.insert(0, _text(fit(MARKERS[message.tone] + message.text, 1)[0], Role.HISTORY))
    return [[] for _ in range(HISTORY_LINES - len(rows))] + rows


def _layout(
    title: str,
    moves: int,
    picture: list[Line],
    hint: str,
    description: list[str],
    inventory: Inventory,
    icons: Mapping[str, Picture],
    history: Sequence[Message],
    slot_focus: str | None,
) -> list[Line]:
    """Every row above the prompt, top to bottom (docs/SCREEN-SPEC.md §3 row map)."""
    rows = [top_border(title, moves), *_framed(picture), bottom_border(hint)]
    rows += [_text(row, Role.TEXT) for row in description]
    rows.append([])
    rows += panels(inventory, icons, slot_focus)
    rows.append([])
    rows += history_rows(history)
    rows.append([])
    return rows


def build_screen(
    room: Room,
    inventory: Inventory,
    art: Art,
    history: Sequence[Message] = (),
    *,
    moves: int = 0,
    icons: Mapping[str, Picture] | None = None,
    focus: str | None = None,
    inspected: Inspected | None = None,
) -> Screen:
    """The main screen, or the inspect view when `inspected` is given.

    `history` is every entry so far, oldest first (the intro first, as narration). `focus`
    names the thing the last command changed: its slot is spotlit if it is carried, its
    sprite in the room otherwise.
    """
    icons = icons or {}
    carried = focus is not None and inventory.has_item(focus)
    room_focus = sprite_box(art, room, focus) if focus and not carried else None
    title, hint = room.name.upper(), ""
    picture = room_picture(art, room, room_focus)
    description = description_rows(room)
    if inspected is not None:
        title, hint = inspected.name.upper(), INSPECT_HINT
        description = fit(inspected.description, DESCRIPTION_LINES)
        if inspected.picture is not None:
            picture = frame_lines(inspected.picture.frame(inspected.state))
        else:  # no close-up drawn yet: the room stays, with the thing in the spotlight
            picture = room_picture(art, room, sprite_box(art, room, inspected.name))
    rows = _layout(
        title,
        moves,
        picture,
        hint,
        description,
        inventory,
        icons,
        history,
        focus if carried else None,
    )
    return Screen(rows, f"{INDENT}[{room.name}] > ", visible_names(room, inventory))


def flash_screen(screen: Screen) -> Screen:
    """The same screen with the whole picture in FOCUS: plain bold, a white flash
    (docs/SCREEN-SPEC.md §5). The frame, text and panels stay as they are."""
    rows = list(screen.rows)
    for index in range(1, 1 + ART_HEIGHT):  # the picture rows, between the panel's borders
        left, *picture, right = rows[index]
        rows[index] = [left, ("".join(text for text, _ in picture), Role.FOCUS), right]
    return replace(screen, rows=rows)


def build_win_screen(
    room: Room,
    inventory: Inventory,
    art: Art,
    history: Sequence[Message],
    ending: str,
    *,
    moves: int = 0,
    icons: Mapping[str, Picture] | None = None,
) -> Screen:
    """The last screen: the open door in the spotlight, the ending text, and no prompt."""
    rows = _layout(
        room.name.upper(),
        moves,
        room_picture(art, room, sprite_box(art, room, DOOR)),
        "",
        fit(ending, DESCRIPTION_LINES),
        inventory,
        icons or {},
        history,
        None,
    )
    return Screen(rows, "", footer=WIN_FOOTER)


# One ASCII character per cell for terminals that can't show UTF-8, so widths don't change.
ASCII_FALLBACK = str.maketrans(
    {
        **dict.fromkeys("╭╮╰╯┌┐└┘┬┴├┤╔╗╚╝╧╤┓┣┸┑╡┳┿╪", "+"),
        **dict.fromkeys("─▔━▀╸╺╾▬╌", "-"),
        **dict.fromkeys("═", "="),
        **dict.fromkeys("│║▌▐┃╻╹", "|"),
        **dict.fromkeys("▓▮█▟▙▜▛▆▄", "#"),
        **dict.fromkeys("▗▖▝▘", "."),
        **dict.fromkeys("▪▫▯", "o"),
        **dict.fromkeys("╨╥", "'"),
        "▒": "%",
        "╲": "\\",
        "╱": "/",
        "▁": "_",
        "░": ":",
        "ϟ": "*",
        "●": "@",
        "◦": "o",
        "·": ".",
        "»": ">",
        "✗": "x",
        "✓": "+",
        "×": "x",
        "╳": "x",
        "…": ".",
        " ": " ",
    }
)


def to_ascii(text: str) -> str:
    """Replace every non-ASCII character with a one-cell ASCII stand-in."""
    return text.translate(ASCII_FALLBACK)


def line_text(line: Line) -> str:
    """A row's text without its roles."""
    return "".join(text for text, _ in line)


def too_small_lines(columns: int, rows: int) -> list[tuple[str, Role]]:
    """What the too-small screen says (docs/SCREEN-SPEC.md §10), one role per line."""
    return [
        ("Make the window bigger", Role.TITLE),
        (f"The game needs {MIN_COLUMNS} × {MIN_ROWS}. It is now {columns} × {rows}.", Role.TEXT),
        ("It redraws as soon as it fits.", Role.LABEL),
    ]
