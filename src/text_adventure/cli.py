"""Command-line entry point. Reads the world files and runs the game loop."""

import json
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Annotated

import typer

from .art import Art, ArtError, Picture, parse_art, parse_picture
from .game import play_turn
from .models import Inventory, Player
from .screen import Tone, build_screen, build_win_screen
from .solve import shortest_win
from .terminal import Terminal
from .world import (
    World,
    WorldError,
    art_paths,
    build_world,
    missing_pictures,
    picture_paths,
    summarize,
)

GOODBYE = "Goodbye."
DEFAULT_WORLD = "world.json"

app = typer.Typer(
    help="A text adventure: get out of the room by typing commands.",
    no_args_is_help=True,
    add_completion=False,
)


def _read(folder: Traversable, relative: str) -> str:
    """Read a file named in world.json, relative to the world file's folder."""
    return folder.joinpath(*relative.split("/")).read_text(encoding="utf-8")


def load_world(world_file: Traversable, folder: Traversable) -> World:
    """Read world.json, the room art and the pictures it names (relative to `folder`),
    then build the world."""
    world_json = json.loads(world_file.read_text(encoding="utf-8"))
    art: dict[str, Art] = {}
    for relative in art_paths(world_json):
        art[relative] = parse_art(_read(folder, relative))
    pictures: dict[str, Picture] = {}
    for relative, size in picture_paths(world_json).items():
        try:
            pictures[relative] = parse_picture(_read(folder, relative), size)
        except ArtError as error:
            raise ArtError(f"{relative}: {error}") from error
    return build_world(world_json, art, pictures)


def _load_or_exit(path: Path | None) -> World:
    """Load the given world file, or the built-in one. On failure print Error: … and exit 1."""
    source = path or DEFAULT_WORLD
    try:
        if path is None:
            package = files("text_adventure")
            return load_world(package / DEFAULT_WORLD, package)
        return load_world(path, path.parent)
    except OSError as error:
        message = f"cannot read {error.filename or source}: {error.strerror}"
    except json.JSONDecodeError as error:
        message = f"{source} is not valid JSON (line {error.lineno}, column {error.colno})"
    except UnicodeDecodeError:
        message = f"{source} is not UTF-8 text"
    except (WorldError, ArtError) as error:
        message = f"{source}: {error}"
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


def run(world: World, terminal: Terminal) -> None:
    """The game loop: draw, read a line, apply it, until the player wins or quits."""
    player = Player(world.first_room, Inventory())
    message, tone = world.intro, Tone.NARRATION
    focus: str | None = None
    while True:
        room = player.current_room
        screen = build_screen(room, player.inventory, world.art_for(room), message, tone, focus)
        terminal.draw(screen)
        outcome = play_turn(player, terminal.read(screen.prompt, screen.options), world.par)
        if outcome is None:
            continue
        if outcome.won:
            terminal.draw(
                build_win_screen(room, world.art_for(room), outcome.message, world.ending)
            )
            return
        if outcome.quit:
            terminal.say(outcome.message)
            return
        message, tone = outcome.message, Tone.ERROR if outcome.error else Tone.RESULT
        focus = outcome.subject


WorldOption = Annotated[
    Path | None, typer.Option("--world", help="World file to play instead of the built-in one.")
]


@app.command()
def play(world: WorldOption = None) -> None:
    """Play the game."""
    loaded = _load_or_exit(world)
    terminal = Terminal()
    try:
        run(loaded, terminal)
    except (KeyboardInterrupt, EOFError):
        terminal.say(GOODBYE, new_line=True)


@app.command()
def check(path: Annotated[Path, typer.Argument(help="World file to check.")]) -> None:
    """Load a world file, check every rule and that it can be won, and print a summary and
    any missing art."""
    world = _load_or_exit(path)
    route = shortest_win(world)
    if route is None:
        typer.echo(f"Error: {path}: the world can't be won", err=True)
        raise typer.Exit(code=1)
    if world.par is not None and world.par < len(route):
        typer.echo(
            f"Error: {path}: par is {world.par}, but the shortest win takes {len(route)} moves",
            err=True,
        )
        raise typer.Exit(code=1)
    summary = summarize(world)
    typer.echo(
        f"OK: {path} has {summary.rooms} room(s), {summary.containers} containers and "
        f"{summary.items} items. The game starts in the {summary.first_room}."
    )
    par = f" Par is {world.par}." if world.par is not None else ""
    typer.echo(f"The shortest win takes {len(route)} moves.{par}")
    for warning in missing_pictures(world):
        typer.echo(f"Warning: {warning}.")


if __name__ == "__main__":
    app()
