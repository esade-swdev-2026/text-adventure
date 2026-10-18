# Architecture

This document is the design for the text adventure. It started as the team's design brief
("Blackout at the Observatory") and goes further: it describes how the code
is organised, how one turn flows through it, and every rule the game follows.

**Every design decision is made. Only the story is still open.** The engine does not depend
on the story. Names, descriptions and the opening and ending text all live in `world.json`, so
picking a story means writing data, not code. Object names in this document (desk, chest,
key, screwdriver…) are placeholders.

---

## 1. The game in one paragraph

The player is locked in three rooms in a row and has to open the last door to escape. The game
always says which room the player is in, and the player acts by typing short commands such as
`open desk`, `take key`, `inventory` or `open door`. Items are carried in an inventory of at
most 4 slots and are needed to open doors and some containers. Opening the third room's door
wins the game.

The three requirements from the assignment map onto this directly:

| Requirement   | How the game meets it                                                        |
|---------------|------------------------------------------------------------------------------|
| Rooms         | Three rooms. Each is announced by name and description when the player enters, and the prompt always shows the current room. |
| Inventory     | An `Inventory` class with at most 4 items. Items open doors and containers.  |
| Win condition | Opening the third room's door.                                               |

### Roadmap

| Version | Scope | Status |
|---|---|---|
| **v0.5** | **One room, fully playable from start to win**, with a drawn screen: art that changes with the room's state, a live description, and the exact commands you can type. Uses every mechanic: containers, a locked container, items, the 4-slot inventory and a locked door. | Done |
| **v1.0** | Three rooms in a row and the chosen story. The engine already links rooms through doors (`next_room`), so this is mostly data: two more rooms in `world.json`, their art files, and the loader rule going back to "exactly three rooms". | Next |

---

## 2. Decisions

The brief left three questions open. They are now settled:

| Question                           | Decision                                                      | Status        |
|------------------------------------|---------------------------------------------------------------|---------------|
| Are all doors locked, or only the last? | **All three doors are locked.** Each needs one item.     | Decided       |
| Numbered choices or typed commands? | **Typed commands** (`verb` + optional object name). No numbered menu. | Decided, built in v0.5 |
| Story and theme                    | **Not chosen.** It will be written into `world.json` and needs no code changes. | Open, on purpose |

These rules are also fixed. Each was implied by the brief or the existing code and is now
stated outright:

1. **The world is three separate rooms, not a grid.** There are no directions and no walking
   back. The only way to move is forward, through the current room's door.
2. **A door uses up its key.** On success, `Door.open` removes the required item from the
   inventory, so used keys stop taking up slots.
3. **A container keeps its tool.** On success, `Container.open` leaves the required item in
   the inventory (for example, a screwdriver can be used again).
4. **Containers only open once.** An opened container stays open, and its contents can then
   be taken. Items inside a closed container are hidden: `take` can't reach them, and `look`
   doesn't list them.
5. **Locked containers look like any other closed container.** `open` on one without the right
   item prints that it is locked and changes nothing. The player has to find out what is locked
   by trying.
6. **The inventory holds 4 items.** A fifth is refused with a message. To make room, the player
   types `drop <item>`, and the item goes on the floor of the current room, where it can be
   taken again.
7. **Some items can't be carried.** `Item.portable = False` marks scenery. Trying to take it
   prints a message and changes nothing.
8. **Bad input never crashes the game.** Empty input, unknown verbs, a missing or unexpected
   object, and names of things that aren't here all print a short message and ask again.
9. **Quit ends the game at once.** Nothing is saved.
10. **Names are unique across the whole world, and none is called `door`.** Commands and
    `required_item` both refer to things by name, so names must be unique, and `door` is
    reserved for the room's door.

---

## 3. Commands

Commands are the whole interface, so their grammar is fixed here.

### Grammar

```
command  =  verb [ "the" ] [ name ]
```

- Input is trimmed, lower-cased and has repeated spaces collapsed before parsing.
- The first word is the verb. Everything after it (minus a leading `the`) is the object name,
  which may be several words (`take brass key`).
- The name must match an object's full name exactly (case-insensitive). There is no
  partial matching.

### The command set

