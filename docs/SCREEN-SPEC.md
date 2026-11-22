# Screen spec

How every screen of the game looks and behaves. It follows common terminal-UI design principles
(visual hierarchy, colour and emphasis, designed states and feedback, keyboard first). It is the
contract for the epics that build it: **E1** (inspect, use, moves), **E2** (layout), **E3**
(close-ups), **E4** (colour), **E5** (lighting), **E6** (intro and ending) and **E7** (tonal
art). Where a rule can be checked in code, a test checks it (section 12).

> **Status.** Built: the main screen layout, the inspect view, the room art, the picture
> format, the too-small screen and redraw on resize (E0, E2), the `inspect` and `use` verbs and
> moves (E1), the colour palette (E4.1, E4.2) and the flashbulb flash (E5.2).
>
> **This version describes the tonal art redesign (E7).** It changes the picture to 92 × 24
> drawn in line art plus `░▒▓█` shading, the screen to 96 × 43, the icons to 10 × 4 and the
> palette to a graded light scale, and drops light-theme support. Built: the engine (E7.2:
> sizes, tone, light levels, light maps by state, the graded roles), the room (E7.3: drawn
> at 92 × 24, light baked by `scripts/bake_light.py`, with `[light:power on]`, so power-on
> lighting, E5.1, works too) and the pictures (E7.4: the screwdriver close-up at 92 × 24,
> drafted by `scripts/bake_closeup.py`, and the five icons at 10 × 4) and the lamp flicker
> (E5.3, with `play --no-motion`). Also not built: the colour-off switch (E4.3), close-ups
> for the other objects (E3.2) and the intro and ending screens (E6).
>
> **More rooms (E8)** adds the Darkroom and the Night Office after the Electrical Room
> (section 5.7): a light colour and a flicker switch per room, and a door that won't let the
> player leave a needed tool behind. Built: the engine (E8.2), the Darkroom (E8.3) and the
> Night Office (E8.4), with icons and the photograph and matchbook close-ups.

Rows and columns are counted from 1, inside the **screen block** (section 2), top-left first.

## 1. Mood

**Noir, drawn in light.** The room is mostly darkness. One lamp throws a pool of light that
fades from solid `█` under the lamp through `▓` and `▒` to a thin `░` and then to nothing, and
whatever stands in it turns from cold slate to warm amber. The look borrows from tonal ASCII
artwork (images built from a density ramp), but it is **hybrid**: walls, edges and every object
you can use keep crisp line-art outlines, and only surfaces and light are shaded. At this size a
fully shaded room would lose its objects, and the game no longer suggests commands, so the
player has to be able to find every object by eye.

Mood still comes from contrast first: every colour has a weight (bold, normal, dim) that tells
the same story without colour (section 6). The picture is the largest thing on screen, because
it is how the player sees the room change. **The game no longer suggests commands**: the room,
its description, the verbs and the things you carry are the only hints. The player looks, then
chooses a verb and a thing.

## 2. Size

| Rule | Value | Why |
|---|---|---|
| Minimum terminal | **100 × 44** | The room panel, a verb panel and four icon slots side by side need 96 columns. 44 rows fit a 24-row picture, a 3-row description, the 7-row panels, a 3-line history and the prompt. A maximised window on a laptop fits it. |
| Screen block | **96 × 43** cells | 2 columns of margin each side at the minimum. Row 44 stays spare, so pressing Enter on the prompt never scrolls the screen. |
| Picture area | **92 × 24** cells | The room panel is 92 + 2 padding + 2 border = 96 wide. The room art, every close-up and the ending picture all use this size. 24 rows give the shading room to fall off and the floor real depth. |
| Text column | 92 cells, indented 2 | Text lines up with the inside edge of the picture, so the screen has one left edge. |
| Larger terminals | Block is centred both ways | The layout never changes shape. Only the margins grow. |
| Below minimum | The too-small screen (section 10) | A broken layout is worse than a clear request. |
| Theme | **Dark background only** | Shading draws light as ink: `█` is the brightest cell. On a light background that reads as a photo negative. The README says to use a dark theme. |

Every region has a fixed number of rows, so nothing jumps between turns. Short text is padded
with blank rows. Text that is too long is cut at a word boundary on its last row and ends with
`…`, never mid-word. All widths are terminal cells (`rich.cells.cell_len`), never `len()`.

## 3. Main screen

### Row map

```
row    region                          rows  level
 1     room panel top border             1   room name centred (TITLE), moves in a corner (LABEL)
 2-25  room picture                     24   primary
26     room panel bottom border          1   empty in the room; a hint when inspecting (sec. 4)
27-29  description                       3   secondary (TEXT)
30     (blank)                           1
31-37  verb panel | inventory slots      7   secondary
38     (blank)                           1
39-41  message history                   3   newest primary, older tertiary
42     (blank)                           1
43     prompt                            1   primary (PROMPT)
```

### Column map

```
cols   region
 1-96  room panel (rows 1-26): border col 1 and 96, padding col 2 and 95, picture cols 3-94
 3-94  description, message history, prompt (indent 2)
 1-32  verb panel (rows 31-37)
33-34  gap
35-96  inventory: 4 slots of 14 columns with 2-column gaps
       slot 1: 35-48   slot 2: 51-64   slot 3: 67-80   slot 4: 83-96
```

### Mock (96 × 43, after three moves)

The picture in this mock comes from the E7 prototype: lighting baked by the prototype's model,
sprites still at their 11-row sizes. E7.3 redraws the sprites about twice as tall (section 5.3).
Colour is not shown: the lamp's pool is amber, the shadowed edges slate (section 6).

