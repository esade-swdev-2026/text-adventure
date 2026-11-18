"""Draft the screwdriver close-up: a [default] frame with its [default:colors] and
[default:shade] maps (docs/SCREEN-SPEC.md §4, §7).

A development tool, not part of the game: the package never imports it. It prints the three
sections; paste them into src/text_adventure/art/closeups/screwdriver.txt, then edit them by
hand and look at the result in the real game. Never paste over hand edits without reading the
diff.

    uv run python scripts/bake_closeup.py

The handle and the shaft are cylinders lying on their side, lit from the top left: Lambert
shading, plus a sharp highlight on the steel. Every fifth column of the handle is darker, for
the ribs. Cells are twice as tall as they are wide, so lengths along the screwdriver count in
columns and thicknesses in rows (a radius of 3 is a part 6 rows tall).

Each cell is one of three things. Where the part covers both halves of the row, the frame holds
a blank and the shade map holds how bright the surface is; the game draws it as `░▒▓█` tone.
Where it covers only the lower or upper half, the frame holds `▄` or `▀`, so the outline keeps
the shape in the no-colour fallback. Below the screwdriver, a soft shadow is tone in shade `3`-`5`.
"""

import math

WIDTH, HEIGHT = 92, 24  # a close-up fills the room panel
AXIS = 10.0  # the row boundary the screwdriver's axis runs along

# Where each part starts, in columns, from the flat tip on the left to the handle's end.
TIP_START, SHAFT_START, FERRULE_START, HANDLE_START = 5, 17, 46, 50
SHOULDER_END, DOME_START, HANDLE_END = 56, 80, 89.5
# Radii in rows. Half-row values put the outline on the middle of a row (`▄` and `▀`).
TIP_RADIUS, SHAFT_RADIUS, FERRULE_RADIUS = 1.5, 2.5, 3.5
HANDLE_RADIUS, HANDLE_SHOULDER_RADIUS = 6.5, 5.0
RIB_EVERY = 5  # columns

# The light comes from the top left and the front. x runs right, y down, z toward the viewer.
LIGHT = (-0.45, -0.55, 0.70)
AMBIENT = 0.18  # the handle's share of light on its underside
RIB_DARKEN = 0.6
SHINE = 18  # the steel's highlight: higher is sharper

SHADOW_CENTER = (48.0, 18.4)  # column, row
SHADOW_SIZE = (40.0, 2.2)  # half width in columns, half height in rows
SHADOW_PEAK = 4.6  # shade digit at the shadow's centre; it fades to nothing at the edge
MIN_SHADE = 3  # below this a tone cell is black, which would hide the part's underside

STEEL, HANDLE = "steel", "handle"
LOWER, UPPER = "▄", "▀"

Vector = tuple[float, float, float]


def unit(vector: Vector) -> Vector:
    """The vector scaled to length 1."""
    length = math.sqrt(sum(part * part for part in vector))
    return vector[0] / length, vector[1] / length, vector[2] / length


def dot(a: Vector, b: Vector) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


TO_LIGHT = unit(LIGHT)
HALFWAY = unit((LIGHT[0], LIGHT[1], LIGHT[2] + 1.0))  # between the light and the viewer


def profile(x: float) -> tuple[str, float] | None:
    """The part under column position `x`: its material and radius in rows, or None."""
    if x < TIP_START or x > HANDLE_END:
        return None
    if x < SHAFT_START:  # the flat tip: thin at the end, widening to the shaft
        grow = (x - TIP_START) / (SHAFT_START - TIP_START)
        return STEEL, TIP_RADIUS + (SHAFT_RADIUS - TIP_RADIUS) * grow
    if x < FERRULE_START:
        return STEEL, SHAFT_RADIUS
    if x < HANDLE_START:
        return STEEL, FERRULE_RADIUS
    if x < SHOULDER_END:  # the handle's rounded shoulder
        back = (SHOULDER_END - x) / (SHOULDER_END - HANDLE_START)
        rise = HANDLE_RADIUS - HANDLE_SHOULDER_RADIUS
        return HANDLE, HANDLE_SHOULDER_RADIUS + rise * math.sqrt(1 - back * back)
    if x < DOME_START:
        return HANDLE, HANDLE_RADIUS
    along = (x - DOME_START) / (HANDLE_END - DOME_START)  # the domed end
    return HANDLE, HANDLE_RADIUS * math.sqrt(1 - along * along)


