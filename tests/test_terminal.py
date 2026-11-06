from io import StringIO

from rich.console import Console

from text_adventure.screen import BLOCK_WIDTH, Role
from text_adventure.terminal import ROLE_STYLES, Terminal


def test_every_role_has_a_no_colour_style() -> None:
    assert set(ROLE_STYLES) == set(Role)
    assert set(ROLE_STYLES.values()) <= {"", "bold", "dim", "italic"}


def test_piped_output_is_never_too_small() -> None:
    terminal = Terminal(Console(file=StringIO(), width=80, height=24))
    assert terminal.fits()
    assert terminal.console.width >= BLOCK_WIDTH