| Command          | Aliases            | Object      | What it does                                                    |
|------------------|--------------------|-------------|-----------------------------------------------------------------|
| `look`           | `l`                | none        | Repeats the room's name and description, and lists what is visible (see below). |
| `open <name>`    | —                  | required    | Opens a container in the room. `open door` tries the room's door. |
| `take <name>`    | `get`              | required    | Takes a visible item (on the floor or in an open container).    |
| `drop <name>`    | —                  | required    | Drops a carried item onto the floor of the current room.        |
| `inventory`      | `i`, `inv`         | none        | Lists carried items with descriptions and slots used (`n/4`).   |
| `help`           | `?`                | none        | Lists these commands.                                           |
| `quit`           | `q`, `exit`        | none        | Ends the game.                                                  |

### What `look` lists

Because there is no menu, `look` is how the player finds out what they can act on. It prints:

1. The room's name and description.
2. Each container, in `world.json` order, with its state: "There is a desk (closed)." or "The
   desk is open. Inside: key." / "The desk is open and empty."
3. Each loose item on the floor (including items the player dropped).
4. "There is a door."

`look` runs automatically every time the player enters a room, so the player always starts a
room knowing what's in it.

### Example

```
You are in Room 1.
A small, dusty room.
There is a desk (closed).
There is a chest (closed).
On the floor: coin.
There is a door.

[Room 1] > open desk
You open the desk. Inside: key.
[Room 1] > take the key
You take the key.
[Room 1] > open door
The door opens.

You are in Room 2.
...
[Room 2] > dance
I don't know how to "dance". Type "help" for a list of commands.
[Room 2] > take
Take what?
[Room 2] > take lamp
There is no lamp here.
```

### Error messages

| Situation                                   | Message                                                      |
|---------------------------------------------|--------------------------------------------------------------|
| Empty input                                 | (nothing printed; the prompt is shown again)                 |
| Unknown verb                                | `I don't know how to "<verb>". Type "help" for a list of commands.` |
| Verb needs an object but none was given     | `Open what?` / `Take what?` / `Drop what?`                   |
| Verb takes no object but one was given      | `"<verb>" doesn't take an object.`                           |
| `open`: no container with that name here    | `There is no <name> here.`                                   |
| `take`: no visible item with that name      | `There is no <name> here.` (also for items in closed containers) |
| `drop`: not carrying that item              | `You aren't carrying a <name>.`                              |

---

## 4. Code layout

Every module is either **pure** (works on plain data, never prints, never reads files) or
**I/O** (talks to files or the terminal and does nothing else). Only `cli.py` and
`terminal.py` are I/O. Everything else is tested with plain pytest, without a terminal.

| File | Kind | Contents |
|---|---|---|
| `models.py` | pure | `Item`, `Door`, `Container`, `Room`, `Player`, `Inventory`, the name lookups, `CAPACITY` and the reserved name `DOOR`. |
| `commands.py` | pure | `Verb`, the alias table, `Command(verb, name)` and `parse(text) -> Command \| None`, which raises `CommandError`. |
| `game.py` | pure | `apply_command(player, command) -> Outcome` (the rules) and `play_turn(player, text)`, which parses first. `Outcome` holds `message`, `error`, `won` and `quit`. |
| `world.py` | pure | `build_world(data, art) -> World` checks the parsed JSON and raises `WorldError`. `World` holds `first_room`, `intro`, `ending` and each room's `Art`. |
| `art.py` | pure | `parse_art(text) -> Art` and `compose(art, room) -> list[str]`, which draws each object's sprite for its current state. Widths are in terminal cells. |
| `screen.py` | pure | `describe_room`, `available_commands`, `build_screen` / `build_win_screen` and `layout(screen)`, which returns every row as text tagged with a role (border, art, error…). |
| `terminal.py` | I/O | `Terminal`: draws a screen with rich (one named palette, centred, cleared between turns), reads a line, prints "Goodbye.". |
| `cli.py` | I/O | Typer commands `play [--world PATH]` and `check PATH`. Reads `world.json` and the art files, runs the loop, turns every load error into `Error: …` and exit code 1, and handles Ctrl-C / Ctrl-D. |
| `world.json`, `art/*.txt` | data | The story and the drawings. |

The old numbered `menu.py` is gone: typed commands replaced it.

### Layers and dependencies

Dependencies only point downward. Lower layers know nothing about the layers above them.

```
             cli.py  (files, loop)
            /    |    \
   terminal.py   |    world.py ──► art.py ──► models.py
        |        |                               ▲
   screen.py ────┼──► art.py                      │
                 └──► game.py ──► commands.py     │
                          └───────────────────────┘
```

- **`models.py`** holds state and rules. It reports results by returning `True`/`False`
  (`open`), `None` (lookups that find nothing) or raising `ValueError` with a message the
  player can read (`take_item`).
