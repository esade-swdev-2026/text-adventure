# Screen spec

How the game screen looks and behaves. It follows common terminal-UI design principles
(visual hierarchy, colour and emphasis, designed states and feedback, interaction). Code in
`art.py`, `screen.py` and `terminal.py` follows it. Where a rule can be checked in code, a test
checks it (listed at the end).

## 1. Mood

**Noir: black and white, lit by one lamp and a frosted door.** There is no colour at all.
Mood comes from contrast: whatever the light falls on is drawn at full weight, everything
else sits dim in shadow, the light sources themselves are bold, and the room is drawn in
perspective so it has depth. The picture is the largest thing on screen, because it is
how the player sees the room change.

## 2. Size

| Rule | Value | Why |
|---|---|---|
| Minimum terminal | **80 × 24** | The universal default. Every state must fit it with nothing wrapped or cut off. |
| Screen block | **76 × 23** cells | Leaves one spare row so pressing Enter on the prompt never scrolls the panel away. |
| Art | **72 × 10** cells (`SCREEN_WIDTH`, `ART_HEIGHT`) | The panel is 72 + 2 padding + 2 border = 76 wide. 10 of the 23 rows go to the picture. |
| Text column | 72 cells, indented 2 | Text lines up with the inside edge of the art, so the screen has one left edge. |
| Larger terminals | Block is centred both ways | The layout never changes shape at larger sizes. Only the margins grow. |
| Below minimum | One line: `Make the window at least 80×24 (it is now W×H).` and the prompt | A broken layout is worse than a clear request. Commands typed there still work. |

Height is fixed so the layout doesn't jump between turns. Every text area has a fixed number of
rows. Short text is padded with blank rows. Text that is too long is cut at the last row and
ends with `…`.

## 3. Hierarchy and spacing

Reading order matches importance, top to bottom: where you are, what it looks like, what
changed, what you can do, where to type.

```
row  area                       rows  level
 1   panel top + room name        1   primary   (bold, in the border)
 2   art                         10   primary
12   panel bottom + Carrying      1   tertiary  (dim, in the border)
13   description                  3   secondary (plain text)
16   (blank)                      1
17   last result                  2   primary   (marker + bold)
19   (blank)                      1
20   Try  commands                2   secondary (bold commands, dim " · ")
22   (blank)                      1
23   prompt                       1   primary   ([Room] > )
```

- One border only, around the art. The text below is grouped by blank lines, not boxes.
- The inventory is a status line set into the panel's bottom border, a common TUI pattern.
  It saves two rows for the picture and keeps "what you hold" next to "what you see".
- Rounded corners on the panel. Inside the art, square corners for the room and its objects.
- One blank line between groups, never two.

## 4. Palette

| Name | Style | Used for |
|---|---|---|
| `STYLE_TITLE` | bold | Room name in the panel border |
| `STYLE_BORDER` | dim | Panel border |
| `STYLE_LIT` | normal | Art inside the light map: the lamp's cone and what stands in it, the door's glass and the light it spills on the floor |
| `STYLE_SHADOW` | dim | Art outside the light map: the walls, the conduit, the fuse box, the door frame, the dark floor |
| `STYLE_LIGHT` | bold | Light sources inside the light: the lamp `▗▟█▙▖`, the bulb `●`, stars `*` |
| `STYLE_FOCUS` | bold | The spotlight: the object the last command changed, for one turn |
| `STYLE_RESULT` | bold | `» You open the toolbox…` |
| `STYLE_ERROR` | bold | `✗ The fuse box is locked.` |
| `STYLE_WIN` | bold | `✓ The door swings open…` |
| `STYLE_NARRATION` | italic | The intro, shown once on the first screen |
| `STYLE_LABEL` | dim | `Try`, the ` · ` between commands, `Carrying (n/4): …` |
| `STYLE_COMMAND` | normal | Each available command, plain so the bold result is what the eye finds first |
| `STYLE_PROMPT` | bold | `[Electrical Room] > ` |

- **Never colour alone, here never colour at all.** Result, error and win are told apart by
  their symbols `» ✗ ✓`, which also work in `NO_COLOR` and `TERM=dumb` terminals.
- **Light and dark themes:** only weight (bold, dim, italic) is used, never a colour or a
  background, so the picture reads the same way in both. Nothing essential is dim: dim marks
  shadow and labels whose meaning the layout already gives.
- `⚡` is 2 cells wide in rich and many terminals, so sparks use `ϟ`. Art uses only
  box-drawing, block and 1-cell characters. `parse_art` rejects anything else.
- No banner font is used. The banner fonts we drafted (`mini`, `small`, `lean`) are 4–7 rows tall:
  none fits the one-row panel title, and on the win screen a banner would hide the open door.

## 5. The art

- **The room:** a back wall in one-point perspective, with ceiling and floor edges running out
  to the viewer, and a conduit on the wall. A lamp hangs on a cable and throws a cone of
  light that gets sparser as it falls. The floor has three rows of depth, so objects stand in
  front of the wall.
- **Light by area, not by character.** The art file has a `[light]` map the size of the
  background: `#` where light falls. The lamp's cone is lit, and so is the door's frosted
  pane and the patch of light it spills on the floor. Only lit light sources are bold, so an
  object's edge never glows like a lamp. Everything else is in shadow, whatever
  it is made of. An object is lit by where it stands.
