import pytest
from rich.cells import cell_len

from text_adventure.art import ART_HEIGHT, ICON, RAMP, Frame, parse_art, parse_picture
from text_adventure.game import play_turn
from text_adventure.models import Container, Door, Inventory, Item, Player, Room
from text_adventure.screen import (
    BLOCK_HEIGHT,
    BLOCK_WIDTH,
    DESCRIPTION_ROW,
    FIRST_HINT,
    HISTORY_ROW,
    PANEL_HEIGHT,
    PANELS_ROW,
    Inspected,
    Message,
    Role,
    Screen,
    Tone,
    build_screen,
    build_win_screen,
    complete,
    describe_room,
    flash_screen,
    frame_lines,
    history_rows,
    line_text,
    room_picture,
    slot,
    to_ascii,
    too_small_lines,
    top_border,
    visible_names,
)
from text_adventure.world import World

PLAYTHROUGH = [
    "open toolbox",
    "take screwdriver",
    "take wrench",
    "open fuse box",
    "take key",
    "open vent",
    "take flashbulb",
    "dance",
    "help",
    "inventory",
    "drop wrench",
]


def screen_for(
    world: World,
    player: Player,
    history: list[Message] | None = None,
    moves: int = 0,
    focus: str | None = None,
    inspected: Inspected | None = None,
) -> Screen:
    room = player.current_room
    return build_screen(
        room,
        player.inventory,
        world.art_for(room),
        history or [],
        moves=moves,
        icons=world.icons,
        focus=focus,
        inspected=inspected,
    )


def rows(screen: Screen) -> list[str]:
    """Every row of the screen block, the prompt (or footer) included, as plain text."""
    return [line_text(line) for line in screen.rows] + [screen.prompt or screen.footer]


def inspect(world: World, player: Player, name: str) -> Inspected:
    """Inspect a thing through the rules, as the game loop does."""
    outcome = play_turn(player, f"inspect {name}")
    assert outcome is not None and outcome.inspected is not None, name
    found = outcome.inspected
    picture = world.closeup_for(player.current_room, name)
    return Inspected(found.name, found.text, picture, found.state)


def roles_of(screen: Screen, role: Role) -> str:
    return "".join(text for line in screen.rows for text, r in line if r is role)


def test_every_screen_fits_the_block_in_a_whole_playthrough(world: World, player: Player) -> None:
    history: list[Message] = []
    for line in PLAYTHROUGH:
        outcome = play_turn(player, line)
        assert outcome is not None
        history.append(Message(outcome.message, Tone.ERROR if outcome.error else Tone.RESULT))
        screens = [
            screen_for(world, player, history, moves=len(history)),
            screen_for(world, player, history, inspected=inspect(world, player, "door")),
            screen_for(world, player, history, inspected=inspect(world, player, "toolbox")),
        ]
        if player.inventory.has_item("screwdriver"):
            screens.append(
                screen_for(world, player, history, inspected=inspect(world, player, "screwdriver"))
            )
        for screen in screens:
            assert len(rows(screen)) == BLOCK_HEIGHT, line
            assert all(cell_len(row) <= BLOCK_WIDTH for row in rows(screen)), line


def test_first_screen_shows_the_intro_above_the_hint(world: World, player: Player) -> None:
    lines = rows(screen_for(world, player, [Message(world.intro, Tone.NARRATION)]))
    assert lines[HISTORY_ROW + 1] == "  " + world.intro
    assert lines[HISTORY_ROW + 2] == "  " + FIRST_HINT
    screen = screen_for(world, player, [Message(world.intro, Tone.NARRATION), Message("Hi.")])
    lines = rows(screen)
    assert lines[HISTORY_ROW + 1] == "  " + world.intro  # now an older, dim entry
    assert lines[HISTORY_ROW + 2] == "  » Hi."
    assert screen.rows[HISTORY_ROW + 1][0][1] is Role.HISTORY


def test_first_screen_shows_the_hint_and_nothing_is_cut(world: World, player: Player) -> None:
    lines = rows(screen_for(world, player))
    assert lines[HISTORY_ROW + 2] == "  " + FIRST_HINT
    assert lines[HISTORY_ROW] == lines[HISTORY_ROW + 1] == ""
    assert lines[-1] == "  [Electrical Room] > "
    assert not any(line.endswith("…") for line in lines)


