# Screen spec

How every screen of the game looks and behaves. It follows common terminal-UI design principles
(visual hierarchy, colour and emphasis, designed states and feedback, keyboard first). It is the
contract for the epics that build it: **E1** (inspect, use, moves), **E2** (layout), **E3**
(close-ups), **E4** (colour), **E5** (lighting) and **E6** (intro and ending). Where a rule can
be checked in code, a test checks it (section 12).

> **Status.** The main screen (section 3), the inspect view's drawing (section 4), the room
> art (section 5), the too-small screen and redraw on resize (section 10) and the picture
> format (section 7) are built (E0, E2), and so are the `inspect` and `use` verbs and moves
> (E1) and the colour palette (section 6, E4.1 and E4.2). The colour-off switch (E4.3),
> close-up art (E3) and the intro and ending screens (E6) are not yet.

Rows and columns are counted from 1, inside the **screen block** (section 2), top-left first.

## 1. Mood

**Noir, now in colour, lit by one lamp.** The room sits in cold slate-blue shadow. Whatever the
lamp's light falls on turns warm amber, the lamp itself is bold, the night outside the door is a
cold blue, and red is kept for danger and mistakes. Mood still comes from contrast first: every
colour has a weight (bold, normal, dim) that tells the same story without colour (section 6).
The picture is still the largest thing on screen, because it is how the player sees the room
change. **The game no longer suggests commands**: the room, its description, the verbs and the
things you carry are the only hints. The player looks, then chooses a verb and a thing.

## 2. Size

| Rule | Value | Why |
|---|---|---|
| Minimum terminal | **100 × 30** | The room panel, a verb panel and four icon slots side by side need 96 columns. 30 rows fit an 11-row picture, a 3-row description, the panels, a 3-line history and the prompt. |
| Screen block | **96 × 29** cells | 2 columns of margin each side at the minimum. Row 30 stays spare, so pressing Enter on the prompt never scrolls the screen. |
| Picture area | **92 × 11** cells | The room panel is 92 + 2 padding + 2 border = 96 wide. The room art, every close-up and the ending picture all use this size. |
| Text column | 92 cells, indented 2 | Text lines up with the inside edge of the picture, so the screen has one left edge. |
| Larger terminals | Block is centred both ways | The layout never changes shape. Only the margins grow. |
| Below minimum | The too-small screen (section 10) | A broken layout is worse than a clear request. |

Every region has a fixed number of rows, so nothing jumps between turns. Short text is padded
with blank rows. Text that is too long is cut at a word boundary on its last row and ends with
`…`, never mid-word. All widths are terminal cells (`rich.cells.cell_len`), never `len()`.

## 3. Main screen

### Row map

```
row    region                          rows  level
 1     room panel top border             1   room name centred (TITLE), moves in a corner (LABEL)
 2-12  room picture                     11   primary
13     room panel bottom border          1   empty in the room; a hint when inspecting (sec. 4)
14-16  description                       3   secondary (TEXT)
17     (blank)                           1
18-23  verb panel | inventory slots      6   secondary
24     (blank)                           1
25-27  message history                   3   newest primary, older tertiary
28     (blank)                           1
29     prompt                            1   primary (PROMPT)
```

### Column map

```
cols   region
 1-96  room panel (rows 1-13): border col 1 and 96, padding col 2 and 95, picture cols 3-94
 3-94  description, message history, prompt (indent 2)
 1-32  verb panel (rows 18-23)
33-34  gap
35-96  inventory: 4 slots of 14 columns with 2-column gaps
       slot 1: 35-48   slot 2: 51-64   slot 3: 67-80   slot 4: 83-96
```

### Mock (96 × 29, after three moves)

The room art in this mock is the v0.5 drawing (72 × 10) centred in the new 92 × 11 area. E2
widens it.

