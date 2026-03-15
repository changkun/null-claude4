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
```

### Options

| Flag        | Default   | Description                          |
|-------------|-----------|--------------------------------------|
| `--rows`    | 40        | Grid height                          |
| `--cols`    | 80        | Grid width                           |
| `--speed`   | 0.1       | Delay between generations (seconds)  |
| `--pattern` | `glider`  | One of: `glider`, `pulsar`, `gosper`, `random` |
| `--load`    | —         | Load a `.cells` file (path or name from `~/.life-patterns/`) |
| `--rule`    | `life`    | Rule preset or B/S notation (e.g. `B36/S23`) |

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
| `s`             | Save grid to a `.cells` file |
| `l`             | Load a pattern (picker or path) |
| `c`             | Clear the entire grid     |
| `R`             | Cycle to next ruleset     |
| `g`             | Toggle population stats panel |
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

Patterns are saved in the standard plaintext `.cells` format, compatible with files from the broader Game of Life community. Saved patterns live in `~/.life-patterns/` by default.

- **Save from editor** — press `s`, type a name, and the current grid is exported with empty borders trimmed.
- **Load from editor** — press `l` to browse saved patterns with an interactive picker (arrow keys + enter), or enter a file path if no patterns are saved yet.
- **Load at startup** — use `--load <name-or-path>` to start with a pattern from your library or any `.cells` file.

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

## Design Notes

- **Toroidal grid** — cells wrap around all edges, so patterns don't die at boundaries.
- **Cell aging with color gradients** — cells change color based on how many generations they've been alive, creating a visual heatmap that reveals stable structures vs. active frontiers at a glance:
  - **Green** (age 1–3) — newborn / active frontier
  - **Cyan** (age 4–8) — young
  - **Blue** (age 9–20) — mature
  - **Magenta** (age 21+) — ancient / stable structures
- **Curses rendering** — each live cell is drawn as a double-width block (`██`) for a square aspect ratio.
- **All standard library** — only `curses`, `argparse`, `copy`, `os`, `time`, and `random` are used.