def test_there_is_no_try_line(world: World, player: Player) -> None:
    play_turn(player, "open toolbox")
    text = "\n".join(rows(screen_for(world, player, [Message("You open the toolbox.")])))
    assert "Try" not in text
    assert "take screwdriver" not in text


def test_top_border_matches_the_spec_mock() -> None:
    mock = (
        "╭────────────────────────────────────── ELECTRICAL ROOM "
        "───────────────────────────── 3 moves ─╮"
    )
    assert line_text(top_border("ELECTRICAL ROOM", 3)) == mock


@pytest.mark.parametrize(
    ("moves", "label"), [(0, " 0 moves "), (1, " 1 move "), (11, " 11 moves ")]
)
def test_move_counter_sits_one_dash_before_the_corner(moves: int, label: str) -> None:
    border = top_border("ELECTRICAL ROOM", moves)
    text = line_text(border)
    assert cell_len(text) == BLOCK_WIDTH
    assert text.endswith(label + "─╮")
    assert (label, Role.LABEL) in border


def test_long_titles_are_cut_so_they_never_reach_the_counter() -> None:
    text = line_text(top_border("X" * 80, 999))
    assert cell_len(text) == BLOCK_WIDTH
    assert "X" * 59 + "…" in text and " 999 moves ─╮" in text


def test_verb_panel_is_the_same_in_every_state_and_names_no_object(
    world: World, player: Player
) -> None:
    names = ["toolbox", "fuse box", "screwdriver", "wrench", "key", "fuse", "flashbulb", "door"]
    panels = set()
    for line in PLAYTHROUGH:
        play_turn(player, line)
        panel = tuple(
            row[:32] for row in rows(screen_for(world, player))[PANELS_ROW:][:PANEL_HEIGHT]
        )
        panels.add(panel)
    (panel,) = panels
    assert len(panel) == PANEL_HEIGHT == 7
    assert panel[1] == "│ Look    l     Inspect x      │"
    assert panel[4] == "│ Help    ?     Quit    q      │"
    assert panel[5] == "│" + " " * 30 + "│"  # blank, as tall as the slots
    assert not any(name in row.lower() for row in panel for name in names)


def test_slots_show_icon_and_name_and_empty_slots_are_empty_frames(
    world: World, player: Player
) -> None:
    play_turn(player, "take flashbulb")
    panel = rows(screen_for(world, player))[PANELS_ROW : PANELS_ROW + PANEL_HEIGHT]
    first = [row[34:48] for row in panel]
    icon = world.icon_for("flashbulb")
    assert icon is not None
    assert first == [
        "╭────────────╮",
        *(f"│ {row} │" for row in icon.frame().rows),  # 10 × 4, one cell of padding
        "│ flashbulb  │",  # odd space goes right
        "╰────────────╯",
    ]
    for start in (50, 66, 82):
        empty = [row[start : start + 14] for row in panel]
        assert empty[1:6] == ["│            │"] * 5


def test_slot_without_an_icon_shows_only_the_name_and_long_names_are_cut() -> None:
    assert [line_text(row) for row in slot("rope")][1:6] == [
        "│            │",
        "│            │",
        "│            │",
        "│            │",
        "│    rope    │",
    ]
    assert line_text(slot("a very long rope name")[5]) == "│a very long…│"


def test_every_portable_item_has_an_icon(world: World) -> None:
    for name in ["flashbulb", "screwdriver", "wrench", "key", "fuse"]:
        icon = world.icon_for(name)
        assert icon is not None and icon.size == ICON, name


def test_just_taken_item_is_spotlit_in_its_slot(world: World, player: Player) -> None:
    play_turn(player, "take flashbulb")
    screen = screen_for(world, player, focus="flashbulb")
    lit = roles_of(screen, Role.FOCUS)
    icon = world.icon_for("flashbulb")
    assert icon is not None
    assert icon.frame().rows[0].strip() in lit and "╭────────────╮" in lit
    assert "flashbulb" not in lit  # the name keeps its VERB role


