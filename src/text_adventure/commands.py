"""Turn a typed line such as "take the brass key" into a Command. Knows nothing about rooms."""

from dataclasses import dataclass
from enum import Enum


class Verb(Enum):
    """The actions the game understands. Each value is the word the player types."""

    LOOK = "look"
    OPEN = "open"
    TAKE = "take"
    DROP = "drop"
    INVENTORY = "inventory"
    HELP = "help"
    QUIT = "quit"


ALIASES: dict[str, Verb] = {
    **{verb.value: verb for verb in Verb},
    "l": Verb.LOOK,
    "get": Verb.TAKE,
    "i": Verb.INVENTORY,
    "inv": Verb.INVENTORY,
    "?": Verb.HELP,
    "q": Verb.QUIT,
    "exit": Verb.QUIT,
}

NEEDS_OBJECT = frozenset({Verb.OPEN, Verb.TAKE, Verb.DROP})
ARTICLE = "the"


class CommandError(ValueError):
    """The line could not be understood. The message is shown to the player as is."""


@dataclass(frozen=True)
class Command:
    """A parsed line: the verb, and the object's name for verbs that need one."""

    verb: Verb
    name: str | None = None


def parse(text: str) -> Command | None:
    """Parse one line of input. Return None for an empty line, raise CommandError if invalid."""
    words = text.lower().split()
    if not words:
        return None
    first, rest = words[0], words[1:]
    if rest and rest[0] == ARTICLE:
        rest = rest[1:]
    name = " ".join(rest) or None

    verb = ALIASES.get(first)
    if verb is None:
        raise CommandError(f'I don\'t know how to "{first}". Type "help" for a list of commands.')
    if verb in NEEDS_OBJECT and name is None:
        raise CommandError(f"{verb.value.capitalize()} what?")
    if verb not in NEEDS_OBJECT and name is not None:
        raise CommandError(f'"{first}" doesn\'t take an object.')
    return Command(verb, name)