- **`commands.py`** knows the verbs and the grammar but nothing about rooms or items.
- **`game.py`** is the only code that changes game state in response to a command. It returns
  the message; it never prints it.
- **`screen.py`** decides what is on screen and where. **`terminal.py`** only decides how it
  looks (colours) and puts it there.
- **`cli.py`** is the only code that knows files exist.

---

## 5. The classes

| Class       | Module        | Responsibility                                                          |
|-------------|---------------|-------------------------------------------------------------------------|
| `Item`      | `models.py`   | Name, description, `portable` flag, `floor_text` (its sentence while on the floor). |
| `Container` | `models.py`   | Name, open/closed, optional `required_item` (a name), `contents`, `closed_text` / `open_text`. |
| `Door`      | `models.py`   | `required_item`, `next_room` (a `Room`, or `None` for the exit) and `is_open`. |
| `Room`      | `models.py`   | Name, mood description, containers, loose items, one door. `remove_item` takes an item off the floor or out of an open container. |
| `Inventory` | `models.py`   | Up to `CAPACITY = 4` items. Add, find by name, count, use up, drop, list. Refuses a fifth. |
| `Player`    | `models.py`   | `current_room` and one `Inventory`. `take_item` and `drop_item` move items between room and inventory. |
| `Verb`, `Command` | `commands.py` | The seven verbs and one parsed command.                        |
| `Outcome`   | `game.py`     | What one command did: the message, and whether it was an error, a win or a quit. |
| `Art`       | `art.py`      | Background rows, named sprites, and where each object's sprite goes.     |
| `Position`, `Box`, `DrawnObject` | `art.py` | A cell (row, column); the rectangle a sprite covers, used for the spotlight; one object drawn right now (name, sprite section, position). |
| `World`     | `world.py`    | The first room, intro, ending and each room's art.                       |
| `Screen`    | `screen.py`   | Everything on screen for one turn, as plain strings.                     |

### Name lookups in `models.py`

Each returns `None` when nothing matches:

- `Room.find_container(name) -> Container | None`
- `Room.find_visible_item(name) -> Item | None`: searches the floor and open containers only.
- `Inventory.find(name) -> Item | None`

---

## 6. How one turn works

The game is one loop in `cli.run`: **draw the screen → read a line → apply it → check for a
win or quit.**

```
run(world, terminal)
  message = world.intro                      # first screen shows the intro
  loop:
      terminal.draw(build_screen(room, inventory, art, message))
      outcome = play_turn(player, terminal.read(prompt))
      empty line   → draw again
      outcome.won  → draw the win screen (ending text), stop
      outcome.quit → print "Goodbye.", stop
      otherwise    → message = outcome.message, loop
```

The room name is in the panel title and in the prompt, so the player always knows where they
are. Ctrl-C and Ctrl-D end the game the same way as `quit`.

### What each command does (`game.apply_command`)

