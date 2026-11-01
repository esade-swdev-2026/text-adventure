import copy
from typing import Any

import pytest

from text_adventure.art import CLOSEUP, ICON, parse_art, parse_picture
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


def broken(change: Any) -> dict[str, Any]:
    data = copy.deepcopy(BASE)
    change(data["rooms"][0])
    return data


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
    assert (summary.rooms, summary.containers, summary.items) == (1, 2, 5)
    assert summary.first_room == "Electrical Room"


def test_art_paths_lists_each_rooms_art_file() -> None:
    assert art_paths(BASE) == ["room.txt"]


def test_art_paths_skips_malformed_data() -> None:
    assert art_paths({"rooms": "not a list"}) == []
    assert art_paths({"rooms": [{"art": 3}, "x"]}) == []
    assert art_paths([]) == []