```
╭────────────────────────────────────── ELECTRICAL ROOM ───────────────────────────── 3 moves ─╮
│ ╲                              │                                                           ╱ │
│    ╲╲                          │                                                       ╱╱    │
│        ╲                       │                                                    ╱        │
│           ╲╲                   │                                                ╱╱           │
│               ┌──────────────▗▟█▙▖───────────────────────────────────────────┐               │
│               │░░░░░ ░░░░░░░ ░▓▓▓░░░ ░░░░░░░┌──────────┐                     │               │
│               │░ ░░░░░░░ ░░▒▓▓▓▓▓▓▒▒░░░░ ░░░│ ▫  ϟ   ▫ │                     │               │
│               │░░░   ░░░▒▒▓▓▓▓█▓█▓█▓▓▒▒░▒░░░│  ━━━━━━  │░                    │               │
│               │░ ░░░░▒▒▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░▒░▒└──────────┘                     │               │
│               │░▒░▒▒▒▒▓▓▓▓█▓▓▓█▓▓▓▓▓▓▓█▓▓▒▓▒▒░▒░░░░    ░      ┌─────────┐    │               │
│             ░░│▒░▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▒▒░▒░░░░░         │         │    │               │
│           ░░▒░│▒▓▒▓▓▓▓█▓█▓▓▓▓▓▓▓█▓█▓▓▓█▓█▓▓▓▓▓▓▒▒▒▒░░░░ ░     │         │    │               │
│        ░░░░▒░▒│▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▒▒▒▒░▒░░░░ ░  │     ▪━━━┿━   │               │
│      ░░░▒░▒▒▒▒│▓▓▓▓▓▓▓█▓█▓█▓▓▓█▓█▓█▓▓▓█▓█▓█▓▓▓▓▓▓▒▓▒▒▒▒░▒░▒░░░│         │    │               │
│  ░ ░░░░▒░▒░▒▒▓│▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▒▓▒▒▒▒░▒░░░░│         │    │               │
│ ░░░░▒░▒▒▒▒▒▒▓▒└───────────────────────────────────────────────│         │────┘               │
│ ░░░░░▒░▒▒▒▒▒╱▒▒▓▒▓▓▓▓▓▓▓▒▓▓▓▓▓▒▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▒▓▒▓▒▓▒▓▒▒▒▒░▒░░░▒░░░░           ╲             │
│ ▒░▒▒▒▒▒▒▒▒╱╱▓▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▒▓▒▒▒▒▒▒▒▒░▒░▒░▒    ░      ╲╲           │
│ ░▒░▒▒▒▒▒▒╱▒▓▓▓▓▓▒▓▒▓▓▓▓▓▒▓▓▓▓▓▒▓▓▓▒▓▓▓▓▓▒▓▒▓▓▓▒▓▒▓▓▓▒▓▒▓▒▒▒▒▒▒░▒▒▒░░░░░░          ╲          │
│ ▒▒▒▒▒▒▒╱▓▓▓▒▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▓▓▒▓▓▓▓▓▒▓▒▒▒▓▒▒░▒▒▒░▒░▒░▒░░░        ╲        │
│ ░▒░▒▒╱▒▓▒▒▒▓▒▓▓▓▒▓▒▓╔═════════╗▓▓▓▓▓▓▓▒▓▓▓▒▓▒▓▒▓▓▓▒▓▒▒▒▓▒▒▒▓░▒▒▒░▒░▒░▒░░░░░░░░░       ╲      │
│ ▒▒▒╱╱▒▓▒▓▒▓▓▓▒▓▒▓▒▓▓║▒▪▒═══▒▪▒║▓▓▒▓▓▓▒▓▓▓▒▓▓▓▒▓▒▓▒▓▓▓▒▓▓▓▒▓▒▓▒▒▒▒▒▒░▒▒▒░▒░░░░░░░ ░     ╲╲    │
│ ░▒╱▒▒▒▒▓▒▓▒▓▒▓▒▒▒▓▒▓╚═════════╝▓▒▓▒▓▓▓▒▓▓▓▓▓▒▓▒▓▓▓▒▓▒▒▒▓▒▓▒▒▒▒▒▒▒▒▒▒░▒░▒░▒░░░░ ░░░░░░    ╲   │
│ ╱▒▒▒▓▓▓▒▓▓▓▒▓▒▓▓▓▓▓▒▓▓▓▓▓▓▓▒▓▓▓▒▓▒▓▓▓▒▓▓▓▓▓▓▓▒▓▒▓▓▓▒▓▓▓▒▓▓▒▒▒▒▓▒▒▒▒▒▒░▒░▒▒▒░▒░░░ ░░░ ░     ╲ │
╰──────────────────────────────────────────────────────────────────────────────────────────────╯
  A lone lamp swings overhead. Beyond its light, the walls hum. The toolbox is shut.
  A fuse box is screwed to the wall. The door is shut tight.


╭──────────────────────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮
│ Look    l     Inspect x      │  │      ▗▄▄▄▖ │  │ ▜▙      ▟▛ │  │    ▄██▄    │  │            │
│ Open          Take    get    │  │ ╺━━━━▐█▓▒▌ │  │  ▐▓▓▓▒▒▒▌  │  │   ▐█▓▓▒▌   │  │            │
│ Drop          Use            │  │      ▐▓▒░▌ │  │  ▐▒▒▒░░░▌  │  │    ▀▓▒▀    │  │            │
│ Help    ?     Quit    q      │  │      ▝▀▀▀▘ │  │ ▟▛      ▜▙ │  │     ▒░     │  │            │
│                              │  │screwdriver │  │   wrench   │  │ flashbulb  │  │            │
╰──────────────────────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯

  » You open the toolbox. Inside: screwdriver, wrench.
  » You take the wrench.
  » You take the screwdriver.

  [Electrical Room] > _
```

### 3.1 Room panel (rows 1-26)

- One rounded border (`╭╮╰╯─│`, BORDER). Inside the picture, square corners for the room and
  its objects, as before.
- **Title:** ` ELECTRICAL ROOM `, the room name in upper case with one space each side,
  centred on the 94 inner columns (left part gets the extra column when odd). TITLE role.
- **Move counter:** ` 11 moves ` ending one `─` before the `╮` (it occupies cols 85-94 for
  two digits, so `╮` stays at col 96 and `─` at col 95). `1 move` singular, `0 moves` at the
  start. LABEL role. It never overlaps the title: a title longer than 60 cells is cut with `…`.
  Which commands count is E1.5's rule (typos, `help`, `look` and `inspect` don't).