| Verb        | Looks up / calls                                           | Success                                                     | Failure                                         |
|-------------|------------------------------------------------------------|-------------------------------------------------------------|-------------------------------------------------|
| `LOOK`      | —                                                          | Redraws the screen ("You look around.").                    | —                                               |
| `OPEN`      | `door` → `room.door.open(inventory)`                       | If `door.is_exit()`: the player wins. Otherwise `player.current_room = door.next_room`. | `False` → "The door is locked." |
| `OPEN`      | other name → `room.find_container(name)`, then `container.open(inventory)` | "You open the X. Inside: …" (or "It's empty."). Already open → "The X is already open." | Not found → "There is no X here." `False` → "The X is locked." |
| `TAKE`      | `room.find_visible_item(name)`, then `player.take_item(item)` | "You take the Y."                                        | Not found → "There is no Y here." `ValueError` → its message (hands full, can't be carried). |
| `DROP`      | `inventory.find(name)`, then `player.drop_item(item)`      | "You drop the Y."                                           | Not found → "You aren't carrying a Y."         |
| `INVENTORY` | `inventory.show_inventory()`                               | Lists items with descriptions.                              | Empty → "You are carrying nothing."             |
| `HELP`      | —                                                          | Lists the commands.                                         | —                                               |
| `QUIT`      | —                                                          | "Goodbye." and the loop ends.                               | —                                               |

### Ending the game

- **Win:** the last room's door opens (`Door.is_exit()` is `True`). The win screen shows the
  door open and the `ending` text, and the game exits with code 0.
- **Quit:** `quit`, Ctrl-C or Ctrl-D. Exit code 0, no traceback.
- There is no lose condition. A move limit is a stretch goal (section 11).

---

## 7. The screen

The full spec, with a mock of every state, is [docs/SCREEN-SPEC.md](docs/SCREEN-SPEC.md). In
short, the screen is redrawn after every command and has three parts under the room's art:

1. **Art.** Sprites placed on a background, one sprite per object state: the toolbox closed or
   open, the door closed or open, a floor item drawn only while it lies on the floor. Opening or
   taking something changes the picture.
2. **Description.** The room's mood text plus one sentence per object for its current state
   ("A battered toolbox sits by the wall." becomes "The toolbox lies open. Inside: wrench.").
   Dropped items show up in it.
3. **Try.** The exact commands that make sense right now: `open` for each closed
   container, `take` for each visible item, `drop` for each carried item, `open door`, then
   `look`, `inventory`, `help`, `quit`. Locked containers are listed too (decision 5).

`Carrying (n/4): …` sits in the art panel's bottom border. Below the text come the last
result (`»` normal, `✗` error, `✓` win) and the prompt. The style is noir: black and white,
with the art's `[light]` map deciding what is lit (normal weight) and what is in shadow (dim), and the object the last
command changed is drawn bold for one turn. The whole screen is 76 × 23 cells and fits an
80 × 24 terminal. Smaller windows get
a one-line request to resize.

`look` stays as a command: it redraws the screen.

---

## 8. The world file

`world.json` lives inside the package (`src/text_adventure/world.json`) and is read with
`importlib.resources`, so it works when the game is installed. `cli.py` accepts
`--world PATH` to load a different file. This makes it easy to test other puzzles or stories
without touching the default one.

### Schema

```json
{
  "intro": "Shown in place of a result on the first screen.",
  "ending": "Shown on the win screen.",
  "rooms": [
    {
      "id": "electrical",
      "name": "Electrical Room",
      "description": "The room's mood, the first sentence of its description.",
      "art": "art/electrical_room.txt",
      "items": [
        { "name": "flashbulb", "description": "an old camera flashbulb",
          "floor_text": "A flashbulb glints in the dust.", "sprite": [4, 44] }
      ],
      "containers": [
        {
          "name": "fuse box",
          "required_item": "screwdriver",
          "closed_text": "A fuse box is screwed shut on the wall.",
          "open_text": "The fuse box hangs open.",
          "sprite": [1, 26],
          "contents": [{ "name": "key", "description": "small and brass" }]
        }
      ],
      "door": { "required_item": "key", "next_room": null, "sprite": [0, 52] }
    }
  ]
}
```

- `rooms` is in play order. The first room is where the player starts.
- `door.next_room` is another room's `id`, or `null` for the final exit.
- `required_item` is an item `name`, or `null`. Doors always need one (decision 1).
- `portable` defaults to `true`. `floor_text`, `closed_text` and `open_text` can be left out;
  a plain sentence ("There is a desk.") is used instead.
- `art` is a path relative to the world file. `sprite` is `[row, column]` inside the room's
  art (row 0, column 0 is the top-left). An object without `sprite` is not drawn. An item can
  also have `floor`: where it lies once dropped (otherwise it is drawn back at `sprite`).
- Names are what the player types, so they are written in lower case and kept short.

### What the loader checks

`build_world` builds every object first, then links each door to its `next_room`. It raises
`WorldError` with a clear message if:

- there are no rooms (v0.5 has one room; v1.0 will require three);
- a `next_room` id doesn't exist, or any door other than the last room's leads to `null`;
- two items or containers share a name, or any of them is called `door`;
- a name isn't lower case or has leading, trailing or double spaces (it couldn't be typed to
  match);
- a `required_item` names an item that doesn't exist anywhere in the world;
- a door has no `required_item`;
- a field has the wrong type, or the art file lacks a sprite section that `sprite` needs.

The loader does **not** check that the puzzle can be solved. That is covered by tests that
play the default world from start to finish (section 11).

### The art file

Plain UTF-8 text, split into sections by a `[name]` line:

```
[background]
  ║ ║ ║   ─┬──┬──┬─
...
[toolbox:closed]
   ┌───┐
┌──┴───┴──┐
│ TOOLBOX │
└─────────┘

[toolbox:open]
...
[flashbulb]
 ●
 ╨
```

- `[background]` is required and must fit 72 × 10 cells. `[light]` is optional and the same
  size: `#` where light falls, anything else is shadow (no `[light]` means all lit). It is padded with spaces to exactly
  that size.