```
╭────────────────────────────────────── ELECTRICAL ROOM ───────────────────────────── 3 moves ─╮
│                                                                                              │
│              ╲                  │                                             ╱              │
│               ╲┌────────────────┴───────────────────────────────────────────┐╱               │
│                │━━━━┓         ▗▟█▙▖           ┌──────────┐      ┌─────────┐ │                │
│                │    ┃         ░░▒░░           │ ▫  ϟ   ▫ │      │░░░   ░░░│ │                │
│                │    ┣━╸     ░░▒▒▒▒▒░░         │  ━━━━━━  │      │░░     ░░│ │                │
│                │    ┃     ░░ ░  ░  ░ ░░       └──────────┘      │░       ░│ │                │
│                └────┸───────────────────────────────────────────┴─────────┴─┘                │
│               ╱       ╔═════════╗╻  ░  ░ ░░         ·      ·      ░░░ ░░░    ╲               │
│              ╱      ░░║     c══ ║┃ ░  ░  ░ ░░                    ░░░░  ░░░░   ╲              │
│             ╱     ░░  ╚═════════╝╹░  ░  ●▬ ░ ░░                 ░░░░░   ░░░░░  ╲             │
╰──────────────────────────────────────────────────────────────────────────────────────────────╯
  A lone lamp swings overhead. Beyond its light, the walls hum. The toolbox gapes open.
  Inside: wrench. A fuse box is screwed shut. A flashbulb lies in the light. The door is shut
  tight.

╭──────────────────────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮
│ Look    l     Inspect x      │  │      ▗▄▄▖  │  │            │  │            │  │            │
│ Open          Take    get    │  │  ╺━━━▐██▌  │  │            │  │            │  │            │
│ Drop          Use            │  │      ▝▀▀▘  │  │            │  │            │  │            │
│ Help    ?     Quit    q      │  │screwdriver │  │            │  │            │  │            │
╰──────────────────────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯

  » You open the toolbox. Inside: screwdriver, wrench.
  ✗ The fuse box is locked.
  » You take the screwdriver.

  [Electrical Room] > _
```

### 3.1 Room panel (rows 1-13)

- One rounded border (`╭╮╰╯─│`, BORDER). Inside the picture, square corners for the room and
  its objects, as before.
- **Title:** ` ELECTRICAL ROOM `, the room name in upper case with one space each side,
  centred on the 94 inner columns (left part gets the extra column when odd). TITLE role.