def surface_normal(x: float, y: float, radius: float) -> Vector:
    """The direction the surface faces at (x, y), which lies inside the part's outline."""
    across = max(-1.0, min(1.0, (y - AXIS) / radius))
    if x < DOME_START or x > HANDLE_END:
        return 0.0, across, math.sqrt(1 - across * across)
    along = (x - DOME_START) / (HANDLE_END - DOME_START)
    across = (y - AXIS) / HANDLE_RADIUS  # on the dome, relative to the full handle
    depth = math.sqrt(max(0.0, 1 - along * along - across * across))
    full = HANDLE_RADIUS * 2  # in columns, as a round handle is as thick as it is wide
    return unit((along / (HANDLE_END - DOME_START), across / full, depth / full))


def brightness(material: str, x: float, y: float, radius: float, column: int) -> float:
    """How bright the part is at (x, y), 0 to 1: the handle by Lambert's law with a darker rib
    every fifth column, the steel by Lambert's law plus a sharp highlight."""
    normal = surface_normal(x, y, radius)
    lambert = max(0.0, dot(normal, TO_LIGHT))
    if material == HANDLE:
        value = AMBIENT + (1 - AMBIENT) * lambert
        return value * RIB_DARKEN if column % RIB_EVERY == 0 else value
    glint = max(0.0, dot(normal, HALFWAY)) ** SHINE
    return min(1.0, 0.10 + 0.55 * lambert + 0.95 * glint)


def shade_digit(value: float) -> str:
    """A shade digit for a brightness: 3 (a thin `░`) to 9 (`█`)."""
    return str(MIN_SHADE + round((9 - MIN_SHADE) * value))


def light_digit(value: float) -> str:
    """A light-level colour letter for the handle: 5 (amber) on the underside to 9 (gold)."""
    return str(5 + round(4 * value))


def shadow_shade(column: int, row: int) -> str:
    """The cast shadow's shade digit at a cell, or a space where there is none."""
    across = (column + 0.5 - SHADOW_CENTER[0]) / SHADOW_SIZE[0]
    down = (row + 0.5 - SHADOW_CENTER[1]) / SHADOW_SIZE[1]
    distance = across * across + down * down
    if distance >= 1:
        return " "
    strength = round(SHADOW_PEAK * (1 - distance))
    return str(strength) if strength >= MIN_SHADE else " "


def cell(row: int, column: int) -> tuple[str, str, str]:
    """One cell's (character, colour letter, shade digit); a space where nothing is drawn."""
    x = column + 0.5
    found = profile(x)
    if found is None:
        shade = shadow_shade(column, row)
        return " ", ("1" if shade != " " else " "), shade
    material, radius = found
    top, bottom = AXIS - radius, AXIS + radius
    upper = top <= row + 0.25 <= bottom  # is the upper half of the row covered?
    lower = top <= row + 0.75 <= bottom
    if not upper and not lower:
        shade = shadow_shade(column, row)
        return " ", ("1" if shade != " " else " "), shade
    # Measure an outline cell's brightness a little inside the part, never beyond its edge.
    y = min(max(row + 0.5, top + 0.15), bottom - 0.15)
    value = brightness(material, x, y, radius, column)
    colour = light_digit(value) if material == HANDLE else "f"
    if upper and lower:
        return " ", colour, shade_digit(value)
    return (LOWER if lower else UPPER), colour, " "


def draft() -> str:
    """The [default], [default:colors] and [default:shade] sections, as art-file text."""
    grid = [[cell(row, column) for column in range(WIDTH)] for row in range(HEIGHT)]
    out = []
    for name, index in (("default", 0), ("default:colors", 1), ("default:shade", 2)):
        out.append(f"[{name}]")
        out += ["".join(item[index] for item in row).rstrip() for row in grid]
        out.append("")
    return "\n".join(out)


def main() -> None:
    print(draft(), end="")


if __name__ == "__main__":
    main()