def test_changed_object_is_spotlit_in_the_room(world: World, player: Player) -> None:
    play_turn(player, "open toolbox")
    screen = screen_for(world, player, focus="toolbox")
    lit = [text for line in screen.rows for text, role in line if role is Role.FOCUS]
    assert lit[0] == world.art_for(player.current_room).sprites["toolbox:open"][0]
    assert all(len(text) == len(lit[0]) for text in lit)  # only the toolbox's columns


def test_the_flash_lights_the_whole_picture_and_nothing_else(world: World, player: Player) -> None:
    screen = screen_for(world, player)
    flashed = flash_screen(screen)
    assert [line_text(row) for row in flashed.rows] == [line_text(row) for row in screen.rows]
    picture = flashed.rows[1 : 1 + ART_HEIGHT]
    assert all(role is Role.FOCUS for row in picture for _, role in row[1:-1])
    assert all(row[0][1] is Role.BORDER and row[-1][1] is Role.BORDER for row in picture)
    rest = [*flashed.rows[:1], *flashed.rows[1 + ART_HEIGHT :]]
    assert rest == [*screen.rows[:1], *screen.rows[1 + ART_HEIGHT :]]
    assert (flashed.prompt, flashed.names) == (screen.prompt, screen.names)


def test_shading_follows_the_light_map(world: World, player: Player) -> None:
    screen = screen_for(world, player)
    lamp_row = screen.rows[5]  # picture row 4: the lamp's shade
    assert "▗▟█▙▖" in "".join(text for text, role in lamp_row if role is Role.LIGHT)
    floor_row = screen.rows[17]  # picture row 16: the floor under the lamp, the door far off
    pool = "".join(text for text, role in floor_row if role is Role.GLOW)
    assert "█" in pool or "▓" in pool  # dense tone where the light is strongest
    door_row = screen.rows[6]  # picture row 5: the door's top, far from the lamp
    assert "┌───────────┐" in "".join(text for text, role in door_row if role is Role.SHADOW)


def test_history_keeps_the_newest_at_the_bottom_in_three_rows() -> None:
    history = [Message(f"Result {n}.") for n in range(5)] + [Message("Nope.", Tone.ERROR)]
    lines = history_rows(history)
    assert [line_text(line) for line in lines] == [
        "  » Result 3.",
        "  » Result 4.",
        "  ✗ Nope.",
    ]
    assert [line[0][1] for line in lines] == [Role.HISTORY, Role.HISTORY, Role.ERROR]


def test_a_long_newest_entry_takes_two_rows_and_older_ones_are_cut() -> None:
    long = "word " * 30
    lines = history_rows([Message("old " * 40), Message(long.strip())])
    texts = [line_text(line) for line in lines]
    assert texts[0].endswith("…") and cell_len(texts[0]) <= BLOCK_WIDTH
    assert texts[1].startswith("  » word") and texts[2].startswith("    word")
    assert lines[1][0][1] is Role.RESULT


def test_short_history_is_padded_from_the_top() -> None:
    assert [line_text(line) for line in history_rows([Message("Hi.")])] == ["", "", "  » Hi."]


def test_help_is_one_entry_in_the_history(world: World, player: Player) -> None:
    outcome = play_turn(player, "help")
    assert outcome is not None
    lines = rows(screen_for(world, player, [Message(outcome.message)]))
    assert lines[HISTORY_ROW + 1].startswith("  » Verbs:")  # two rows: it is the newest


def test_tab_offers_verbs_then_visible_names(world: World, player: Player) -> None:
    room, inventory = player.current_room, player.inventory
    names = visible_names(room, inventory)
    assert complete("ins", names) == ["inspect "]
    assert complete("lo", names) == ["look"]
    assert complete("inspect fu", names) == ["inspect fuse box"]
    assert complete("x do", names) == ["x door"]
    assert complete("dance ", names) == []
    play_turn(player, "open toolbox")
    play_turn(player, "take screwdriver")
    names = visible_names(room, inventory)
    assert complete("use scr", names) == ["use screwdriver "]
    assert complete("use screwdriver o", names) == ["use screwdriver on "]
    assert complete("use screwdriver on fu", names) == ["use screwdriver on fuse box"]


def test_tab_never_offers_an_item_inside_a_closed_container(world: World, player: Player) -> None:
    room = player.current_room
    names = visible_names(room, player.inventory)
    assert "screwdriver" not in names and "key" not in names
    assert complete("take k", names) == []
    play_turn(player, "open toolbox")
    assert "screwdriver" in visible_names(room, player.inventory)