- **Move counter:** ` 11 moves ` ending one `─` before the `╮` (it occupies cols 85-94 for
  two digits, so `╮` stays at col 96 and `─` at col 95). `1 move` singular, `0 moves` at the start. LABEL role. It never overlaps the
  title: a title longer than 60 cells is cut with `…`. Which commands count is E1.5's rule
  (typos, `help`, `look` and `inspect` don't).
- **Bottom border:** plain in the room. While inspecting it carries a hint (section 4). The
  inventory no longer lives here.
- **Picture:** 92 × 11, the room art composed for the current state (section 5), shaded by the
  light map and colour roles (section 6).

### 3.2 Description (rows 14-16)

The room's mood sentence, then one sentence per object in its current state, then the door
(same sentences as v0.5). Three rows. If it doesn't fit, the mood sentence goes first, so the
state of every object and the door is always shown. Text that still doesn't fit is cut with `…`.
TEXT role.

### 3.3 Verb panel (rows 18-23, cols 1-32)

A fixed, rounded frame (BORDER) with 4 rows of 2 cells. Each cell is 14 columns: the verb padded
to 8, then its short form. It lists **verbs only, never objects**, so it can't give puzzles away.
It never changes during play.

```
cell 1 (cols 3-16)   cell 2 (cols 17-30)
Look     l           Inspect  x
Open                 Take     get
Drop                 Use
Help     ?           Quit     q
```

- Verbs are VERB role, short forms LABEL. `Help` and `Quit` are LABEL as a whole: they are
  about the game, not the room, so they sit back.
- `inventory` (`i`) still works but is not listed: the slots already show what you carry.
- It is not interactive yet. E2.9 (mouse clicks) may make it so later; keyboard stays first.

### 3.4 Inventory slots (rows 18-23, cols 35-96)

Four slots, always all four, in pick-up order. Each slot is a rounded frame 14 × 6:

```
╭────────────╮   row 18  frame (BORDER)
│  ▗▄▄▖      │   rows 19-21  the item's icon, 8 × 3, at slot cols 4-11 (2 cells padding)
│╺━━━▐██▌    │
│    ▝▀▀▘    │
│screwdriver │   row 22  the item's name, centred in 12 cells (odd space goes right), VERB role
╰────────────╯   row 23  frame
```

- **Empty slot:** the frame with nothing inside. Four frames make the capacity obvious, so
  there is no `Carrying (n/4)` label.
- **Item without an icon** (allowed while art is missing, see section 7.5): the icon rows stay
  blank and only the name shows.
- **Long names** are cut to 12 cells with `…`. Names should be at most 12 characters.
- **Spotlight:** the slot of an item just taken is drawn in FOCUS (frame and icon) for one turn.
  An item just dropped is spotlit in the room picture instead, as before.

### 3.5 Message history (rows 25-27)

The last results, oldest at the top, **newest on row 27**, right above the prompt.

- Each entry keeps its marker: `»` result, `✗` error, `✓` win. The text after the marker is
  aligned under the first word when it wraps.
- **Newest entry:** its tone's role (RESULT bold, ERROR red bold). It may take **2 rows**. Older
  entries: HISTORY role, **1 row each**, cut with `…`. Rows are filled from the bottom up: the
  newest takes 1 or 2 rows and older entries fill what is left, so 2 or 3 entries show.
- Every command adds an entry, including errors, `help`, `look` ("You look around.") and
  `inspect` ("You look closely at the fuse box."). Empty input adds nothing.
- **First screen:** no entries yet. Row 27 shows one LABEL hint instead:
  `Type a verb and a thing, like  look  or  inspect door. Tab completes.` It disappears after the
  first command. The intro story text lives on the intro screen (section 8), not here.

### 3.6 Prompt and input (row 29)

- `  [Electrical Room] > ` in PROMPT, then the cursor. Unchanged from v0.5. While inspecting it
  stays the same: the room is where you are.
- Typing is the only input. The old `Try  open toolbox · …` row is **removed**.
- **Tab completes** a verb, then a name: `ins` → `inspect `, `inspect fu` → `inspect fuse box`,
  `use scr` → `use screwdriver `, then `o` → `on `. Names offered are only things the player can
  see in the room right now, things carried, and `door`. **Never items hidden in closed
  containers**: completion must not give a puzzle away. ↑ recalls earlier commands (readline).
- Ctrl-C and Ctrl-D quit, as before, and are not shown.

## 4. Inspect view

`inspect <thing>` (short `x <thing>`) works on every item (in the room or carried), every
container and the door. Hidden items (inside a closed container) get the usual
`✗ There is no key here.`

```
╭──────────────────────────────────────── SCREWDRIVER ─────────────────────────────── 3 moves ─╮
│                                                                                              │
│                                             ┌──────┬──────────────────────────────────────┐  │
│                                             │      │  ║    ║    ║    ║    ║    ║    ║    │╲  │
│    ▗▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄┤      │  ║    ║    ║    ║    ║    ║    ║    │ │ │
│   ▐▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀┤      │  ║    ║    ║    ║    ║    ║    ║    │ │ │
│                                             │      │  ║    ║    ║    ║    ║    ║    ║    │╱  │
│                                             └──────┴──────────────────────────────────────┘  │
│                                                                                              │
│   ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔  │
│                                                                                              │
│                                                                                              │
╰─ Enter returns to the room ──────────────────────────────────────────────────────────────────╯
  A worn flathead.



╭──────────────────────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮
│ Look    l     Inspect x      │  │      ▗▄▄▖  │  │            │  │            │  │            │
│ Open          Take    get    │  │  ╺━━━▐██▌  │  │            │  │            │  │            │
│ Drop          Use            │  │      ▝▀▀▘  │  │            │  │            │  │            │
│ Help    ?     Quit    q      │  │screwdriver │  │            │  │            │  │            │
╰──────────────────────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯

  ✗ The fuse box is locked.
  » You take the screwdriver.
  » You look closely at the screwdriver.

  [Electrical Room] > _
```

- **Rows 1-13:** the room panel is replaced by the close-up. Title = the thing's name in upper
  case (`FUSE BOX`, `DOOR`). The move counter stays. The bottom border reads
  `─ Enter returns to the room ─` in LABEL.
- **Rows 2-12:** the close-up picture (92 × 11, section 7), in the frame for the thing's current
  state: a container `closed` / `open`, the door `locked` / `unlocked` / `open`, and any story
  state later (`power on`, `flashed`). Clues for the mystery live here, so clue text inside a
  close-up uses the PLAIN role and must be readable.
- **Rows 14-16:** the thing's description (its `description` in `world.json`, or the container's
  or door's current sentence). TEXT role.
- **Rows 18-29:** verb panel, inventory, history and prompt stay exactly as in the room.
- **Leaving:** the next input returns to the room, including Enter alone (which adds no history
  entry and no move). That command is applied first, then the room is drawn. Another `inspect`
  shows the new close-up instead.
- **No close-up yet** (art still missing): the room stays on screen and the description rows
  show the thing's description. Nothing breaks.

## 5. The room art

- **Size:** 92 × 11 (E2 redraws the v0.5 72 × 10 room at this size). Same file format as
  before: `[background]`, `[light]`, and one section per object state.
- **Perspective and light:** unchanged ideas. A back wall in one-point perspective, a lamp on a
  cable throwing a cone of light that gets sparser as it falls, three rows of floor depth.
- **Light by area, not by character.** The `[light]` map is the size of the background: `#`
  where the lamp's light falls, anything else is shadow. An object is lit by where it stands.
  In E4 the map also accepts the picture colour letters (section 7.2), so the door's glass and
  the night behind it can be `n`, a warning mark `r`.
- **Every interactable object is drawn and shows its state.** Required sections:

  | Object | Sections | Today |
  |---|---|---|
  | Container | `[name:closed]`, `[name:open]` (lid or door swung aside, `╻┃╹`) | built |
  | Door | `[door:locked]`, `[door:unlocked]`, `[door:open]` (open shows the night skyline) | `closed` / `open`; E2.5 adds the three states |
  | Item | `[name]`, drawn inside its open container or on the floor at its `floor` place, gone once taken | built |

  Locked and unlocked doors must differ visibly (e.g. a lit keyhole or the bolt drawn back),
  because there is no longer a list of commands to tell the player.
- **Sprites overlap the background:** spaces outside a sprite row's outline are transparent,
  spaces inside are opaque.
- **The spotlight:** after `open`, `take`, `drop` or `use`, the object that changed is drawn in
  FOCUS for one turn (blank sprite rows excluded).
- **Flashbulb flash (E5.2, built):** a `use` rule with `"flash": true` draws one frame with
  the whole picture in PLAIN bold (a white flash) for 0.15 s, then the room returns with the
  object it was used on in FOCUS. The borders, text, panels and prompt don't change, so only
  the picture flashes.
- **Room for E5 (not specified yet):**
  - *Power-on lighting:* a room can have a second light map (e.g. `[light:power on]`) that
    replaces `[light]` once the power is back; most of the room turns from SHADOW to LIT.

## 6. Palette

256-colour ANSI (`38;5;n`), foreground only, never a background. It works in macOS Terminal.app,
which has no truecolor. Every colour was picked to keep **at least 3:1 contrast on both pure
black and pure white** (computed with the WCAG formula), so it reads on dark and light themes.
Text that matters most uses the terminal's own foreground, which always has full contrast.

| Role | Used for | Colour | Hex | On black | On white | Weight | No colour |
|---|---|---|---|---|---|---|---|
| `TITLE` | Room or thing name in the border | default | | | | bold | bold |
| `BORDER` | Room panel, verb panel and slot frames | 243 | `#767676` | 4.6 | 4.5 | normal | dim |
| `SHADOW` | Art outside the light; picture cells ` ` `.` `s` | 60 | `#5f5f87` | 3.5 | 6.0 | normal | dim |
| `LIT` | Art in the lamp's light; picture cells `#` | 136 | `#af8700` | 6.3 | 3.3 | normal | normal |
| `LIGHT` | Light sources in the light (lamp, bulb, stars); picture cells `*` | 136 | `#af8700` | 6.3 | 3.3 | bold | bold |
| `NIGHT` | The night outside: open door, skyline, ending picture; picture cells `n` | 32 | `#0087d7` | 5.4 | 3.9 | normal | normal |
| `DANGER` | Warning marks and danger in art; picture cells `r` | 160 | `#d70000` | 3.9 | 5.4 | normal | normal |
| `PLAIN` | Art in the terminal's own colour: metal, paper, clue text; picture cells `f` | default | | | | normal | normal |
| `FOCUS` | Spotlight: the object or slot the last command changed | default | | | | bold | bold |
| `TEXT` | Description rows | default | | | | normal | normal |
| `VERB` | Verbs, item names in slots | default | | | | normal | normal |
| `LABEL` | Short forms, `Help` / `Quit`, move counter, hints | 243 | `#767676` | 4.6 | 4.5 | normal | dim |
| `RESULT` | Newest `»` entry | default | | | | bold | bold |
| `ERROR` | Newest `✗` entry | 160 | `#d70000` | 3.9 | 5.4 | bold | bold |
| `WIN` | `✓` lines | 32 | `#0087d7` | 5.4 | 3.9 | bold | bold |
| `HISTORY` | Older history entries | 243 | `#767676` | 4.6 | 4.5 | normal | dim |
| `NARRATION` | Intro text | default | | | | italic | italic |
| `PROMPT` | `[Room] > ` | default | | | | bold | bold |

Rules:

- **Never colour alone.** Result, error and win are told apart by `» ✗ ✓`; lit and shadow by
  weight in the fallback; the spotlight by bold. The fallback column is exactly the v0.5
  black-and-white style.
- **Colour off** (fallback column) when any of these holds: the `NO_COLOR` environment variable
  is set and not empty, `play --no-color` is passed, `TERM=dumb`, or stdout is not a terminal.
- **No dim on colour.** Dim on top of a colour can vanish on some themes, so coloured roles
  never use it; dim is only used in the fallback.
- **No truecolor upgrade.** Colours are the 256 numbers above even where truecolor exists, so
  the game looks the same everywhere. On a 16-colour terminal rich picks the nearest colour.
- At most four hues are on screen at once (slate, amber, grey, plus red or blue as accents).
- Every art character is exactly one cell wide; `parse_art` and `parse_picture` reject anything
  else (`ϟ`, not `⚡`). Terminals that can't show UTF-8 get the ASCII fallback, as before.

## 7. Picture files: icons and close-ups

### 7.1 Format

One plain UTF-8 text file per picture, in the same `[section]` syntax as the room art:

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

- Each `[state]` section is one **frame**. The **first frame is the default**: it is drawn when
  the object's current state has no frame of its own. A picture with one look needs only one
  frame (name it `[default]`).
- Each frame may have a `[state:colors]` map: one letter per cell (7.2). A missing map or a
  blank cell means SHADOW.
- Frames and maps must fit in the picture's size and are padded with spaces to exactly that
  size. Leading blank lines count (they push the drawing down); trailing ones don't.
- Every character must be one cell wide.

| Kind | Size | Where it shows | `world.json` field |
|---|---|---|---|
| Icon | **8 × 3** | Inventory slot (3.4) | `icon` on items |
| Close-up | **92 × 11** | Inspect view (4) | `closeup` on items, containers and the door |
| Portrait | 44 × 18 (E6) | Intro screen (8) | top-level `portrait` (not built yet) |
| Ending | 92 × 11 (E6) | Ending screen (9) | top-level `ending_art` (not built yet) |

### 7.2 Colour letters

| Letter | Role |
|---|---|
| space, `.`, `s` | SHADOW |
| `#` | LIT (as in the room's `[light]` map) |
| `*` | LIGHT |
| `n` | NIGHT |
| `r` | DANGER |
| `f` | PLAIN (the terminal's own foreground; use it for clue text) |

### 7.3 State names

Frames are picked by the object's state name: containers `closed` / `open`; the door `locked` /
`unlocked` / `open`; anything else is a story state chosen in E1 (`power on`, `flashed`, …).
Section names are lower case, digits, spaces and `:`.

### 7.4 `world.json` and loading

```json
{ "name": "screwdriver", "description": "a worn flathead",
  "icon": "art/icons/screwdriver.txt", "closeup": "art/closeups/screwdriver.txt" }
```

Paths are relative to the world file, like `art`. `cli.load_world` reads every file named
(`picture_paths` lists them with their size), `art.parse_picture` parses each one, and
`world.build_world` checks the references and keeps them on the `World`: `icon_for(item)` and
`closeup_for(room, name)` (the door's close-up is per room).

### 7.5 Errors and warnings

| Problem | Result |
|---|---|
| A named picture file is missing or unreadable | `Error: cannot read …`, exit 1 |
| A frame or map is bigger than its kind's size, a wide character, an unknown colour letter, a map with no frame, a file with no frame | `Error: <file>: …`, exit 1 |
| `icon` names a close-up-size file or the other way round | `Error: … needs icon size (8x3), but … is close-up size`, exit 1 |
| A portable item has no `icon` | `check` prints `Warning: item "wrench" has no icon.`, exit 0 |
| An item, container or door has no `closeup` | `Warning: container "toolbox" has no close-up.`, exit 0 |

Missing art is a warning while the art is being drawn (E2.4, E3.2). E1.6 may turn it into an
error once every object has its pictures.

## 8. Intro screen (E6)

Shown once at launch, before the room. Same 96 × 29 block, no border: the portrait is the frame.

```
row    region
 1     (blank)
 2-19  portrait, 44 × 18, centred (cols 27-70)
20     (blank)
21-24  intro text from world.json, up to 4 rows, 64 wide, block centred (cols 17-80), NARRATION
25     (blank)
26     Press Enter to begin       centred, PROMPT
27     q quits                    centred, LABEL
28-29  (blank)
```

```
                          ┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐
                          ╎                                          ╎
                          ╎            portrait  44 × 18             ╎
                          ╎    (outline only marks the area; it is   ╎
                          ╎     not drawn)                           ╎
                          ╎                                          ╎
                          └╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘

                The power died an hour ago. Somebody wanted you in the dark. Find a
                way out.


                                      Press Enter to begin
                                            q quits
```

- **The portrait:** a beaten-up man, scars across his face, eyes wide open. Hard light from one
  side (LIT and LIGHT), the rest of the face in SHADOW, the background empty. One frame, in the
  picture format (7), kind "portrait". The art is drawn in E6.1.
- Enter starts the game. `q`, `quit`, Ctrl-C and Ctrl-D quit with "Goodbye.". Anything else is
  ignored. The intro is not a move.

## 9. Ending screen (E6)

Replaces the v0.5 win screen. Drawn at the top of the block (rows 1-22) so the panel doesn't jump;
rows 23-29 stay blank.

```
row    region
 1     border: ESCAPED as title, final moves in the corner
 2-12  ending picture 92 × 11: the open door and a wet city skyline (NIGHT, rain in SHADOW)
13     border
14-16  ending text from world.json, 3 rows, NARRATION
17     (blank)
18     ✓ Escaped in 11 moves. Par is 8.      WIN
19     (blank)
20     Enter  play again     q  quit         keys in PROMPT, words in LABEL
21     (blank)
22     > _                                   PROMPT
```

```
╭────────────────────────────────────────── ESCAPED ──────────────────────────────── 11 moves ─╮
│                                                                                              │
│        ending picture 92 × 11: the open door, wet city skyline at night (night blue)         │
│                                                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────╯
  Cold air rushes in. Beyond the door the city glitters under a wet night sky, and for the
  first time tonight you can see where you're going.

  ✓ Escaped in 11 moves. Par is 8.

  Enter  play again     q  quit

  > _
```

- Under or at par adds a short word: `✓ Escaped in 7 moves. Par is 8. Sharp.` Without a par in
  `world.json`, the line is `✓ Escaped in 11 moves.`
- Enter starts a new game from the intro screen with a freshly loaded world. `q`, Ctrl-C and
  Ctrl-D quit with "Goodbye.". Exit code 0.

## 10. Other states

### First entry

As the main screen, with `0 moves`, four empty slots and the one-line hint on row 27 (3.5).

### Errors

Same place as any result (newest history entry), so the eye doesn't have to look for it. The
rest of the screen doesn't change. Errors are states, not crashes.

```
  ✗ I don't know how to "dance". Type "help" for the verbs.
  ✗ Take what?
  ✗ The fuse box is locked.
  ✗ Your hands are full. Drop something to take the flashbulb.
```

### Full inventory

All four slots filled. Taking a fifth item gives the error above; nothing else changes.

### Help

```
  » Verbs: look (l), inspect (x), open, take (get), drop, use … on …, inventory (i),
    help (?), quit (q). Tab completes names.
```

### Too small

Below 100 × 30 the whole screen is replaced by three lines, **centred both ways** in the actual
terminal:

```
                     Make the window bigger
             The game needs 100 × 30. It is now 80 × 24.
                It redraws as soon as it fits.
```

Line 1 TITLE, line 2 TEXT, line 3 LABEL. Lines wider than the terminal are cut, never wrapped.
**Redraw on resize** (E2.8): on every resize signal (`SIGWINCH`) the game redraws at once, the
too-small screen when shrinking below the minimum, the full screen with the prompt when it fits
again. Text already typed on the prompt is kept. Ctrl-C and Ctrl-D still quit. The intro and
ending screens follow the same rule.

### Goodbye

`quit`, Ctrl-C and Ctrl-D leave the last screen in place and print `Goodbye.` under it, in the
text column. Exit code 0. No traceback, ever.

### Bad world file (outside the game)

```
Error: cannot read nope.json: No such file or directory
```

Printed to stderr, exit code 1, nothing drawn. Bad picture files report the same way (7.5).

## 11. What changed from v0.5

| v0.5 | Now |
|---|---|
| 80 × 24, block 76 × 23, art 72 × 10 | 100 × 30, block 96 × 29, picture 92 × 11 |
| `Carrying (n/4): …` in the bottom border | 4 icon slots beside a verb panel |
| `Try  open toolbox · …` hints | Removed. Verb panel lists verbs only |
| One last result, 2 rows | History of 2-3 entries, newest bold |
| Intro in the result area | Intro screen with portrait |
| Win screen with the ending text | Ending screen with moves and par, play again |
| Black and white | 256-colour noir; black and white is the fallback |
| Resize noticed after the next command | Redraw on resize |

## 12. Checked by tests

Built now (E0.2):

| Rule | Test |
|---|---|
| Picture frames are padded to exactly their kind's size | `test_art.py` |
| Too big, wide characters, unknown colour letters, a map without a frame are errors | `test_art.py` |
| An unknown state falls back to the first frame | `test_art.py` |
| The example icon and close-up load at 8 × 3 and 92 × 11 | `test_art.py` |
| `icon` / `closeup` must name a loaded file of the right kind | `test_world.py` |
| Missing icons and close-ups are listed; scenery needs no icon | `test_world.py` |
| `check` warns about missing pictures and exits 0; a bad picture exits 1 | `test_cli.py` |

To add with E2 / E4 (each replaces its v0.5 counterpart):

| Rule | Test |
|---|---|
| Every row of every screen is at most 96 cells; the screen block is exactly 29 rows | `test_screen.py` |
| Every screen in a full playthrough has the same height, in the room and inspecting | `test_screen.py` |
| The flash turns every picture cell to FOCUS and leaves every other row as it was | `test_screen.py` |
| The verb panel is the same in every state and names no object | `test_screen.py` |
| Slots show icon and name; empty slots are empty frames; long names end in `…` | `test_screen.py` |
| History keeps the newest at the bottom, at most 3 rows | `test_screen.py` |
| Tab never offers an item inside a closed container | `test_screen.py` |
| Move counter text and position in the border | `test_screen.py` |
| Every role has a colour and a no-colour style; colours are the palette's, never dim, same weight as the fallback | `test_terminal.py` |
| Colour prints as 256-colour codes, never truecolor; piped output has no colour | `test_terminal.py` |
| `NO_COLOR` and `--no-color` give the fallback | `test_terminal.py` (E4.3) |
| The real screen at 100 × 30 and 140 × 40, too small, resize | pilotty, before each merge |
