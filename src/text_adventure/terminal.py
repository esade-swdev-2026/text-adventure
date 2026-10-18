"""Draw a Screen with rich and read a line. The only module that prints during play."""

try:  # gives input() arrow keys, history and Tab; not on Windows, where the console edits lines
    import readline
except ImportError:  # pragma: no cover
    readline = None  # type: ignore[assignment]

from rich.console import Console
from rich.text import Text

from .screen import (
    BLOCK_WIDTH,
    INDENT,
    MIN_COLUMNS,
    MIN_ROWS,
    Role,
    Screen,
    complete,
    layout,
    to_ascii,
    too_small_message,
)

# The noir palette from docs/SCREEN-SPEC.md §3: no colour at all, only weight. Bold is what
# the light falls on, dim is what sits in shadow. This reads the same on dark and light themes.
STYLE_TITLE = "bold"
STYLE_BORDER = "dim"
STYLE_SHADOW = "dim"  # art outside the light map
STYLE_LIT = ""  # art inside it
STYLE_LIGHT = "bold"  # light sources themselves
STYLE_FOCUS = "bold"
STYLE_RESULT = "bold"
STYLE_ERROR = "bold"
STYLE_WIN = "bold"
STYLE_NARRATION = "italic"
STYLE_LABEL = "dim"
STYLE_COMMAND = ""  # plain, so the bold result line is what the eye finds first
STYLE_PROMPT = "bold"
STYLE_TEXT = ""

ROLE_STYLES: dict[Role, str] = {
    Role.BORDER: STYLE_BORDER,
    Role.TITLE: STYLE_TITLE,
    Role.ART: STYLE_SHADOW,
    Role.LIT: STYLE_LIT,
    Role.FOCUS: STYLE_FOCUS,
    Role.TEXT: STYLE_TEXT,
    Role.LABEL: STYLE_LABEL,
    Role.COMMAND: STYLE_COMMAND,
    Role.NARRATION: STYLE_NARRATION,
    Role.RESULT: STYLE_RESULT,
    Role.ERROR: STYLE_ERROR,
    Role.WIN: STYLE_WIN,
}

# Light sources are bold wherever the light map says the light falls.
LIGHT_SOURCES = r"[▗▟█▙▖●*ϟ@#]"


class Terminal:
    """The real terminal: draws screens with rich and reads the player's commands."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console(highlight=False)
        self.margin = ""
        self.plain = not self.console.encoding.startswith("utf")

    def _text(self, text: str) -> str:
        return to_ascii(text) if self.plain else text

    def _fits(self) -> bool:
        width, height = self.console.size
        return width >= MIN_COLUMNS and height >= MIN_ROWS

    def draw(self, screen: Screen) -> None:
        """Clear the terminal and draw the whole screen, centred horizontally."""
        self.console.clear()
        width, height = self.console.size
        if not self._fits():
            self.margin = ""
            self.console.print(self._text(too_small_message(width, height)), style=STYLE_ERROR)
            return
        self.margin = " " * ((width - BLOCK_WIDTH) // 2)
        lines = layout(screen)
        rows_used = len(lines) + 1  # and the prompt
        for _ in range((height - rows_used) // 2 if self.console.is_terminal else 0):
            self.console.print()
        for line in lines:
            text = Text(self.margin)
            for segment, role in line:
                piece = Text(self._text(segment), style=ROLE_STYLES[role])
                if role is Role.LIT:
                    piece.highlight_regex(LIGHT_SOURCES, STYLE_LIGHT)
                text.append_text(piece)
            self.console.print(text, no_wrap=True, overflow="crop")

    def _enable_tab(self, options: list[str]) -> None:
        if readline is None:
            return
        readline.set_completer_delims("")  # complete the whole line, so "open fu" → "open fuse box"
        binding = (
            "bind ^I rl_complete" if "libedit" in (readline.__doc__ or "") else "tab: complete"
        )
        readline.parse_and_bind(binding)

        def completer(_text: str, state: int) -> str | None:
            matches = complete(readline.get_line_buffer(), options)
            return matches[state] if state < len(matches) else None

        readline.set_completer(completer)

    def read(self, prompt: str, options: list[str] | None = None) -> str:
        """Show the prompt and return the typed line (raises EOFError on Ctrl-D).
        Tab completes any of `options`."""
        self._enable_tab(options or [])
        return self.console.input(Text(self.margin + self._text(prompt), style=STYLE_PROMPT))

    def say(self, message: str, new_line: bool = False) -> None:
        """Print one line under the screen, e.g. "Goodbye."."""
        if new_line:
            self.console.print()
        self.console.print(
            self.margin + INDENT + self._text(message), highlight=False, markup=False
        )