- **Bottom border:** plain in the room. While inspecting it carries a hint (section 4).
- **Picture:** 92 × 24, the room art composed for the current state and drawn cell by cell as
  line art or tone (section 5), coloured by light level (section 6).

### 3.2 Description (rows 27-29)

The room's mood sentence, then one sentence per object in its current state, then the door.
Three rows. If it doesn't fit, the mood sentence goes first, so the state of every object and
the door is always shown. Text that still doesn't fit is cut with `…`. TEXT role.

### 3.3 Verb panel (rows 31-37, cols 1-32)

A fixed, rounded frame (BORDER), 32 × 7, with 4 rows of 2 cells on inner rows 1-4 and a blank
fifth row, so it is as tall as the slots beside it. Each cell is 14 columns: the verb padded to
8, then its short form. It lists **verbs only, never objects**, so it can't give puzzles away.
It never changes during play.

```
cell 1 (cols 3-16)   cell 2 (cols 17-30)
Look     l           Inspect  x
Open                 Take     get
Drop                 Use
Help     ?           Quit     q
(blank)
```

- Verbs are VERB role, short forms LABEL. `Help` and `Quit` are LABEL as a whole: they are
  about the game, not the room, so they sit back.
- `inventory` (`i`) still works but is not listed: the slots already show what you carry.
- It is not interactive yet. E2.9 (mouse clicks) may make it so later; keyboard stays first.

### 3.4 Inventory slots (rows 31-37, cols 35-96)

Four slots, always all four, in pick-up order. Each slot is a rounded frame 14 × 7:

```
╭────────────╮   row 31  frame (BORDER)
│      ▗▄▄▄▖ │   rows 32-35  the item's icon, 10 × 4, at slot cols 3-12 (1 cell padding)
│ ╺━━━━▐█▓▒▌ │
│      ▐▓▒░▌ │
│      ▝▀▀▀▘ │
│screwdriver │   row 36  the item's name, centred in 12 cells (odd space goes right), VERB role
╰────────────╯   row 37  frame
```

- Icons follow the same hybrid style as the room: line-art outline, `░▒▓█` shading inside, lit
  from the top left (section 7).
- **Empty slot:** the frame with nothing inside. Four frames make the capacity obvious, so
  there is no `Carrying (n/4)` label.
- **Item without an icon** (allowed while art is missing, see section 7.5): the icon rows stay
  blank and only the name shows.
- **Long names** are cut to 12 cells with `…`. Names should be at most 12 characters.
- **Spotlight:** the slot of an item just taken is drawn in FOCUS (frame and icon) for one turn.
  An item just dropped is spotlit in the room picture instead, as before.

### 3.5 Message history (rows 39-41)

The last results, oldest at the top, **newest on row 41**, right above the prompt.

- Each entry keeps its marker: `»` result, `✗` error, `✓` win. The text after the marker is
  aligned under the first word when it wraps.
- **Newest entry:** its tone's role (RESULT bold, ERROR red bold). It may take **2 rows**. Older
  entries: HISTORY role, **1 row each**, cut with `…`. Rows are filled from the bottom up: the
  newest takes 1 or 2 rows and older entries fill what is left, so 2 or 3 entries show.
- Every command adds an entry, including errors, `help`, `look` ("You look around.") and
  `inspect` ("You look closely at the fuse box."). Empty input adds nothing.
- **First screen:** no entries yet. Row 41 shows one LABEL hint instead:
  `Type a verb and a thing, like  look  or  inspect door. Tab completes.` It disappears after the
  first command. The intro story text lives on the intro screen (section 8), not here.

### 3.6 Prompt and input (row 43)

- `  [Electrical Room] > ` in PROMPT, then the cursor. While inspecting it stays the same: the
  room is where you are.
- Typing is the only input.
- **Tab completes** a verb, then a name: `ins` → `inspect `, `inspect fu` → `inspect fuse box`,
  `use scr` → `use screwdriver `, then `o` → `on `. Names offered are only things the player can
  see in the room right now, things carried, and `door`. **Never items hidden in closed
  containers**: completion must not give a puzzle away. ↑ recalls earlier commands (readline).
- Ctrl-C and Ctrl-D quit, as before, and are not shown.
- The lamp flicker (5.6) redraws picture rows while the player types; it never moves the
  cursor or touches the typed text.

## 4. Inspect view

`inspect <thing>` (short `x <thing>`) works on every item (in the room or carried), every
container and the door. Hidden items (inside a closed container) get the usual
`✗ There is no key here.`

