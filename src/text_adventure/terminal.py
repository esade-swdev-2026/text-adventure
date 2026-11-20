"""Draw a Screen with rich and read a line. The only module that prints during play."""

import os
import re
import signal
import threading
import time
from collections.abc import Sequence
from types import FrameType

try:  # gives input() arrow keys, history and Tab; not on Windows, where the console edits lines
    import readline
except ImportError:  # pragma: no cover
    readline = None  # type: ignore[assignment]

from rich.console import Console
from rich.text import Text

from .art import (
    ART_HEIGHT,
    DIP_GAP,
    DIP_SECONDS,
    FLICKER_WAIT,
    Art,
    FlickerSchedule,
    flicker_wanted,
)
from .models import Room
from .screen import (
    BLOCK_WIDTH,
    INDENT,
    MIN_COLUMNS,
    MIN_ROWS,
    Line,
    Role,
    Screen,
    complete,
    flash_screen,
    to_ascii,
    too_small_lines,
)

# The palette in docs/SCREEN-SPEC.md §6: 256-colour numbers, foreground only, for dark themes.
# Each one keeps at least 3:1 contrast on black. The picture's light scale runs from cold to
# warm: SLATE, MAUVE, AMBER, GOLD, and PALE_GOLD for light sources. Coloured roles are never
# dim, because dim on a colour can vanish on some themes.
SLATE, MAUVE, AMBER, GOLD, PALE_GOLD = (
    "color(60)",
    "color(96)",
    "color(136)",
    "color(178)",
    "color(221)",
)
GREY, BLUE, RED = "color(243)", "color(32)", "color(160)"
COLOR_STYLES: dict[Role, str] = {
    Role.TITLE: "bold",
    Role.BORDER: GREY,
    Role.SHADOW: SLATE,
    Role.DUSK: MAUVE,
    Role.LIT: AMBER,
    Role.GLOW: GOLD,
    Role.LIGHT: f"bold {PALE_GOLD}",
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
    Role.DUSK: "dim",
    Role.LIT: "",
    Role.GLOW: "",
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

# Lamp flicker (docs/SCREEN-SPEC.md §5.6). Debug only: setting this to a number of seconds
# makes every flicker come that often, so pilotty need not wait 3 to 8 seconds. The cap of 3
# dips in any 10 seconds is kept either way.
FLICKER_EVERY_VARIABLE = "TEXT_ADVENTURE_FLICKER_EVERY"
SAVE_CURSOR, RESTORE_CURSOR = "\x1b7", "\x1b8"
HIDE_CURSOR, SHOW_CURSOR, RESET_STYLE = "\x1b[?25l", "\x1b[?25h", "\x1b[0m"
JOIN_SECONDS = 1.0  # the longest to wait for the flicker thread to stop

# readline skips what lies between these when it measures the prompt (RL_PROMPT_START_IGNORE
# and RL_PROMPT_END_IGNORE), so colour codes don't count as width.
ESCAPE_CODE = re.compile(r"\x1b\[[0-9;]*m")
IGNORE_START, IGNORE_END = "\x01", "\x02"


def picture_write(rows: Sequence[str], top: int, column: int) -> str:
    """The text that redraws the picture's rows in place and leaves the cursor where it was.

    `rows` are ready-made ANSI strings, one per picture row. `top` is how many terminal rows
    lie above the screen block (counted from 0) and `column` is where the picture starts
    (counted from 1). Picture row n is on terminal row `top + 2 + n`: the block's top border
    comes first. Only picture rows are written, never the prompt's row, and the cursor is
    saved and restored (and hidden meanwhile, so it does not visibly jump), all in one string
    so it goes out in one write and readline cannot slip a keystroke's echo in between.
    """
    moves = [f"\x1b[{top + 2 + n};{column}H{row}{RESET_STYLE}" for n, row in enumerate(rows)]
    return SAVE_CURSOR + HIDE_CURSOR + "".join(moves) + RESTORE_CURSOR + SHOW_CURSOR


def readline_prompt(ansi: str) -> str:
    """The prompt as `input()` should get it: each colour code wrapped so readline skips it.

    The prompt must go to `input()`, not be printed before it. readline thinks the line
    starts where its prompt does, so with an empty prompt, deleting the last typed character
    redraws the line from column 0 and wipes out the margin and the room name.
    """
    return ESCAPE_CODE.sub(lambda code: IGNORE_START + code.group() + IGNORE_END, ansi)


def _flicker_wait() -> tuple[float, float] | None:
    """The debug interval from the environment, or None for the normal 3 to 8 seconds."""
    try:
        seconds = float(os.environ[FLICKER_EVERY_VARIABLE])
    except (KeyError, ValueError):
        return None
    return (seconds, seconds) if seconds > 0 else None


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

    def __init__(self, console: Console | None = None, motion: bool = True) -> None:
        self.console = console or Console(highlight=False)
        self.motion = motion  # False for `play --no-motion`
        self.margin = ""
        self.plain = not self.console.encoding.startswith("utf")
        self.screen: Screen | None = None
        self.dipped: Screen | None = None  # the same screen with the lamp dipped, if it flickers
        self.styles = COLOR_STYLES if self.console.color_system else NO_COLOR_STYLES
        self.schedule = FlickerSchedule(wait=_flicker_wait() or FLICKER_WAIT)
        self._reading = False
        self._frames: tuple[str, str] | None = None  # the picture, normal and dipped, as ANSI
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()  # one writer to the terminal at a time
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

    def draw(self, screen: Screen, dipped: Screen | None = None) -> None:
        """Clear the terminal and draw the whole screen, centred both ways. Give `dipped`,
        the same screen built with the lamp dipped, if the picture should flicker while the
        player thinks (see `flicker_for`)."""
        self.screen = screen
        self.dipped = dipped
        self._redraw()

    def flicker_for(self, art: Art, room: Room, inspecting: bool) -> bool:
        """Should the screen about to be drawn flicker? The rules are `flicker_wanted`'s; this
        adds what only the terminal knows."""
        return flicker_wanted(
            art,
            room,
            inspecting=inspecting,
            color=self.styles is COLOR_STYLES,
            is_terminal=self.console.is_terminal,
            term=os.environ.get("TERM", ""),
            motion=self.motion,
        )

    def flash(self, screen: Screen) -> None:
        """Draw the screen with its picture lit white for an instant. `screen` is built at full
        light (`build_screen(..., flash=True)`); the caller then draws the normal screen, so
        the room comes back after the flash."""
        self.draw(flash_screen(screen))
        time.sleep(FLASH_SECONDS)

    def _redraw(self) -> None:
        with self._lock:
            self._frames = None
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
            if self.dipped is not None:
                self._frames = self._flicker_frames(self.screen, self.dipped, top)

    def _ansi(self, line: Line) -> str:
        """One row as the string rich would print for it, without the margin."""
        text = Text()
        for segment, role in line:
            text.append(self._text(segment), style=self.styles[role])
        with self.console.capture() as capture:
            self.console.print(text, end="", no_wrap=True, overflow="crop")
        return capture.get()

    def _flicker_frames(self, normal: Screen, dipped: Screen, top: int) -> tuple[str, str]:
        """The picture's rows, normal and dipped, each ready to write in one go. Done here, in
        the main thread, so the flicker thread never calls rich."""
        column = len(self.margin) + 3  # border and one cell of padding, counted from 1

        def frame(screen: Screen) -> str:
            # Row 0 of the block is the top border; the picture rows sit between the borders.
            picture = [self._ansi(screen.rows[1 + n][1:-1]) for n in range(ART_HEIGHT)]
            return picture_write(picture, top, column)

        return frame(normal), frame(dipped)

    def _flicker(self, stop: threading.Event, frames: tuple[str, str]) -> None:
        """The flicker thread: sleep until the schedule's next flicker, dip the picture, bring
        it back. It only writes ready-made strings. A dip is always put right again, even if
        `stop` is set meanwhile, so the picture is never left dim. If the terminal is gone (a
        broken pipe on quit), the thread ends quietly."""
        normal, dipped = frames
        after = time.monotonic()
        try:
            while not stop.is_set():
                flicker = self.schedule.next(after)
                if stop.wait(max(0.0, flicker.start - time.monotonic())):
                    return
                for dip in range(flicker.dips):
                    if dip and stop.wait(DIP_GAP):
                        return
                    try:
                        self._write(dipped)
                        time.sleep(DIP_SECONDS)
                    finally:
                        self._write(normal)
                after = flicker.start
        except OSError:
            return

    def _write(self, text: str) -> None:
        with self._lock:
            self.console.file.write(text)
            self.console.file.flush()

    def _start_flicker(self) -> None:
        """Start the flicker thread if the screen on show has a dipped twin."""
        if self._frames is None or self._thread is not None:
            return
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._flicker, args=(self._stop, self._frames), daemon=True, name="lamp-flicker"
        )
        self._thread.start()

    def _stop_flicker(self) -> None:
        """Stop the flicker thread, if it runs, and wait until it has put the picture right."""
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(JOIN_SECONDS)
        self._thread = None
        self.schedule.cancel_after(time.monotonic())  # dips planned but never run don't count

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

    def _prompt(self, prompt: str) -> str:
        """The margin and prompt, styled, as the string `input()` shows (see readline_prompt)."""
        text = Text(self.margin + self._text(prompt), style=self.styles[Role.PROMPT])
        with self.console.capture() as captured:
            self.console.print(text, end="", no_wrap=True, overflow="crop")
        ansi = captured.get()
        return ansi if readline is None else readline_prompt(ansi)

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
            self._start_flicker()  # before _reading, so a resize can't interrupt the start
            self._reading = True
            try:
                return input(self._prompt(prompt))
            except _Resized as resized:
                typed = resized.typed
                self._reading = False
                self._stop_flicker()  # the redraw below sets up the next one, if it fits
                self._redraw()
            finally:
                self._reading = False
                self._stop_flicker()

    def say(self, message: str, new_line: bool = False, style: str = "") -> None:
        """Print one line under the screen, in the text column, e.g. "Goodbye."."""
        if new_line:
            self.console.print()
        line = Text(self.margin + INDENT + self._text(message), style=style)
        self.console.print(line, no_wrap=True, overflow="crop")
