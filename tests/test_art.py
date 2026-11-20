import random
from typing import Any

import pytest
from rich.cells import cell_len

from text_adventure.art import (
    ART_HEIGHT,
    BLACK,
    CLOSEUP,
    DIP_GAP,
    DIP_SECONDS,
    FLICKER_WAIT,
    ICON,
    MAX_DIPS,
    POWER_ON,
    RAMP,
    SCREEN_WIDTH,
    WINDOW,
    Art,
    ArtError,
    Box,
    Flicker,
    FlickerSchedule,
    Position,
    compose,
    compose_shade,
    dimmed,
    flicker_wanted,
    floor_key,
    level,
    light_for,
    light_state,
    parse_art,
    parse_picture,
    tone,
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
[door:locked]
D
[door:unlocked]
U
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


def test_every_composed_line_is_screen_width_in_every_state(
    world: World, player: Player, win_script: list[str]
) -> None:
    room = world.first_room
    art = world.art_for(room)
    for line in ["", "take flashbulb", "drop flashbulb", *win_script]:
        play_turn(player, line)
        assert all(cell_len(row) == SCREEN_WIDTH for row in compose(art, room)), line
    assert room.door.is_open


def test_each_sprite_fits_inside_the_background(world: World) -> None:
    art = world.art_for(world.first_room)
    for key, sprite in art.sprites.items():
        name = key.split(":")[0]
        places = [art.placements[k] for k in (name, floor_key(name)) if k in art.placements]
        assert places, key
        for place in places:
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


PICTURE = """\
[closed]
[#]
[closed:colors]
.#.
[open]
]#[
"""


def test_picture_frames_are_padded_to_their_full_size() -> None:
    frame = parse_picture(PICTURE, ICON).frame("closed")
    assert len(frame.rows) == len(frame.colors) == ICON.height
    assert all(cell_len(row) == ICON.width for row in frame.rows + frame.colors)
    assert frame.rows[0] == "[#]       "
    assert frame.colors[0] == ".#.       "


def test_a_frame_without_a_colour_map_is_all_shadow() -> None:
    assert parse_picture(PICTURE, ICON).frame("open").colors == (" " * ICON.width,) * ICON.height


def test_an_unknown_state_falls_back_to_the_first_frame() -> None:
    picture = parse_picture(PICTURE, ICON)
    assert picture.frame("power on") == picture.frame("closed") == picture.frame()


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[default]\n12345678901\n", "must fit in 10x4"),
        ("[default]\n1\n2\n3\n4\n5\n", "must fit in 10x4"),
        ("[default]\nab\n[default:colors]\nxz\n", "not a colour"),
        ("[open:colors]\n##\n", r"no \[open\] frame"),
        ("", r"no \[state\] frame"),
        ("[default]\n⚡\n", "one cell"),
    ],
)
def test_broken_picture_raises(text: str, message: str) -> None:
    with pytest.raises(ArtError, match=message):
        parse_picture(text, ICON)


def test_example_pictures_have_the_right_size(world: World) -> None:
    icon = world.icon_for("screwdriver")
    closeup = world.closeup_for(world.first_room, "screwdriver")
    assert icon is not None and icon.size == ICON
    assert closeup is not None and closeup.size == CLOSEUP
    for picture in (icon, closeup):
        frame = picture.frame()
        assert len(frame.rows) == len(frame.colors) == picture.size.height
        assert all(cell_len(row) == picture.size.width for row in frame.rows + frame.colors)


def test_door_is_drawn_locked_unlocked_or_open() -> None:
    art, room = make({"door": (0, 0)})
    room.door = Door(None, "key")
    assert compose(art, room)[0][0] == "D"
    room.door.is_unlocked = True
    assert compose(art, room)[0][0] == "U"
    room.door.open()
    assert compose(art, room)[0][0] == "d"


def test_story_state_uses_its_own_sprite_or_falls_back_to_open() -> None:
    art = Art(
        (".....",),
        {"box:closed": ("c",), "box:open": ("o",), "box:lit": ("L",)},
        {"box": Position(0, 0)},
    )
    room = Room("Lab", "", Door(None), [Container("box")])
    box = room.containers[0]
    box.open(Inventory())
    box.story = "lit"
    assert compose(art, room)[0][0] == "L"
    box.story = "humming"  # no sprite of its own
    assert compose(art, room)[0][0] == "o"


