import copy
import textwrap
from typing import Any

import pytest

from text_adventure.art import CLOSEUP, ICON, parse_art, parse_picture
from text_adventure.game import play_turn
from text_adventure.models import Player, Thing
from text_adventure.screen import describe_room, object_sentences
from text_adventure.solve import reachable
from text_adventure.world import (
    World,
    WorldError,
    art_paths,
    build_world,
    missing_pictures,
    picture_paths,
    summarize,
)

ART = {"room.txt": parse_art("[background]\n.\n")}
PICTURES = {
    "icon.txt": parse_picture("[default]\no\n", ICON),
    "big.txt": parse_picture("[closed]\n[ ]\n[open]\n] [\n", CLOSEUP),
}
BASE: dict[str, Any] = {
    "rooms": [
        {
            "id": "r1",
            "name": "Lab",
            "description": "A lab.",
            "art": "room.txt",
            "items": [{"name": "coin"}],
            "containers": [{"name": "desk", "contents": [{"name": "key"}]}],
            "door": {"required_item": "key", "next_room": None},
        }
    ]
}


COIN_USE = {"item": "coin", "text": "Clink."}
NEEDY_USE = {**COIN_USE, "refusal": "Not yet."}


def broken(change: Any) -> dict[str, Any]:
    data = copy.deepcopy(BASE)
    change(data["rooms"][0])
    return data


def desk(room: dict[str, Any], **fields: Any) -> None:
    room["containers"][0].update(fields)


def with_a_puzzle(room: dict[str, Any]) -> None:
    """Rubbing the coin on the desk lights it and brings a gem out from under it."""
    room["items"].append({"name": "gem", "hidden": True})
    desk(
        room,
        inspect={"closed": "A desk.", "lit": "A glowing desk."},
        uses=[
            {
                "item": "coin",
                "needs": {"desk": "closed"},
                "refusal": "Close it first.",
                "text": "The desk glows.",
                "state": "lit",
                "reveal": ["gem"],
                "consume": True,
            }
        ],
    )
    room["door"].update(needs={"desk": "lit"}, refusal="Not yet.", inspect="Oak.")


def test_uses_needs_and_hidden_items_build() -> None:
    data = broken(with_a_puzzle)
    data["par"] = 4
    world = build_world(data, ART)
    room = world.first_room
    desk_ = room.find_container("desk")
    assert desk_ is not None
    assert desk_.uses[0].reveal == ("gem",) and desk_.uses[0].consume
    assert desk_.details == {"closed": "A desk.", "lit": "A glowing desk."}
    assert [item.name for item in room.hidden] == ["gem"]
    assert room.door.needs == {"desk": "lit"} and room.door.details == {"": "Oak."}
    assert world.par == 4


def test_a_use_can_flash() -> None:
    data = broken(with_a_puzzle)
    world = build_world(data, ART)
    desk_ = world.first_room.find_container("desk")
    assert desk_ is not None and not desk_.uses[0].flash  # off unless the rule says so
    data["rooms"][0]["containers"][0]["uses"][0]["flash"] = True
    desk_ = build_world(data, ART).first_room.find_container("desk")
    assert desk_ is not None and desk_.uses[0].flash


def test_flash_must_be_true_or_false() -> None:
    data = broken(with_a_puzzle)
    data["rooms"][0]["containers"][0]["uses"][0]["flash"] = "yes"
    with pytest.raises(WorldError, match='"flash"'):
        build_world(data, ART)


@pytest.mark.parametrize("par", [0, -1, "8", True, 2.5])
def test_par_must_be_a_positive_whole_number(par: Any) -> None:
    with pytest.raises(WorldError, match='"par"'):
        build_world({**BASE, "par": par}, ART)


def test_default_world_loads_from_package_data(world: World) -> None:
    room = world.first_room
    assert room.name == "Electrical Room"
    assert room.door.is_exit()
    assert world.intro and world.ending


