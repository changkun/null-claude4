# Conway's Game of Life — Terminal Simulator

A single-file Python implementation of Conway's Game of Life that runs in the terminal using `curses`. No external dependencies.

## Usage

```bash
python3 life.py                                    # default glider pattern
python3 life.py --pattern gosper                   # gosper glider gun
python3 life.py --pattern pulsar                   # period-3 oscillator
python3 life.py --pattern random                   # random initial state
python3 life.py --rows 60 --cols 120 --speed 0.2   # custom grid and speed
python3 life.py --load spaceship                   # load a saved pattern by name
python3 life.py --load ~/patterns/my.cells         # load from a file path
```

### Options

| Flag        | Default   | Description                          |
|-------------|-----------|--------------------------------------|
| `--rows`    | 40        | Grid height                          |
| `--cols`    | 80        | Grid width                           |
| `--speed`   | 0.1       | Delay between generations (seconds)  |
| `--pattern` | `glider`  | One of: `glider`, `pulsar`, `gosper`, `random` |
| `--load`    | —         | Load a `.cells` file (path or name from `~/.life-patterns/`) |

### Controls

| Key       | Action                            |
|-----------|-----------------------------------|
| `Space`   | Pause / resume                    |
| `+` / `-` | Speed up / slow down             |
| `n`       | Step one generation (when paused) |
| `r`       | Randomize the grid                |
| `e`       | Enter editor mode (auto-pauses)   |
| `q`       | Quit                              |

### Editor Mode

Press `e` to enter an interactive cell editor. The simulation pauses and a cursor appears on the grid (yellow highlight on dead cells, green on live cells).

| Key             | Action                    |
|-----------------|---------------------------|
| Arrow keys      | Move cursor (wraps edges) |
| `Enter` / `Space` | Toggle cell alive/dead |
| `s`             | Save grid to a `.cells` file |
| `l`             | Load a pattern (picker or path) |
| `c`             | Clear the entire grid     |
| `e`             | Exit editor, stay paused  |
| `q`             | Quit                      |

### Save / Load

Patterns are saved in the standard plaintext `.cells` format, compatible with files from the broader Game of Life community. Saved patterns live in `~/.life-patterns/` by default.

- **Save from editor** — press `s`, type a name, and the current grid is exported with empty borders trimmed.
- **Load from editor** — press `l` to browse saved patterns with an interactive picker (arrow keys + enter), or enter a file path if no patterns are saved yet.
- **Load at startup** — use `--load <name-or-path>` to start with a pattern from your library or any `.cells` file.

## Design Notes

- **Toroidal grid** — cells wrap around all edges, so patterns don't die at boundaries.
- **Cell aging with color gradients** — cells change color based on how many generations they've been alive, creating a visual heatmap that reveals stable structures vs. active frontiers at a glance:
  - **Green** (age 1–3) — newborn / active frontier
  - **Cyan** (age 4–8) — young
  - **Blue** (age 9–20) — mature
  - **Magenta** (age 21+) — ancient / stable structures
- **Curses rendering** — each live cell is drawn as a double-width block (`██`) for a square aspect ratio.
- **All standard library** — only `curses`, `argparse`, `copy`, `os`, `time`, and `random` are used.
