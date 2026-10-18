"""Build the screen as plain text tagged with roles. terminal.py only adds colour and prints.

The layout follows docs/SCREEN-SPEC.md: every area has a fixed height, so the screen never
changes shape between turns.
"""

import textwrap
from dataclasses import dataclass, field
from enum import Enum, auto

from .art import LIT, SCREEN_WIDTH, Art, Box, compose, sprite_box
from .models import DOOR, Inventory, Room

MIN_COLUMNS = 80
MIN_ROWS = 24
BLOCK_WIDTH = SCREEN_WIDTH + 4  # art + one cell of padding and one of border on each side
INDENT = "  "
TEXT_WIDTH = SCREEN_WIDTH
DESCRIPTION_LINES = 3
MESSAGE_LINES = 2
COMMAND_LINES = 2
COMMAND_GAP = " · "
COMMANDS_PREFIX = "Try  "
ELLIPSIS = "…"

DOOR_CLOSED_TEXT = "The door is shut tight."
DOOR_OPEN_TEXT = "The door stands open."
WIN_FOOTER = "Thanks for playing."
META_COMMANDS = ["look", "inventory", "help", "quit"]


class Tone(Enum):
    """How the last message reads: story text, a result, a mistake, or the win."""

    NARRATION = auto()
    RESULT = auto()
    ERROR = auto()
    WIN = auto()


MARKERS = {Tone.NARRATION: "", Tone.RESULT: "» ", Tone.ERROR: "✗ ", Tone.WIN: "✓ "}


class Role(Enum):
    """What a piece of text is, so terminal.py can pick its style."""

    BORDER = auto()
    TITLE = auto()
    ART = auto()  # art in shadow
    LIT = auto()  # art where the light falls
    FOCUS = auto()  # the object the last command changed
    TEXT = auto()
    LABEL = auto()
    COMMAND = auto()
    NARRATION = auto()
    RESULT = auto()
    ERROR = auto()
    WIN = auto()


TONE_ROLES = {
    Tone.NARRATION: Role.NARRATION,
    Tone.RESULT: Role.RESULT,
    Tone.ERROR: Role.ERROR,
    Tone.WIN: Role.WIN,
}

type Segment = tuple[str, Role]
type Line = list[Segment]


@dataclass(frozen=True)
class Screen:
    """Everything one screen shows, as plain text. layout() turns it into styled rows."""

    title: str
    art: list[str]
    description: list[str]  # exactly DESCRIPTION_LINES rows
    message: list[str]  # exactly MESSAGE_LINES rows, marker included
    tone: Tone
    commands: list[list[str]]  # exactly COMMAND_LINES rows of commands; empty when won
    carrying: str  # shown in the panel's bottom border
    prompt: str  # empty when the game is over
    options: list[str] = field(default_factory=list)  # every available command, for Tab
    footer: str = ""
    focus: Box | None = None  # the art to spotlight
    light: tuple[str, ...] = ()  # the art's light map, "#" where lit


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


def _open_sentence(text: str, contents: list[str]) -> str:
    """An open container's sentence, followed by what is inside it."""
    if contents:
        return f"{text} Inside: {', '.join(contents)}."
    return text.removesuffix(".") + ", empty."


def object_sentences(room: Room) -> list[str]:
    """One sentence per object in its current state, then the door."""
    sentences = []
    for container in room.containers:
        if container.is_open:
            text = container.open_text or f"The {container.name} is open."
            sentences.append(_open_sentence(text, [item.name for item in container.contents]))
        else:
            sentences.append(container.closed_text or f"There is a {container.name}.")
    sentences += [item.floor_text for item in room.items if item.floor_text]
    dropped = [item.name for item in room.items if not item.floor_text]
    if dropped:
        sentences.append(f"On the floor: {', '.join(dropped)}.")
    sentences.append(DOOR_OPEN_TEXT if room.door.is_open else DOOR_CLOSED_TEXT)
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


