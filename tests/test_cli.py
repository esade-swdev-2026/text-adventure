import json
import shutil
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from text_adventure.cli import app
from text_adventure.world import art_paths, picture_paths

runner = CliRunner()


def test_scripted_playthrough_wins_and_exits_0(win_script: list[str]) -> None:
    lines = ["dance", "x the key", *win_script]
    result = runner.invoke(app, ["play"], input="\n".join(lines) + "\n")
    assert result.exit_code == 0
    assert 'I don\'t know how to "dance"' in result.output
    assert "Escaped in 12 moves. Par is 12. Sharp." in result.output
    assert "Thanks for playing." in result.output


def test_end_of_input_says_goodbye_without_a_traceback() -> None:
    result = runner.invoke(app, ["play"], input="open toolbox\n")
    assert result.exit_code == 0
    assert result.output.rstrip().endswith("Goodbye.")


def test_missing_world_file_exits_1() -> None:
    result = runner.invoke(app, ["play", "--world", "nope.json"])
    assert result.exit_code == 1
    assert "Error: cannot read nope.json" in result.output


def test_invalid_json_exits_1(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    result = runner.invoke(app, ["check", str(bad)])
    assert result.exit_code == 1
    assert "Error:" in result.output and "not valid JSON" in result.output


def test_check_prints_a_summary() -> None:
    result = runner.invoke(app, ["check", "src/text_adventure/world.json"])
    assert result.exit_code == 0
    assert "1 room(s), 3 containers and 5 items" in result.output
    assert "The shortest win takes 12 moves. Par is 12." in result.output


def test_check_warns_about_missing_pictures_but_exits_0() -> None:
    result = runner.invoke(app, ["check", "src/text_adventure/world.json"])
    assert result.exit_code == 0
    assert "has no icon" not in result.output  # every item has its icon
    assert 'Warning: item "wrench" has no close-up.' in result.output
    assert 'Warning: container "toolbox" has no close-up.' in result.output
    assert "screwdriver" not in result.output  # the example icon and close-up exist


def write_world(folder: Path, icon: str, par: int | None = None, **room: Any) -> Path:
    """A one-room world whose coin has the given icon file, next to a tiny room art file.
    The coin opens the door, so it is won in 3 moves."""
    (folder / "room.txt").write_text("[background]\n.\n", encoding="utf-8")
    (folder / "coin.txt").write_text(icon, encoding="utf-8")
    world = {
        "par": par,
        "rooms": [
            {
                "id": "r1",
                "name": "Lab",
                "description": "A lab.",
                "art": "room.txt",
                "items": [{"name": "coin", "icon": "coin.txt"}],
                "door": {"required_item": "coin", "next_room": None},
                **room,
            }
        ],
    }
    path = folder / "world.json"
    path.write_text(json.dumps(world), encoding="utf-8")
    return path


def test_check_loads_pictures_next_to_the_world_file(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(write_world(tmp_path, "[default]\n(o)\n"))])
    assert result.exit_code == 0
    assert "has no icon" not in result.output


def test_picture_too_big_is_an_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(write_world(tmp_path, "[default]\n123456789\n"))])
    assert result.exit_code == 1
    assert "Error:" in result.output and "coin.txt: [default] must fit in 8x3" in result.output


def test_missing_picture_file_is_an_error(tmp_path: Path) -> None:
    path = write_world(tmp_path, "")
    (tmp_path / "coin.txt").unlink()
    result = runner.invoke(app, ["check", str(path)])
    assert result.exit_code == 1
    assert "Error: cannot read" in result.output and "coin.txt" in result.output


def test_check_reports_the_shortest_win_without_a_par(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(write_world(tmp_path, "[default]\no\n"))])
    assert result.exit_code == 0
    assert "The shortest win takes 3 moves.\n" in result.output


def test_a_world_that_cant_be_won_is_an_error(tmp_path: Path) -> None:
    box = {"name": "box", "required_item": "coin", "contents": [{"name": "coin"}]}
    path = write_world(tmp_path, "[default]\no\n", items=[], containers=[box])
    result = runner.invoke(app, ["check", str(path)])
    assert result.exit_code == 1
    assert "can't be won" in result.output


def test_a_par_below_the_shortest_win_is_an_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(write_world(tmp_path, "[default]\no\n", par=2))])
    assert result.exit_code == 1
    assert "par is 2, but the shortest win takes 3 moves" in result.output


def test_a_broken_use_is_an_error(tmp_path: Path) -> None:
    door = {"required_item": "coin", "next_room": None, "uses": [{"item": "gem", "text": "x"}]}
    path = write_world(tmp_path, "[default]\no\n", door=door)
    result = runner.invoke(app, ["check", str(path)])
    assert result.exit_code == 1
    assert 'there is no item "gem"' in result.output


def test_the_world_runs_from_a_folder_outside_the_package(tmp_path: Path) -> None:
    """The release's world.zip is world.json plus art/, mounted into Docker at /world.
    That only works if every file the world names is a relative path inside that folder."""
    package = Path("src/text_adventure")
    world_json = json.loads((package / "world.json").read_text(encoding="utf-8"))
    for relative in [*art_paths(world_json), *picture_paths(world_json)]:
        assert not Path(relative).is_absolute() and ".." not in Path(relative).parts, relative
    shutil.copy(package / "world.json", tmp_path / "world.json")
    shutil.copytree(package / "art", tmp_path / "art")
    result = runner.invoke(app, ["check", str(tmp_path / "world.json")])
    assert result.exit_code == 0, result.output
    assert "1 room(s), 3 containers and 5 items" in result.output
