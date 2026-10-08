from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from .models import Container, Door, Item, Room


class Action(Enum):
    OPEN = auto()
    TAKE = auto()
    DOOR = auto()
    INVENTORY = auto()
    QUIT = auto()


@dataclass
class Option:

    label: str
    action: Action
    target: Item | Container | Door | None = None


def build_options(room: Room) -> list[Option]:

    options: list[Option] = []

    for container in room.containers:
        if not container.is_open:
            options.append(Option(f"Open the {container.name}", Action.OPEN, container))
        else:
            for item in container.contents:
                options.append(Option(f"Take the {item.name}", Action.TAKE, item))

    for item in room.items:
        options.append(Option(f"Take the {item.name}", Action.TAKE, item))

    options.append(Option("Try the door", Action.DOOR, room.door))
    options.append(Option("Show inventory", Action.INVENTORY))
    options.append(Option("Quit", Action.QUIT))
    return options


def show_menu(room: Room, options: list[Option]) -> None:
   
    print(f"\nYou are in {room.name}.")
    print("What do you want to do?")
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option.label}")


def read_choice(option_count: int, read: Callable[[str], str] = input) -> int:
   
    while True:
        text = read("> ").strip()
        if not text:
            print("Please type a number.")
            continue
        try:
            number = int(text)
        except ValueError:
            print("That's not a number. Try again.")
            continue
        if not 1 <= number <= option_count:
            print(f"Choose a number from 1 to {option_count}.")
            continue
        return number


def ask_player(room: Room) -> Option:
  
    options = build_options(room)
    show_menu(room, options)
    choice = read_choice(len(options))
    return options[choice - 1]