def available_commands(room: Room, inventory: Inventory) -> list[str]:
    """The exact commands that make sense right now, in the order the spec gives."""
    commands = [f"open {c.name}" for c in room.containers if not c.is_open]
    commands += [f"take {item.name}" for item in room.items]
    for container in room.containers:
        if container.is_open:
            commands += [f"take {item.name}" for item in container.contents]
    commands += [f"drop {item.name}" for item in inventory.items]
    commands.append(f"open {DOOR}")
    return commands + META_COMMANDS


def wrap_commands(commands: list[str]) -> list[list[str]]:
    """Group whole commands into COMMAND_LINES rows; the last row ends with … if some don't fit."""
    width = TEXT_WIDTH - len(COMMANDS_PREFIX)
    rows: list[list[str]] = [[]]
    for command in commands:
        row = rows[-1]
        if row and len(COMMAND_GAP.join([*row, command])) > width:
            if len(rows) == COMMAND_LINES:
                while row and len(COMMAND_GAP.join([*row, ELLIPSIS])) > width:
                    row.pop()
                row.append(ELLIPSIS)
                break
            rows.append([])
        rows[-1].append(command)
    return rows + [[] for _ in range(COMMAND_LINES - len(rows))]


def complete(typed: str, commands: list[str]) -> list[str]:
    """The available commands that start with what has been typed so far (for Tab)."""
    start = " ".join(typed.lower().split()) + (" " if typed.endswith(" ") and typed.strip() else "")
    return [command for command in commands if command.startswith(start)]


def carrying_text(inventory: Inventory) -> str:
    """The inventory status written into the panel's bottom border."""
    names = ", ".join(item.name for item in inventory.items) or "nothing"
    return f"Carrying ({inventory.count()}/{inventory.capacity}): {names}"


def _message(text: str, tone: Tone) -> list[str]:
    """The last message in MESSAGE_LINES rows, with its tone's marker on the first row."""
    marker = MARKERS[tone]
    return fit(text, MESSAGE_LINES, marker, " " * len(marker))


def build_screen(
    room: Room,
    inventory: Inventory,
    art: Art,
    message: str,
    tone: Tone = Tone.RESULT,
    focus: str | None = None,
) -> Screen:
    """Everything shown during play, as plain strings."""
    return Screen(
        title=room.name.upper(),
        art=compose(art, room),
        description=description_rows(room),
        message=_message(message, tone),
        tone=tone,
        commands=wrap_commands(available_commands(room, inventory)),
        options=available_commands(room, inventory),
        carrying=carrying_text(inventory),
        prompt=f"{INDENT}[{room.name}] > ",
        focus=sprite_box(art, room, focus) if focus else None,
        light=art.light,
    )


def build_win_screen(room: Room, art: Art, message: str, ending: str) -> Screen:
    """The last screen: the open door, the ending text, and no prompt."""
    return Screen(
        title=room.name.upper(),
        art=compose(art, room),
        description=fit(ending, DESCRIPTION_LINES),
        message=_message(message, Tone.WIN),
        tone=Tone.WIN,
        commands=[],
        carrying="",
        prompt="",
        footer=WIN_FOOTER,
        focus=sprite_box(art, room, DOOR),
        light=art.light,
    )


def _art_row(screen: Screen, row: int) -> Line:
    """Split one art row into runs: in the spotlight, in the light, or in shadow."""
    cells = screen.art[row]
    focus = screen.focus

    def role(column: int) -> Role:
        if focus and focus.contains(row, column):
            return Role.FOCUS
        if screen.light and screen.light[row][column] == LIT:
            return Role.LIT
        return Role.ART

    line: Line = []
    for column, char in enumerate(cells):
        current = role(column)
        if line and line[-1][1] is current:
            line[-1] = (line[-1][0] + char, current)
        else:
            line.append((char, current))
    return line