def test_room_shows_every_object_and_each_state_changes_visibly(
    world: World, player: Player, win_script: list[str]
) -> None:
    room = player.current_room
    art = world.art_for(room)
    assert len(art.background) == ART_HEIGHT == 24
    assert all(cell_len(row) == SCREEN_WIDTH == 92 for row in art.background)
    start = "\n".join(compose(art, room))
    for sprite in ["toolbox:closed", "fuse box:closed", "vent:closed", "flashbulb", "door:locked"]:
        assert art.sprites[sprite][0].strip() in start, sprite
    assert "┿━" in start  # the bolt is shot across the frame
    unlocked = art.sprites["door:unlocked"]
    assert unlocked != art.sprites["door:locked"]
    assert not any("┿" in row for row in unlocked)
    seen = {"\n".join(compose(art, room))}
    for line in win_script:
        play_turn(player, line)
        if player.current_room is not room:
            break
        picture = "\n".join(compose(art, room))
        assert picture not in seen or line.startswith("take"), line  # every step shows
        seen.add(picture)
        if line == "use flashbulb on vent":
            place = art.placements["fuse"]
            fuse = art.sprites["fuse"][0]
            row = compose(art, room)[place.row]
            assert row[place.column : place.column + len(fuse)] == fuse  # the fuse is revealed
    for state in ["vent:open", "vent:flashed", "fuse box:power on"]:
        assert state in art.sprites, state


def play_into(player: Player, win_script: list[str], name: str) -> list[str]:
    """Play the win script until the player stands in the room called `name`; return the
    lines still to play."""
    for index, line in enumerate(win_script):
        if player.current_room.name == name:
            return win_script[index:]
        play_turn(player, line)
    raise AssertionError(f"the win script never reaches the {name}")


def test_every_step_in_the_darkroom_shows_in_its_picture(
    world: World, player: Player, win_script: list[str]
) -> None:
    rest = play_into(player, win_script, "Darkroom")
    room = player.current_room
    art = world.art_for(room)
    assert all(cell_len(row) == SCREEN_WIDTH for row in art.background)
    seen = {"\n".join(compose(art, room))}
    for line in rest:
        play_turn(player, line)
        if player.current_room is not room:
            break
        picture = "\n".join(compose(art, room))
        assert picture not in seen or line.startswith("take"), line
        seen.add(picture)
    assert room.door.is_open


def test_the_enlarger_lights_its_beam_in_the_darkroom(
    world: World, player: Player, win_script: list[str]
) -> None:
    rest = play_into(player, win_script, "Darkroom")
    room = player.current_room
    art = world.art_for(room)
    assert light_state(art, room) is None
    for line in rest[: rest.index("use lens on enlarger") + 1]:
        play_turn(player, line)
    assert light_state(art, room) == "focused"
    assert "f" in "".join(light_for(art, room))  # the white beam
    assert not room.flicker and room.light == "red"


# Tone (docs/SCREEN-SPEC.md §5.1)


def test_tone_is_black_below_the_threshold_and_a_ramp_character_above() -> None:
    assert tone(0, 9, 0, 0) == tone(9, 0, 0, 0) == " "
    assert all(tone(2, 9, row, column) == " " for row in range(4) for column in range(4))
    assert 2 * 9 / 81 < BLACK <= 3 * 9 / 81
    assert all(tone(9, 9, row, column) == "█" for row in range(4) for column in range(4))
    for shade in range(3, 10):
        for row in range(4):
            for column in range(4):
                assert tone(shade, 9, row, column) in RAMP[1:], (shade, row, column)


def test_tone_dithers_by_position_and_never_changes_between_calls() -> None:
    cells = [tone(5, 9, row, column) for row in range(4) for column in range(4)]
    assert len(set(cells)) == 2  # a mid tone mixes two neighbouring ramp characters
    assert cells == [tone(5, 9, row, column) for row in range(4) for column in range(4)]
    assert tone(5, 9, 0, 0) == tone(5, 9, 4, 4)  # the 4 × 4 pattern repeats


def test_tone_gets_denser_as_the_light_grows() -> None:
    def ink(light: int) -> int:
        return sum(RAMP.index(tone(9, light, r, c)) for r in range(4) for c in range(4))

    assert [ink(light) for light in range(10)] == sorted(ink(light) for light in range(10))


def test_level_reads_digits_blanks_and_letters() -> None:
    assert [level(c) for c in "0 79n*"] == [0, 0, 7, 9, 9, 9]


