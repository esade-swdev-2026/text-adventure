"""Turn a typed line such as "take the brass key" into a Command. Knows nothing about rooms."""

from dataclasses import dataclass
from enum import Enum


class Verb(Enum):
    """The actions the game understands. Each value is the word the player types."""

    LOOK = "look"
    INSPECT = "inspect"
    OPEN = "open"
    TAKE = "take"
    DROP = "drop"
    USE = "use"
    INVENTORY = "inventory"
    HELP = "help"
    QUIT = "quit"


ALIASES: dict[str, Verb] = {
    **{verb.value: verb for verb in Verb},
    "l": Verb.LOOK,
    "x": Verb.INSPECT,
    "examine": Verb.INSPECT,
    "get": Verb.TAKE,
    "i": Verb.INVENTORY,
    "inv": Verb.INVENTORY,
    "?": Verb.HELP,
    "q": Verb.QUIT,
    "exit": Verb.QUIT,
}

NEEDS_OBJECT = frozenset({Verb.INSPECT, Verb.OPEN, Verb.TAKE, Verb.DROP, Verb.USE})
ARTICLE = "the"
LOOK_AT = "at"  # "look at fuse box" means "inspect fuse box"
ON_WORDS = frozenset({"on", "in", "with"})  # "use fuse on/in fuse box", "use wrench with vent"


class CommandError(ValueError):
    """The line could not be understood. The message is shown to the player as is."""


@dataclass(frozen=True)
class Command:
    """A parsed line: the verb, the object's name for verbs that need one, and for
    `use … on …` the thing it is used on."""

    verb: Verb
    name: str | None = None
    target: str | None = None


def _name(words: list[str]) -> str | None:
    """The words as one name, without a leading "the"; None if nothing is left."""
    if words and words[0] == ARTICLE:
        words = words[1:]
    return " ".join(words) or None


def _use(words: list[str]) -> Command:
    """`use <item>` or `use <item> on <thing>`."""
    split = next((index for index, word in enumerate(words) if word in ON_WORDS), None)
    if split is None:
        item = _name(words)
        if item is None:
            raise CommandError("Use what?")
        return Command(Verb.USE, item)
    item, target = _name(words[:split]), _name(words[split + 1 :])
    if item is None:
        raise CommandError("Use what?")
    if target is None:
        raise CommandError(f"Use the {item} {words[split]} what?")
    return Command(Verb.USE, item, target)


def parse(text: str) -> Command | None:
    """Parse one line of input. Return None for an empty line, raise CommandError if invalid."""
    words = text.lower().split()
    if not words:
        return None
    first, rest = words[0], words[1:]

    verb = ALIASES.get(first)
    if verb is None:
        raise CommandError(f'I don\'t know how to "{first}". Type "help" for the verbs.')
    if verb is Verb.LOOK and rest[:1] == [LOOK_AT]:
        verb, rest = Verb.INSPECT, rest[1:]
    if verb is Verb.USE:
        return _use(rest)
    name = _name(rest)
    if verb in NEEDS_OBJECT and name is None:
        raise CommandError(f"{verb.value.capitalize()} what?")
    if verb not in NEEDS_OBJECT and name is not None:
        raise CommandError(f'"{first}" doesn\'t take an object.')
    return Command(verb, name)
