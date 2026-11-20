"""Bake a room's [shade] and [light] maps from a scene file (docs/SCREEN-SPEC.md §5.4).

A development tool, not part of the game: the package never imports it. It prints the
sections; paste them into the room's art file, then edit them by hand and look at the result
in the real game. Never paste over hand edits without reading the diff.

    uv run python scripts/bake_light.py scripts/scenes/electrical_room.toml

The scene file describes the back wall's rectangle, a shade per surface (with plank and seam
texture), the lamp, colour letters stamped onto rectangles, and the extra light of each light
state ("power on"). See scripts/scenes/electrical_room.toml.
"""

import argparse
import math
import tomllib
from pathlib import Path
from typing import Any

MAX_LEVEL = 9


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """0 below edge0, 1 above edge1, a smooth S between."""
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def noise(row: int, column: int) -> int:
    """A fixed pseudo-random -1, 0 or 1 per cell, so a bake is the same every time."""
    n = (row * 668265263 + column * 374761393) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n >> 16) % 3 - 1


def surface(scene: dict[str, Any], row: int, column: int) -> str:
    """Which surface a cell shows: ceiling, back_wall, side_walls or floor.

    The edges run one column per row from the back wall's corners, as the art draws them.
    """
    wall = scene["wall"]
    top, bottom, left, right = wall["top"], wall["bottom"], wall["left"], wall["right"]
    if row < top:
        reach = top - row
        return "ceiling" if left - reach < column < right + reach else "side_walls"
    if row > bottom:
        reach = row - bottom
        return "floor" if left - reach < column < right + reach else "side_walls"
    return "back_wall" if left <= column <= right else "side_walls"


def shade_at(scene: dict[str, Any], row: int, column: int) -> int:
    """The surface's shade with its texture: floor planks toward the vanishing point, block
    seams on the back wall, and one step of noise."""
    shades, wall = scene["shade"], scene["wall"]
    kind = surface(scene, row, column)
    value = shades[kind]
    if kind == "floor":
        vanish_row = (wall["top"] + wall["bottom"]) / 2
        vanish_column = (wall["left"] + wall["right"]) / 2
        angle = math.atan2(column - vanish_column, (row - vanish_row) * 2)
        value += shades["plank"] if math.floor(angle * 14) % 2 else 0
    if kind == "back_wall" and (column + (row % 2) * 4) % 8 == 0:
        value -= shades["seam"]
    return max(0, min(MAX_LEVEL, value + noise(row, column)))


def lamp_at(lamp: dict[str, Any], row: int, column: int) -> float:
    """How much of the lamp's light reaches a cell, 0 to 1: a cone below it that fades with
    distance, and a little glow all round. Rows count double, as cells are twice as tall."""
    across, down = column - lamp["column"], (row - lamp["row"]) * 2
    falloff = 1 / (1 + (math.hypot(across, down) / lamp["reach"]) ** 2)
    angle = math.atan2(abs(across), down) if down > 0 else math.pi
    cone = 1 - smoothstep(lamp["cone"] - 0.25, lamp["cone"] + 0.25, angle)
    return min(1.0, falloff * (lamp["glow"] + (1 - lamp["glow"]) * cone) * lamp["power"])


def light_level(strength: float, ambient: int) -> int:
    """A light digit: the lamp's share, or with a light state's ambient light at least
    `ambient` (more near the lamp), kept below full light so the lamp stays brightest."""
    lit = round(MAX_LEVEL * strength)
    if not ambient:
        return lit
    return max(lit, min(MAX_LEVEL - 1, ambient + round(3 * strength)))


def stamp(grid: list[list[str]], marks: list[dict[str, Any]]) -> None:
    """Write each mark's colour letter (or level) over its rectangle of cells."""
    for mark in marks:
        first_row, last_row = mark["rows"]
        first_column, last_column = mark["columns"]
        for row in range(first_row, last_row + 1):
            for column in range(first_column, last_column + 1):
                grid[row][column] = str(mark["letter"])


def bake(scene: dict[str, Any]) -> str:
    """The [shade], [light] and [light:<state>] sections for the scene, as art-file text."""
    width, height = scene["width"], scene["height"]
    cells = [(row, column) for row in range(height) for column in range(width)]
    shade = [[" "] * width for _ in range(height)]
    lamp = [[0.0] * width for _ in range(height)]
    for row, column in cells:
        shade[row][column] = str(shade_at(scene, row, column))
        lamp[row][column] = lamp_at(scene["lamp"], row, column)

    def light_map(ambient: int, extra: list[dict[str, Any]]) -> list[list[str]]:
        grid = [[" "] * width for _ in range(height)]
        for row, column in cells:
            grid[row][column] = str(light_level(lamp[row][column], ambient))
        stamp(grid, scene.get("marks", []) + extra)
        return grid

    sections = [("shade", shade), ("light", light_map(0, []))]
    for state in scene.get("light_state", []):
        extra = state.get("marks", [])
        sections.append((f"light:{state['state']}", light_map(state["ambient"], extra)))
    out = []
    for name, grid in sections:
        out.append(f"[{name}]")
        out += ["".join(row) for row in grid]
        out.append("")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scene", type=Path, help="the scene file (TOML)")
    args = parser.parse_args()
    print(bake(tomllib.loads(args.scene.read_text(encoding="utf-8"))), end="")


if __name__ == "__main__":
    main()
