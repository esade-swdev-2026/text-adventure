# text-adventure

A text adventure for the terminal, played by typing commands such as `open toolbox` or
`take key`: you are locked in, and must open containers, collect items in a 4-slot inventory
and unlock the door to escape. Every command redraws the room, so you can see what changed. It
is a group project for Software Development for Business at ESADE, built for anyone who wants a
short puzzle game, and for the team to practise clean, tested Python.

The game has **three rooms, playable from start to win**: the Electrical Room, the Darkroom
and the Night Office, then the street. How
the code is organised, how a turn flows through it, and every design decision are documented in
[ARCHITECTURE.md](ARCHITECTURE.md). The screen layout is specified in
[docs/SCREEN-SPEC.md](docs/SCREEN-SPEC.md).

```
╭────────────────────────────────────── ELECTRICAL ROOM ───────────────────────────── 0 moves ─╮
│     ╲                       │                                                          ╱     │
│      ╲┌─────────────────────┴────────────────────────────────────────────────────────┐╱      │
│       │━━━━┓              ▗▟█▙▖               ┌──────────┐              ┌─────────┐  │       │
│       │    ┃              ░░▒░░               │ ▫  ϟ   ▫ │              │░░░ · ░░░│  │       │
│       │    ┣━╸          ░░▒▒▒▒▒░░             │  ━━━━━━  │              │░░     ░░│  │       │
│       │    ┃          ░░ ░  ░  ░ ░░           └──────────┘  ▪═══════▪   │░    ▪━━━┿━ │       │
│       │    ┃        ░░ ░  ░  ░  ░  ░░                       ║╪╪╪╪╪╪╪║   │░       ░│  │       │
│       └────┸────────────────────────────────────────────────▪═══════▪───┴─────────┴──┘       │
│      ╱        ╔═════════╗░  ░  ░  ░  ░░             ·                     ░░░ ░░░     ╲      │
│     ╱         ║ ▪ ═══ ▪ ║░  ░  ░  ░  ░ ░░                   ·            ░░░░  ░░░░    ╲     │
│    ╱          ╚═════════╝ ░  ░  ░ ●▬  ░  ░░    ·                        ░░░░░   ░░░░░   ╲    │
╰──────────────────────────────────────────────────────────────────────────────────────────────╯
  A lone lamp swings overhead. Beyond its light, the walls hum. A toolbox waits on the floor.
  A fuse box is screwed shut. A vent sits low in the dark. A flashbulb lies in the light. The
  steel door is locked.

╭──────────────────────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮
│ Look    l     Inspect x      │  │            │  │            │  │            │  │            │
│ Open          Take    get    │  │            │  │            │  │            │  │            │
│ Drop          Use            │  │            │  │            │  │            │  │            │
│ Help    ?     Quit    q      │  │            │  │            │  │            │  │            │
╰──────────────────────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯


  The power died an hour ago. Somebody wanted you in the dark. Find a way out.
  Type a verb and a thing, like  look  or  inspect door. Tab completes.

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

Use a terminal of at least 100 × 44 with a dark background. While you think, the lamp
dips now and then; `play --no-motion` keeps the picture still. Other commands:

```
uv run text-adventure --help
uv run text-adventure check src/text_adventure/world.json
```

`check` loads a world file, checks every rule (including every `use` and what it refers to),
searches for the shortest way to win and prints a summary, then a warning for each item
without an inventory icon and each object without a close-up (the art is still being drawn,
so these don't fail the check). A world that can't be won, or whose `par` is below the
shortest win, fails with exit code 1:

```
OK: src/text_adventure/world.json has 3 room(s), 11 containers and 16 items. The game starts in the Electrical Room.
The shortest win takes 36 moves. Par is 36.
Warning: item "flashbulb" has no close-up.
Warning: item "wrench" has no close-up.
...
```

Bad input is reported in one line, with exit code 1 and no traceback:

```
$ uv run text-adventure play --world nope.json; echo "exit code $?"
Error: cannot read nope.json: No such file or directory
exit code 1
```

## Run with Docker

Requires [Docker](https://docs.docker.com/get-docker/). Every release publishes the image to
GitHub Container Registry, so there is nothing to build. Pull it:

```
docker pull ghcr.io/esade-swdev-2026/text-adventure:latest
```

The world (the story, the rooms and their art) lives **outside the image**. Download it from
the latest release and unzip it into a folder:

```
curl -L -o world.zip https://github.com/esade-swdev-2026/text-adventure/releases/latest/download/world.zip
unzip world.zip -d my-world
```

`my-world/` now holds `world.json` and the `art/` folder it names. Mount it into the
container read-only (`:ro`) and play it. The game is interactive, so `play` needs `-it`:

```
docker run --rm -it -v "$PWD/my-world":/world:ro ghcr.io/esade-swdev-2026/text-adventure:latest play --world /world/world.json
```

To check the mounted world loads and can be won without playing it (no `-it` needed):

```
docker run --rm -v "$PWD/my-world":/world:ro ghcr.io/esade-swdev-2026/text-adventure:latest check /world/world.json
```

**The world changes without a rebuild.** Open `my-world/world.json`, change the room's
`"description"`, save, and run the same `docker run ... play` command again: the game shows
your new text. The image is the same one you pulled above. Only the mounted folder changed.

Any folder works the same way, as long as it holds the world file and every art file the
world names, at the relative paths it gives them.

To build the image yourself instead, run `docker build -t text-adventure .` in the cloned
repository and use `text-adventure` in place of `ghcr.io/esade-swdev-2026/text-adventure:latest`
in the commands above.

## How to play

Type a verb and a thing and press Enter. The game doesn't list what to try: the picture,
the description, the verb panel and the four inventory slots are your clues. The last
three results stay on screen, newest at the bottom.

| Command | Short | What it does |
|---|---|---|
| `inspect <thing>` | `x`, `examine`, `look at` | Looks closely at an item, a container or the door. Clues are here. |
| `open <thing>` | | Opens a container. Some are locked until you carry the right tool. |
| `use <item>` / `use <item> on <thing>` | `in`, `with` for `on` | Uses a carried item, e.g. `use key on door` to unlock it. |
| `open door` | | Opens the door once it is unlocked. |
| `take <thing>` | `get` | Picks up an item. You can carry 4. |
| `drop <thing>` | | Puts a carried item on the floor. |
| `look` | `l` | Redraws the room. |
| `inventory` | `i` | Lists what you carry. |
| `help` | `?` | Lists the commands. |
| `quit` | `q` | Ends the game. Ctrl-C and Ctrl-D do too. |

Every `open`, `take`, `drop` and `use` that changes something is a move; looking, inspecting
and mistakes are free. Escape in par or better and the game calls it sharp.

Names can be several words (`open fuse box`), and a leading "the" is ignored
(`take the key`). Tab completes a verb, then the name of something you can see or carry
(`open f` → `open fuse box`), and ↑ recalls earlier ones.

**Terminal support:** needs a UTF-8 terminal of at least 100 × 44, **with a dark
background**. The room is drawn in line art and `░▒▓█` shading, light falling off from the
lamp into true black, in 256 colours (slate shadow, amber lamplight, red for mistakes). On a
light background the shading reads as a photo negative. Bold and dim carry the same meaning
as the colours, so piped output and `TERM=dumb` get a black and white version, and a
terminal that can't show UTF-8 gets plain ASCII art. The lamp's flicker (at most 3 dips in any
10 seconds, never while inspecting or once the power is on) only runs in colour, in a real
terminal. If you resize the window, the screen is
redrawn at once; below 100 × 44 it asks for a bigger window. What you had typed is kept with GNU readline (most Linux builds) and lost with
libedit (the macOS default).

## Use of AI

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
uv run ruff check .           # lint
uv run ruff format .          # format (CI runs `--check` and fails on a diff)
uv run mypy src tests scripts # types (strict)
uv run pytest                 # tests
```