```
╭──────────────────────────────────────── SCREWDRIVER ─────────────────────────────── 3 moves ─╮
│                                                                                              │
│                                                                                              │
│                                                                                              │
│                                                    ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄         │
│                                                   ▄█▓█▓▒▓█▓█▒█▓█▓▒▓█▓█▒█▓█▓▒▓█▓█▒█▓█▄        │
│                                                   █████▓████▓████▒████▓████▓████▓████        │
│                                                  ██████▓████▒████▓████▒████▓████▒█████       │
│                                                 ▄██████▒████▓████▒████▓████▒████▓█████▄      │
│                                                 ██▓█▓█▓▒▓█▓█▒█▓█▓▒▓█▓█▒█▓█▓▒▓█▓█▒█▓█▓██      │
│                                                 █▓█▓█▓█▒█▓█▓▒▓█▓█▒█▓█▓▒▓█▓█▒█▓█▓▒▓█▓█▓█      │
│        █▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▓▓▓░▓▓▓▓▒▓▓▓▓░▓▓▓▓▒▓▓▓▓░▓▓▓▓▓▓      │
│   ▒▒▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░▓▓▓▓▒▓▓▓▓░▓▓▓▓▒▓▓▓▓░▓▓▓▓▒▓▓▓▓▓▓      │
│   ░▒▒▒▒▓░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒▒▓▒▓▒▓▒▒▒▓▒▓░▓▒▓▒░▒▓▒▓░▓▒▓▒▒▒▓▒▓░▓▒▓▒▓▒      │
│        ▓                                        ▒▒▓▒▓▒▓░▓▒▓▒░▒▓▒▓░▓▒▓▒▒▒▓▒▓░▓▒▓▒░▒▓▒▒▒▒      │
│                                                 ░▒░▒▒▒▒░▒▒▒▒░▒▒▒▒░▒▒▒▒░▒▒▒▒░▒▒▒▒░▒▒▒▒▒░      │
│                                                  ░▒░▒▒▒ ▒▒▒░ ▒▒░▒ ▒░▒▒ ░▒▒▒ ▒▒▒░ ▒▒░▒░       │
│                                                 ▀ ░░░░░ ░░░░ ░░░░ ░░░░ ░░░░ ░░░░ ░░░░ ▀      │
│                                                                                              │
│                                                                                              │
│                                                   ▀                                 ▀        │
│                                                    ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀         │
│                                                                                              │
│                                                                                              │
│                                                                                              │
╰─ Enter returns to the room ──────────────────────────────────────────────────────────────────╯
  A flat-head screwdriver with a ribbed amber handle. The tip is worn bright from use.



╭──────────────────────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮  ╭────────────╮
│ Look    l     Inspect x      │  │      ▗▄▄▄▖ │  │ ▜▙      ▟▛ │  │    ▄██▄    │  │            │
│ Open          Take    get    │  │ ╺━━━━▐█▓▒▌ │  │  ▐▓▓▓▒▒▒▌  │  │   ▐█▓▓▒▌   │  │            │
│ Drop          Use            │  │      ▐▓▒░▌ │  │  ▐▒▒▒░░░▌  │  │    ▀▓▒▀    │  │            │
│ Help    ?     Quit    q      │  │      ▝▀▀▀▘ │  │ ▟▛      ▜▙ │  │     ▒░     │  │            │
│                              │  │screwdriver │  │   wrench   │  │ flashbulb  │  │            │
╰──────────────────────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯  ╰────────────╯

  » You open the toolbox. Inside: screwdriver, wrench.
  » You take the screwdriver.
  » You look closely at the screwdriver.

  [Electrical Room] > _
```

- **Rows 1-26:** the room panel is replaced by the close-up. Title = the thing's name in upper
  case (`FUSE BOX`, `DOOR`). The move counter stays. The bottom border reads
  `─ Enter returns to the room ─` in LABEL.
- **Rows 2-25:** the close-up picture (92 × 24, section 7), in the frame for the thing's current
  state: a container `closed` / `open`, the door `locked` / `unlocked` / `open`, and any story
  state later (`power on`, `flashed`). Close-ups are where the style goes furthest: one object
  filling the frame, shaded as a solid thing, on a black background. Clues for the mystery live
  here, so clue text inside a close-up uses the PLAIN role and must be readable.
- **Rows 27-29:** the thing's description (its `description` in `world.json`, or the
  container's or door's current sentence). TEXT role.
- **Rows 31-43:** verb panel, inventory, history and prompt stay exactly as in the room.
- **No flicker** while inspecting: a close-up is still.
- **Leaving:** the next input returns to the room, including Enter alone (which adds no history
  entry and no move). That command is applied first, then the room is drawn. Another `inspect`
  shows the new close-up instead.
- **No close-up yet** (art still missing): the room stays on screen and the description rows
  show the thing's description. Nothing breaks.

## 5. The room art

### 5.1 How a picture cell is drawn

Every cell of the picture is either **line art** or **tone**:

- **Line art:** the cell holds a non-space character from `[background]` or from a sprite drawn
  on top. It is drawn as that character. Its colour comes from the light level there
  (section 6).
- **Tone:** the cell is a space. It is drawn from two digits, the surface's **shade** `s` (how
  much light the surface gives back) and the **light** `l` falling on it, both `0`–`9`:

  ```
  t = s × l / 81                         0.0 … 1.0
  t < 0.24          →  " "               true black
  otherwise         →  RAMP[clamp(floor(t × 4 + d), 1, 4)]
  RAMP = " ░▒▓█"
  d    = (BAYER[row mod 4][col mod 4] + 0.5) / 16
  BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
  ```

  `d` is an ordered dither: neighbouring cells round differently, so a smooth fall-off reads as a
  gradient instead of bands. It depends only on the cell's position, so the same room always
  draws the same characters: nothing shimmers between turns.

Rows and columns in the formula count from 0 inside the picture. The whole picture is a pure
function of the art, the room's state and the light map in use, so tests can check it.

### 5.2 Sections of a room art file

Same `[section]` syntax as before.

| Section | Size | Content |
|---|---|---|
| `[background]` | 92 × 24 | Line art only: the back wall's frame, the perspective edges, the lamp and its cable. Spaces are tone cells. |
| `[shade]` | 92 × 24 | One digit `0`–`9` per cell: the surface's shade. A space or a missing row counts as `0`. |
| `[light]` | 92 × 24 | One digit `0`–`9` per cell: the light falling there. A colour letter (`n`, `r`, `f`, `*`, section 7.2) fixes the cell's role instead and counts as `9` for the tone. A space counts as `0`. |
| `[light:<state>]` | 92 × 24 | Optional. Replaces `[light]` while any object in the room is in `<state>` (power-on lighting, 5.5). |
| `[name]`, `[name:<state>]` | its own size | A sprite, line art as before. |
| `[name:shade]`, `[name:<state>:shade]` | same size as its sprite | Optional. Shade digits for the sprite's inside. Spaces inside the sprite's outline with no shade digit are black. |

- `shade` is a reserved word: no state may be called `shade`, and no object `light`.
- Anything but digits in a `[shade]` section, or anything but digits and colour letters in a
  `[light]` section, is an error (`ArtError`), like a too-wide character.
- An art file without `[shade]` draws every tone cell black, so line art alone still works.

### 5.3 Perspective, light and objects

- **Perspective:** a back wall in one-point perspective, side walls and ceiling running to the
  picture's corners, about eight rows of floor in front of the wall.
- **Light by area, not by character.** An object is lit by where it stands: its line art takes
  its colour from the light level of its cells, and its shaded inside uses its own shade digits
  times that light.
- **Size of objects.** Sprites are drawn for the 24-row room, about twice as tall as in the
  11-row version (the door around 12 rows, the fuse box around 6), so they read at the new size.
