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
