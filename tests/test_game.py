from text_adventure.commands import Command, Verb
from text_adventure.game import apply_command, play_turn
from text_adventure.models import CAPACITY, Player


def run(player: Player, *lines: str) -> str:
    message = ""
    for line in lines:
        outcome = play_turn(player, line)
        assert outcome is not None
        message = outcome.message
    return message


def test_locked_container_stays_shut_without_the_tool(player: Player) -> None:
    outcome = play_turn(player, "open fuse box")
    assert outcome is not None and outcome.error
    assert outcome.message == "The fuse box is locked."


def test_container_opens_with_the_tool_and_the_tool_is_kept(player: Player) -> None:
    message = run(player, "open toolbox", "take screwdriver", "open fuse box")
    assert message == "You open the fuse box with the screwdriver. Inside: key, fuse."
    assert player.inventory.has_item("screwdriver")


def test_full_inventory_refuses_a_fifth_item(player: Player) -> None:
    run(player, "open toolbox", "take screwdriver", "take wrench", "open fuse box")
    run(player, "take key", "take fuse")
    assert player.inventory.count() == CAPACITY
    outcome = play_turn(player, "take flashbulb")
    assert outcome is not None and outcome.error
    assert "hands are full" in outcome.message


def test_drop_then_take_back(player: Player) -> None:
    assert run(player, "take flashbulb", "drop flashbulb") == "You drop the flashbulb."
    assert player.current_room.find_visible_item("flashbulb") is not None
    assert run(player, "take flashbulb") == "You take the flashbulb."


def test_door_is_locked_without_the_key(player: Player) -> None:
    outcome = apply_command(player, Command(Verb.OPEN, "door"))
    assert outcome.error and not outcome.won


def test_opening_the_door_with_the_key_wins_and_uses_it_up(player: Player) -> None:
    run(player, "open toolbox", "take screwdriver", "open fuse box", "take key")
    outcome = play_turn(player, "open door")
    assert outcome is not None and outcome.won
    assert not player.inventory.has_item("key")


def test_unknown_names_give_the_right_message(player: Player) -> None:
    assert run(player, "open lamp") == "There is no lamp here."
    assert run(player, "take key") == "There is no key here."
    assert run(player, "drop key") == "You aren't carrying a key."


def test_empty_line_does_nothing_and_quit_quits(player: Player) -> None:
    assert play_turn(player, "  ") is None
    outcome = play_turn(player, "q")
    assert outcome is not None and outcome.quit
