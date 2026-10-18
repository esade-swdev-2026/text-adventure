import pytest
from rich.cells import cell_len

from text_adventure.art import (
    ART_HEIGHT,
    SCREEN_WIDTH,
    Art,
    ArtError,
    Box,
    Position,
    compose,
    parse_art,
)
from text_adventure.game import play_turn
from text_adventure.models import Container, Door, Inventory, Item, Player, Room
from text_adventure.world import World

ART = """\
[background]
..........
[box:closed]
AB
[box:open]
ab
[gem]
*
[door:closed]
D
[door:open]
d
"""


def make(placements: dict[str, tuple[int, int]]) -> tuple[Art, Room]:
    art = parse_art(ART)
    positions = {name: Position(row, column) for name, (row, column) in placements.items()}
    art = Art(art.background, art.sprites, positions)
    room = Room("Lab", "", Door(None), [Container("box")], [Item("gem")])
    return art, room


def test_sprite_lands_at_its_row_and_column() -> None:
    art, room = make({"box": (0, 3)})
    assert compose(art, room)[0].startswith("...AB.....")


def test_open_and_closed_states_swap() -> None:
    art, room = make({"box": (0, 0)})
    room.containers[0].open(Inventory())
    assert compose(art, room)[0].startswith("ab")


def test_taken_item_disappears() -> None:
    art, room = make({"gem": (1, 0)})
    assert compose(art, room)[1][0] == "*"
    room.items.clear()
    assert compose(art, room)[1][0] == " "


def test_sprite_past_the_edge_is_clipped() -> None:
    art, room = make({"box": (0, SCREEN_WIDTH - 1), "door": (ART_HEIGHT, 0)})
    lines = compose(art, room)
    assert lines[0].endswith("A")
    assert len(lines) == ART_HEIGHT
    assert all(cell_len(line) == SCREEN_WIDTH for line in lines)


def test_missing_background_raises() -> None:
    with pytest.raises(ArtError, match="background"):
        parse_art("[box:open]\nab\n")


def test_wide_character_is_rejected() -> None:
    with pytest.raises(ArtError, match="one cell"):
        parse_art("[background]\n⚡\n")


def test_every_composed_line_is_screen_width_in_every_state(world: World, player: Player) -> None:
    room = world.first_room
    art = world.art_for(room)
    script = ["open toolbox", "take screwdriver", "open fuse box", "take key", "take flashbulb"]
    for line in ["", *script, "drop flashbulb", "open door"]:
        play_turn(player, line)
        assert all(cell_len(row) == SCREEN_WIDTH for row in compose(art, room)), line
    assert room.door.is_open


def test_each_sprite_fits_inside_the_background(world: World) -> None:
    art = world.art_for(world.first_room)
    for key, sprite in art.sprites.items():
        place = art.placements[key.split(":")[0]]
        assert place.row + len(sprite) <= ART_HEIGHT, key
        assert place.column + max(cell_len(row) for row in sprite) <= SCREEN_WIDTH, key


def test_spaces_around_a_sprite_are_transparent_and_inside_opaque() -> None:
    art = Art(("abcdefg",), {"box:closed": (" [ ] ",)}, {"box": Position(0, 1)})
    room = Room("Lab", "", Door(None), [Container("box")])
    assert compose(art, room)[0].startswith("ab[ ]fg")


def test_art_follows_contents_and_dropped_items(world: World, player: Player) -> None:
    room = player.current_room
    art = world.art_for(room)
    play_turn(player, "open toolbox")
    assert "╾━━" in "".join(compose(art, room))  # the screwdriver lies in the open box
    play_turn(player, "take screwdriver")
    assert "╾━━" not in "".join(compose(art, room))
    play_turn(player, "drop screwdriver")
    place = art.placements["screwdriver@floor"]
    assert compose(art, room)[place.row][place.column : place.column + 3] == "╾━━"


def test_box_contains_its_cells_and_not_its_neighbours() -> None:
    box = Box(top=2, left=5, height=3, width=4)
    assert box.contains(2, 5) and box.contains(4, 8)
    assert not box.contains(1, 5) and not box.contains(5, 5)
    assert not box.contains(2, 4) and not box.contains(2, 9)
