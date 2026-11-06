from typing import Any

from text_adventure.art import parse_art
from text_adventure.commands import Command, Verb
from text_adventure.solve import command_text, shortest_win
from text_adventure.world import World, build_world

ART = {"room.txt": parse_art("[background]\n.\n")}


def one_room(**room: Any) -> dict[str, Any]:
    return {
        "rooms": [
            {"id": "r1", "name": "Lab", "description": "A lab.", "art": "room.txt", **room},
        ]
    }


def test_the_built_in_world_is_won_in_par(world: World, win_script: list[str]) -> None:
    route = shortest_win(world)
    assert route is not None
    assert len(route) == len(win_script) == world.par
    assert route[-1] == "open door"


def test_the_search_plays_a_copy_and_leaves_the_world_alone(world: World) -> None:
    shortest_win(world)
    room = world.first_room
    assert not room.door.is_open
    assert not any(container.is_open for container in room.containers)


def test_a_world_whose_key_is_locked_inside_its_own_box_cant_be_won() -> None:
    data = one_room(
        containers=[{"name": "box", "required_item": "key", "contents": [{"name": "key"}]}],
        door={"required_item": "key", "next_room": None},
    )
    assert shortest_win(build_world(data, ART)) is None


def test_the_search_finds_a_route_through_two_rooms() -> None:
    data = one_room(items=[{"name": "key"}], door={"required_item": "key", "next_room": "r2"})
    data["rooms"].append(
        {
            "id": "r2",
            "name": "Hall",
            "description": "A hall.",
            "art": "room.txt",
            "items": [{"name": "pass"}],
            "door": {"required_item": "pass", "next_room": None},
        }
    )
    assert shortest_win(build_world(data, ART)) == [
        "take key",
        "use key on door",
        "open door",
        "take pass",
        "use pass on door",
        "open door",
    ]


def test_command_text_reads_as_typed() -> None:
    assert command_text(Command(Verb.USE, "fuse", "fuse box")) == "use fuse on fuse box"
    assert command_text(Command(Verb.TAKE, "key")) == "take key"
