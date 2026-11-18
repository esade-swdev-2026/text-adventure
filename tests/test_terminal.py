import random
import re
import time
from io import StringIO

import pytest
from rich.color import Color
from rich.console import Console
from rich.style import Style

from text_adventure.art import ART_HEIGHT, DIP, FlickerSchedule
from text_adventure.models import Player
from text_adventure.screen import BLOCK_WIDTH, Role, Screen, build_screen, line_text
from text_adventure.terminal import (
    COLOR_STYLES,
    FLICKER_EVERY_VARIABLE,
    NO_COLOR_STYLES,
    Terminal,
    picture_write,
)
from text_adventure.world import World

# The 256-colour numbers docs/SCREEN-SPEC.md §6 allows: the light scale (slate, mauve, amber,
# gold, pale gold), grey, blue and red.
PALETTE = {60, 96, 136, 178, 221, 243, 32, 160}


def _contrast_on_black(number: int) -> float:
    """WCAG contrast ratio of a 256-colour number against pure black."""

    def channel(value: int) -> float:
        value_01 = value / 255
        return value_01 / 12.92 if value_01 <= 0.03928 else ((value_01 + 0.055) / 1.055) ** 2.4

    red, green, blue = Color.from_ansi(number).get_truecolor()
    luminance = 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)
    return (luminance + 0.05) / 0.05


def _colour_console() -> Console:
    return Console(file=StringIO(), force_terminal=True, color_system="256", width=100, height=30)


def test_every_role_has_a_colour_and_a_no_colour_style() -> None:
    assert set(COLOR_STYLES) == set(Role)
    assert set(NO_COLOR_STYLES) == set(Role)
    assert set(NO_COLOR_STYLES.values()) <= {"", "bold", "dim", "italic"}


def test_colours_come_from_the_palette_and_are_never_dim() -> None:
    for role, style in COLOR_STYLES.items():
        parsed = Style.parse(style)
        assert not parsed.dim, role
        assert parsed.bgcolor is None, role  # foreground only
        if parsed.color is not None:
            assert parsed.color.number in PALETTE, role


def test_every_palette_colour_reads_on_black() -> None:
    # Dark themes only (docs/SCREEN-SPEC.md §6): at least 3:1 against pure black.
    for number in PALETTE:
        assert _contrast_on_black(number) >= 3, number


def test_colour_keeps_the_weight_of_the_fallback() -> None:
    # Never colour alone: whatever is bold without colour is bold with it.
    for role, style in NO_COLOR_STYLES.items():
        assert Style.parse(COLOR_STYLES[role]).bold == Style.parse(style).bold, role


def test_a_colour_terminal_uses_the_palette() -> None:
    assert Terminal(_colour_console()).styles is COLOR_STYLES


def test_piped_output_has_no_colour() -> None:
    assert Terminal(Console(file=StringIO())).styles is NO_COLOR_STYLES


def test_lines_print_in_256_colours() -> None:
    console = _colour_console()
    Terminal(console).say("Goodbye.", style=COLOR_STYLES[Role.ERROR])
    output = console.file.getvalue()  # type: ignore[attr-defined]
    assert "38;5;160" in output
    assert "38;2;" not in output  # no truecolor upgrade


def test_piped_output_is_never_too_small() -> None:
    terminal = Terminal(Console(file=StringIO(), width=80, height=24))
    assert terminal.fits()
    assert terminal.console.width >= BLOCK_WIDTH


# --- Lamp flicker (docs/SCREEN-SPEC.md §5.6) -------------------------------------------------

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[78]")
MOVE = re.compile(r"\x1b\[(\d+);(\d+)H")


def _big_console() -> Console:
    """A colour terminal of 140 × 50: the block sits 3 rows down and 22 columns in."""
    return Console(
        file=StringIO(), force_terminal=True, color_system="256", width=140, height=50,
        highlight=False,
    )  # fmt: skip


def _screens(world: World, player: Player) -> tuple[Screen, Screen]:
    room = player.current_room

    def build(dip: int) -> Screen:
        return build_screen(
            room, player.inventory, world.art_for(room), moves=0, icons=world.icons, dip=dip
        )

    return build(0), build(DIP)


def test_picture_write_saves_the_cursor_moves_to_each_row_and_puts_the_cursor_back() -> None:
    text = picture_write(["one", "two"], top=3, column=25)
    assert text == (
        "\x1b7\x1b[?25l"  # save the cursor, hide it while it jumps about
        "\x1b[5;25Hone\x1b[0m"  # picture row 0 is terminal row top + 2
        "\x1b[6;25Htwo\x1b[0m"
        "\x1b8\x1b[?25h"  # restore the cursor, show it again
    )


def test_the_frames_write_only_the_pictures_rows_and_never_the_prompts(
    world: World, player: Player
) -> None:
    terminal = Terminal(_big_console())
    terminal.draw(*_screens(world, player))
    assert terminal._frames is not None
    for frame in terminal._frames:
        rows = [int(row) for row, _ in MOVE.findall(frame)]
        assert rows == list(range(5, 5 + ART_HEIGHT))  # block top border is row 4 (top = 3)
        assert {int(column) for _, column in MOVE.findall(frame)} == {25}  # margin 22 + 3
        assert frame.startswith("\x1b7") and frame.endswith("\x1b8\x1b[?25h")
    assert 3 + 43 not in rows  # the prompt is on terminal row top + 43


