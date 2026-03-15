# Contributing

Thanks for your interest in contributing to cellsim.

## Getting started

```bash
# Clone the repo
git clone https://github.com/changkun/null-claude4.git
cd null-claude4

# Install in development mode with all extras
make install-dev

# Run the simulator
make run
```

## Architecture

The entire simulator lives in a single file (`life.py`). This is intentional — it keeps the project zero-dependency and easy to distribute as a standalone script.

### Code organization (by line range)

| Lines       | Section                | Purpose                                         |
|-------------|------------------------|-------------------------------------------------|
| 1-27        | Imports                | Standard library + optional NumPy/SciPy         |
| 28-62       | `RULES`                | All 28 rule presets with metadata                |
| 63-122      | Topology               | Torus/Klein/Mobius/Bounded boundary wrapping     |
| 124-229     | Mode detectors         | `_is_wireworld()`, `_is_grayscott()`, etc.      |
| 231-5317    | Simulation engines     | Each mode's init/step/grid/color functions       |
| 5219-5317   | Patterns               | Built-in gliders, pulsars, gosper gun, wireworld |
| 5326-6255   | `ScriptEngine`         | Python script execution with Lua-like API        |
| 5644-5928   | File I/O               | RLE and `.cells` pattern format support           |
| 6035-6251   | Core `step()`          | B/S rule application + HashLife dispatch          |
| 6259-6627   | `HashLifeEngine`       | Quadtree-memoized hypercomputation               |
| 6664-7360   | Rendering              | Braille, GIF export, PNG rendering               |
| 7362-7562   | `SoundEngine`          | Audio synthesis (optional)                       |
| 7565-7890   | Pattern recognition    | Detect gliders, oscillators, still lifes         |
| 7892-8058   | `NetworkPeer`          | Multiplayer networking via sockets               |
| 8059-9814   | `run()`                | Main terminal UI loop                            |
| 9815-10126  | `run_demo()`           | Auto-cycling demo reel                           |
| 10127-11070 | `run_split()`          | Split-screen comparison mode                     |
| 11074-11617 | `GeneticRuleDiscovery` | GA-based rule evolution                          |
| 11618-12283 | `main()` + argparse    | CLI entry point                                  |

### Key classes

- **`ScriptEngine`** — Custom script execution (Lua-like API)
- **`HashLifeEngine`** — Quadtree-memoized hypercomputation
- **`SoundEngine`** — Audio synthesis for visual feedback
- **`NetworkPeer`** — Multiplayer session coordination
- **`GeneticRuleDiscovery`** — GA-based rule evolution

## Code style

```bash
make lint    # ruff
make check   # mypy
```

- Follow existing patterns for naming and structure
- Variables like `u`, `v`, `F`, `k` are standard mathematical notation — don't rename them
- Keep all code in `life.py` unless there's a strong reason to split

## Adding a new simulation mode

1. Define a preset dictionary (e.g., `MY_PRESETS = {...}`) with parameter sets
2. Add state initialization function (`_my_init(rows, cols, preset_name)`)
3. Add step function (`_my_step(...)`) for simulation update logic
4. Add grid conversion function (`_my_to_grid(rows, cols)`) to map state to display
5. Add color function (`_my_color(val, max_val)`) for terminal rendering
6. Register the mode in the `RULES` dictionary
7. Wire it into `main()` argparse and the `run()` loop
8. Add a `--my-preset` CLI flag and `<`/`>` preset cycling
9. Update `README.md` with usage, presets, and a description section

## Submitting changes

1. Fork the repository
2. Create a feature branch
3. Run `make lint` before committing
4. Open a pull request with a clear description
