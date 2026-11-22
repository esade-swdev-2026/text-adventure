# Product backlog

Planned features after version 0.5 (one room, playable from start to win).

**Size:** S = under an hour · M = a few hours · L = a day or more (usually because of art).
**Priority:** Must · Should · Could.

Rule from `CLAUDE.md`: every item that changes the screen starts by updating
`docs/SCREEN-SPEC.md`, and is checked in the real game with pilotty before it is done.
ascii-art output is only a draft and is edited by hand before it goes into the repo.

---

## E0 · Enablers

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E0.1 | **New screen spec** | Rewrite `docs/SCREEN-SPEC.md` for the new layout (room, verb panel, inventory icons, inspect view, intro, ending) and the colour palette. Decide the minimum terminal size: 80×24 may be too small once the verb panel and icons are added, so check whether 100×30 is needed. | M | Must | — |
| E0.2 | **Sprite format for icons and close-ups** | One file format for small inventory icons and large close-up drawings, with colour roles, loaded the same way as the room art. `check` reports any item that has no icon or close-up. | M | Must | E0.1 |

## E1 · Interaction and puzzles

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E1.1 | **Inspect command** | `inspect <thing>` (short form `x`) works on every item, container and door, whether it is in the room or carried. The main panel switches from the room to a close-up of that thing (see E3). This is where clues about the mystery and the way out are found. | M | Must | E0.2 |
| E1.2 | **Use command** | `use <item>` and `use <item> on <thing>`. Each object in `world.json` lists what it reacts to and what happens: it changes state, reveals an item or unlocks something. Using an item that does nothing gives a short, in-world refusal. | M | Must | — |
| E1.3 | **Every item matters** | Fuse in the fuse box brings the power back. Flashbulb shows something hidden in the dark. Wrench opens a second container (e.g. a vent). There are no useless decoy items. | M | Must | E1.2 |
| E1.4 | **Longer puzzle chain** | Rework `world.json` so the way out takes 3–4 steps that build on each other, with clues found through inspect (e.g. power → keypad → code seen in a close-up). Target length is about 12–15 moves instead of 5. | M | Must | E1.1, E1.3 |
| E1.5 | **Move counter and par** | Count moves that change the game (typos, `help` and `look` don't count). The win screen shows "Escaped in 11 moves (par 8)". Par is set in `world.json`. | S | Should | — |
| E1.6 | **`check` validates the new rules** | `text-adventure check` also confirms that every `use` target exists, every object has its art, and the world can still be won. | S | Should | E1.2, E0.2 |

## E2 · Main screen layout (verb panel and inventory)

The layout follows the classic point-and-click split: the room on top, and below it a verb panel on
the left and the inventory as pictures on the right. The game no longer tells the player what to do
next. The player has to look at the room and choose a verb and a thing.

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E2.1 | **Remove the "Try" line** | No more ready-made commands such as `open toolbox · take screwdriver`. The room drawing and description are the only source of what can be interacted with. | S | Must | E2.2 |
| E2.2 | **Verb panel** | A fixed grid under the room listing the verbs on their own: Look, Inspect, Open, Take, Drop, Use, plus Help and Quit. It never names objects, so it can't give puzzles away. Typing stays the main way to play, and Tab completion keeps working. | M | Must | E0.1 |
| E2.3 | **Inventory as icons** | The inventory moves from a sentence in the border to a grid of 4 slots next to the verb panel. Each slot shows the item's little picture with its name underneath, and empty slots are drawn as empty frames. | M | Must | E0.2, E2.4 |
| E2.4 | **An icon for every item** | Each item in `world.json` gets a small drawing (about 6×3 characters) used in the inventory. | M | Must | E0.2 |
| E2.5 | **Visible objects in the room** | Every object you can interact with is clearly drawn in the room art and changes when its state changes (toolbox open/closed, fuse box open, door locked/unlocked/open), so the room shows what is possible without a list. | M | Must | — |
| E2.6 | **Short message history** | Show the last 2–3 results under the room: the newest one bold, older ones dim. | S | Should | E0.1 |
| E2.7 | **Move counter in the frame** | The move count sits in a corner of the room border, like a stopwatch (`11 moves`). | S | Should | E1.5 |
| E2.8 | **Terminal-too-small screen** | Below the minimum size, show a centred "Make the window bigger" message instead of a broken layout, and redraw on resize. | S | Should | E0.1 |
| E2.9 | **Clickable verbs and items** | Clicking a verb, then an object or inventory icon, builds the command, using the terminal's mouse support. Typing still works. | L | Could | E2.2, E2.3 |

## E3 · Inspect view (close-ups)

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E3.1 | **Close-up panel** | While inspecting, the room panel is replaced by a large drawing of the thing, with its name in the border and a short description below. The next command returns to the room. The verb panel and inventory stay visible. | M | Must | E1.1, E0.2 |
| E3.2 | **Close-up art for every object** | A close-up drawing for each item, container and the door, with a state version where it matters (e.g. the fuse box closed and open, a keypad dark and lit). | L | Must | E3.1 |
| E3.3 | **Clues in the close-ups** | Clues for the puzzle chain and the story are written into the close-ups: scratched numbers, a note, a name on a tag, a missing screw. Some only appear after a change (e.g. power on, flashbulb used). | M | Must | E3.2, E1.4 |

## E4 · Colour

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E4.1 | **Colour palette** | The noir style moves to a coloured version. Dark blues and greys for the room in shadow, warm amber for the lamp and everything in its light, red for errors and danger, and a cold blue for the night outside the door. Icons and close-ups use the same palette. 256 colours, so it works in macOS Terminal. | M | Must | E0.1 |
| E4.2 | ~~**Readable on any theme**~~ | Built, then **replaced by E7**: tonal shading draws light as ink, so the game is now for dark themes only (SCREEN-SPEC §2, §6). Bold and dim stay alongside colour as a fallback. | S | Must | E4.1 |
| E4.3 | **Colour off switch** | Respect the `NO_COLOR` environment variable and add a `--no-color` flag. Without colour, the game falls back to the current black-and-white style. | S | Should | E4.1 |

## E5 · Lighting and key moments

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E5.1 | **Power-on lighting** | When the fuse is fixed, the light spreads across the room: most of it turns from shadow to amber, and the lamp stops swinging. This is the visual high point of the room. Built in E7.3 as a second baked light map, `[light:power on]` (SCREEN-SPEC §5.5); the lamp stops flickering (E5.3). | M | Should | E1.3, E4.1, E7.3 |
| E5.2 | **Flashbulb flash** | Using the flashbulb shows one fully lit, white frame, then the room returns to normal with the newly found thing highlighted. | S | Should | E1.3 |
| E5.3 | **Lamp flicker** | While the player thinks, the lamp dips now and then: the pool of light darkens for a moment and comes back, without disturbing what is being typed. Never a strobe; off without colour, while inspecting, once the power is on, or with `--no-motion` (SCREEN-SPEC §5.6). Built: the timing and the 3-dips-in-10-seconds cap are pure code in `art.py`; a thread in `terminal.py` draws the dips. | M | Could | E7.2 |

## E6 · Intro and ending

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E6.1 | **Intro screen with portrait** | When the game launches, it shows the face of a beaten-up man before the room: scars across his face, eyes wide open, drawn in noir style (hard light on one side, the rest in shadow, in the game's palette). Under the portrait, a short text introduces the story and the situation. Ends with "Press Enter to begin". | L | Must | E0.1, E4.1 |
| E6.2 | **Ending screen** | A dedicated win screen: the open door with the wet city skyline from the ending text, the move count against par, and "play again / quit". | M | Should | E1.5, E4.1 |

## E7 · Tonal art

The look of tonal ASCII artwork (pictures built from a density ramp), kept readable: line art
for walls and every object you can use, `░▒▓█` shading for surfaces and light. Agreed after a
prototype; see SCREEN-SPEC §1, §2, §5, §6 and §7.

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E7.1 | **Spec** | SCREEN-SPEC rewritten for the 92 × 24 picture, the 96 × 43 screen, tone cells, light levels, 10 × 4 icons and dark themes only. | S | Must | |
| E7.2 | **Tone engine** | Parse `[shade]`, light levels `0`–`9`, `[light:<state>]` and shade maps for sprites and pictures; draw each cell as line art or dithered tone; the graded light roles and their styles; the new sizes. Ships with a placeholder room so the game keeps running. README and ARCHITECTURE updated. | M | Must | E7.1 |
| E7.3 | **Room art and light baking** | `scripts/bake_light.py` and a scene file bake the shade and light maps as a draft; the electrical room is redrawn at 92 × 24 with sprites about twice as tall, then edited by hand and checked with pilotty. | L | Must | E7.2 |
| E7.4 | **Close-up and icons** | The screwdriver close-up redrawn at 92 × 24 as a fully shaded object; the five icons redrawn at 10 × 4 with shading. Built: the close-up is drafted by `scripts/bake_closeup.py` (SCREEN-SPEC §7.1), then edited by hand. | M | Must | E7.2 |

## E8 · More rooms

Two more rooms at the Electrical Room's level: about 12 moves each, a tool-locked container, a
story state with `needs`, a hidden item revealed by a `use`, a key and a condition on the door,
92 × 24 tonal art with baked light, 10 × 4 icons and a close-up. Electrical Room → Darkroom →
Night Office → the street. Each room needs one tool from the room before (SCREEN-SPEC §5.7).

| ID | Feature | Description | Size | Priority | Depends on |
|---|---|---|---|---|---|
| E8.1 | **Spec** | SCREEN-SPEC §5.7: entering a room, light colour and flicker per room, the carry guard; the red light scale in §6. | S | Must | |
| E8.2 | **Engine** | `carry` on doors (refuse to leave a needed tool behind, checked by `build_world`), `flicker` and `light` per room, several lamps in `scripts/bake_light.py`. | M | Must | E8.1 |
| E8.3 | **Darkroom** | Red safelight, no flicker. Wrench opens the cabinet; lens and negatives in the enlarger print a photograph; the photo shows where V. hid the padlock key; tongs reach behind the hot safelight. Art, four icons, the photograph close-up. | L | Must | E8.2 |
| E8.4 | **Night Office** | Neon through the blinds. Tongs fish a matchbook from behind the radiator; the lantern lit shows the shutter key; the coat, desk and alarm panel open in turn; the street door wins. Art, four icons, the matchbook close-up. Par 36. | L | Must | E8.3 |

---

## Suggested order

1. **Spec and formats:** E0.1, E0.2
2. **Core mechanics:** E1.1, E1.2, E1.3, E1.5
3. **New layout:** E2.1–E2.5, E3.1, E4.1, E4.2
4. **Content:** E2.4 icons, E3.2 close-ups, E1.4 + E3.3 puzzle chain and clues
5. **Polish:** E6.1 intro, E5.1, E5.2, E6.2, E2.6–E2.8, E4.3, E1.6
6. **Tonal art:** E7.1, E7.2, E7.3 + E7.4, then E5.1 power-on and E5.3 flicker
7. **More rooms:** E8.1, E8.2, E8.3, E8.4
8. **Stretch:** E2.9 clickable verbs

## Open questions

- **Terminal size:** the room, verb panel and icon grid have to fit together. Decide in E0.1 whether the
  minimum stays 80×24 or grows.
- **Discoverability:** without the "Try" line, players who get stuck have no help. Consider a `hint`
  command later if playtests show this.
