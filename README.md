# Conway's Game of Life — Terminal Simulator

A single-file Python implementation of Conway's Game of Life that runs in the terminal using `curses`. No external dependencies.

## Usage

```bash
python3 life.py                                    # default glider pattern
python3 life.py --pattern gosper                   # gosper glider gun
python3 life.py --pattern pulsar                   # period-3 oscillator
python3 life.py --pattern random                   # random initial state
python3 life.py --rows 60 --cols 120 --speed 0.2   # custom grid and speed
```

### Options

| Flag        | Default   | Description                          |
|-------------|-----------|--------------------------------------|
| `--rows`    | 40        | Grid height                          |
| `--cols`    | 80        | Grid width                           |
| `--speed`   | 0.1       | Delay between generations (seconds)  |
| `--pattern` | `glider`  | One of: `glider`, `pulsar`, `gosper`, `random` |

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
| `c`             | Clear the entire grid     |
| `e`             | Exit editor, stay paused  |
| `q`             | Quit                      |

## Design Notes

- **Toroidal grid** — cells wrap around all edges, so patterns don't die at boundaries.
- **Curses rendering** — each live cell is drawn as a double-width block (`██`) for a square aspect ratio.
- **All standard library** — only `curses`, `argparse`, `copy`, `time`, and `random` are used.
