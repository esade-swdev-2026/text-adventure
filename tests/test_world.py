import copy
from typing import Any

import pytest

from text_adventure.art import parse_art
from text_adventure.world import World, WorldError, art_paths, build_world, summarize

ART = {"room.txt": parse_art("[background]\n.\n")}
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
    ],
)
def test_broken_world_raises(change: Any, message: str) -> None:
    with pytest.raises(WorldError, match=message):
        build_world(broken(change), ART)


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