def test_inspect_view_shows_the_close_up_name_hint_and_description(
    world: World, player: Player
) -> None:
    for line in ["open toolbox", "take screwdriver"]:
        play_turn(player, line)
    history = [Message("You look closely at the screwdriver.")]
    screen = screen_for(
        world, player, history, moves=3, inspected=inspect(world, player, "screwdriver")
    )
    lines = rows(screen)
    assert " SCREWDRIVER " in lines[0] and lines[0].endswith(" 3 moves ─╮")
    assert lines[ART_HEIGHT + 1].startswith("╰─ Enter returns to the room ─")
    assert "▗▄▄▄▄" in lines[4]  # the close-up, not the room
    assert lines[DESCRIPTION_ROW].startswith("  A worn flathead. The tip is just the width")
    assert lines[-1] == "  [Electrical Room] > "  # the room is still where you are


def test_inspecting_without_a_close_up_keeps_the_room_with_the_thing_in_the_spotlight(
    world: World, player: Player
) -> None:
    room_rows = rows(screen_for(world, player))
    screen = screen_for(world, player, inspected=inspect(world, player, "toolbox"))
    lines = rows(screen)
    assert " TOOLBOX " in lines[0]
    assert lines[1 : ART_HEIGHT + 1] == room_rows[1 : ART_HEIGHT + 1]  # the room picture stays
    assert lines[ART_HEIGHT + 1].startswith("╰─ Enter returns to the room ─")
    assert lines[DESCRIPTION_ROW].startswith("  Your own toolbox, dented and familiar.")
    lit = roles_of(screen, Role.FOCUS)
    assert world.art_for(player.current_room).sprites["toolbox:closed"][1] in lit


def test_close_up_frame_follows_the_state() -> None:
    picture = parse_picture("[closed]\nshut\n[open]\nwide\n", ICON)
    inventory = Inventory([Item("box")])
    room = Room("Lab", "", Door(None, "key"), [Container("crate")])
    art = parse_art("[background]\n.\n[door:locked]\nD\n")
    for state, shown in [("closed", "shut"), ("open", "wide"), (None, "shut")]:
        inspected = Inspected("crate", "A crate.", picture, state)
        assert shown in line_text(build_screen(room, inventory, art, inspected=inspected).rows[1])


def test_tab_never_offers_the_hidden_fuse(world: World, player: Player) -> None:
    room = player.current_room
    for line in ["open toolbox", "take wrench", "open vent"]:
        play_turn(player, line)
    assert "fuse" not in visible_names(room, player.inventory)
    for line in ["take flashbulb", "use flashbulb on vent"]:
        play_turn(player, line)
    assert "fuse" in visible_names(room, player.inventory)


def test_win_screen_shows_the_ending_and_no_prompt(
    world: World, player: Player, win_script: list[str]
) -> None:
    outcomes = [play_turn(player, line, world.par) for line in win_script]
    outcome = outcomes[-1]
    assert outcome is not None and outcome.won
    history = [Message(outcome.message, Tone.WIN)]
    room = player.current_room
    screen = build_win_screen(
        room, player.inventory, world.art_for(room), history, world.ending, moves=player.moves
    )
    lines = rows(screen)
    assert screen.prompt == "" and lines[-1] == "Thanks for playing."
    assert lines[HISTORY_ROW + 2] == "  ✓ Escaped in 12 moves. Par is 12. Sharp."
    assert lines[0].endswith(" 12 moves ─╮")
    assert len(lines) == BLOCK_HEIGHT


def test_ascii_fallback_keeps_every_row_the_same_width(
    world: World, player: Player, win_script: list[str]
) -> None:
    history = [Message("x"), Message("Nope…", Tone.ERROR)]
    screens = []
    for line in win_script:
        play_turn(player, line)
        screens.append(screen_for(world, player, history))
        if line == "take screwdriver":
            inspected = inspect(world, player, "screwdriver")
            screens.append(screen_for(world, player, history, inspected=inspected))
    for screen in screens:
        for row in rows(screen):
            plain = to_ascii(row)
            assert plain.isascii(), plain
            assert len(plain) == cell_len(row)