These four commands are exactly what `.github/workflows/check.yml` runs on every push.
If they pass here, CI passes. A second CI job builds the Docker image and runs `check` on a
world mounted from outside it.

To release, push a version tag (`git tag v0.7 && git push origin v0.7`).
`.github/workflows/release.yml` packs `world.json` and `art/` into `world.zip`, checks the
image can load it from a bind mount, then pushes the image to
`ghcr.io/esade-swdev-2026/text-adventure` (tagged with the version and `latest`) and publishes
a GitHub release with the zip attached. Those are the image and the file the "Run with
Docker" section uses.

## Layout

```
src/text_adventure/   the package; pure modules never print or read files
  models.py           Item, Door, Container, Room, Player, Inventory
  commands.py         parse typed input into a Command
  game.py             the rules: apply a Command, return an Outcome
  world.py            check world.json data and build the rooms
  solve.py            find the shortest win, for check
  art.py              parse the art file, draw sprites for the room's state
  screen.py           build the screen as plain text (description, commands, layout)
  terminal.py         I/O: draw the screen with rich, read a line
  cli.py              I/O: the play and check commands, file reading, game loop
  world.json          the room, its items and texts (the story)
  art/                the room drawings; icons/ and closeups/ hold the object pictures
  __main__.py         lets `python -m text_adventure` work
tests/                pytest tests, mirroring src/
docs/SCREEN-SPEC.md   the screen design (next version): size, layout, palette, every state
pyproject.toml        dependencies and tool configuration — the single source of truth
Dockerfile            the image: the package installed from uv.lock (.dockerignore: what stays out)
ARCHITECTURE.md       full design: classes, game loop, world file, decisions
```
