"""scripts/bake_closeup.py drafts the screwdriver close-up. The art file is hand-edited after
a bake, so these tests check the draft's properties, not the committed picture."""

from collections.abc import Callable
from types import ModuleType

import pytest

from text_adventure.art import CLOSEUP, parse_picture

HANDLE_LIGHTS = "56789"


@pytest.fixture(scope="module")
def bake(load_script: Callable[[str], ModuleType]) -> ModuleType:
    return load_script("bake_closeup")


def sections(text: str) -> dict[str, list[str]]:
    """The draft's rows by section name, each padded to the full 92 × 24."""
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("["):
            current = found.setdefault(line.strip("[]"), [])
        elif current is not None:
            current.append(line)
    return {name: [row.ljust(92) for row in rows[:24]] for name, rows in found.items()}


def test_the_draft_loads_as_a_92_by_24_close_up(bake: ModuleType) -> None:
    picture = parse_picture(bake.draft(), CLOSEUP)
    assert picture.size == CLOSEUP
    frame = picture.frame()
    assert len(frame.rows) == len(frame.colors) == len(frame.shade) == 24
    assert all(len(row) == 92 for row in frame.rows + frame.colors + frame.shade)


def test_two_bakes_are_identical(bake: ModuleType) -> None:
    assert bake.draft() == bake.draft()


def test_the_frame_is_only_half_block_edges_and_blanks_for_tone(bake: ModuleType) -> None:
    drawn = sections(bake.draft())
    assert set("".join(drawn["default"])) == {" ", "▄", "▀"}
    for row, (chars, shade) in enumerate(
        zip(drawn["default"], drawn["default:shade"], strict=True)
    ):
        for column, (char, digit) in enumerate(zip(chars, shade, strict=True)):
            # a blank is tone (a shade digit) or empty; an edge character has no shade
            assert (char == " ") or (digit == " "), (row, column)
            assert digit == " " or digit in "3456789", (row, column)


def test_colours_are_light_digits_for_the_handle_f_for_steel_and_1_for_the_shadow(
    bake: ModuleType,
) -> None:
    drawn = sections(bake.draft())
    assert set("".join(drawn["default:colors"])) <= set(" f1" + HANDLE_LIGHTS)
    assert "f" in "".join(drawn["default:colors"])
    for chars, shade, colors in zip(
        drawn["default"], drawn["default:shade"], drawn["default:colors"], strict=True
    ):
        for char, digit, colour in zip(chars, shade, colors, strict=True):
            assert (colour == " ") == (char == " " and digit == " ")  # a colour for every cell


def test_the_handle_is_gold_on_its_lit_side_and_amber_underneath(bake: ModuleType) -> None:
    colors = sections(bake.draft())["default:colors"]
    column = 72  # not a rib
    lit, underneath = colors[5][column], colors[15][column]
    assert lit in HANDLE_LIGHTS and underneath in HANDLE_LIGHTS
    assert lit > underneath
    assert lit in "89" and underneath in "567"


def test_the_shaft_and_tip_are_bare_metal(bake: ModuleType) -> None:
    drawn = sections(bake.draft())
    for column in (6, 20, 40):
        assert drawn["default:colors"][10][column] == "f"


def test_every_fifth_handle_column_is_darker_for_a_rib(bake: ModuleType) -> None:
    shade = sections(bake.draft())["default:shade"]
    for column in (60, 65, 70, 75):
        for row in (5, 6, 7):
            assert shade[row][column] < shade[row][column - 1]
            assert shade[row][column] < shade[row][column + 1]


def test_the_handle_keeps_a_line_art_top_and_bottom(bake: ModuleType) -> None:
    frame = sections(bake.draft())["default"]
    assert set(frame[3][60:70]) == {"▄"}
    assert set(frame[16][60:70]) == {"▀"}


def test_the_cast_shadow_lies_below_the_screwdriver_in_slate(bake: ModuleType) -> None:
    colors = sections(bake.draft())["default:colors"]
    shadow_rows = [row for row, cells in enumerate(colors) if "1" in cells]
    assert shadow_rows and min(shadow_rows) > 16
    assert all(set(colors[row]) <= {" ", "1"} for row in shadow_rows)
