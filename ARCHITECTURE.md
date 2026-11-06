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
2. **A door is unlocked, then opened, and uses up its key.** `use key on door` unlocks it
   (`Door.unlock` removes the key from the inventory, so it stops taking up a slot), and only
   then does `open door` open it. A door can also wait for other objects to be in a state
   first (`needs`, e.g. the power back on); until then the key won't turn.
3. **A container keeps its tool.** On success, `Container.open` leaves the required item in
   the inventory (for example, a screwdriver can be used again).
4. **Containers only open once.** An opened container stays open, and its contents can then
   be taken. Items inside a closed container are hidden: `take` can't reach them, and `look`
   doesn't list them. An item can also be **hidden** on purpose (`"hidden": true`): it can't
   be seen, taken or inspected, even in an open container, until a `use` reveals it.
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
    reserved for the room's door. No name contains the words `on`, `in` or `with`, which split
    `use <item> on <thing>`.
11. **Moves count what changes the game.** A successful `open`, `take`, `drop` or `use` is a
    move (`Player.moves`). Typos, errors, refusals, `look`, `inspect`, `inventory` and `help`
    are not. Winning says `Escaped in N moves. Par is P.`, adding ` Sharp.` at or under par
    (`par` in `world.json`; without it, just `Escaped in N moves.`).
12. **Every item has a purpose.** No decoys: each item opens, unlocks, reveals or powers
    something on the way out.

---

## 3. Commands

Commands are the whole interface, so their grammar is fixed here.

### Grammar

```
command  =  verb [ "the" ] [ name ]
use      =  "use" [ "the" ] item [ ( "on" | "in" | "with" ) [ "the" ] name ]
inspect  =  "look at" [ "the" ] name          (same as inspect <name>)
```

- Input is trimmed, lower-cased and has repeated spaces collapsed before parsing.
- The first word is the verb. Everything after it (minus a leading `the`) is the object name,
  which may be several words (`take brass key`). For `use`, the first `on`, `in` or `with`
  splits the item from the thing it is used on (`use fuse on fuse box`).
- The name must match an object's full name exactly (case-insensitive). There is no
  partial matching.

### The command set

| Command          | Aliases            | Object      | What it does                                                    |
|------------------|--------------------|-------------|-----------------------------------------------------------------|
| `look`           | `l`                | none        | Repeats the room's name and description, and lists what is visible (see below). |
| `inspect <name>` | `x`, `examine`, `look at` | required | The detailed description of an item (in the room or carried), a container or the door, for its current state. Clues live here. Not a move. |
| `open <name>`    | —                  | required    | Opens a container in the room. `open door` opens the room's door once it is unlocked. |
| `take <name>`    | `get`              | required    | Takes a visible item (on the floor or in an open container).    |
| `drop <name>`    | —                  | required    | Drops a carried item onto the floor of the current room.        |
| `use <item> [on <name>]` | `in`, `with` for `on` | required | Uses a carried item on something (or on its own). What happens is written in `world.json` (section 8). |
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
| Unknown verb                                | `I don't know how to "<verb>". Type "help" for the verbs.`   |
| Verb needs an object but none was given     | `Open what?` / `Take what?` / `Inspect what?` / `Use what?`  |
| `use <item> on` with nothing after it       | `Use the <item> on what?`                                    |
| Verb takes no object but one was given      | `"<verb>" doesn't take an object.`                           |
| `open`: no container with that name here    | `There is no <name> here.`                                   |
| `take`/`inspect`: nothing visible with that name | `There is no <name> here.` (also for items in closed containers and hidden items) |
| `drop`/`use`: not carrying that item        | `You aren't carrying a <name>.`                              |
| `use <item>` alone, and it has no own use   | `Use the <item> on what?`                                    |
| `use`: a combination that does nothing      | The item's `refusal`, or `The <item> is no use on the <name>.` |
| `use`: a rule's `needs` not met yet         | The rule's `refusal` (e.g. `The grille is bolted shut. Get it open first.`) |
| `open door` while it is locked              | `The door is locked.`                                        |

---

## 4. Code layout

Every module is either **pure** (works on plain data, never prints, never reads files) or
**I/O** (talks to files or the terminal and does nothing else). Only `cli.py` and
`terminal.py` are I/O. Everything else is tested with plain pytest, without a terminal.