def test_small_valid_world_builds() -> None:
    assert build_world(BASE, ART).first_room.find_container("desk") is not None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda r: r["items"].append({"name": "key"}), "repeat: key"),
        (lambda r: r["items"].append({"name": "door"}), "reserved"),
        (lambda r: r["door"].update(required_item="crowbar"), "crowbar"),
        (lambda r: r["containers"][0].update(sprite=[0, 0]), r"\[desk:open\]"),
        (lambda r: r["items"].append({"name": "Big Coin"}), "lower case"),
        (lambda r: r.pop("door"), "door"),
        (lambda r: r["door"].update(next_room="r9"), "r9"),
        (lambda r: r["items"][0].update(icon="nope.txt"), 'no picture loaded for "nope.txt"'),
        (lambda r: r["items"][0].update(icon="big.txt"), "needs icon size"),
        (lambda r: r["door"].update(closeup="icon.txt"), "is icon size"),
        (lambda r: r["containers"][0].update(closeup=3), '"closeup" must be a string'),
        (lambda r: r["items"].append({"name": "box on top"}), "can't contain"),
        (lambda r: r["items"].append({"name": "box with lid"}), "can't contain"),
        (lambda r: desk(r, uses=[{"item": "nope", "text": "x"}]), 'no item "nope"'),
        (lambda r: desk(r, uses=[{"text": "x"}]), 'needs an "item"'),
        (lambda r: desk(r, uses=[COIN_USE, COIN_USE]), "two uses"),
        (lambda r: desk(r, uses=[{**NEEDY_USE, "needs": {"lamp": "lit"}}]), "isn't in this room"),
        (lambda r: desk(r, uses=[{**NEEDY_USE, "needs": {"desk": "lit"}}]), 'never "lit"'),
        (lambda r: desk(r, uses=[{**COIN_USE, "needs": {"desk": "open"}}]), '"refusal"'),
        (lambda r: desk(r, uses=[{**COIN_USE, "reveal": ["key"]}]), "not a hidden item"),
        (lambda r: desk(r, uses=[{**COIN_USE, "state": "open"}]), "lower case words"),
        (lambda r: desk(r, uses=[{**COIN_USE, "state": "Lit Up"}]), "lower case words"),
        (lambda r: desk(r, required_item="coin", uses=[COIN_USE]), "already the required_item"),
        (lambda r: desk(r, inspect={"lit": "Bright."}), "never in"),
        (lambda r: desk(r, inspect=["x"]), '"inspect" must be'),
        (lambda r: r["door"].update(uses=[{**COIN_USE, "state": "lit"}]), "no story states"),
        (lambda r: r["door"].update(needs={"desk": "closed"}), '"refusal"'),
        (lambda r: r["items"].append({"name": "gem", "hidden": True}), '"gem" is never revealed'),
    ],
)
def test_broken_world_raises(change: Any, message: str) -> None:
    with pytest.raises(WorldError, match=message):
        build_world(broken(change), ART, PICTURES)


def with_pictures(room: dict[str, Any]) -> None:
    room["items"][0].update(icon="icon.txt", closeup="big.txt")
    room["containers"][0].update(closeup="big.txt")
    room["containers"][0]["contents"][0].update(icon="icon.txt")
    room["door"].update(closeup="big.txt")


def test_pictures_are_found_by_object() -> None:
    world = build_world(broken(with_pictures), ART, PICTURES)
    room = world.first_room
    assert world.icon_for("coin") is PICTURES["icon.txt"]
    assert world.closeup_for(room, "desk") is PICTURES["big.txt"]
    assert world.closeup_for(room, "door") is PICTURES["big.txt"]
    assert world.closeup_for(room, "key") is None


def test_missing_pictures_lists_each_missing_icon_and_closeup() -> None:
    assert missing_pictures(build_world(broken(with_pictures), ART, PICTURES)) == [
        'item "key" has no close-up'
    ]
    assert missing_pictures(build_world(BASE, ART)) == [
        'item "coin" has no icon',
        'item "coin" has no close-up',
        'item "key" has no icon',
        'item "key" has no close-up',
        'container "desk" has no close-up',
        'room "Lab": the door has no close-up',
    ]


def test_scenery_needs_no_icon() -> None:
    world = build_world(broken(lambda r: r["items"][0].update(portable=False)), ART)
    assert 'item "coin" has no icon' not in missing_pictures(world)


def test_picture_paths_lists_each_picture_with_its_size() -> None:
    assert picture_paths(broken(with_pictures)) == {"icon.txt": ICON, "big.txt": CLOSEUP}
    assert picture_paths({"rooms": [{"items": "x", "door": 3}, 1]}) == {}
    assert picture_paths([]) == {}