# Shade and light maps (docs/SCREEN-SPEC.md §5.2)

TONED = """\
[background]
|..
[shade]
9 5
[light]
8*
[light:open]
2
[box:closed]
( )
[box:open]
(x)
[box:open:shade]
 4
"""


def test_shade_and_light_maps_are_padded_with_zeros() -> None:
    art = parse_art(TONED)
    assert len(art.shade) == len(art.light) == ART_HEIGHT
    assert art.shade[0] == "905" + "0" * (SCREEN_WIDTH - 3)
    assert art.light[0] == "8*" + "0" * (SCREEN_WIDTH - 2)
    assert art.shade[1] == art.light[1] == "0" * SCREEN_WIDTH


def test_a_room_without_light_or_shade_is_evenly_lit_and_black() -> None:
    art = parse_art("[background]\n.\n")
    assert set("".join(art.light)) == {"6"}
    assert set("".join(art.shade)) == {"0"}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[background]\n.\n[shade]\n5a\n", "not a digit"),
        ("[background]\n.\n[shade]\n*\n", "not a digit"),
        ("[background]\n.\n[light]\n5#\n", "not a light level"),
        ("[background]\n.\n[light:power on]\nx\n", "not a light level"),
        ("[background]\n.\n[shade]\n" + "1" * 93 + "\n", "must fit in 92x24"),
        ("[background]\n.\n[light]\n" + "1\n" * 25, "must fit in 92x24"),
        ("[background]\n.\n[box:shade]\n1\n", r"no \[box\] sprite"),
        ("[background]\n.\n[box]\nab\n[box:shade]\n123\n", "must fit in its sprite"),
        ("[background]\n.\n[box]\nab\n[box:shade]\nx\n", "not a digit"),
    ],
)
def test_broken_shade_or_light_raises(text: str, message: str) -> None:
    with pytest.raises(ArtError, match=message):
        parse_art(text)


def test_a_sprite_brings_its_own_shade_and_black_where_it_has_none() -> None:
    art = parse_art(TONED)
    art = Art(art.background, art.sprites, {"box": Position(0, 0)}, art.light, art.shade,
              art.lights, art.sprite_shades)  # fmt: skip
    room = Room("Lab", "", Door(None), [Container("box")])
    assert compose_shade(art, room)[0][:4] == "0000"  # closed: no shade map, all black inside
    room.containers[0].open(Inventory())
    assert compose_shade(art, room)[0][:4] == "0400"  # open: its own map; outside untouched


def test_a_state_light_map_replaces_the_light_while_an_object_is_in_that_state() -> None:
    art = parse_art(TONED)
    room = Room("Lab", "", Door(None), [Container("box")])
    assert light_for(art, room) == art.light
    room.containers[0].open(Inventory())
    assert light_for(art, room) == art.lights["open"]


def test_with_two_state_maps_active_the_first_container_wins_then_the_door() -> None:
    art = parse_art("[background]\n.\n[light:open]\n1\n[light:closed]\n2\n[light:unlocked]\n3\n")
    room = Room("Lab", "", Door(None), [Container("box"), Container("bin")])
    assert light_for(art, room) == art.lights["closed"]  # both closed: one map, the first's
    room.containers[1].open(Inventory())
    assert light_for(art, room) == art.lights["closed"]  # box (first) closed, bin open
    room.containers[0].open(Inventory())
    assert light_for(art, room) == art.lights["open"]  # box open now wins over bin
    hall = Room("Hall", "", Door(None), [Container("box")])
    hall.door.unlock(Inventory())
    assert light_for(art, hall) == art.lights["closed"]  # a container before the door
    no_containers = Room("Yard", "", hall.door)
    assert light_for(art, no_containers) == art.lights["unlocked"]


def test_the_fuse_box_powering_on_would_switch_a_power_on_light_map(
    world: World, player: Player, win_script: list[str]
) -> None:
    room = player.current_room
    art = world.art_for(room)
    lit = Art(art.background, art.sprites, art.placements, art.light, art.shade,
              {"power on": ("9" * SCREEN_WIDTH,) * ART_HEIGHT})  # fmt: skip
    for line in win_script:
        before = light_for(lit, room)
        play_turn(player, line)
        if light_for(lit, room) != before:
            assert line.startswith("use fuse"), line
            break
    assert light_for(lit, room) == lit.lights["power on"]