| File | Kind | Contents |
|---|---|---|
| `models.py` | pure | `Item`, `Door`, `Container`, `Room`, `Player`, `Inventory`, the `Use` rule, the name lookups, the state names, `CAPACITY` and the reserved name `DOOR`. |
| `commands.py` | pure | `Verb`, the alias table, `Command(verb, name, target)` and `parse(text) -> Command \| None`, which raises `CommandError`. |
| `game.py` | pure | `apply_command(player, command, par) -> Outcome` (the rules, and the move count) and `play_turn(player, text, par)`, which parses first. `Outcome` holds `message`, `error`, `won`, `quit`, `subject`, `moved` and `inspected` (an `Inspection`). `win_message(moves, par)`. |
| `world.py` | pure | `build_world(data, art, pictures) -> World` checks the parsed JSON and raises `WorldError`. `World` holds `first_room`, `intro`, `ending`, `par`, each room's `Art` and each object's icon and close-up. `missing_pictures(world)` lists the art still to draw. |
| `solve.py` | pure | `shortest_win(world)`: a breadth-first search over game states that returns the fewest commands that win, or `None`. `reachable(world)` returns every state the player can reach. Used by `check` and the tests. |
| `art.py` | pure | `parse_art(text) -> Art` and `compose(art, room) -> list[str]`, which draws each object's sprite for its current state (`door_state`: locked, unlocked or open). `parse_picture(text, size) -> Picture` reads an icon or close-up. Widths are in terminal cells. |
| `screen.py` | pure | `describe_room`, `thing_description`, `visible_names` and `complete` (Tab), and `build_screen` / `build_win_screen`, which return every row of the 96 × 29 block as text tagged with a role (border, shadow, lit, result, history…). |
| `terminal.py` | I/O | `Terminal`: draws a screen with rich (one style per role, centred both ways, cleared between turns), shows the too-small screen, redraws on resize keeping typed text, reads a line, prints "Goodbye.". |
| `cli.py` | I/O | Typer commands `play [--world PATH]` and `check PATH` (which also proves the world can be won within its par). Reads `world.json`, the art files and the picture files, runs the loop, turns every load error into `Error: …` and exit code 1, and handles Ctrl-C / Ctrl-D. |
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
| `Item`      | `models.py`   | Name, description, `portable` flag, `floor_text` (its sentence while on the floor), `details` (inspect texts by state), `uses`, `refusal`, and a `story` state a `use` may set (`state`). |
| `Container` | `models.py`   | Name, open/closed, optional `required_item` (a name) with `needs` / `refusal`, `contents`, `hidden` items, `closed_text` / `open_text`, `room_texts` (its room sentence by state, `room_sentence()`), `details`, `uses`, and `state`: its story state, else `open` / `closed`. |
| `Door`      | `models.py`   | `required_item`, `needs` / `refusal`, `unlock_text`, `room_texts`, `details`, `uses`, `next_room` (a `Room`, or `None` for the exit), `is_unlocked`, `is_open`, and `state`: `locked` / `unlocked` / `open`. |
| `Use`       | `models.py`   | One rule from `world.json`: the `item` used (or `None` for an item's own use), `text`, `needs` and `refusal`, the new story `state`, the names to `reveal`, and whether the item is `consume`d. |
| `Room`      | `models.py`   | Name, mood description, containers, loose items, `hidden` loose items, one door. `remove_item` takes an item off the floor or out of an open container; `reveal(name)` brings a hidden item into sight. |
| `Inventory` | `models.py`   | Up to `CAPACITY = 4` items. Add, find by name, count, use up, drop, list. Refuses a fifth. |
| `Player`    | `models.py`   | `current_room`, one `Inventory` and `moves`. `take_item` and `drop_item` move items between room and inventory. |
| `Verb`, `Command` | `commands.py` | The nine verbs and one parsed command (`target` is the thing a `use` is aimed at). |
| `Outcome`   | `game.py`     | What one command did: the message, whether it was an error, a win or a quit, the object it changed (`subject`), whether it was a move (`moved`), and what was inspected. |
| `Inspection` | `game.py`    | What `inspect` looked at: `name`, `kind` (`item` / `container` / `door`), `state` (picks the close-up frame) and `text`. |
| `Art`       | `art.py`      | Background rows, named sprites, and where each object's sprite goes.     |
| `Position`, `Box`, `DrawnObject` | `art.py` | A cell (row, column); the rectangle a sprite covers, used for the spotlight; one object drawn right now (name, sprite section, position). |
| `Picture`, `Frame`, `PictureSize` | `art.py` | An icon or close-up: one `Frame` (rows plus a colour letter per cell) per state, at a fixed `PictureSize` (`ICON` 8 × 3, `CLOSEUP` 92 × 11). |
| `World`     | `world.py`    | The first room, intro, ending, each room's art, and the icons and close-ups (`icon_for`, `closeup_for`). |
| `Message`, `Inspected`, `Screen` | `screen.py` | One history entry (text and tone); the thing in the inspect view (name, text, close-up, state); every row of one screen tagged with roles, the prompt and the names Tab offers. |

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
  history = [world.intro]                    # the story so far, until E6's intro screen
  loop:
      terminal.draw(build_screen(room, inventory, art, history,
                                 moves=player.moves, focus=…, inspected=…))
      outcome = play_turn(player, terminal.read(), world.par)
      empty line        → back to the room, draw again
      outcome.quit      → print "Goodbye.", stop
      outcome.inspected → history += "You look closely at the X.", draw the close-up
      otherwise         → history += outcome.message
      outcome.won       → draw the win screen (ending text, "Escaped in N moves."), stop
```

The room name is in the panel title and in the prompt, so the player always knows where they
are. Ctrl-C and Ctrl-D end the game the same way as `quit`.

### What each command does (`game.apply_command`)

| Verb        | Looks up / calls                                           | Success                                                     | Failure                                         |
|-------------|------------------------------------------------------------|-------------------------------------------------------------|-------------------------------------------------|
| `LOOK`      | —                                                          | Redraws the screen ("You look around.").                    | —                                               |
| `INSPECT`   | the door, a container, a visible item or a carried one     | The thing's `inspect` text for its state (or its plain description), with an `Inspection`. | Not visible → "There is no X here." |
| `OPEN`      | `door` → `room.door.open()`                                | If `door.is_exit()`: the player wins. Otherwise `player.current_room = door.next_room`. | Still locked → "The door is locked." |
| `OPEN`      | other name → `room.find_container(name)`, then `container.open(inventory)` | "You open the X. Inside: …" (or "It's empty.", or "You can't make anything out." while something hides in it). Already open → "The X is already open." | Not found → "There is no X here." No tool → "The X is locked." `needs` not met → its `refusal`. |
| `USE`       | the carried item, then the target's `uses` rule for it      | The rule's `text`; its `state`, `reveal` and `consume` are applied. With no rule, the lock's own tool works like `open` (container) or unlocks the door (if its `needs` are met; the key is used up). | See the error table in section 3. |
| `TAKE`      | `room.find_visible_item(name)`, then `player.take_item(item)` | "You take the Y."                                        | Not found → "There is no Y here." `ValueError` → its message (hands full, can't be carried). |
| `DROP`      | `inventory.find(name)`, then `player.drop_item(item)`      | "You drop the Y."                                           | Not found → "You aren't carrying a Y."         |
| `INVENTORY` | `inventory.show_inventory()`                               | Lists items with descriptions.                              | Empty → "You are carrying nothing."             |
| `HELP`      | —                                                          | Lists the commands.                                         | —                                               |
| `QUIT`      | —                                                          | "Goodbye." and the loop ends.                               | —                                               |

### Ending the game

- **Win:** the last room's door opens (`Door.is_exit()` is `True`). The message is
  `win_message(moves, par)`, e.g. `Escaped in 12 moves. Par is 12. Sharp.` The win screen shows
  the door open and the `ending` text, and the game exits with code 0.
- **Quit:** `quit`, Ctrl-C or Ctrl-D. Exit code 0, no traceback.
- There is no lose condition. Moves are counted against par but never end the game.

---

## 7. The screen

The full spec, with a mock of every state, is [docs/SCREEN-SPEC.md](docs/SCREEN-SPEC.md). In
short, the screen is a 96 × 29 block (100 × 30 minimum terminal), redrawn after every command:

1. **Room panel.** A 92 × 11 picture: sprites placed on a background, one sprite per object
   state (toolbox closed or open, the fuse box closed, open or powered, the vent closed, open
   or flashed, the door locked, unlocked or open, a floor item only while it lies there). The room name is in the top border, the move counter in its
   corner. While inspecting, the thing's close-up replaces the picture.
2. **Description.** The room's mood text plus one sentence per object for its current state.
3. **Verb panel and inventory.** The verbs only (never objects), and four slots with each
   carried item's icon and name. The game no longer lists commands to try.
4. **History.** The last results (`»` result, `✗` error, `✓` win), newest at the bottom.

The style is noir, black and white for now (colour is E4): the art's `[light]` map decides
what is lit (normal) and what is in shadow (dim), and the object the last command changed is
drawn bold for one turn. Smaller windows get a centred request to resize, and the screen
redraws as soon as the window changes size.

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
  "par": 12,
  "rooms": [
    {
      "id": "electrical",
      "name": "Electrical Room",
      "description": "The room's mood, the first sentence of its description.",
      "art": "art/electrical_room.txt",
      "items": [
        { "name": "flashbulb", "description": "an old camera flashbulb",
          "floor_text": "A flashbulb glints in the dust.", "sprite": [4, 44],
          "icon": "art/icons/flashbulb.txt", "closeup": "art/closeups/flashbulb.txt" }
      ],
      "containers": [
        {
          "name": "fuse box",
          "required_item": "screwdriver",
          "closed_text": "A fuse box is screwed shut on the wall.",
          "open_text": "The fuse box hangs open.",
          "room_text": { "power on": "The fuse box hums; a red light glows by the door." },
          "inspect": { "closed": "Fresh scratches round every screw.",
                       "open": "One empty socket.", "power on": "Every socket full." },
          "uses": [
            { "item": "fuse", "needs": { "fuse box": "open" },
              "refusal": "The fuse box is screwed shut.",
              "text": "You press the fuse home. The box hums.",
              "state": "power on", "consume": true }
          ],
          "sprite": [1, 26],
          "closeup": "art/closeups/fuse_box.txt",
          "contents": [{ "name": "key", "description": "small and brass",
                         "inspect": "A paper tag: \"For when you wake up. V.\"" }]
        },
        {
          "name": "vent",
          "required_item": "wrench",
          "uses": [
            { "item": "flashbulb", "needs": { "vent": "open" }, "refusal": "Open it first.",
              "text": "The bulb pops…", "state": "flashed", "reveal": ["fuse"],
              "consume": true }
          ],
          "contents": [{ "name": "fuse", "hidden": true }]
        }
      ],
      "door": { "required_item": "key", "next_room": null, "sprite": [0, 52],
                "needs": { "fuse box": "power on" },
                "refusal": "The key won't turn. The electric bolt holds it.",
                "unlock_text": "The key turns.",
                "room_text": { "locked": "The steel door is locked." },
                "closeup": "art/closeups/door.txt" }
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
- `icon` (items) and `closeup` (items, containers, the door) name picture files, relative to
  the world file like `art`. Both are optional for now: `check` warns about each one missing.
- `par` (optional, a whole number ≥ 1): the moves a sharp player needs.
- **States.** A container is `closed` or `open`, the door `locked`, `unlocked` or `open`. A
  `use` can give an item or a container a **story state** (lower-case words, e.g. `power on`,
  `flashed`), which then replaces `open` / `closed` as its state. The door has no story states.
- `inspect` (any object): one text, or `{state: text}`; the first text is the default for a
  state without one.
- `room_text` (containers, the door): `{state: sentence}`, the object's sentence in the room
  description for that state. It wins over `closed_text` / `open_text`. An open container
  still gets "Inside: …" added; a `room_text` sentence is never followed by ", empty".
- `uses` (any object): what happens when an item is used on it. Each rule has `item`
  (required, except on an item's own rule, which runs for `use <item>` alone), `text`, and
  optionally `needs` (`{object name: state}`, with a `refusal` said until they are met),
  `state` (the object's new story state), `reveal` (names of hidden items to bring out) and
  `consume` (the item is used up; default `false`). Using the lock's own `required_item` needs
  no rule: it opens the container or unlocks the door.
- `needs` and `refusal` also work on a container's or the door's lock, and the door has
  `unlock_text` for when the key turns.
- `hidden: true` on an item keeps it out of sight until a rule `reveal`s it.
- `refusal` on an item: said when it is used on something that doesn't react to it.

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
- a field has the wrong type, or the art file lacks a sprite section that `sprite` needs;
- a name contains `on`, `in` or `with`, or `par` isn't a whole number ≥ 1;
- a `use` names an item that doesn't exist, an object has two rules for the same item, or a
  rule is written for the lock's own `required_item`;
- a `needs` names an object that isn't in the room, or a state that object is never in (a
  container's states are `closed`, `open` and every story state a rule gives it);
- `needs` comes without a `refusal`;
- a story `state` isn't lower-case words, is a built-in state name, or is set on the door;
- a `reveal` names something that isn't a hidden item in that room, or a hidden item is never
  revealed by any rule;
- an `inspect` or `room_text` is keyed by a state the object is never in;
- an `icon` or `closeup` names a picture that wasn't loaded, or one of the wrong size (an icon
  file used as a close-up, or the other way round).

A picture file that is missing, too big or malformed stops loading with `Error: <file>: …` and
exit code 1, like the room art. A missing `icon` or `closeup` is not an error: `check` prints
one `Warning:` line per missing picture after its summary and still exits 0, because the art is
drawn after the format (E2.4, E3.2).

The loader does **not** check that the puzzle can be solved; `check` does. After loading,
`check` runs `solve.shortest_win`, a breadth-first search over every reachable game state
(each `open`, `take`, `drop` and `use` the player could try). It exits 1 with
`Error: <file>: the world can't be won` if no route wins, or
`Error: <file>: par is P, but the shortest win takes N moves` if `par` is below the best
route. Otherwise it prints `The shortest win takes N moves. Par is P.` after the summary.

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

### Picture files (icons and close-ups)

Each icon and close-up is its own UTF-8 file, in the same `[section]` syntax as the room art.
The full rules are in [docs/SCREEN-SPEC.md](docs/SCREEN-SPEC.md) §7.

```
[closed]
┌──────────┐
│ ▫  ϟ   ▫ │
└──────────┘

[closed:colors]
ssssssssssss
ss sr  s ss
ssssssssssss

[open]
...
```

- Each `[state]` section is a frame. The first frame is the default, used when the object's
  state (`closed`, `open`, `locked`, `power on`…) has no frame of its own.
- `[state:colors]` is optional: one letter per cell, ` ` `.` `s` shadow, `#` lit, `*` light
  source, `n` night, `r` danger, `f` plain. A missing map means all shadow.
- An icon must fit in 8 × 3 cells, a close-up in 92 × 11. Both are padded to exactly that size.
- `cli.load_world` reads every file `picture_paths(world_json)` lists, with the size it is used
  at, and `parse_picture` parses it. `build_world` checks every reference and stores the
  pictures on the `World`. Nothing draws them yet; E2 and E3 do.

The packaged world has one example of each: `art/icons/screwdriver.txt` and
`art/closeups/screwdriver.txt`.

### The Electrical Room puzzle

Somebody ("V.") pulled the fuse, hid it in the vent and left you locked in with the key. The
way out, at par 12:

1. `open toolbox` → `take wrench` → `open vent` (pitch black inside).
2. `take flashbulb` → `use flashbulb on vent`: the flash (used up) reveals the hidden fuse.
3. `take fuse` → `take screwdriver` → `open fuse box` → `take key`.
4. `use fuse on fuse box`: the power comes back (`power on`).
5. `use key on door` (only with power; the key stays in the lock) → `open door`. **You win.**

Every item has one job, and the clues for each step are in the `inspect` texts. At most 4
items are carried at once on the best route, so the inventory limit still bites on others.

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
  aliases, empty input, an unknown verb, a missing object and an unexpected object, `inspect`
  and its short forms, and `use` with and without `on` / `in` / `with`.
- **Art** (`test_art.py`): picture frames padded to size, bad pictures rejected, the default
  frame, the example pictures' sizes; sprite placement, state swaps, a taken item disappearing, clipping,
  missing or malformed sections, transparency, and that every composed line is exactly 72 cells in
  every state of the real room.
- **World** (`test_world.py`): pictures are found by object, missing ones are listed (scenery needs
  no icon), the packaged world loads, each rule in section 8 rejects a
  small broken example, every clue and result fits its rows, and the room description fits
  3 rows at 92 columns along the par route and in every reachable state.
- **Game** (`test_game.py`): locked container, tool kept, full inventory, drop and take back,
  the door's unlock-then-open with its power `needs`, the full par route, which commands are
  moves, the win message, inspect in every state, every kind of `use` and refusal, reveals and
  story states, unknown names, empty input and quit.
- **Solver** (`test_solve.py`): the packaged world is won in exactly its par, the search leaves
  the world untouched, an unwinnable world gives `None`, and a two-room route is found.
- **Screen** (`test_screen.py`): every screen in a playthrough is exactly 96 × 29, in the room
  and inspecting; the border with title and move counter; the verb panel never changes and
  names no object; slots, icons and empty frames; the history; Tab never offers hidden items;
  the inspect view; the spotlight; the win screen and the ASCII fallback.
- **CLI** (`test_cli.py`): a scripted win exits 0, end of input says goodbye, a missing world
  file, invalid JSON and a bad picture file exit 1 with `Error:`, `check` prints a summary,
  the shortest win and a warning for each missing icon or close-up, and an unwinnable world,
  a par below the shortest win or a broken `use` exit 1.

The real terminal (layout at 100 × 30 and 140 × 40, Ctrl-C/Ctrl-D, a too-small window, resize)
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
2. A move limit as a lose condition (`Player.moves` is already counted).
3. A score or rank at the end beyond par's "Sharp." (moves and par already exist).
4. Save and load progress to JSON (`save` and `load` commands that serialise `Player` and the
   open/closed and contents state).
5. Combining two items into a new one (a `combine <item> with <item>` command and a `recipes`
   list in `world.json`).