- **Objects are drawn, not labelled:** a toolbox with latches and a front handle (it sits
  wholly on the floor, so the wall line stays unbroken), a fuse box with a warning mark, and a
  door with frosted glass. **A figure in a hat stands behind the glass**: crown, brim and
  shoulders cut out of the `░`, and its shadow runs through the light on the floor. The light
  on the floor belongs to the door's sprite, so once the door opens the figure, and its
  shadow, are gone.
- **Open means swung open:** the toolbox lid and the fuse box door are drawn edge-on beside
  the box (`╻┃╹`).
- **The art follows the state.** Items are drawn where they are: inside an open container,
  gone once taken, and on the floor at their own `floor` place once dropped. The open door
  shows a night skyline.
- **Sprites overlap the background:** spaces outside a sprite row's outline are transparent;
  spaces inside are opaque.
- **The spotlight:** after `open`, `take` or `drop`, the object that changed is drawn bold
  for one turn (blank sprite rows excluded), so the eye goes to it.

## 5b. The description

Mood sentence, then one sentence per object in its current state, then the door. An empty
open container reads "The toolbox gapes open, empty.", and dropped items are grouped into one
sentence ("On the floor: wrench, fuse."). If it doesn't fit in three rows, the mood sentence
goes first, so the state of every object and the door is always shown. Text that still
doesn't fit is cut at a word boundary with `…`, never mid-word.

## 6. Designed states

This mock is the real game, captured from a terminal at 80 × 24 (margin removed).

### First entry

The intro takes the result area, in italics, with no marker. There is no last result yet.

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

### Normal result

```
    » You open the toolbox. Inside: screwdriver, wrench.
```

The toolbox sprite changes (lid swung aside, the screwdriver and wrench inside) and is drawn
bold for this turn. When the screwdriver opens the fuse box, the message says so:
`» You open the fuse box with the screwdriver. Inside: key, fuse.`
The description and the `Try` row swap `open toolbox` for `take screwdriver · take wrench`.

### Errors

Same place as a result, so the eye doesn't have to look for it:

```
    ✗ I don't know how to "dance". Type "help" for a list of commands.
    ✗ Take what?
    ✗ The fuse box is locked.
    ✗ Your hands are full. Drop something to take the flashbulb.
```

The screen doesn't change otherwise. Errors are states, not crashes.

### Full inventory (4/4)

```
  ╰─ Carrying (4/4): screwdriver, wrench, key, fuse ─────────────────────────╯
  ...
    Try  take flashbulb · drop screwdriver · drop wrench · drop key
         drop fuse · open door · look · inventory · help · quit
```

### Help

```
    » Commands: look, open <thing>, take <thing>, drop <thing>,
      inventory (i), help (?), quit (q).
```

### Win

The door's sprite shows a night skyline and is in the spotlight. The bottom border is empty
(the game is over), the description area holds the ending, and the commands and prompt are
replaced by one line.

```
  │      └──────╲▔▔▔▔▔▔▔▔▔╲───────────────────────────────┴─────────┴─┘      │
  ...
  ╰──────────────────────────────────────────────────────────────────────────╯
    Cold air rushes in. Beyond the door the city glitters under a wet night
    sky, and for the first time tonight you can see where you're going.

    ✓ The door swings open. You're out.

    Thanks for playing.
```

### Below the minimum size

```
Make the window at least 80×24 (it is now 60×20).
  [Electrical Room] > _
```

The game can't hear a resize while it waits for input, so the full screen comes back after the
next command once the window is big enough.

### Goodbye

`quit`, Ctrl-C and Ctrl-D all leave the last screen in place and print one line under it,
in the text column. The exit code is 0. No traceback, ever.

### Bad world file (outside the game)

```
Error: cannot read nope.json: No such file or directory
```

Printed to stderr, exit code 1, nothing drawn.

## 7. Key hints (the `Try` row)

- Lists the exact commands that make sense now, in this order: `open` for each closed
  container, `take` for each visible item, `drop` for each carried item, `open door`, then
  `look`, `inventory`, `help`, `quit`.
- Locked containers are listed like any other: the player learns they are locked by trying
  (ARCHITECTURE.md, decision 5).
- Commands are plain and separated by a dim ` · `. They wrap as whole commands, never split,
  with the second row aligned under the first. Two rows at most. If they don't fit, the
  second row ends with `…` and `help` lists everything.
- **Tab completes** any command in the row (`open f` + Tab → `open fuse box`), and ↑
  recalls earlier commands (readline).
- Ctrl-C and Ctrl-D are not shown: they are terminal conventions and both just quit.

## 8. Checked by tests

| Rule | Test |
|---|---|
| Every composed art line is exactly 72 cells, in every state | `test_art.py` |
| Each sprite fits inside the background | `test_art.py` |
| Spaces around a sprite are transparent, inside it opaque | `test_art.py` |
| The opening screen fits 80 × 24, every line ≤ 80 cells, nothing cut off | `test_screen.py` |
| Every screen in a full playthrough has the same height | `test_screen.py` |
| Commands list matches the state | `test_screen.py` |
| The changed object, and only its columns, is in the spotlight | `test_screen.py` |
| The inventory sits in the panel's bottom border | `test_screen.py` |
| The prompt lines up with the text column | `test_screen.py` |
| The ASCII fallback keeps every row the same width | `test_screen.py` |
| The art follows contents, taking and dropping | `test_art.py` |
| Shading follows the light map (lamp lit, fuse box in shadow) | `test_screen.py` |
| A crowded description keeps every object and the door, with no `…` | `test_screen.py` |
| `help` never splits a command from its short form | `test_screen.py` |
| Tab completes from the available commands | `test_screen.py` |