# Picture shade maps (docs/SCREEN-SPEC.md §7.1)


def test_a_picture_shade_map_is_digits_padded_to_size() -> None:
    frame = parse_picture("[default]\n( )\n[default:shade]\n 7\n", ICON).frame()
    assert frame.shade[0] == "07" + "0" * (ICON.width - 2)
    assert len(frame.shade) == ICON.height
    assert parse_picture("[default]\nx\n", ICON).frame().shade == ()


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[default]\nab\n[default:shade]\n1x\n", "not a digit"),
        ("[open:shade]\n11\n", r"no \[open\] frame"),
        ("[default]\nab\n[default:shade]\n12345678901\n", "must fit in 10x4"),
    ],
)
def test_broken_picture_shade_raises(text: str, message: str) -> None:
    with pytest.raises(ArtError, match=message):
        parse_picture(text, ICON)


def test_colour_maps_accept_light_levels() -> None:
    frame = parse_picture("[default]\nab\n[default:colors]\n09\n", ICON).frame()
    assert frame.colors[0].startswith("09")


def test_dimmed_lowers_every_digit_never_below_zero_and_leaves_letters_alone() -> None:
    assert dimmed(("9876543210", "n r*f 05"), 2) == ("7654321000", "n r*f 03")
    assert dimmed(("9876543210",), 0) == ("9876543210",)
    assert dimmed(("12",), 9) == ("00",)


def test_dimmed_keeps_the_size_of_the_light_map(world: World) -> None:
    light = world.art_for(world.first_room).light
    dipped = dimmed(light, 2)
    assert len(dipped) == len(light) and all(
        len(a) == len(b) for a, b in zip(dipped, light, strict=True)
    )
    assert dipped != light and all(len(row) == SCREEN_WIDTH for row in dipped)


CAN_FLICKER: dict[str, Any] = {
    "inspecting": False,
    "color": True,
    "is_terminal": True,
    "term": "xterm-256color",
    "motion": True,
}


def wanted(world: World, room: Room, **changes: Any) -> bool:
    return flicker_wanted(world.art_for(room), room, **{**CAN_FLICKER, **changes})


def test_the_lamp_flickers_in_the_room_view_with_the_power_off(
    world: World, player: Player
) -> None:
    assert wanted(world, player.current_room)


@pytest.mark.parametrize(
    "change",
    [
        {"inspecting": True},
        {"color": False},
        {"is_terminal": False},
        {"term": "dumb"},
        {"motion": False},
    ],
    ids=lambda change: next(iter(change)),
)
def test_no_flicker_while_inspecting_without_colour_a_terminal_or_room_or_with_no_motion(
    world: World, player: Player, change: dict[str, Any]
) -> None:
    assert not wanted(world, player.current_room, **change)


def test_no_flicker_once_the_power_is_on(
    world: World, player: Player, win_script: list[str]
) -> None:
    room = player.current_room
    for line in win_script[:9]:
        play_turn(player, line)
    assert wanted(world, room)  # the fuse is not in yet
    play_turn(player, win_script[9])  # use fuse on fuse box
    assert light_state(world.art_for(room), room) == POWER_ON
    assert not wanted(world, room)


def test_no_flicker_in_a_room_whose_light_is_steady() -> None:
    art = parse_art("[background]\n.\n")
    assert flicker_wanted(art, Room("Lab", "", Door(None)), **CAN_FLICKER)
    assert not flicker_wanted(art, Room("Lab", "", Door(None), flicker=False), **CAN_FLICKER)


def test_a_light_map_for_another_state_does_not_stop_the_flicker() -> None:
    art = parse_art("[background]\n.\n[light:open]\n9\n[light:power on]\n8\n")
    room = Room("Lab", "", Door(None), [Container("box")])
    room.containers[0].open(Inventory())
    assert light_state(art, room) == "open" and light_for(art, room) == art.lights["open"]
    assert flicker_wanted(art, room, **CAN_FLICKER)


def plan(schedule: FlickerSchedule, seconds: float = 600.0) -> list[tuple[float, Flicker]]:
    """Ask for flickers for `seconds`, each measured from the start of the one before, as the
    terminal does. Returns (asked at, flicker) pairs."""
    asked, planned = 0.0, []
    while asked < seconds:
        flicker = schedule.next(asked)
        planned.append((asked, flicker))
        asked = flicker.start
    return planned


