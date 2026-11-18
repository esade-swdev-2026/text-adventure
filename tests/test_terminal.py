from io import StringIO

from rich.color import Color
from rich.console import Console
from rich.style import Style

from text_adventure.screen import BLOCK_WIDTH, Role
from text_adventure.terminal import COLOR_STYLES, NO_COLOR_STYLES, Terminal

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
