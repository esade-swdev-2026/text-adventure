"""Draw a Screen with rich and read a line. The only module that prints during play."""

import signal
import time
from types import FrameType

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
    flash_screen,
    to_ascii,
    too_small_lines,
)

# The palette in docs/SCREEN-SPEC.md §6: 256-colour numbers, foreground only. Each one keeps at
# least 3:1 contrast on both black and white, so it reads on dark and light themes. Coloured
# roles are never dim, because dim on a colour can vanish on some themes.
SLATE, AMBER, GREY, BLUE, RED = "color(60)", "color(136)", "color(243)", "color(32)", "color(160)"
COLOR_STYLES: dict[Role, str] = {
    Role.TITLE: "bold",
    Role.BORDER: GREY,
    Role.SHADOW: SLATE,
    Role.LIT: AMBER,
    Role.LIGHT: f"bold {AMBER}",
    Role.NIGHT: BLUE,
    Role.DANGER: RED,
    Role.PLAIN: "",
    Role.FOCUS: "bold",
    Role.TEXT: "",
    Role.VERB: "",
    Role.LABEL: GREY,
    Role.RESULT: "bold",
    Role.ERROR: f"bold {RED}",
    Role.WIN: f"bold {BLUE}",
    Role.HISTORY: GREY,
    Role.NARRATION: "italic",
    Role.PROMPT: "bold",
}

# The no-colour column of the same table: weight only, exactly the v0.5 black-and-white
# style. Bold is what matters most, dim is what sits back. Used where rich finds no colour
# (output is not a terminal, or TERM=dumb).
NO_COLOR_STYLES: dict[Role, str] = {
    Role.TITLE: "bold",
    Role.BORDER: "dim",
    Role.SHADOW: "dim",
    Role.LIT: "",
    Role.LIGHT: "bold",
    Role.NIGHT: "",
    Role.DANGER: "",
    Role.PLAIN: "",
    Role.FOCUS: "bold",
    Role.TEXT: "",
    Role.VERB: "",
    Role.LABEL: "dim",
    Role.RESULT: "bold",
    Role.ERROR: "bold",
    Role.WIN: "bold",
    Role.HISTORY: "dim",
    Role.NARRATION: "italic",
    Role.PROMPT: "bold",
}

FLASH_SECONDS = 0.15  # long enough to see, short enough to feel like a camera flash


class _Resized(Exception):
    """The window changed size while the player was typing. Carries what was typed."""

    def __init__(self, typed: str) -> None:
        super().__init__(typed)
        self.typed = typed


def _typed_so_far() -> str:
    """The line being edited. libedit keeps the last submitted line, newline included, until
    the player types again; that line was already played, so it counts as nothing typed."""
    if readline is None:  # pragma: no cover
        return ""
    line = readline.get_line_buffer()
    return "" if "\n" in line or "\r" in line else line


class Terminal:
    """The real terminal: draws screens with rich and reads the player's commands."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console(highlight=False)
        self.margin = ""
        self.plain = not self.console.encoding.startswith("utf")
        self.screen: Screen | None = None
        self.styles = COLOR_STYLES if self.console.color_system else NO_COLOR_STYLES
        self._reading = False
        if not self.console.is_terminal:  # piped output: draw full width, never "too small"
            self.console.width = max(self.console.width, BLOCK_WIDTH)
        elif hasattr(signal, "SIGWINCH"):
            signal.signal(signal.SIGWINCH, self._on_resize)

    def _on_resize(self, _signal: int, _frame: FrameType | None) -> None:
        # Stop input() so the screen can be redrawn at the new size. The line is read here,
        # because readline clears it while the exception unwinds.
        if self._reading:
            raise _Resized(_typed_so_far())

    def _text(self, text: str) -> str:
        return to_ascii(text) if self.plain else text

    def fits(self) -> bool:
        width, height = self.console.size
        return not self.console.is_terminal or (width >= MIN_COLUMNS and height >= MIN_ROWS)

    def draw(self, screen: Screen) -> None:
        """Clear the terminal and draw the whole screen, centred both ways."""
        self.screen = screen
        self._redraw()

    def flash(self, screen: Screen) -> None:
        """Draw the screen with its picture lit white for an instant. The caller then draws
        the screen itself, so the room comes back after the flash."""
        self.draw(flash_screen(screen))
        time.sleep(FLASH_SECONDS)

    def _redraw(self) -> None:
        self.console.clear()
        if self.screen is None:
            return
        if not self.fits():
            self._draw_too_small()
            return
        width, height = self.console.size
        self.margin = " " * ((width - BLOCK_WIDTH) // 2)
        top = (height - MIN_ROWS) // 2 if self.console.is_terminal else 0
        for _ in range(top):
            self.console.print()
        for line in self.screen.rows:
            text = Text(self.margin)
            for segment, role in line:
                text.append(self._text(segment), style=self.styles[role])
            self.console.print(text, no_wrap=True, overflow="crop")
        if self.screen.footer:
            self.say(self.screen.footer, style=self.styles[Role.LABEL])

    def _draw_too_small(self) -> None:
        """Three lines centred both ways in whatever space there is; long lines are cut."""
        width, height = self.console.size
        self.margin = ""
        lines = too_small_lines(width, height)
        for _ in range(max(height - len(lines), 0) // 2):
            self.console.print()
        for message, role in lines:
            message = self._text(message)[:width]
            text = Text(" " * ((width - len(message)) // 2) + message, style=self.styles[role])
            self.console.print(text, no_wrap=True, overflow="crop")

    def _enable_tab(self, names: list[str]) -> None:
        if readline is None:
            return
        readline.set_completer_delims("")  # complete the whole line, so "open fu" → "open fuse box"
        binding = (
            "bind ^I rl_complete" if "libedit" in (readline.__doc__ or "") else "tab: complete"
        )
        readline.parse_and_bind(binding)

        def completer(_text: str, state: int) -> str | None:
            matches = complete(readline.get_line_buffer(), names)
            return matches[state] if state < len(matches) else None

        readline.set_completer(completer)

    def _prefill(self, typed: str) -> None:
        """Put back what the player had typed before a resize interrupted the prompt.

        This needs GNU readline. libedit (the macOS default) ignores the hook, so there the
        typed text is lost on resize.
        """
        if readline is None:
            return

        def hook() -> None:
            readline.insert_text(typed)
            readline.redisplay()

        readline.set_pre_input_hook(hook if typed else None)

    def read(self) -> str:
        """Show the drawn screen's prompt and return the typed line (EOFError on Ctrl-D).

        Tab completes verbs and the names the screen lists. A resize redraws the screen at
        once, keeping what has been typed so far where readline allows it.
        """
        screen = self.screen
        names = screen.names if screen else []
        typed = ""
        while True:
            self._enable_tab(names)
            self._prefill(typed)
            prompt = screen.prompt if screen and self.fits() else ""
            self._reading = True
            try:
                return self.console.input(
                    Text(self.margin + self._text(prompt), style=self.styles[Role.PROMPT])
                )
            except _Resized as resized:
                typed = resized.typed
                self._reading = False
                self._redraw()
            finally:
                self._reading = False

    def say(self, message: str, new_line: bool = False, style: str = "") -> None:
        """Print one line under the screen, in the text column, e.g. "Goodbye."."""
        if new_line:
            self.console.print()
        line = Text(self.margin + INDENT + self._text(message), style=style)
        self.console.print(line, no_wrap=True, overflow="crop")