- **Every interactable object is drawn and shows its state:**

  | Object | Sections |
  |---|---|
  | Container | `[name:closed]`, `[name:open]` (lid or door swung aside), plus story states (`[vent:flashed]`, `[fuse box:power on]`) |
  | Door | `[door:locked]`, `[door:unlocked]`, `[door:open]` (open shows the night skyline, `n` in the light map) |
  | Item | `[name]`, drawn inside its open container or on the floor at its `floor` place, gone once taken |

  Locked and unlocked doors must differ visibly (e.g. a lit keyhole or the bolt drawn back),
  because there is no list of commands to tell the player.
- **Sprites overlap the background:** spaces outside a sprite row's outline are transparent
  (the background's line art and tone show through), spaces inside are opaque (the sprite's own
  shade, or black).
- **Light sources:** line-art cells drawn with `▗▟█▙▖●*ϟ` where the light is `5` or more are
  LIGHT (bold). This applies to line art only, never to tone cells, which use `█` too.
- **The spotlight:** after `open`, `take`, `drop` or `use`, the object that changed is drawn in
  FOCUS for one turn (blank sprite rows excluded). Its characters, line art and tone alike, stay
  the same; only the role changes.
- **Flashbulb flash (E5.2):** a `use` rule with `"flash": true` draws one frame of the picture
  with every light level set to `9` and every cell in PLAIN bold (a white flash) for 0.15 s,
  then the room returns with the object it was used on in FOCUS. The borders, text, panels and
  prompt don't change, so only the picture flashes.

### 5.4 Baking the light (tooling, E7.3)

Nobody types 2,208 digits by hand. `scripts/bake_light.py` is a development tool: it is not in
the package, the game never runs or imports it, and its output is a draft.

- It reads a small **scene file**, kept with the script in `scripts/scenes/` so it is not
  shipped with the game: the surfaces (back wall, side walls, ceiling,
  floor) with a shade each and optional texture (floor planks, wall seams), the lamp's position,
  cone and fall-off, colour letters or levels stamped on rectangles (the night inside the door
  frame, the lamp itself at full light), and the extra light of each light state (the ceiling
  tube for `power on`).
- It prints `[shade]`, `[light]` and `[light:power on]` sections. The author pastes them into
  the art file, then edits them by hand: darkening a corner, lighting the edge of an object.
  The committed art file is the source of truth; the script is never rerun over hand edits
  without looking at the diff.
- Like ascii-art output (CLAUDE.md rule 4), nothing it prints goes into the repo unedited
  without being seen in the real game with pilotty.

### 5.5 Power-on lighting (E5.1)

When the fuse box reaches `power on`, the room switches to `[light:power on]` on that same turn.
A ceiling tube comes on: the whole room lifts to light `5`–`8` (LIT and GLOW), so the corners
that were black now show their walls, the lamp's pool is still the brightest place, and the
door's red light (`r`) stays. The lamp stops flickering (5.6). The fuse box is in FOCUS for that
turn, as for any `use`. This is the visual high point of the room.

### 5.6 Lamp flicker (E5.3)

While the game waits for input in the room view and the power is off, the lamp flickers now
and then:

- A **dip** draws the picture with every light digit lowered by 2 (never below 0; colour
  letters unchanged) for 70 ms, then draws it normally again.
- A **flicker** is one dip, or two dips 70 ms apart (the light is normal for 70 ms between
  them). Flickers come at random intervals of 3 to 8 seconds. At most 3 dips in any 10
  seconds: never a strobe. The interval alone does not keep to that (flickers 3 seconds apart
  with two dips each would make 8), so the schedule remembers its dips: a flicker that would
  make a fourth within 10 seconds loses its second dip or waits.
- Only the picture rows (2-25) are redrawn. The cursor's position and the text being typed are
  saved and restored, so typing is never disturbed.
- **No flicker** when: inspecting, the power is on, the room has `"flicker": false` (5.7),
  colour is off (section 6), stdout is not a terminal, `TERM=dumb`, the screen is too small,
  or `play --no-motion` is passed.
- `dimmed(light, by)` (lower every digit), `flicker_wanted` and the schedule that picks the
  next flicker are pure code in `art.py` and tested. The timer lives in `terminal.py`: a thread
  that only writes picture rows rendered beforehand. It stops when the player's line is
  entered, on a resize and on exit.

### 5.7 Rooms after the first (E8)

The way out runs through three rooms, one after the other: **Electrical Room → Darkroom →
Night Office → the street**. Doors are one-way: once through, the player never goes back.

- **Entering a room.** `open door` on a door that leads on counts as a move and shows
  `» The door opens. You step into the Darkroom.` The same turn draws the new room: its name in
  the top border, its picture and description. The move counter, the inventory slots and the
  message history carry on. Nothing is in FOCUS. Only the last room's door wins.
- **Each room has its own light.** Every room is drawn with the same rules (5.1-5.3) and has
  its own art file, scene file (5.4) and `[light:<state>]` maps. Any container state can
  switch the map, not only `power on`:

  | Room | Light | Flicker | High point |
  |---|---|---|---|
  | Electrical Room | amber lamp | yes, until the power is on | `[light:power on]` |
  | Darkroom | red safelight, `"light": "red"` (section 6) | no: a safelight burns steady | the enlarger's white beam, `[light:focused]` / `[light:printed]` in `f` (PLAIN) |
  | Night Office | neon through the blinds in `n` stripes, plus an amber lantern | no: a dip lowers light digits only, so the `n` neon would not change | `[light:lit]`: the lantern lights the room |

- **`"flicker"`** (room, default `true`) switches the flicker off for a room whose light is
  steady. `flicker_wanted` reads it (5.6).
- **`"light"`** (room, `"amber"` by default or `"red"`) picks the colour of the LIT, GLOW and
  LIGHT roles in that room's picture (section 6). Icons and close-ups keep the amber scale.
- **The carry guard.** A door can list `"carry": ["wrench"]`: tools the next room needs. While
  one of them is not in the inventory, `open door` is refused and doesn't count as a move:
  `✗ You'll want the wrench where you're going.` So the player can't get stuck behind
  a one-way door. `build_world` checks that each carried name exists in this room or an earlier
  one, that the next room uses it, and that the last door carries nothing.
