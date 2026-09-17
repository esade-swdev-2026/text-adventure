from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def test_greet_says_hello() -> None:
    result = runner.invoke(app, ["greet", "Ada"])
    assert result.exit_code == 0
    assert "Hello, Ada!" in result.stdout


def test_greet_repeats_with_count() -> None:
    result = runner.invoke(app, ["greet", "Ada", "--count", "3"])
    assert result.exit_code == 0
    assert result.stdout.count("Hello, Ada!") == 3


def test_greet_rejects_bad_count() -> None:
    result = runner.invoke(app, ["greet", "Ada", "--count", "0"])
    assert result.exit_code == 1


def test_bye_says_goodbye() -> None:
    result = runner.invoke(app, ["bye", "Ada"])
    assert result.exit_code == 0
    assert "Goodbye, Ada." in result.stdout
