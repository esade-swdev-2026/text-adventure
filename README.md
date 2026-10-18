# text-adventure

A text adventure for the terminal, played by typing commands such as `open toolbox` or
`take key`: you are locked in, and must open containers, collect items in a 4-slot inventory
and unlock the door to escape. Every command redraws the room, so you can see what changed. It
is a group project for Software Development for Business at ESADE, built for anyone who wants a
short puzzle game, and for the team to practise clean, tested Python.

Version 0.5 has **one room, playable from start to win**. Version 1.0 will have three. How
the code is organised, how a turn flows through it, and every design decision are documented in
[ARCHITECTURE.md](ARCHITECTURE.md). The screen layout is specified in
[docs/SCREEN-SPEC.md](docs/SCREEN-SPEC.md).

```
╭──────────────────────────── ELECTRICAL ROOM ─────────────────────────────╮
│    ╲                  │                                             ╱    │
│     ╲┌────────────────┴───────────────────────────────────────────┐╱     │
│      │━━━━┓         ▗▟█▙▖           ┌──────────┐      ┌─────────┐ │      │
│      │    ┃         ░░▒░░           │ ▫  ϟ   ▫ │      │░░░   ░░░│ │      │
│      │    ┣━╸     ░░▒▒▒▒▒░░         │  ━━━━━━  │      │░░     ░░│ │      │
│      │    ┃     ░░ ░  ░  ░ ░░       └──────────┘      │░       ░│ │      │
│      └────┸───────────────────────────────────────────┴─────────┴─┘      │
│     ╱       ╔═════════╗░  ░  ░ ░░         ·      ·      ░░░ ░░░    ╲     │
│    ╱      ░░║ ▪ ═══ ▪ ║  ░  ░  ░ ░░                    ░░░░  ░░░░   ╲    │
│   ╱     ░░  ╚═════════╝ ░  ░  ●▬ ░ ░░                 ░░░░░   ░░░░░  ╲   │
╰─ Carrying (0/4): nothing ────────────────────────────────────────────────╯
  A lone lamp swings overhead. Beyond its light, the walls hum. A toolbox
  waits on the floor. A fuse box is screwed shut. A flashbulb lies in the
  light. The door is shut tight.

  The power died an hour ago. Somebody wanted you in the dark. Find a way
  out.

  Try  open toolbox · open fuse box · take flashbulb · open door · look
       inventory · help · quit

  [Electrical Room] > _
```

## Install

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.13 for you if needed.

```
git clone https://github.com/esade-swdev-2026/text-adventure.git
cd text-adventure
uv sync
```

This creates a virtual environment and installs everything, including the development
tools, from `uv.lock` — the committed file that pins exact versions so every teammate
and CI resolve the same ones. When you change a dependency in `pyproject.toml`, run
`uv lock` and commit the updated `uv.lock`; CI fails if the two disagree.

## Run

```
uv run text-adventure play
```

Use a terminal of at least 80 × 24. Other commands:

```
uv run text-adventure --help
uv run text-adventure check src/text_adventure/world.json
```

`check` loads a world file, checks every rule and prints a summary:

```
OK: src/text_adventure/world.json has 1 room(s), 2 containers and 5 items. The game starts in the Electrical Room.
```

Bad input is reported in one line, with exit code 1 and no traceback:

```
$ uv run text-adventure play --world nope.json; echo "exit code $?"
Error: cannot read nope.json: No such file or directory
exit code 1
```

## How to play

Type a command and press Enter. The `Try` row always lists the commands that make sense right
now, and what you carry is shown under the picture.

| Command | Short | What it does |
|---|---|---|
| `open <thing>` | | Opens a container. Some are locked until you carry the right tool. |
| `open door` | | Tries the door. It needs a key, which is used up. |
| `take <thing>` | `get` | Picks up an item. You can carry 4. |
| `drop <thing>` | | Puts a carried item on the floor. |
| `look` | `l` | Redraws the room. |
| `inventory` | `i` | Lists what you carry. |
| `help` | `?` | Lists the commands. |
| `quit` | `q` | Ends the game. Ctrl-C and Ctrl-D do too. |

Names can be several words (`open fuse box`), and a leading "the" is ignored
(`take the key`). Tab completes a command (`open f` → `open fuse box`), and ↑ recalls
earlier ones.

**Terminal support:** needs a UTF-8 terminal of at least 80 × 24. The game is black and white by
design (bold and dim only), so it looks the same in light and dark themes. A terminal that can't show UTF-8 gets plain ASCII art. If you
resize the window, the screen is redrawn after your next command.

## The role of AI in this project

We used an AI coding assistant, and want to be clear about where.

**What we did ourselves.** The game design, the rules and the core logic: the models
(`Item`, `Container`, `Door`, `Room`, `Player`, `Inventory`), how a command changes the game
state, the win condition, the world file format and the story. We decided the architecture
(pure modules inside, a thin I/O layer outside), reviewed and tested every change, and are
responsible for all of the code in this repository.

**What AI helped with.** Some parts are code-heavy and tedious but add little to the logic.
Done by hand, they would have taken weeks, and we wanted the game to look good. We used AI
heavily for these:

- terminal drawing: the framed panel, fixed-height layout, text wrapping, styles and the
  ASCII fallback (`screen.py`, `terminal.py`)
- ASCII art: drafting the room and object sprites, which we then edited by hand, and the
  code that composes them by state (`art.py`, `art/`)
- parsing and validation: the art file parser and the many checks with clear error messages
  when loading `world.json` (`art.py`, `world.py`)
- boilerplate tests for those parts, and polishing docstrings and documentation

Everything AI produced was read, run and changed by us before it was merged, and goes through
the same four checks and pull-request review as the rest of the code.

## Develop

```
uv run ruff check .          # lint
uv run ruff format .         # format (CI runs `--check` and fails on a diff)
uv run mypy src tests        # types
uv run pytest                # tests
```

These four commands are exactly what `.github/workflows/check.yml` runs on every push.
If they pass here, CI passes.

## Layout

```
src/text_adventure/   the package; pure modules never print or read files
  models.py           Item, Door, Container, Room, Player, Inventory
  commands.py         parse typed input into a Command
  game.py             the rules: apply a Command, return an Outcome
  world.py            check world.json data and build the rooms
  art.py              parse the art file, draw sprites for the room's state
  screen.py           build the screen as plain text (description, commands, layout)
  terminal.py         I/O: draw the screen with rich, read a line
  cli.py              I/O: the play and check commands, file reading, game loop
  world.json          the room, its items and texts (the story)
  art/                the room drawings
  __main__.py         lets `python -m text_adventure` work
tests/                pytest tests, mirroring src/
docs/SCREEN-SPEC.md   the screen design: size, layout, palette, every state
pyproject.toml        dependencies and tool configuration — the single source of truth
ARCHITECTURE.md       full design: classes, game loop, world file, decisions
```