- **A door that leads on** has `[door:open]` drawn as a dark doorway, not the night: the night
  belongs to the last room's door.

## 6. Palette

256-colour ANSI (`38;5;n`), foreground only, never a background. It works in macOS Terminal.app,
which has no truecolor. **Dark themes only** (section 2). Every colour keeps **at least 3:1
contrast on pure black** (WCAG formula). Text that matters most uses the terminal's own
foreground, which always has full contrast.

The picture's colour follows the **light level** of each cell, on one cold-to-warm scale:

| Light | Role | Colour | Hex | On black |
|---|---|---|---|---|
| `0`–`2` | `SHADOW` | 60 | `#5f5f87` | 3.5 |
| `3`–`4` | `DUSK` | 96 | `#875f87` | 4.0 |
| `5`–`7` | `LIT` | 136 | `#af8700` | 6.3 |
| `8`–`9` | `GLOW` | 178 | `#d7af00` | 10.0 |

All roles:

| Role | Used for | Colour | Hex | On black | Weight | No colour |
|---|---|---|---|---|---|---|
| `TITLE` | Room or thing name in the border | default | | | bold | bold |
| `BORDER` | Room panel, verb panel and slot frames | 243 | `#767676` | 4.6 | normal | dim |
| `SHADOW` | Picture cells at light `0`–`2`; colour letters ` ` `.` `s` `0`–`2` | 60 | `#5f5f87` | 3.5 | normal | dim |
| `DUSK` | Picture cells at light `3`–`4`; colour letters `3` `4` | 96 | `#875f87` | 4.0 | normal | dim |
| `LIT` | Picture cells at light `5`–`7`; colour letters `#` `5`–`7` | 136 | `#af8700` | 6.3 | normal | normal |
| `GLOW` | Picture cells at light `8`–`9`; colour letters `8` `9` | 178 | `#d7af00` | 10.0 | normal | normal |
| `LIGHT` | Light sources (lamp, bulb, stars, 5.3); colour letter `*` | 221 | `#ffd75f` | 15.1 | bold | bold |
| `NIGHT` | The night outside: open door, skyline, ending picture; letter `n` | 32 | `#0087d7` | 5.4 | normal | normal |
| `DANGER` | Warning marks and danger in art; letter `r` | 160 | `#d70000` | 3.9 | normal | normal |
| `PLAIN` | Art in the terminal's own colour: metal, paper, clue text; letter `f` | default | | | normal | normal |
| `FOCUS` | Spotlight: the object or slot the last command changed | default | | | bold | bold |
| `TEXT` | Description rows | default | | | normal | normal |
| `VERB` | Verbs, item names in slots | default | | | normal | normal |
| `LABEL` | Short forms, `Help` / `Quit`, move counter, hints | 243 | `#767676` | 4.6 | normal | dim |
| `RESULT` | Newest `»` entry | default | | | bold | bold |
| `ERROR` | Newest `✗` entry | 160 | `#d70000` | 3.9 | bold | bold |
| `WIN` | `✓` lines | 32 | `#0087d7` | 5.4 | bold | bold |
| `HISTORY` | Older history entries | 243 | `#767676` | 4.6 | normal | dim |
| `NARRATION` | Intro text | default | | | italic | italic |
| `PROMPT` | `[Room] > ` | default | | | bold | bold |

Rules:

- **Never colour alone.** Result, error and win are told apart by `» ✗ ✓`; light and shadow by
  the shading itself (`░` against `█`) and by weight in the fallback; the spotlight by bold.
- **Colour off** (fallback column) when any of these holds: the `NO_COLOR` environment variable
  is set and not empty, `play --no-color` is passed, `TERM=dumb`, or stdout is not a terminal.
  The shading characters stay; only colour goes.
- **No dim on colour.** Dim on top of a colour can vanish on some themes, so coloured roles
  never use it; dim is only used in the fallback.
- **No truecolor upgrade.** Colours are the 256 numbers above even where truecolor exists, so
  the game looks the same everywhere. On a 16-colour terminal rich picks the nearest colour.
- **Hues.** The light scale (SHADOW → DUSK → LIT → GLOW, with LIGHT at its top) is one
  cold-to-warm family. Besides it, only grey, plus red or blue as accents, are on screen.
  The exception is a room with `"light": "red"` (5.7): its LIT, GLOW and LIGHT turn red
  (table below). SHADOW and DUSK don't change, so shadow looks the same in every room.
  DANGER (160) is not part of the red scale, so `r` marks still stand out.

  | Light (red room) | Role | Colour | Hex | On black |
  |---|---|---|---|---|
  | `5`–`7` | `LIT` | 167 | `#d75f5f` | 5.7 |
  | `8`–`9` | `GLOW` | 203 | `#ff5f5f` | 7.1 |
  | `*` | `LIGHT` | 210 | `#ff8787` | 9.1 |
- **Dark-grey themes.** On a typical dark-grey background (`#1e1e1e`) SHADOW drops to 2.8:1.
  That is accepted: shadow is meant to recede, and nothing the player must read is SHADOW.
- Every art character is exactly one cell wide; `parse_art` and `parse_picture` reject anything
  else (`ϟ`, not `⚡`). Terminals that can't show UTF-8 get the ASCII fallback: `░` → `:`,
  `▒` → `%`, `▓` and `█` → `#`.

## 7. Picture files: icons and close-ups

### 7.1 Format

One plain UTF-8 text file per picture, in the same `[section]` syntax as the room art:

```
[closed]
┌──────────┐
│ ▫  ϟ   ▫ │
└──────────┘

[closed:colors]
444444444444
44 44r 44 44
444444444444

[closed:shade]

 5555555555
 4444444444

[open]
...
```

- Each `[state]` section is one **frame**. The **first frame is the default**: it is drawn when
  the object's current state has no frame of its own. A picture with one look needs only one
  frame (name it `[default]`).
- Each frame may have a `[state:colors]` map: one letter per cell (7.2). A missing map or a
  blank cell means SHADOW.
