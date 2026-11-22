"""scripts/bake_light.py drafts the room's shade and light maps. The art file is hand-edited
after a bake, so these tests check the properties of a bake, not the committed maps."""

import tomllib
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from text_adventure.art import ART_HEIGHT, DIGITS, LIGHT_LETTERS, SCREEN_WIDTH

SCENE = Path(__file__).resolve().parent.parent / "scripts" / "scenes" / "electrical_room.toml"
LIGHT_CELLS = DIGITS | LIGHT_LETTERS
POWER_ON = "light:power on"


@pytest.fixture(scope="module")
def bake(load_script: Callable[[str], ModuleType]) -> ModuleType:
    return load_script("bake_light")


@pytest.fixture(scope="module")
def scene() -> dict[str, Any]:
    return tomllib.loads(SCENE.read_text(encoding="utf-8"))


def sections(text: str) -> dict[str, list[str]]:
    """The bake's rows by section name."""
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("["):
            current = found.setdefault(line.strip("[]"), [])
        elif line and current is not None:
            current.append(line)
    return found


def marked(marks: list[dict[str, Any]]) -> dict[tuple[int, int], str]:
    """The cells the marks stamp, with the letter each one gets."""
    cells = {}
    for mark in marks:
        (first_row, last_row), (first_column, last_column) = mark["rows"], mark["columns"]
        for row in range(first_row, last_row + 1):
            for column in range(first_column, last_column + 1):
                cells[row, column] = str(mark["letter"])
    return cells


def test_the_bake_has_a_shade_a_light_and_a_power_on_section(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    assert list(sections(bake.bake(scene))) == ["shade", "light", POWER_ON]


def test_every_section_is_92_by_24(bake: ModuleType, scene: dict[str, Any]) -> None:
    for name, rows in sections(bake.bake(scene)).items():
        assert len(rows) == ART_HEIGHT, name
        assert all(len(row) == SCREEN_WIDTH for row in rows), name


def test_cells_are_digits_or_colour_letters_and_the_shade_map_only_digits(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    for name, rows in sections(bake.bake(scene)).items():
        allowed = DIGITS if name == "shade" else LIGHT_CELLS
        assert set("".join(rows)) <= allowed, name


def test_the_lamps_marked_cells_are_full_light_with_the_power_off_and_on(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    lamp = {cell for cell, letter in marked(scene["marks"]).items() if letter == "9"}
    assert lamp  # the scene marks the lamp
    baked = sections(bake.bake(scene))
    for name in ("light", POWER_ON):
        for row, column in lamp:
            assert baked[name][row][column] == "9", (name, row, column)


def test_every_power_on_cell_is_at_least_the_ambient_level_except_marks(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    state = next(item for item in scene["light_state"] if item["state"] == "power on")
    stamped = marked(scene["marks"] + state["marks"])
    rows = sections(bake.bake(scene))[POWER_ON]
    for row in range(ART_HEIGHT):
        for column in range(SCREEN_WIDTH):
            if (row, column) not in stamped:
                assert int(rows[row][column]) >= state["ambient"], (row, column)


def test_power_on_never_darkens_a_cell_the_marks_leave_alone(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    state = next(item for item in scene["light_state"] if item["state"] == "power on")
    stamped = marked(scene["marks"] + state["marks"])
    baked = sections(bake.bake(scene))
    for row in range(ART_HEIGHT):
        for column in range(SCREEN_WIDTH):
            if (row, column) not in stamped:
                assert baked[POWER_ON][row][column] >= baked["light"][row][column], (row, column)


def test_two_bakes_are_identical(bake: ModuleType, scene: dict[str, Any]) -> None:
    assert bake.bake(scene) == bake.bake(scene)


def test_noise_is_a_fixed_step_of_minus_one_zero_or_one(bake: ModuleType) -> None:
    values = {bake.noise(row, column) for row in range(24) for column in range(92)}
    assert values == {-1, 0, 1}
    assert bake.noise(5, 9) == bake.noise(5, 9)


def test_smoothstep_runs_from_0_to_1_between_its_edges(bake: ModuleType) -> None:
    assert bake.smoothstep(1.0, 3.0, 0.0) == 0.0
    assert bake.smoothstep(1.0, 3.0, 2.0) == 0.5
    assert bake.smoothstep(1.0, 3.0, 9.0) == 1.0


def test_light_level_is_the_lamps_share_or_the_ambient_light_below_full(
    bake: ModuleType,
) -> None:
    assert [bake.light_level(share, 0) for share in (0.0, 0.5, 1.0)] == [0, 4, 9]
    assert bake.light_level(0.0, 5) == 5  # a lit room has at least the ambient light
    assert bake.light_level(0.9, 5) == 8  # ...but stays below full, so the lamp is brightest
    assert bake.light_level(1.0, 0) == 9


def test_surfaces_follow_the_back_walls_frame(bake: ModuleType, scene: dict[str, Any]) -> None:
    wall = scene["wall"]
    middle = (wall["left"] + wall["right"]) // 2
    assert bake.surface(scene, wall["top"] - 1, middle) == "ceiling"
    assert bake.surface(scene, wall["top"], middle) == "back_wall"
    assert bake.surface(scene, wall["bottom"] + 1, middle) == "floor"
    assert bake.surface(scene, wall["top"], wall["left"] - 1) == "side_walls"


# Several lamps (E8.2)


def light_rows(bake: ModuleType, scene: dict[str, Any], name: str = "light") -> list[str]:
    return sections(bake.bake(scene))[name]


def test_a_lamps_list_of_one_bakes_like_the_single_lamp(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    as_list = {key: value for key, value in scene.items() if key != "lamp"}
    as_list["lamps"] = [scene["lamp"]]
    assert bake.bake(as_list) == bake.bake(scene)


def test_one_lamp_alone_gives_exactly_its_own_light(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    lamp = scene["lamp"]
    for row, column in [(0, 0), (6, 31), (20, 50)]:
        assert bake.lamps_at([lamp], row, column) == bake.lamp_at(lamp, row, column)


def test_a_second_lamp_only_adds_light_and_never_passes_full(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    second = {**scene["lamp"], "column": 70}
    both = {**scene, "lamps": [second]}
    one, two = light_rows(bake, scene), light_rows(bake, both)
    pairs = [
        (a, b)
        for row_a, row_b in zip(one, two, strict=True)
        for a, b in zip(row_a, row_b, strict=True)
    ]
    digits = [(int(a), int(b)) for a, b in pairs if a.isdigit() and b.isdigit()]
    assert all(b >= a for a, b in digits)
    assert any(b > a for a, b in digits)
    lamp = scene["lamp"]
    assert bake.lamps_at([lamp, second], 6, 31) <= 1.0


def test_a_light_state_can_switch_on_a_lamp_of_its_own(
    bake: ModuleType, scene: dict[str, Any]
) -> None:
    beam = {**scene["lamp"], "column": 70, "row": 10}
    state = {"state": "focused", "lamps": [beam]}
    with_beam = {**scene, "light_state": [state]}
    off, on = light_rows(bake, with_beam), light_rows(bake, with_beam, "light:focused")
    assert off == light_rows(bake, scene)  # the beam is dark until the state
    assert on != off