def test_rooms_must_be_a_non_empty_list() -> None:
    with pytest.raises(WorldError):
        build_world({"rooms": []}, ART)
    with pytest.raises(WorldError):
        build_world([1, 2], ART)


def test_summarize_counts_rooms_containers_and_items(world: World) -> None:
    summary = summarize(world)
    assert (summary.rooms, summary.containers, summary.items) == (1, 3, 5)  # the fuse is hidden
    assert summary.first_room == "Electrical Room"


def test_art_paths_lists_each_rooms_art_file() -> None:
    assert art_paths(BASE) == ["room.txt"]


def test_art_paths_skips_malformed_data() -> None:
    assert art_paths({"rooms": "not a list"}) == []
    assert art_paths({"rooms": [{"art": 3}, "x"]}) == []
    assert art_paths([]) == []


SPEC_TEXT_WIDTH = 92  # docs/SCREEN-SPEC.md §2: description and history text width


def test_every_clue_fits_the_inspect_view_and_every_result_the_history(world: World) -> None:
    """Inspect texts fill the 3 description rows (§4), use results the newest history entry,
    which may take 2 rows after its 2-cell marker (§3.5)."""
    room = world.first_room
    things: list[Thing] = [room.door, *room.containers, *room.items, *room.hidden]
    things += [item for container in room.containers for item in container.contents]
    things += [item for container in room.containers for item in container.hidden]
    for thing in things:
        assert thing.details, thing  # every object has something to say when inspected
        for text in thing.details.values():
            assert len(textwrap.wrap(text, SPEC_TEXT_WIDTH)) <= 3, text
        results = [thing.refusal, *(use.text for use in thing.uses)]
        results += [use.refusal for use in thing.uses]
        for text in results:
            assert len(textwrap.wrap(text, SPEC_TEXT_WIDTH - 2)) <= 2, text


def rows_at_spec_width(text: str) -> int:
    return len(textwrap.wrap(text, SPEC_TEXT_WIDTH))


def test_the_whole_description_fits_along_the_par_route(
    world: World, player: Player, win_script: list[str]
) -> None:
    """Mood and every object's sentence fit the 3 description rows (§3.2) at each step."""
    for line in ["", *win_script]:
        if line:
            play_turn(player, line)
        assert rows_at_spec_width(describe_room(player.current_room)) <= 3, line


def test_object_sentences_fit_in_every_reachable_state(world: World) -> None:
    """In any state, however many things lie on the floor, the objects and the door fit the
    3 rows once the mood sentence makes way (§3.2), so nothing is ever cut."""
    states = reachable(world)
    assert len(states) > 100
    for player in states:
        sentences = " ".join(object_sentences(player.current_room))
        assert rows_at_spec_width(sentences) <= 3, sentences


def test_room_text_follows_the_state(player: Player, win_script: list[str]) -> None:
    room = player.current_room
    assert "A vent sits low in the dark." in describe_room(room)
    assert "The steel door is locked." in describe_room(room)
    for line in win_script[:5]:  # up to the flash
        play_turn(player, line)
    assert "The vent hangs open, its duct gone dark again. Inside: fuse." in describe_room(room)
    for line in win_script[5:10]:  # up to the power coming back
        play_turn(player, line)
    assert "The fuse box hums; a red light glows by the door." in describe_room(room)
    play_turn(player, win_script[10])
    assert describe_room(room).endswith("a green light over its keyhole.")


def test_room_text_states_are_checked() -> None:
    with pytest.raises(WorldError, match='room_text for "lit"'):
        build_world(broken(lambda r: desk(r, room_text={"lit": "Bright."})), ART)
    with pytest.raises(WorldError, match='"room_text" must be'):
        build_world(broken(lambda r: desk(r, room_text={"open": 3})), ART)
    world = build_world(broken(lambda r: desk(r, room_text={"open": "Wide."})), ART)
    desk_ = world.first_room.find_container("desk")
    assert desk_ is not None and desk_.room_sentence() == ""  # no closed_text either
    desk_.is_open = True
    assert desk_.room_sentence() == "Wide."