- Each frame may have a `[state:shade]` map: one digit `0`–`9` per cell. Cells that are spaces
  in the frame are drawn as tone with `t = shade / 9` and the same ramp, dither and black
  threshold as the room (5.1). Pictures have no light map: their light is already in the shade
  digits, and their colour comes from the colour letters.
- Frames and maps must fit in the picture's size and are padded with spaces to exactly that
  size. Leading blank lines count (they push the drawing down); trailing ones don't.
- Every character must be one cell wide.

- Like the room's maps, a close-up's shading is drafted by a script and then edited by hand:
  `scripts/bake_closeup.py` draws the handle and the shaft as cylinders lit from the top left
  (Lambert, plus a highlight on the steel, a darker rib every fifth handle column) and prints
  the `[default]`, `[default:colors]` and `[default:shade]` sections. It is a development tool
  outside the package, and its output is a draft.

| Kind | Size | Where it shows | `world.json` field |
|---|---|---|---|
| Icon | **10 × 4** | Inventory slot (3.4) | `icon` on items |
| Close-up | **92 × 24** | Inspect view (4) | `closeup` on items, containers and the door |
| Portrait | 44 × 18 (E6) | Intro screen (8) | top-level `portrait` (not built yet) |
| Ending | 92 × 24 (E6) | Ending screen (9) | top-level `ending_art` (not built yet) |

### 7.2 Colour letters