PANEL_INNER_WIDTH = BLOCK_WIDTH - len("╭╮")  # cells between the panel's two side borders
STATUS_LEAD = "─"  # border drawn before the carrying status, after the corner


def _top_border(title: str) -> Line:
    """The top border, with the room's name centred in it."""
    label = f" {title} "
    left = (PANEL_INNER_WIDTH - len(label)) // 2
    right = PANEL_INNER_WIDTH - left - len(label)
    return [("╭" + "─" * left, Role.BORDER), (label, Role.TITLE), ("─" * right + "╮", Role.BORDER)]


def _bottom_border(carrying: str) -> Line:
    """The bottom border, with what the player carries written into it."""
    room_for_status = PANEL_INNER_WIDTH - len(STATUS_LEAD) - len("  ") - len(STATUS_LEAD)
    if len(carrying) > room_for_status:
        carrying = _cut(carrying, room_for_status)
    status = f" {carrying} " if carrying else ""
    rest = PANEL_INNER_WIDTH - len(STATUS_LEAD) - len(status)
    return [
        ("╰" + STATUS_LEAD, Role.BORDER),
        (status, Role.LABEL),
        ("─" * rest + "╯", Role.BORDER),
    ]


def _panel(screen: Screen) -> list[Line]:
    """The framed art panel: top border, art rows, bottom border."""
    rows: list[Line] = [
        [("│ ", Role.BORDER), *_art_row(screen, row), (" │", Role.BORDER)]
        for row in range(len(screen.art))
    ]
    return [_top_border(screen.title), *rows, _bottom_border(screen.carrying)]


def _text(text: str, role: Role) -> Line:
    return [(INDENT + text, role)] if text else []


def _commands(row: list[str], first: bool) -> Line:
    """One row of the command hints; only the first row carries the "Try" label."""
    if not row:
        return []
    prefix = COMMANDS_PREFIX if first else " " * len(COMMANDS_PREFIX)
    line: Line = [(INDENT + prefix, Role.LABEL)]
    for index, command in enumerate(row):
        if index:
            line.append((COMMAND_GAP, Role.LABEL))
        line.append((command, Role.LABEL if command == ELLIPSIS else Role.COMMAND))
    return line


def layout(screen: Screen) -> list[Line]:
    """Every row above the prompt, top to bottom, as role-tagged segments."""
    lines = _panel(screen)
    lines += [_text(row, Role.TEXT) for row in screen.description]
    lines.append([])
    lines += [_text(row, TONE_ROLES[screen.tone]) for row in screen.message]
    lines.append([])
    if screen.commands:
        lines += [_commands(row, index == 0) for index, row in enumerate(screen.commands)]
        lines.append([])
    if screen.footer:
        lines.append(_text(screen.footer, Role.LABEL))
    return lines


# One ASCII character per cell for terminals that can't show UTF-8, so widths don't change.
ASCII_FALLBACK = str.maketrans(
    {
        **dict.fromkeys("╭╮╰╯┌┐└┘┬┴├┤╔╗╚╝╧╤┓┣┸┑╡", "+"),
        **dict.fromkeys("─▔━▀╸╾▬", "-"),
        **dict.fromkeys("═", "="),
        **dict.fromkeys("│║▌▐┃╻╹", "|"),
        **dict.fromkeys("▓▮█▟▙", "#"),
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
        "…": ".",
        "\u00a0": " ",
    }
)


def to_ascii(text: str) -> str:
    """Replace every non-ASCII character with a one-cell ASCII stand-in."""
    return text.translate(ASCII_FALLBACK)


def line_text(line: Line) -> str:
    """A row's text without its roles."""
    return "".join(text for text, _ in line)


def too_small_message(columns: int, rows: int) -> str:
    """What to show instead of the game when the terminal is below the minimum size."""
    return f"Make the window at least {MIN_COLUMNS}×{MIN_ROWS} (it is now {columns}×{rows})."
