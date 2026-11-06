import pytest
from rich.cells import cell_len

from text_adventure.art import ART_HEIGHT, ICON, parse_art, parse_picture
from text_adventure.game import play_turn
from text_adventure.models import Container, Door, Inventory, Item, Player, Room
from text_adventure.screen import (
    BLOCK_HEIGHT,
    BLOCK_WIDTH,
    DESCRIPTION_ROW,
    FIRST_HINT,
    HISTORY_ROW,
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
    history_rows,
    line_text,
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
        panel = tuple(row[:32] for row in rows(screen_for(world, player))[PANELS_ROW:][:6])
        panels.add(panel)
    (panel,) = panels
    assert panel[1] == "│ Look    l     Inspect x      │"
    assert panel[4] == "│ Help    ?     Quit    q      │"
    assert not any(name in row.lower() for row in panel for name in names)


def test_slots_show_icon_and_name_and_empty_slots_are_empty_frames(
    world: World, player: Player
) -> None:
    play_turn(player, "take flashbulb")
    panel = rows(screen_for(world, player))[PANELS_ROW : PANELS_ROW + 6]
    first = [row[34:48] for row in panel]
    assert first == [
        "╭────────────╮",
        "│    ▗▆▆▖    │",
        "│    ▐██▌    │",
        "│     ╨╨     │",
        "│ flashbulb  │",  # odd space goes right
        "╰────────────╯",
    ]
    for start in (50, 66, 82):
        empty = [row[start : start + 14] for row in panel]
        assert empty[1:5] == ["│            │"] * 4


def test_slot_without_an_icon_shows_only_the_name_and_long_names_are_cut() -> None:
    assert [line_text(row) for row in slot("rope")][1:5] == [
        "│            │",
        "│            │",
        "│            │",
        "│    rope    │",
    ]
    assert line_text(slot("a very long rope name")[4]) == "│a very long…│"


def test_every_portable_item_has_an_icon(world: World) -> None:
    for name in ["flashbulb", "screwdriver", "wrench", "key", "fuse"]:
        icon = world.icon_for(name)
        assert icon is not None and icon.size == ICON, name


def test_just_taken_item_is_spotlit_in_its_slot(world: World, player: Player) -> None:
    play_turn(player, "take flashbulb")
    screen = screen_for(world, player, focus="flashbulb")
    lit = roles_of(screen, Role.FOCUS)
    assert "▗▆▆▖" in lit and "╭────────────╮" in lit
    assert "flashbulb" not in lit  # the name keeps its VERB role


def test_changed_object_is_spotlit_in_the_room(world: World, player: Player) -> None:
    play_turn(player, "open toolbox")
    screen = screen_for(world, player, focus="toolbox")
    lit = [text for line in screen.rows for text, role in line if role is Role.FOCUS]
    assert lit[0].startswith("╔═════════╗╻")  # only the toolbox's columns
    assert all(len(text) == len(lit[0]) for text in lit)


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
    lamp_row = screen_for(world, player).rows[3]  # picture row 2: the lamp and the fuse box
    light = "".join(text for text, role in lamp_row if role is Role.LIGHT)
    shadow = "".join(text for text, role in lamp_row if role is Role.SHADOW)
    assert "▗▟█▙▖" in light
    assert "┌──────────┐" in shadow


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
    assert lines[12].startswith("╰─ Enter returns to the room ─")
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
    assert lines[1:12] == room_rows[1:12]  # the room picture stays
    assert lines[12].startswith("╰─ Enter returns to the room ─")
    assert lines[DESCRIPTION_ROW].startswith("  Your own toolbox, dented and familiar.")
    lit = roles_of(screen, Role.FOCUS)
    assert "╔═════════╗" in lit


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
        "The game needs 100 × 30. It is now 80 × 24.",
        "It redraws as soon as it fits.",
    ]
    assert [role for _, role in too_small_lines(80, 24)] == [Role.TITLE, Role.TEXT, Role.LABEL]