| Letter | Role |
|---|---|
| space, `.`, `s`, `0` `1` `2` | SHADOW |
| `3` `4` | DUSK |
| `#`, `5` `6` `7` | LIT |
| `8` `9` | GLOW |
| `*` | LIGHT |
| `n` | NIGHT |
| `r` | DANGER |
| `f` | PLAIN (the terminal's own foreground; use it for clue text) |

The digits are the room's light levels, so an icon and the room it came from use the same scale.

### 7.3 State names

Frames are picked by the object's state name: containers `closed` / `open`; the door `locked` /
`unlocked` / `open`; anything else is a story state chosen in E1 (`power on`, `flashed`, …).
Section names are lower case, digits, spaces and `:`. `colors` and `shade` are reserved
suffixes, never state names.

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
| A frame or map is bigger than its kind's size, a wide character, an unknown colour letter, a non-digit in a shade map, a map with no frame, a file with no frame | `Error: <file>: …`, exit 1 |
| `icon` names a close-up-size file or the other way round | `Error: … needs icon size (10x4), but … is close-up size`, exit 1 |
| A portable item has no `icon` | `check` prints `Warning: item "wrench" has no icon.`, exit 0 |
| An item, container or door has no `closeup` | `Warning: container "toolbox" has no close-up.`, exit 0 |

Missing art is a warning while the art is being drawn (E2.4, E3.2). E1.6 may turn it into an
error once every object has its pictures.

## 8. Intro screen (E6, not built)

Shown once at launch, before the room. Same 96 × 43 block, no border: the portrait is the frame.
The layout below is 27 rows tall and sits centred in the block, on rows 9-35; the rows above
and below it are blank. Row numbers below count from the top of the layout.

```
row    region
 1     (blank)
 2-19  portrait, 44 × 18, centred (cols 27-70)
20     (blank)
21-24  intro text from world.json, up to 4 rows, 64 wide, block centred (cols 17-80), NARRATION
25     (blank)
26     Press Enter to begin       centred, PROMPT
27     q quits                    centred, LABEL
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
  side, drawn in the tonal style (shade map, LIT and GLOW on the lit side), the rest of the face
  falling into true black, the background empty. One frame, in the picture format (7), kind
  "portrait". The art is drawn in E6.1.
- Enter starts the game. `q`, `quit`, Ctrl-C and Ctrl-D quit with "Goodbye.". Anything else is
  ignored. The intro is not a move.

## 9. Ending screen (E6, not built)

Replaces the v0.5 win screen. Drawn at the top of the block (rows 1-35) so the panel doesn't
jump; rows 36-43 stay blank.

```
row    region
 1     border: ESCAPED as title, final moves in the corner
 2-25  ending picture 92 × 24: the open door and a wet city skyline (NIGHT, rain in SHADOW)
26     border
27-29  ending text from world.json, 3 rows, NARRATION
30     (blank)
31     ✓ Escaped in 11 moves. Par is 8.      WIN
32     (blank)
33     Enter  play again     q  quit         keys in PROMPT, words in LABEL
34     (blank)
35     > _                                   PROMPT
```

```
╭────────────────────────────────────────── ESCAPED ──────────────────────────────── 11 moves ─╮
│                                                                                              │
│        ending picture 92 × 24: the open door, wet city skyline at night (night blue)         │
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

As the main screen, with `0 moves`, four empty slots and the one-line hint on row 41 (3.5).

### Errors

Same place as any result (newest history entry), so the eye doesn't have to look for it. The
rest of the screen doesn't change. Errors are states, not crashes.

```
  ✗ I don't know how to "dance". Type "help" for the verbs.
  ✗ Take what?
  ✗ The fuse box is locked.
  ✗ Your hands are full. Drop something to take the flashbulb.
  ✗ You'll want the wrench where you're going.
```

### Full inventory

All four slots filled. Taking a fifth item gives the error above; nothing else changes.

### Help

```
  » Verbs: look (l), inspect (x), open, take (get), drop, use … on …, inventory (i),
    help (?), quit (q). Tab completes names.
```

### Too small

Below 100 × 44 the whole screen is replaced by three lines, **centred both ways** in the actual
terminal:

```
                     Make the window bigger
             The game needs 100 × 44. It is now 80 × 24.
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

## 11. What changed

From v0.5 to the colour screen (E2, E4):

| v0.5 | Colour screen |
|---|---|
| 80 × 24, block 76 × 23, art 72 × 10 | 100 × 30, block 96 × 29, picture 92 × 11 |
| `Carrying (n/4): …` in the bottom border | 4 icon slots beside a verb panel |
| `Try  open toolbox · …` hints | Removed. Verb panel lists verbs only |
| One last result, 2 rows | History of 2-3 entries, newest bold |
| Intro in the result area | Intro screen with portrait (planned, E6) |
| Win screen with the ending text | Ending screen with moves and par, play again (planned, E6) |
| Black and white | 256-colour noir; black and white is the fallback |
| Resize noticed after the next command | Redraw on resize |

From the colour screen to tonal art (E7, E5.1, E5.3):

| Colour screen | Tonal art |
|---|---|
| 100 × 30, block 96 × 29, picture 92 × 11 | 100 × 44, block 96 × 43, picture 92 × 24 |
| Line art, light map on or off (`#`) | Line art plus `░▒▓█` tone (shade × light, dithered), light levels `0`–`9` |
| Two light colours (slate, amber) | Light scale SHADOW, DUSK, LIT, GLOW, LIGHT |
| Shadow drawn as dim characters | Deep shadow is true black |
| Icons 8 × 3, panels 6 rows | Icons 10 × 4 with shading, panels 7 rows |
| Readable on light and dark themes | Dark themes only |
| A still room | Lamp flicker; power-on lighting when the fuse goes in |

## 12. Checked by tests

Built (E0.2, E2, E4), with sizes updated by E7.2:

| Rule | Test |
|---|---|
| Picture frames are padded to exactly their kind's size | `test_art.py` |
| Too big, wide characters, unknown colour letters, a map without a frame are errors | `test_art.py` |
| An unknown state falls back to the first frame | `test_art.py` |
| The example icon and close-up load at 10 × 4 and 92 × 24 | `test_art.py` |
| Every item has a 10 × 4 icon; every icon character has an ASCII stand-in of the same width | `test_screen.py` |
| `dimmed(light, by)` lowers every digit, never below 0, and leaves colour letters alone; a dip changes only the picture's rows and no colour-letter cell | `test_art.py`, `test_screen.py` |
| Flicker: never more than 3 dips in any 10 s, over 10 minutes for 30 seeds and in the worst case; flickers 3 to 8 s apart, one or two dips | `test_art.py` |
| Flicker: off when inspecting, power on, no colour, not a terminal, `TERM=dumb`, too small or `--no-motion` | `test_art.py`, `test_terminal.py`, `test_cli.py` |
| Flicker: only picture rows are written, never the prompt's; the cursor is saved and restored; a dip is always put right; the thread is a daemon and stops | `test_terminal.py` |
| A light bake: every section 92 × 24, cells digits or colour letters, the lamp's cells at 9, power-on light at least the ambient level, two bakes identical | `test_bake_light.py` |
| The close-up draft loads at 92 × 24 and is the same on every run; handle colours are light digits `5`-`9`, steel `f`, the cast shadow `1`; every fifth handle column is darker | `test_bake_closeup.py` |
| `icon` / `closeup` must name a loaded file of the right kind | `test_world.py` |
| Missing icons and close-ups are listed; scenery needs no icon | `test_world.py` |
| `check` warns about missing pictures and exits 0; a bad picture exits 1 | `test_cli.py` |
| Every row of every screen is at most 96 cells; the screen block is exactly 43 rows | `test_screen.py` |
| Every screen in a full playthrough has the same height, in the room and inspecting | `test_screen.py` |
| The flash turns every picture cell to PLAIN bold at light 9 and leaves every other row as it was | `test_screen.py` |
| The verb panel is the same in every state and names no object | `test_screen.py` |
| Slots show icon and name; empty slots are empty frames; long names end in `…` | `test_screen.py` |
| History keeps the newest at the bottom, at most 3 rows | `test_screen.py` |
| Tab never offers an item inside a closed container | `test_screen.py` |
| Move counter text and position in the border | `test_screen.py` |
| Every role has a colour and a no-colour style; colours are the palette's, never dim, same weight as the fallback | `test_terminal.py` |
| Colour prints as 256-colour codes, never truecolor; piped output has no colour | `test_terminal.py` |
| `NO_COLOR` and `--no-color` give the fallback | `test_terminal.py`, once E4.3 is built |

Added with E7, E5.1 and E5.3:

| Rule | Test |
|---|---|
| The tone formula: black below 0.24, ramp `░▒▓█` above, Bayer dither by position, same output every call | `test_art.py` |
| `[shade]` and `[light]` accept only digits (and colour letters in `[light]`), must fit 92 × 24, missing cells are `0` | `test_art.py` |
| A sprite's shade map must match its sprite's size; spaces inside the outline without shade are black | `test_art.py` |
| `[light:<state>]` replaces `[light]` while an object in the room is in that state | `test_art.py` |
| Picture shade maps: digits only, padded to size, tone only where the frame has a space | `test_art.py` |
| Every tone cell is one of ` ░▒▓█`; every line-art cell keeps its background or sprite character | `test_screen.py` |
| Light level picks SHADOW / DUSK / LIT / GLOW; LIGHT only on line-art light sources | `test_screen.py` |
| Colour letters `0`–`9` map to the same roles as light levels | `test_screen.py` |
| Every palette colour has at least 3:1 contrast on black (computed from its hex) | `test_terminal.py` |
| The real screen at 100 × 44 and 140 × 50, too small, resize, power on, a flicker during typing (`TEXT_ADVENTURE_FLICKER_EVERY=1` shortens the wait) | pilotty, before each merge |

Added with E8 (more rooms):

| Rule | Test |
|---|---|
| A door that leads on moves the player into the next room; only the last door wins | `test_game.py` |
| The carry guard refuses `open door` without the tool and it is not a move; with it, the door opens | `test_game.py` |
| `carry` must name an item in this room or an earlier one that the next room uses; the last door carries nothing | `test_world.py` |
| `"flicker": false` turns the flicker off; `"light"` is `amber` or `red` | `test_art.py`, `test_world.py` |
| In a red room LIT, GLOW and LIGHT use the red colours, each at least 3:1 on black | `test_screen.py`, `test_terminal.py` |
| A bake with several lamps, and lamps in a light state; the electrical scene bakes as before | `test_bake_light.py` |
| The built-in world is won in par through all three rooms | `test_solve.py`, `test_game.py` |
| Entering each room, the red darkroom, the enlarger beam, the lantern, the carry refusal, the win | pilotty, before each merge |
