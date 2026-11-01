import json
from pathlib import Path

from typer.testing import CliRunner

from text_adventure.cli import app

runner = CliRunner()
WIN = "open toolbox\ntake screwdriver\nopen fuse box\ntake the key\nopen door\n"


def test_scripted_playthrough_wins_and_exits_0() -> None:
    result = runner.invoke(app, ["play"], input="dance\n" + WIN)
    assert result.exit_code == 0
    assert 'I don\'t know how to "dance"' in result.output
    assert "The door swings open" in result.output
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
    assert "1 room(s), 2 containers and 5 items" in result.output


def test_check_warns_about_missing_pictures_but_exits_0() -> None:
    result = runner.invoke(app, ["check", "src/text_adventure/world.json"])
    assert result.exit_code == 0
    assert 'Warning: item "wrench" has no icon.' in result.output
    assert 'Warning: container "toolbox" has no close-up.' in result.output
    assert "screwdriver" not in result.output  # the example icon and close-up exist


def write_world(folder: Path, icon: str) -> Path:
    """A one-room world whose coin has the given icon file, next to a tiny room art file."""
    (folder / "room.txt").write_text("[background]\n.\n", encoding="utf-8")
    (folder / "coin.txt").write_text(icon, encoding="utf-8")
    world = {
        "rooms": [
            {
                "id": "r1",
                "name": "Lab",
                "description": "A lab.",
                "art": "room.txt",
                "items": [{"name": "coin", "icon": "coin.txt"}],
                "door": {"required_item": "coin", "next_room": None},
            }
        ]
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
