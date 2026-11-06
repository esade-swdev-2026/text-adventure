import pytest

from text_adventure.commands import Command, CommandError, Verb, parse


def test_case_and_extra_spaces_are_ignored() -> None:
    assert parse("  OPEN    Toolbox  ") == Command(Verb.OPEN, "toolbox")


def test_leading_the_is_dropped_and_names_can_be_several_words() -> None:
    assert parse("open the fuse   box") == Command(Verb.OPEN, "fuse box")


@pytest.mark.parametrize(
    ("text", "verb"),
    [("i", Verb.INVENTORY), ("inv", Verb.INVENTORY), ("q", Verb.QUIT), ("exit", Verb.QUIT)],
)
def test_aliases_without_object(text: str, verb: Verb) -> None:
    assert parse(text) == Command(verb)


def test_get_is_an_alias_for_take() -> None:
    assert parse("get key") == Command(Verb.TAKE, "key")


def test_empty_input_is_none() -> None:
    assert parse("   ") is None


def test_unknown_verb() -> None:
    with pytest.raises(CommandError, match='"dance"'):
        parse("dance")


def test_take_without_object() -> None:
    with pytest.raises(CommandError, match="Take what?"):
        parse("take the")


def test_inventory_with_object() -> None:
    with pytest.raises(CommandError, match="doesn't take an object"):
        parse("inventory key")


@pytest.mark.parametrize("text", ["inspect fuse box", "x the fuse box", "examine fuse box"])
def test_inspect_and_its_short_forms(text: str) -> None:
    assert parse(text) == Command(Verb.INSPECT, "fuse box")


def test_look_at_means_inspect() -> None:
    assert parse("look at the door") == Command(Verb.INSPECT, "door")
    with pytest.raises(CommandError, match="Inspect what?"):
        parse("look at")


@pytest.mark.parametrize(
    ("text", "command"),
    [
        ("use flashbulb", Command(Verb.USE, "flashbulb")),
        ("use the fuse on the fuse box", Command(Verb.USE, "fuse", "fuse box")),
        ("USE fuse  in fuse box", Command(Verb.USE, "fuse", "fuse box")),
        ("use wrench with the vent", Command(Verb.USE, "wrench", "vent")),
    ],
)
def test_use_with_and_without_a_target(text: str, command: Command) -> None:
    assert parse(text) == command


@pytest.mark.parametrize(
    ("text", "message"),
    [("use", "Use what?"), ("use on vent", "Use what?"), ("use fuse on", "Use the fuse on what?")],
)
def test_use_that_is_missing_a_part(text: str, message: str) -> None:
    with pytest.raises(CommandError, match=message):
        parse(text)
