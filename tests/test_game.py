import pytest

from text_adventure.commands import Command, Verb
from text_adventure.game import (
    HELP_TEXT,
    Inspection,
    Outcome,
    apply_command,
    play_turn,
    win_message,
)
from text_adventure.models import CAPACITY, Container, Door, Inventory, Item, Player, Room, Use


def turn(player: Player, line: str, par: int | None = None) -> Outcome:
    outcome = play_turn(player, line, par)
    assert outcome is not None
    return outcome


def run(player: Player, *lines: str) -> str:
    message = ""
    for line in lines:
        message = turn(player, line).message
    return message


# Open, take, drop


def test_locked_container_stays_shut_without_the_tool(player: Player) -> None:
    outcome = turn(player, "open fuse box")
    assert outcome.error
    assert outcome.message == "The fuse box is locked."


def test_container_opens_with_the_tool_and_the_tool_is_kept(player: Player) -> None:
    message = run(player, "open toolbox", "take screwdriver", "open fuse box")
    assert message == "You open the fuse box with the screwdriver. Inside: key."
    assert player.inventory.has_item("screwdriver")


def test_full_inventory_refuses_a_fifth_item(player: Player) -> None:
    run(player, "open toolbox", "take screwdriver", "take wrench", "open fuse box", "take key")
    player.inventory.pick_up_item(Item("coin"))
    assert player.inventory.count() == CAPACITY
    outcome = turn(player, "take flashbulb")
    assert outcome.error
    assert "hands are full" in outcome.message


def test_drop_then_take_back(player: Player) -> None:
    assert run(player, "take flashbulb", "drop flashbulb") == "You drop the flashbulb."
    assert player.current_room.find_visible_item("flashbulb") is not None
    assert run(player, "take flashbulb") == "You take the flashbulb."


def test_unknown_names_give_the_right_message(player: Player) -> None:
    assert run(player, "open lamp") == "There is no lamp here."
    assert run(player, "take key") == "There is no key here."
    assert run(player, "drop key") == "You aren't carrying a key."


def test_empty_line_does_nothing_and_quit_quits(player: Player) -> None:
    assert play_turn(player, "  ") is None
    assert turn(player, "q").quit


def test_help_lists_every_verb() -> None:
    for verb in ["look", "inspect", "open", "take", "drop", "use", "inventory", "help", "quit"]:
        assert verb in HELP_TEXT


# The door


def test_door_is_locked_until_the_key_is_used(player: Player) -> None:
    outcome = apply_command(player, Command(Verb.OPEN, "door"))
    assert outcome.error and not outcome.won


def test_key_wont_turn_until_the_power_is_back(player: Player) -> None:
    run(player, "open toolbox", "take screwdriver", "open fuse box", "take key")
    outcome = turn(player, "use key on door")
    assert outcome.error and "electric bolt" in outcome.message
    assert player.inventory.has_item("key")
    assert player.current_room.door.state == "locked"


def test_the_whole_way_out_wins_in_par(player: Player, win_script: list[str]) -> None:
    for line in win_script[:-1]:
        outcome = turn(player, line, par=12)
        assert not outcome.error and not outcome.won, line
    door = player.current_room.door
    assert door.state == "unlocked"
    assert not player.inventory.has_item("key")  # the key stays in the lock
    outcome = turn(player, "open door", par=12)
    assert outcome.won and outcome.subject == "door"
    assert outcome.message == "Escaped in 12 moves. Par is 12. Sharp."
    assert player.moves == 12


def test_unlocking_twice_says_so(player: Player, win_script: list[str]) -> None:
    run(player, *win_script[:-1])
    player.inventory.pick_up_item(Item("key"))
    outcome = turn(player, "use key on door")
    assert outcome.message == "The door is already unlocked." and not outcome.moved


# Moves and par


@pytest.mark.parametrize("line", ["dance", "help", "look", "inventory", "x door", "open lamp"])
def test_commands_that_change_nothing_are_not_moves(player: Player, line: str) -> None:
    outcome = turn(player, line)
    assert not outcome.moved
    assert player.moves == 0


def test_commands_that_change_the_game_are_moves(player: Player) -> None:
    run(player, "open toolbox", "take wrench", "drop wrench", "open toolbox", "take lamp")
    assert player.moves == 3


@pytest.mark.parametrize(
    ("moves", "par", "message"),
    [
        (11, 8, "Escaped in 11 moves. Par is 8."),
        (8, 8, "Escaped in 8 moves. Par is 8. Sharp."),
        (7, 8, "Escaped in 7 moves. Par is 8. Sharp."),
        (11, None, "Escaped in 11 moves."),
        (1, None, "Escaped in 1 move."),
    ],
)
def test_win_message(moves: int, par: int | None, message: str) -> None:
    assert win_message(moves, par) == message


# Inspect


def test_inspect_an_item_in_the_room(player: Player) -> None:
    outcome = turn(player, "inspect flashbulb")
    assert outcome.inspected == Inspection("flashbulb", "item", None, outcome.message)
    assert "one shot left" in outcome.message
    assert not outcome.error and not outcome.moved


def test_inspect_a_carried_item_with_x_and_examine(player: Player) -> None:
    run(player, "open toolbox", "take wrench")
    assert "bolts on the vent" in run(player, "x wrench")
    assert "bolts on the vent" in run(player, "examine the wrench")