def test_the_frames_are_the_picture_normal_and_dipped(world: World, player: Player) -> None:
    normal, dipped = _screens(world, player)
    terminal = Terminal(_big_console())
    terminal.draw(normal, dipped)
    assert terminal._frames is not None
    for frame, screen in zip(terminal._frames, (normal, dipped), strict=True):
        written = [ANSI.sub("", part) for part in re.split(MOVE, frame)[3::3]]
        picture = [line_text(screen.rows[1 + n])[2:-2] for n in range(ART_HEIGHT)]
        assert written == picture
    assert terminal._frames[0] != terminal._frames[1]
    assert "38;5;" in terminal._frames[0]  # in the palette's 256 colours, rich's own codes


def test_a_screen_with_no_dipped_twin_does_not_flicker(world: World, player: Player) -> None:
    normal, _ = _screens(world, player)
    terminal = Terminal(_big_console())
    terminal.draw(normal)
    assert terminal._frames is None


def test_a_window_too_small_draws_no_frames(world: World, player: Player) -> None:
    console = Console(
        file=StringIO(), force_terminal=True, color_system="256", width=80, height=24
    )  # fmt: skip
    terminal = Terminal(console)
    terminal.draw(*_screens(world, player))
    assert terminal._frames is None


def test_the_flicker_thread_dips_the_picture_and_always_puts_it_right_again(
    world: World, player: Player
) -> None:
    console = _big_console()
    terminal = Terminal(console)
    terminal.schedule = FlickerSchedule(random.Random(1), wait=(0.01, 0.01))
    terminal.draw(*_screens(world, player))
    assert terminal._frames is not None
    normal, dipped = terminal._frames
    terminal._start_flicker()
    deadline = time.monotonic() + 5
    while dipped not in console.file.getvalue() and time.monotonic() < deadline:  # type: ignore[attr-defined]
        time.sleep(0.01)
    terminal._stop_flicker()
    output = console.file.getvalue()  # type: ignore[attr-defined]
    assert output.count(dipped) >= 1
    assert output.count(normal) == output.count(dipped)  # every dip was put right again
    assert output.endswith(normal)  # and the picture is not left dim when the thread stops
    assert terminal._thread is None
    written = len(output)
    time.sleep(0.3)
    assert len(console.file.getvalue()) == written  # type: ignore[attr-defined]


def test_stopping_before_the_first_flicker_writes_nothing(world: World, player: Player) -> None:
    console = _big_console()
    terminal = Terminal(console)  # the first flicker is 3 to 8 seconds away
    terminal.draw(*_screens(world, player))
    drawn = console.file.getvalue()  # type: ignore[attr-defined]
    terminal._start_flicker()
    terminal._stop_flicker()
    assert console.file.getvalue() == drawn  # type: ignore[attr-defined]


def test_the_flicker_thread_is_a_daemon_so_it_never_holds_the_game_open(
    world: World, player: Player
) -> None:
    terminal = Terminal(_big_console())
    terminal.draw(*_screens(world, player))
    terminal._start_flicker()
    try:
        assert terminal._thread is not None and terminal._thread.daemon
    finally:
        terminal._stop_flicker()


def _flickers(terminal: Terminal, world: World, player: Player, inspecting: bool = False) -> bool:
    room = player.current_room
    return terminal.flicker_for(world.art_for(room), room, inspecting)


def test_a_colour_terminal_that_fits_flickers_in_the_room(world: World, player: Player) -> None:
    assert _flickers(Terminal(_big_console()), world, player)


def test_no_flicker_with_no_motion_inspecting_or_in_a_dumb_terminal(
    world: World, player: Player, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert not _flickers(Terminal(_big_console(), motion=False), world, player)
    assert not _flickers(Terminal(_big_console()), world, player, inspecting=True)
    monkeypatch.setenv("TERM", "dumb")
    assert not _flickers(Terminal(_big_console()), world, player)


def test_no_flicker_when_output_is_piped_has_no_colour_or_does_not_fit(
    world: World, player: Player
) -> None:
    assert not _flickers(Terminal(Console(file=StringIO(), width=140, height=50)), world, player)
    no_colour = Console(
        file=StringIO(), force_terminal=True, color_system=None, width=140, height=50
    )
    assert not _flickers(Terminal(no_colour), world, player)
    small = Console(file=StringIO(), force_terminal=True, color_system="256", width=80, height=24)
    assert not _flickers(Terminal(small), world, player)


def test_the_debug_variable_sets_how_often_the_lamp_flickers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(FLICKER_EVERY_VARIABLE, "1")
    assert Terminal(_big_console()).schedule.next(0.0).start == 1.0
    monkeypatch.setenv(FLICKER_EVERY_VARIABLE, "soon")
    assert 3.0 <= Terminal(_big_console()).schedule.next(0.0).start <= 8.0


def test_the_debug_interval_cannot_lift_the_cap_of_three_dips_in_ten_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(FLICKER_EVERY_VARIABLE, "0.5")
    schedule = Terminal(_big_console()).schedule
    times: list[float] = []
    asked = 0.0
    while asked < 120:
        flicker = schedule.next(asked)
        times += flicker.times()
        asked = flicker.start
    assert max(sum(a <= b < a + 10.0 for b in times) for a in times) <= 3
