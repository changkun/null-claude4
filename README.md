# Cellular Automaton — Terminal Simulator

A single-file Python implementation of cellular automata that runs in the terminal using `curses`. No external dependencies. Ships with 8 preset rulesets (Conway's Life, HighLife, Day & Night, Seeds, Diamoeba, Morley, 2x2, Maze) and supports arbitrary rules via B/S notation.

## Usage

```bash
python3 life.py                                    # default glider pattern
python3 life.py --pattern gosper                   # gosper glider gun
python3 life.py --pattern pulsar                   # period-3 oscillator
python3 life.py --pattern random                   # random initial state
python3 life.py --rows 60 --cols 120 --speed 0.2   # custom grid and speed
python3 life.py --load spaceship                   # load a saved pattern by name
python3 life.py --load ~/patterns/my.cells         # load from a file path
python3 life.py --rule highlife --pattern random    # HighLife ruleset
python3 life.py --rule daynight                    # Day & Night ruleset
python3 life.py --rule B2/S                        # custom rule via B/S notation
python3 life.py --script probabilistic_life        # run a user script on startup
python3 life.py --script ~/my_script.py            # run a script from a file path
```

### Options

| Flag        | Default   | Description                          |
|-------------|-----------|--------------------------------------|
| `--rows`    | 40        | Grid height                          |
| `--cols`    | 80        | Grid width                           |
| `--speed`   | 0.1       | Delay between generations (seconds)  |
| `--pattern` | `glider`  | One of: `glider`, `pulsar`, `gosper`, `random` |
| `--load`    | —         | Load a `.cells` or `.rle` file (path or name from `~/.life-patterns/`) |
| `--rule`    | `life`    | Rule preset or B/S notation (e.g. `B36/S23`) |
| `--script`  | —         | Run a Python script on startup (path or name from `~/.life-scripts/`) |

### Controls

| Key       | Action                            |
|-----------|-----------------------------------|
| `Space`   | Pause / resume                    |
| `+` / `-` | Speed up / slow down             |
| `n`       | Step one generation (when paused) |
| `r`       | Randomize the grid                |
| `R`       | Cycle to next ruleset             |
| `e`       | Enter editor mode (auto-pauses)   |
| `g`       | Toggle population stats panel     |
| `d`       | Toggle pattern detection overlay  |
| `G`       | Export history as animated GIF    |
| `L`       | Load and run a script             |
| `[`       | Rewind one generation (auto-pauses) |
| `]`       | Forward one generation through history |
| `b`       | Jump to beginning of recorded history |
| `q`       | Quit                              |

### Editor Mode

Press `e` to enter an interactive cell editor. The simulation pauses and a cursor appears on the grid (yellow highlight on dead cells, green on live cells).

| Key             | Action                    |
|-----------------|---------------------------|
| Arrow keys      | Move cursor (wraps edges) |
| `Enter` / `Space` | Toggle cell alive/dead |
| `v`             | Enter select mode (rectangular region) |
| `p`             | Paste clipboard at cursor |
| `P`             | Open pattern stamp picker |
| `s`             | Save grid (RLE or `.cells` format) |
| `l`             | Load a pattern (picker or path) |
| `c`             | Clear the entire grid     |
| `R`             | Cycle to next ruleset     |
| `g`             | Toggle population stats panel |
| `d`             | Toggle pattern detection overlay |
| `e`             | Exit editor, stay paused  |
| `q`             | Quit                      |

#### Select Mode

Press `v` in the editor to start a rectangular selection at the cursor. The selection is highlighted in cyan.

| Key        | Action                          |
|------------|----------------------------------|
| Arrow keys | Extend selection                 |
| `y`        | Yank (copy) region to clipboard  |
| `x`        | Cut region (copy + clear cells)  |
| `Esc`      | Cancel selection                 |

#### Paste Preview

Press `p` to enter paste preview (requires a clipboard). The stamp is shown in magenta at the cursor position.

| Key        | Action                          |
|------------|----------------------------------|
| Arrow keys | Move stamp                       |
| `Enter`    | Confirm — stamp cells onto grid  |
| `>` / `<`  | Rotate clipboard 90° CW / CCW   |
| `f`        | Flip horizontally                |
| `F`        | Flip vertically                  |
| `Esc`      | Cancel paste                     |

#### Pattern Stamp Picker

Press `P` in the editor to open an interactive picker that lists all built-in patterns (glider, pulsar, gosper gun, etc.) with their dimensions. Select one to load it into the clipboard and enter paste preview.

### Save / Load

Patterns can be saved in **RLE** (Run Length Encoded) or plaintext **`.cells`** format. RLE is the standard used by LifeWiki, Golly, and every major pattern collection — supporting it means you can import thousands of patterns (spaceships, oscillators, guns, breeders) from online libraries and export your creations in a format others can use. Saved patterns live in `~/.life-patterns/` by default.

- **Save from editor** — press `s`, choose format (RLE default, or `.cells`), type a name, and the current grid is exported with empty borders trimmed. RLE files include the active ruleset in the header.
- **Load from editor** — press `l` to browse saved patterns (both `.rle` and `.cells`) with an interactive picker (arrow keys + enter), or enter a file path if no patterns are saved yet.
- **Load at startup** — use `--load <name-or-path>` to start with a pattern from your library. The loader auto-detects format by extension and tries `.rle` before `.cells` when resolving names.

## Rulesets

All rules use Birth/Survival notation — a cell is born if it has exactly B neighbors, and survives if it has exactly S neighbors.

| Preset     | Rule       | Character |
|------------|------------|-----------|
| `life`     | B3/S23     | Classic Conway — gliders, oscillators, still lifes |
| `highlife` | B36/S23    | Like Life but with replicators |
| `daynight` | B3678/S34678 | Symmetric — dead/alive cells behave identically |
| `seeds`    | B2/S       | Every cell dies each tick — explosive growth |
| `diamoeba` | B35678/S5678 | Grows diamond-shaped amoeba blobs |
| `morley`   | B368/S245  | Move — glider-rich rule |
| `2x2`      | B36/S125   | Forms 2x2 blocks |
| `maze`     | B3/S12345  | Generates maze-like corridors |

Use `--rule <preset>` or `--rule B.../S...` for custom rules. Press `R` at runtime to cycle through presets.

## Population Statistics Dashboard

Press `g` to toggle a 35-column side panel that provides real-time population analytics:

- **Current population** — live cell count
- **Peak population** — highest count seen, and the generation it occurred at
- **Growth rate** — percentage change from the previous generation
- **Generation counter**
- **ASCII bar chart** — a scrolling sparkline using Unicode block characters (`▁▂▃▄▅▆▇█`) showing population over recent generations, auto-scaled to the data maximum

Population history is kept in a rolling 500-generation buffer. When the panel is hidden, a compact `Pop N` count appears in the status bar. The grid drawing area shrinks automatically to make room for the panel when it's visible.

## Time Travel

The simulator records up to 10,000 generations of grid history, letting you rewind to any previous state and replay from there.

- **Rewind** — press `[` to step backward one generation. The simulation auto-pauses and the status bar shows `REWOUND | HISTORY 42/300`.
- **Forward** — press `]` to step forward through recorded history. When you reach the latest generation, browsing mode ends automatically.
- **Jump to start** — press `b` to jump to the beginning of recorded history (auto-pauses).
- **Fork and resume** — press `Space` while rewound to discard everything after the current point and resume running from there. Press `n` to single-step forward from the rewound point (also forks).
- **History reset** — randomizing, clearing, or loading a pattern resets the history buffer.

This pairs with the existing pause/step controls and the stats panel — you can rewind to an interesting moment, study the population graph, then fork and let the simulation evolve differently.

## Clipboard & Pattern Stamps

The editor includes a full clipboard system for working with rectangular regions of cells — select, copy, paste, rotate, and flip. This turns the editor from a pixel-by-pixel tool into a pattern construction workbench for building complex structures like guns, puffers, and breeders.

- **Select** (`v`) a rectangular region, then **yank** (`y`) or **cut** (`x`) it to the clipboard.
- **Paste** (`p`) positions a preview at the cursor — move it around, **rotate** (`>`/`<`) 90° in either direction, or **flip** (`f`/`F`) horizontally/vertically before confirming with `Enter`.
- **Pattern stamps** (`P`) lets you load any built-in pattern directly into the clipboard for placement.
- The clipboard persists across paste operations, so you can stamp the same pattern multiple times. Combine with save/load to build a reusable `.cells` snippet library.

## Pattern Recognition

Press `d` to toggle real-time pattern detection. The recognition engine uses connected component analysis with 8-connectivity flood fill to isolate structures, then matches each component against a catalog of known patterns under all D4 symmetry transformations (4 rotations × 2 reflections).

### Recognized Patterns

| Category     | Patterns                                  |
|--------------|-------------------------------------------|
| Still lifes  | block, beehive, loaf, boat, tub, pond     |
| Oscillators  | blinker, toad, beacon, pulsar             |
| Spaceships   | glider, LWSS                              |

Oscillators and spaceships are cataloged across multiple phases so they're identified regardless of which generation you're viewing.

### Display

- **Grid overlay** — detected pattern cells are highlighted in yellow, with the pattern name labeled above each instance.
- **Stats panel** — when both `g` (stats) and `d` (detect) are active, a "DETECTED PATTERNS" section appears in the stats panel showing counts (e.g., `3× glider, 2× block`), sorted by frequency.
- **Status bar** — shows a `DETECT` indicator when detection is enabled.

Connected components larger than 50 cells are skipped to keep detection fast on busy grids.

## Multiplayer

Two terminals can connect peer-to-peer and co-edit the same grid in real-time. Each player has a distinct cursor color (yellow = local, red = remote). Uses only Python's standard library (`socket`, `select`, `threading`) — no external dependencies.

```bash
# Terminal 1: Host a session on port 4444
python3 life.py --host 4444

# Terminal 2: Connect from another terminal (same machine or remote)
python3 life.py --connect 127.0.0.1:4444
```

| Flag        | Description                                      |
|-------------|--------------------------------------------------|
| `--host PORT`       | Host a multiplayer session on PORT      |
| `--connect HOST:PORT` | Connect to a multiplayer host         |

### How it works

- **Host-authoritative simulation** — the host runs `step()` and broadcasts results; the client receives and applies them. This keeps both grids in lockstep.
- **All edits synced** — cell toggles, paste stamps, cut operations, clear, rule changes, and pause/unpause are replicated to the peer immediately.
- **Cursor sharing** — each player's cursor position is sent to the peer at ~20 updates/sec. The remote cursor renders in red so it's easy to distinguish from your own.
- **Connection status** — the status bar shows `[MP:HOST]` or `[MP:CLIENT]` when connected, or `[Waiting for peer...]` before the peer joins.
- **Protocol** — newline-delimited JSON over TCP. Message types: `sync` (full grid), `cell` (toggle), `cur` (cursor), `step` (simulation tick), `clear`, `pause`, `rule`.
- **Initial sync** — when a client connects, the host sends the full grid state, generation count, and active ruleset so the client starts in the correct state.

## Scripting Engine

Press `L` at any time or use `--script` at startup to load user scripts from `~/.life-scripts/`. Scripts are plain Python files executed in a sandboxed namespace — dangerous modules (`os`, `sys`, `subprocess`, etc.) are blocked; only `math`, `random`, `itertools`, `functools`, and `collections` are available for import.

### Script API

Scripts have access to a `grid` object and several global functions:

| API | Description |
|-----|-------------|
| `grid.get(r, c)` / `grid.set(r, c, val)` | Read/write individual cells |
| `grid.clear()` / `grid.population()` | Clear grid or count live cells |
| `grid.neighbours(r, c)` | Count live neighbours (toroidal) |
| `grid.fill_random(density)` | Fill grid randomly |
| `grid.place(pattern, r, c)` | Place a built-in pattern |
| `grid.stamp(cells, r, c)` | Stamp a 2D list onto the grid |
| `grid.rect(r1, c1, r2, c2)` | Draw a filled rectangle |
| `grid.line(r1, c1, r2, c2)` | Draw a line (Bresenham's) |
| `grid.circle(cr, cc, radius)` | Draw a circle outline |
| `grid.rows` / `grid.cols` | Grid dimensions |
| `custom_rule(fn)` | Register `fn(alive, neighbours, age, row, col) -> int` as the step rule |
| `set_rule(birth, survival)` | Set standard B/S rules from script |
| `@on_step` | Register a callback `(generation, population)` called each tick |
| `challenge(target_pop, max_gens)` | Activate challenge mode — reach the target or lose |
| `log(...)` | Display a message on the grid overlay |

### Example Scripts

Five example scripts ship in `~/.life-scripts/` after first use:

- **`probabilistic_life.py`** — Custom rule where lonely cells have a 30% survival chance instead of dying
- **`glider_factory.py`** — Scripted demo that places multiple guns and pulsars
- **`population_challenge.py`** — Challenge: reach population 200 in 100 generations starting from 3 gliders
- **`wave_pattern.py`** — Draws sine waves and circles using the drawing API
- **`asymmetric_gravity.py`** — Position-dependent rule with gravity effect and `@on_step` monitoring

## Animated GIF Export

Press `G` to export the current time-travel history buffer as an animated GIF. The simulation pauses, encodes every recorded frame, and saves to `life_gen<N>.gif` in the current directory (where N is the current generation number).

- **Color-mapped** — uses the same aging palette as the terminal display: green (newborn) → cyan (young) → blue (mature) → magenta (ancient), on a black background.
- **Frame timing** — the GIF frame delay matches your current simulation speed setting.
- **Pure Python** — the GIF89a encoder (LZW compression, NETSCAPE looping extension, sub-block framing) is written from scratch using only `struct`. No Pillow, no ImageMagick, no external dependencies.
- **Cell rendering** — each grid cell is drawn as a 4×4 pixel block, so a default 80×40 grid produces 320×160 pixel frames.
- **Infinite loop** — exported GIFs loop forever by default.

The export uses whatever history is available (up to 10,000 generations from the time-travel system), so longer recordings produce larger files. A status message shows progress and the output path.

## Design Notes

- **Toroidal grid** — cells wrap around all edges, so patterns don't die at boundaries.
- **Cell aging with color gradients** — cells change color based on how many generations they've been alive, creating a visual heatmap that reveals stable structures vs. active frontiers at a glance:
  - **Green** (age 1–3) — newborn / active frontier
  - **Cyan** (age 4–8) — young
  - **Blue** (age 9–20) — mature
  - **Magenta** (age 21+) — ancient / stable structures
- **Curses rendering** — each live cell is drawn as a double-width block (`██`) for a square aspect ratio.
- **All standard library** — only `curses`, `argparse`, `copy`, `json`, `math`, `os`, `queue`, `re`, `select`, `socket`, `struct`, `threading`, `time`, and `random` are used.