def test_inspect_follows_the_state(player: Player) -> None:
    def fuse_box() -> Inspection:
        inspected = turn(player, "inspect fuse box").inspected
        assert inspected is not None and inspected.kind == "container"
        return inspected

    assert fuse_box().state == "closed" and "scratches" in fuse_box().text
    run(player, "open toolbox", "take screwdriver", "open fuse box")
    assert fuse_box().state == "open" and "pulled out by hand" in fuse_box().text
    run(player, "take wrench", "open vent", "take flashbulb", "use flashbulb on vent")
    run(player, "take fuse", "use fuse on fuse box")
    assert fuse_box().state == "power on"


def test_the_flashbulb_flashes_and_spotlights_the_vent(player: Player) -> None:
    run(player, "open toolbox", "take wrench", "open vent", "take flashbulb")
    outcome = turn(player, "use flashbulb on vent")
    assert outcome.flash and outcome.subject == "vent"
    assert not turn(player, "take fuse").flash  # only for that one moment


def test_a_refused_flash_does_not_flash(player: Player) -> None:
    run(player, "take flashbulb")
    outcome = turn(player, "use flashbulb on vent")  # the vent is still bolted shut
    assert outcome.error and not outcome.flash


def test_inspect_the_door(player: Player) -> None:
    inspected = turn(player, "look at the door").inspected
    assert inspected is not None
    assert (inspected.name, inspected.kind, inspected.state) == ("door", "door", "locked")
    assert "keyhole" in inspected.text


def test_hidden_and_shut_away_things_cant_be_inspected(player: Player) -> None:
    assert run(player, "inspect key") == "There is no key here."
    run(player, "open toolbox", "take wrench", "open vent")
    outcome = turn(player, "inspect fuse")
    assert outcome.error and outcome.message == "There is no fuse here."


def test_inspect_without_details_uses_the_plain_description() -> None:
    room = Room("Lab", "", Door(None, "key"), [Container("box", closed_text="A box.")], [])
    player = Player(room, Inventory([Item("key", "small and brass")]))
    assert run(player, "x key") == "Small and brass."
    assert run(player, "x box") == "A box."
    assert run(player, "x door") == "The door is locked."


# Use


def test_use_needs_the_item_in_hand(player: Player) -> None:
    outcome = turn(player, "use flashbulb on vent")
    assert outcome.error and outcome.message == "You aren't carrying a flashbulb."


def test_use_on_something_that_isnt_here(player: Player) -> None:
    run(player, "take flashbulb")
    assert run(player, "use flashbulb on lamp") == "There is no lamp here."


def test_useless_combinations_are_refused_in_world(player: Player) -> None:
    run(player, "take flashbulb", "open toolbox", "take wrench")
    flash = turn(player, "use flashbulb on toolbox")
    assert flash.error and "one flash" in flash.message
    assert run(player, "use wrench on toolbox") == "The wrench is no use on the toolbox."
    assert run(player, "use wrench") == "Use the wrench on what?"
    assert player.inventory.has_item("flashbulb")
    assert player.moves == 3


def test_using_the_tool_on_a_lock_opens_it(player: Player) -> None:
    run(player, "open toolbox", "take wrench")
    outcome = turn(player, "use the wrench on the vent")
    assert outcome.moved and outcome.subject == "vent"
    assert outcome.message == "You open the vent with the wrench. You can't make anything out."


def test_rule_needs_are_checked_first(player: Player) -> None:
    run(player, "take flashbulb", "open toolbox", "take wrench")
    outcome = turn(player, "use flashbulb on vent")
    assert outcome.error and "bolted shut" in outcome.message
    assert player.inventory.has_item("flashbulb")


def test_flash_reveals_the_fuse_and_is_used_up(player: Player) -> None:
    run(player, "take flashbulb", "open toolbox", "take wrench", "open vent")
    assert run(player, "take fuse") == "There is no fuse here."
    outcome = turn(player, "use flashbulb in vent")
    assert outcome.moved and outcome.subject == "vent"
    assert not player.inventory.has_item("flashbulb")
    assert player.current_room.find_container("vent") is not None
    assert run(player, "inspect vent").startswith("The flash burned")
    assert run(player, "take fuse") == "You take the fuse."


def test_fuse_brings_the_power_back(player: Player) -> None:
    run(player, "open toolbox", "take wrench", "open vent", "take flashbulb")
    run(player, "use flashbulb on vent", "take fuse", "take screwdriver")
    assert turn(player, "use fuse on fuse box").error  # still screwed shut
    run(player, "open fuse box")
    outcome = turn(player, "use fuse on fuse box")
    assert outcome.moved and "red light" in outcome.message
    fuse_box = player.current_room.find_container("fuse box")
    assert fuse_box is not None and fuse_box.state == "power on"
    assert not player.inventory.has_item("fuse")


def test_an_items_own_use() -> None:
    match = Item("match", uses=[Use(None, "It flares.", reveal=("note",), consume=True)])
    room = Room("Lab", "", Door(None), hidden=[Item("note")])
    player = Player(room, Inventory([match]))
    outcome = turn(player, "use match")
    assert outcome.message == "It flares." and outcome.subject == "match" and outcome.moved
    assert [item.name for item in room.items] == ["note"]
    assert not player.inventory.has_item("match")


def test_a_use_can_give_an_item_a_story_state() -> None:
    lamp = Item("lamp", uses=[Use("oil", "It glows.", state="lit")])
    player = Player(Room("Lab", "", Door(None), items=[lamp]), Inventory([Item("oil")]))
    run(player, "use oil on lamp")
    assert lamp.state == "lit"
    assert player.inventory.has_item("oil")  # not consumed
