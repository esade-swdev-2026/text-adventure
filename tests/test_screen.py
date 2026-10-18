from rich.cells import cell_len

from text_adventure.game import play_turn
from text_adventure.models import Player
from text_adventure.screen import (
    MIN_COLUMNS,
    MIN_ROWS,
    Role,
    Screen,
    Tone,
    available_commands,
    build_screen,
    build_win_screen,
    complete,
    describe_room,
    layout,
    line_text,
    to_ascii,
)
from text_adventure.world import World


def screen_for(world: World, player: Player, message: str = "") -> Screen:
    room = player.current_room
    return build_screen(room, player.inventory, world.art_for(room), message)


def rows(screen: Screen) -> list[str]:
    """Every row of the screen, including the prompt, as plain text."""
    return [line_text(line) for line in layout(screen)] + [screen.prompt]


def test_description_changes_after_open_and_take(player: Player) -> None:
    room = player.current_room
    assert "A toolbox waits on the floor." in describe_room(room)
    play_turn(player, "open toolbox")
    assert "The toolbox gapes open. Inside: screwdriver, wrench." in describe_room(room)
    play_turn(player, "take wrench")
    assert "Inside: screwdriver." in describe_room(room)


def test_available_commands_follow_the_state(player: Player) -> None:
    room, inventory = player.current_room, player.inventory
    assert "open toolbox" in available_commands(room, inventory)
    play_turn(player, "open toolbox")
    commands = available_commands(room, inventory)
    assert "open toolbox" not in commands
    assert "take screwdriver" in commands
    play_turn(player, "take screwdriver")
    assert "drop screwdriver" in available_commands(room, inventory)


def test_opening_screen_fits_the_minimum_size(world: World, player: Player) -> None:
    screen = screen_for(world, player, world.intro)
    lines = rows(screen)
    assert len(lines) < MIN_ROWS  # one spare row, so Enter never scrolls the panel away
    assert all(cell_len(line) <= MIN_COLUMNS for line in lines)
    assert not any(line.endswith("…") for line in lines), "nothing should be cut off"


def test_every_screen_in_a_playthrough_has_the_same_height(world: World, player: Player) -> None:
    script = [
        "open toolbox",
        "take screwdriver",
        "take wrench",
        "open fuse box",
        "take key",
        "take fuse",
        "take flashbulb",
        "dance",
        "help",
        "inventory",
        "drop wrench",
    ]
    heights = set()
    for line in script:
        outcome = play_turn(player, line)
        assert outcome is not None
        screen = screen_for(world, player, outcome.message)
        heights.add(len(rows(screen)))
        assert all(cell_len(row) <= MIN_COLUMNS for row in rows(screen)), line
    assert len(heights) == 1


def test_win_screen_shows_the_ending_and_no_prompt(world: World, player: Player) -> None:
    for line in ["open toolbox", "take screwdriver", "open fuse box", "take key", "open door"]:
        play_turn(player, line)
    room = player.current_room
    assert room.door.is_open
    screen = build_win_screen(room, world.art_for(room), "out", world.ending)
    assert screen.tone is Tone.WIN and screen.prompt == ""
    assert screen.message[0].startswith("✓ ")
    assert len(rows(screen)) <= MIN_ROWS


def test_prompt_lines_up_with_the_text_column(world: World, player: Player) -> None:
    screen = screen_for(world, player)
    assert screen.prompt == "  [Electrical Room] > "


def test_ascii_fallback_keeps_every_row_the_same_width(world: World, player: Player) -> None:
    for line in ["", "open toolbox", "take screwdriver", "open fuse box", "take key"]:
        play_turn(player, line)
    for row in rows(screen_for(world, player, "✗ Inventory full…")):
        plain = to_ascii(row)
        assert plain.isascii(), plain
        assert len(plain) == cell_len(row)


def test_changed_object_is_in_the_spotlight(world: World, player: Player) -> None:
    play_turn(player, "open toolbox")
    room = player.current_room
    screen = build_screen(room, player.inventory, world.art_for(room), "", focus="toolbox")
    lit = [text for line in layout(screen) for text, role in line if role is Role.FOCUS]
    assert lit[0].startswith("╔═════════╗")  # the open box, and only the toolbox's columns
    assert all(len(text) == len(lit[0]) for text in lit)


def test_inventory_is_shown_in_the_panel_border(world: World, player: Player) -> None:
    play_turn(player, "take flashbulb")
    border = line_text(layout(screen_for(world, player))[11])
    assert border.startswith("╰─ Carrying (1/4): flashbulb ─")
    assert border.endswith("╯")


def test_crowded_description_keeps_every_object_and_the_door(world: World, player: Player) -> None:
    script = ["open toolbox", "take screwdriver", "take wrench", "open fuse box", "take key"]
    for line in [*script, "take fuse", "drop screwdriver", "drop wrench", "drop key", "drop fuse"]:
        play_turn(player, line)
    rows_ = screen_for(world, player).description
    text = " ".join(rows_)
    assert "…" not in text
    assert "On the floor: screwdriver, wrench, key, fuse." in text
    assert text.endswith("The door is shut tight.")


def test_help_never_splits_a_command_from_its_short_form(world: World, player: Player) -> None:
    outcome = play_turn(player, "help")
    assert outcome is not None
    message = screen_for(world, player, outcome.message).message
    assert not any(row.rstrip().endswith(("inventory", "help", "quit")) for row in message)


def test_shading_follows_the_light_map(world: World, player: Player) -> None:
    lines = layout(screen_for(world, player))
    lamp_row = lines[3]  # art row 2: the lamp is lit, the fuse box beside it is in shadow
    lit = "".join(text for text, role in lamp_row if role is Role.LIT)
    shadow = "".join(text for text, role in lamp_row if role is Role.ART)
    assert "▗▟█▙▖" in lit
    assert "┌──────────┐" in shadow


def test_tab_completes_from_the_available_commands() -> None:
    commands = ["open toolbox", "open fuse box", "take flashbulb", "open door"]
    assert complete("open f", commands) == ["open fuse box"]
    assert complete("OPEN  ", commands) == ["open toolbox", "open fuse box", "open door"]
    assert complete("dance", commands) == []