- A container or the door needs `[name:closed]` and `[name:open]`. An item needs `[name]`; it
  is drawn inside its open container, or on the floor.
- Spaces before and after each sprite row's outline are transparent, so the background shows
  around the object. Spaces inside the outline are opaque. Trailing spaces may be dropped by
  an editor without changing anything.
- Every character must be exactly one terminal cell wide. `parse_art` rejects emoji such as
  `⚡`, which many terminals draw two cells wide; use `ϟ` instead.

### The v0.5 room

`world.json` holds one placeholder room until the story is chosen:

1. `open toolbox` → `take screwdriver` (the wrench is there too).
2. `open fuse box` is locked until you hold the screwdriver. Inside: the key and a fuse.
3. `take key` → `open door`. **You win.**

The flashbulb on the floor is a loose extra. The room holds five portable items, so a player
who takes everything fills all 4 slots and is refused the fifth.

---

## 9. The story: the one thing left open

The story can change without touching code because everything about it lives in `world.json`:

| Story element                  | Where it goes                          |
|--------------------------------|----------------------------------------|
| Setting and opening situation  | `intro`                                |
| Room names and atmosphere      | `rooms[].name`, `rooms[].description`  |
| Objects, keys and tools        | `items`, `containers`, `contents` names and descriptions |
| Escape and resolution          | `ending`                               |

Any story fits, as long as its `world.json`:

- has its rooms in play order (three for v1.0), each with a locked door;
- makes every door's required item obtainable in that room or an earlier one;
- never needs more than 4 items carried at the same time;
- uses short, lower-case names the player can guess and type, each used only once, and none
  called `door`.

Choosing the story means: write the text, replace the placeholder names, and run
`uv run pytest`. If the full-playthrough test passes, the new story is playable.

---

## 10. Testing

Each module has its own test file. Tests never need a person typing, and almost all of them
test pure functions. `conftest.py` loads a fresh copy of the packaged world for each test.

- **Models** (`test_models.py`): doors and containers with and without the item, a key used up
  vs. a tool kept, taking from closed/open containers, the 4-item limit, items that can't be
  carried, dropping, and the three name lookups.
- **Commands** (`test_commands.py`): case, extra spaces, a leading `the`, multi-word names,
  aliases, empty input, an unknown verb, a missing object and an unexpected object.
- **Art** (`test_art.py`): sprite placement, state swaps, a taken item disappearing, clipping,
  missing or malformed sections, transparency, and that every composed line is exactly 72 cells in
  every state of the real room.
- **World** (`test_world.py`): the packaged world loads, and each rule in section 8 rejects a
  small broken example.
- **Game** (`test_game.py`): locked container, tool kept, full inventory, drop and take back,
  locked door, winning uses the key, unknown names, empty input and quit.
- **Screen** (`test_screen.py`): description and commands follow the state, the opening screen
  fits 80 × 24, every screen in a playthrough has the same height, the win screen, the prompt,
  the spotlight on the changed object, the inventory in the border and the ASCII fallback.
- **CLI** (`test_cli.py`): a scripted win exits 0, end of input says goodbye, a missing world
  file and invalid JSON exit 1 with `Error:`, and `check` prints a summary.

The real terminal (layout at 80 × 24 and 120 × 40, colours, Ctrl-C/Ctrl-D, a too-small window)
is checked by playing the real game in a terminal before each merge. Anything that can be
checked in code, such as line widths or a missing command hint, becomes a pytest test.

The four CI checks (`ruff check`, `ruff format --check`, `mypy`, `pytest`) must pass before a
pull request is merged.

---

## 11. Team split

| Person   | Owns                                                                     |
|----------|--------------------------------------------------------------------------|
| A        | `models.py` (including the name lookups), `world.py` and the schema for `world.json` |
| B        | `commands.py`: the grammar, aliases, error messages and input loop        |
| C        | `game.py`, `cli.py`, the win check, and the story inside `world.json`     |
| Everyone | Tests for their own module, and the README                               |

### Stretch goals

None of these are started until everything above works and CI is green. They are listed in
order of preference. Each one fits the current design without restructuring it:

1. A `hint` command (a `hint` field per room in `world.json`).
2. A move limit as a lose condition (a counter in the loop, counting valid commands).
3. A score or rank at the end (based on moves).
4. Save and load progress to JSON (`save` and `load` commands that serialise `Player` and the
   open/closed and contents state).
5. Combining two items into a new one (a `combine <item> with <item>` command and a `recipes`
   list in `world.json`).