def dips_of(planned: list[tuple[float, Flicker]]) -> list[float]:
    return [time for _, flicker in planned for time in flicker.times()]


# The photosensitivity rule (docs/SCREEN-SPEC.md §5.6), written out here on purpose: a test that
# read these from the schedule would follow the schedule if someone changed them.
SPEC_MAX_DIPS, SPEC_WINDOW = 3, 10.0
SPEC_WAIT = (3.0, 8.0)


def busiest_window(times: list[float]) -> int:
    """The most dips in any 10 seconds: a window can start at any dip."""
    return max(sum(start <= other < start + SPEC_WINDOW for other in times) for start in times)


def test_the_rule_constants_are_the_specs() -> None:
    assert (MAX_DIPS, WINDOW) == (SPEC_MAX_DIPS, SPEC_WINDOW)
    assert FLICKER_WAIT == SPEC_WAIT
    assert (DIP_SECONDS, DIP_GAP) == (0.07, 0.07)


SEEDS = range(30)


@pytest.mark.parametrize("seed", SEEDS)
def test_flickers_come_3_to_8_seconds_apart_with_one_or_two_dips(seed: int) -> None:
    for asked, flicker in plan(FlickerSchedule(random.Random(seed))):
        assert SPEC_WAIT[0] <= flicker.start - asked <= SPEC_WAIT[1]
        assert flicker.dips in (1, 2)


def test_two_dips_are_70_ms_of_dip_then_70_ms_of_normal_light_apart() -> None:
    first, second = Flicker(10.0, 2).times()
    assert (first, round(second - first, 3)) == (10.0, round(DIP_SECONDS + DIP_GAP, 3))
    assert Flicker(10.0, 1).times() == (10.0,)


@pytest.mark.parametrize("seed", SEEDS)
def test_never_more_than_3_dips_in_any_10_seconds_over_10_minutes(seed: int) -> None:
    times = dips_of(plan(FlickerSchedule(random.Random(seed))))
    assert len(times) > 50  # ten minutes of flickers, not an empty plan
    assert busiest_window(times) <= SPEC_MAX_DIPS


class Eager(random.Random):
    """The worst case for the interval alone: every flicker as soon as allowed, two dips."""

    def uniform(self, a: float, b: float) -> float:
        return a

    def choice(self, seq: Any) -> Any:
        return seq[-1]


def test_the_cap_holds_when_every_flicker_is_as_soon_and_as_long_as_it_may_be() -> None:
    planned = plan(FlickerSchedule(Eager()))
    # Flickers 3 s apart with two dips each would make 8 dips in 10 s; the schedule holds 3.
    assert busiest_window(dips_of(planned)) == SPEC_MAX_DIPS
    for asked, flicker in planned:
        assert SPEC_WAIT[0] <= flicker.start - asked <= SPEC_WAIT[1]


def test_dips_cancelled_before_they_ran_do_not_push_the_next_flicker_back() -> None:
    eager, cancelled = FlickerSchedule(Eager()), FlickerSchedule(Eager())
    for schedule in (eager, cancelled):
        for asked in (0.0, 0.1, 0.2):  # three quick commands: three flickers planned, none run
            schedule.next(asked)
    cancelled.cancel_after(0.3)
    assert eager.next(0.3).start > 0.3 + SPEC_WAIT[1]  # held back by dips that never ran
    assert cancelled.next(0.3).start == 0.3 + SPEC_WAIT[0]  # as soon as the interval allows


def test_cancel_keeps_the_dips_that_already_ran() -> None:
    schedule = FlickerSchedule(Eager())
    times = list(schedule.next(0.0).times())  # two dips at 3.0 s
    times += schedule.next(times[-1]).times()  # two more 3 s later; only one fits the cap
    schedule.cancel_after(times[-1])  # all of these ran
    times += schedule.next(times[-1]).times()
    assert busiest_window(times) <= SPEC_MAX_DIPS


def test_a_schedule_asked_again_before_its_last_flicker_still_keeps_the_cap() -> None:
    # The terminal asks again after every screen; an earlier plan may not have run yet.
    schedule = FlickerSchedule(random.Random(3))
    times: list[float] = []
    for asked in (0.0, 1.0, 1.5, 4.0, 4.2, 9.0, 9.1, 9.2, 15.0):
        times += schedule.next(asked).times()
    assert busiest_window(times) <= SPEC_MAX_DIPS