def test_crowded_description_keeps_every_object_and_the_door(world: World, player: Player) -> None:
    script = ["open toolbox", "take screwdriver", "take wrench", "open fuse box", "take key"]
    for line in [*script, "open vent", "drop screwdriver", "drop wrench", "drop key"]:
        play_turn(player, line)
    lines = rows(screen_for(world, player))[DESCRIPTION_ROW : DESCRIPTION_ROW + 3]
    text = " ".join(line.strip() for line in lines)
    assert "…" not in text
    assert "On the floor: screwdriver, wrench, key." in text
    assert text.endswith("The steel door is locked.")


def test_description_changes_after_open_and_take(player: Player) -> None:
    room = player.current_room
    assert "A toolbox waits on the floor." in describe_room(room)
    play_turn(player, "open toolbox")
    assert "The toolbox gapes open. Inside: screwdriver, wrench." in describe_room(room)
    play_turn(player, "take wrench")
    assert "Inside: screwdriver." in describe_room(room)


def test_too_small_screen_names_both_sizes() -> None:
    lines = [text for text, _ in too_small_lines(80, 24)]
    assert lines == [
        "Make the window bigger",
        "The game needs 100 × 44. It is now 80 × 24.",
        "It redraws as soon as it fits.",
    ]
    assert [role for _, role in too_small_lines(80, 24)] == [Role.TITLE, Role.TEXT, Role.LABEL]


# Drawing cells as line art or tone (docs/SCREEN-SPEC.md §5.1, §6)

LIT_ROOM = """\
[background]
|   *  *
[shade]
 9999999
[light]
99999nrf
"""


def lit_room() -> tuple[Room, list[list[tuple[str, Role]]]]:
    room = Room("Lab", "", Door(None))
    picture = room_picture(parse_art(LIT_ROOM), room)
    return room, [[(char, role) for text, role in line for char in text] for line in picture]


def test_blank_cells_become_tone_and_drawn_cells_stay_as_drawn() -> None:
    _, cells = lit_room()
    row = "".join(char for char, _ in cells[0])
    assert row[0] == "|" and row[4] == "*" and row[7] == "*"
    assert set(row[1:4]) == {"█"}  # shade 9 under light 9
    assert set("".join(char for line in cells for char, _ in line)) <= set(RAMP) | set("|*")


def test_the_light_level_picks_the_role_and_letters_fix_it() -> None:
    art = parse_art("[background]\n" + "x" * 10 + "\n[light]\n0123456789\n")
    picture = room_picture(art, Room("Lab", "", Door(None)))
    roles = [role for text, role in picture[0] for _ in text][:10]
    assert roles == [Role.SHADOW] * 3 + [Role.DUSK] * 2 + [Role.LIT] * 3 + [Role.GLOW] * 2
    _, cells = lit_room()
    assert [role for _, role in cells[0][5:8]] == [Role.NIGHT, Role.DANGER, Role.PLAIN]


def test_only_line_art_light_sources_in_the_light_are_bold_light() -> None:
    _, cells = lit_room()
    assert cells[0][4] == ("*", Role.LIGHT)  # a drawn light source at light 9
    assert all(role is Role.GLOW for _, role in cells[0][1:4])  # tone █ never is LIGHT
    dark = room_picture(parse_art("[background]\n*\n[light]\n4\n"), Room("Lab", "", Door(None)))
    assert dark[0][0] == ("*", Role.DUSK)


def test_the_room_drawing_never_changes_between_draws(world: World, player: Player) -> None:
    room = player.current_room
    art = world.art_for(room)
    assert room_picture(art, room) == room_picture(art, room)


def test_the_flash_draws_the_room_at_full_light() -> None:
    art = parse_art("[background]\n  \n[shade]\n99\n[light]\n00\n")
    room = Room("Lab", "", Door(None))
    assert line_text(room_picture(art, room)[0]).startswith("  ")  # dark: black
    assert line_text(room_picture(art, room, full_light=True)[0]).startswith("██")


def test_picture_blanks_with_shade_become_tone_and_colour_digits_are_light_levels() -> None:
    frame = Frame(("x  ",), ("923",), ("099",))
    (line,) = frame_lines(frame)
    assert line_text(line) == "x██"
    assert [role for text, role in line for _ in text] == [Role.GLOW, Role.SHADOW, Role.DUSK]
