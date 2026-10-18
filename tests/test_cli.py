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
