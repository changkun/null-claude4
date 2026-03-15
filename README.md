# Cellular Automaton — Terminal Simulator

A single-file Python implementation of cellular automata that runs in the terminal using `curses`. No external dependencies. Ships with 8 preset B/S rulesets (Conway's Life, HighLife, Day & Night, Seeds, Diamoeba, Morley, 2x2, Maze), the 4-state **Wireworld** automaton, the continuous-valued **Gray-Scott** reaction-diffusion model, and supports arbitrary rules via B/S notation.

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
python3 life.py --rule wireworld                   # Wireworld 4-state automaton
python3 life.py --rule grayscott                   # Gray-Scott reaction-diffusion
python3 life.py --rule grayscott --gs-preset coral  # Gray-Scott with coral preset
python3 life.py --script probabilistic_life        # run a user script on startup
python3 life.py --script ~/my_script.py            # run a script from a file path
python3 life.py --discover                         # evolve interesting rulesets via GA
python3 life.py --discover --ga-generations 100    # more generations for deeper search
python3 life.py --render 100 --palette ember       # 100 PNG frames with ember palette
python3 life.py --render 1 --cell-size 32 --grid-lines  # single high-res frame with grid
```

### Options

| Flag        | Default   | Description                          |
|-------------|-----------|--------------------------------------|
| `--rows`    | 40        | Grid height                          |
| `--cols`    | 80        | Grid width                           |
| `--speed`   | 0.1       | Delay between generations (seconds)  |
| `--pattern` | `glider`  | One of: `glider`, `pulsar`, `gosper`, `random` |
| `--load`    | —         | Load a `.cells` or `.rle` file (path or name from `~/.life-patterns/`) |
| `--rule`    | `life`    | Rule preset, `wireworld`, `grayscott`, or B/S notation (e.g. `B36/S23`) |
| `--gs-preset` | `mitosis` | Gray-Scott parameter preset (`mitosis`, `coral`, `solitons`, `maze`, `spots`, `worms`, `waves`, `bubbles`) |
| `--script`  | —         | Run a Python script on startup (path or name from `~/.life-scripts/`) |
| `--discover` | off      | Launch genetic algorithm rule discovery mode |
| `--ga-generations` | 50 | Number of GA generations in discovery mode |
| `--ga-pop-size` | 60    | Population size per GA generation |
| `--ga-sim-depth` | 200  | Simulation steps per candidate evaluation |
| `--render`   | —         | Headless batch-render mode: run N generations and output PNG frames |
| `--cell-size`| 8         | Pixel size of each cell for PNG rendering |
| `--palette`  | `classic` | Color palette for PNG rendering (`classic`, `ember`, `ocean`, `mono`, `matrix`) |
| `--grid-lines`| off      | Draw 1px grid lines between cells in PNG output |
| `--no-aa`    | off       | Disable anti-aliasing on cell edges in PNG output |
| `--output-dir`| `frames` | Output directory for rendered PNG frames |

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
| `S`       | Toggle sound synthesis            |
| `B`       | Toggle Braille high-density rendering |
| `T`       | Cycle topology (Torus → Klein Bottle → Möbius Strip → Bounded) |
| `H`       | Toggle HashLife hyperspeed mode   |
| `<` / `>` | Decrease / increase HashLife step exponent; cycle Gray-Scott presets in GS mode |
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
| `wireworld`| *(4-state)* | Logic circuits — see [Wireworld](#wireworld) below |
| `grayscott`| *(continuous)* | Reaction-diffusion — see [Gray-Scott](#gray-scott-reaction-diffusion) below |

Use `--rule <preset>` or `--rule B.../S...` for custom rules. Press `R` at runtime to cycle through presets.

## Wireworld

Wireworld is a 4-state cellular automaton designed for simulating digital logic circuits. Unlike the B/S rulesets above (which are binary alive/dead), Wireworld cells have four distinct states:

| State        | Color  | Rule                                                        |
|--------------|--------|-------------------------------------------------------------|
| **Empty**    | black  | Stays empty forever                                         |
| **Electron head** | blue | Becomes electron tail next generation                  |
| **Electron tail** | red  | Becomes conductor next generation                      |
| **Conductor**     | yellow | Becomes electron head if exactly 1 or 2 neighbors are electron heads; otherwise stays conductor |

This simple ruleset is sufficient to build functional logic gates, clocks, diodes, and even rudimentary computers — all within the terminal UI.

### Starting Wireworld

```bash
python3 life.py --rule wireworld          # starts with a default clock pattern
```

Press `R` at runtime to cycle through all rulesets including Wireworld. Switching between Wireworld and binary rulesets auto-clears the grid (since state semantics differ).

### Built-in Wireworld Patterns

Press `P` in editor mode while in Wireworld to access these patterns via the stamp picker:

| Pattern        | Description                                          |
|----------------|------------------------------------------------------|
| `ww_diode`     | Signal flows in one direction only                   |
| `ww_clock`     | 6-cell loop generating periodic electron signals     |
| `ww_or_gate`   | Outputs a signal if either input has a signal        |
| `ww_and_gate`  | Outputs a signal only if both inputs have signals    |

### Editing

In editor mode, `Enter`/`Space` cycles through states: empty → conductor → head → tail → empty. The status bar shows the current cell state.

### Save/Load

Wireworld patterns are fully supported in both RLE and `.cells` formats. RLE uses multi-state encoding (`b`=empty, `o`=head, `B`=tail, `C`=conductor) and saves `Wireworld` as the rule string. The `.cells` format uses `H`/`T`/`C` characters. Loading a Wireworld file automatically switches to Wireworld mode.

### GIF Export

GIF export uses a Wireworld-specific palette (blue/red/yellow) when in Wireworld mode.

## Gray-Scott Reaction-Diffusion

Gray-Scott is a continuous-valued reaction-diffusion model that produces organic patterns — spots, stripes, coral growths, mitosis-like cell splitting, and labyrinthine mazes. Unlike the binary alive/dead rulesets, Gray-Scott tracks two chemical concentrations (U and V) across the grid and renders them as smooth color gradients.

The governing equations:

```
du/dt = Du·∇²u − u·v² + F·(1−u)
dv/dt = Dv·∇²v + u·v² − (F+k)·v
```

where F (feed rate) and k (kill rate) control the pattern type, and Du/Dv are diffusion rates.

### Starting Gray-Scott

```bash
python3 life.py --rule grayscott                    # default mitosis preset
python3 life.py --rule grayscott --gs-preset coral   # branching coral growth
python3 life.py --rule grayscott --gs-preset maze    # labyrinthine patterns
```

### Parameter Presets

Press `<` / `>` at runtime to cycle through presets. Each produces qualitatively different emergent behavior:

| Preset     | F       | k       | Visual character                   |
|------------|---------|---------|-------------------------------------|
| `mitosis`  | 0.0367  | 0.0649  | Cell-like blobs that split and divide |
| `coral`    | 0.0545  | 0.062   | Branching growth resembling coral reefs |
| `solitons` | 0.03    | 0.06    | Pulsing, isolated dots              |
| `maze`     | 0.029   | 0.057   | Labyrinthine corridors              |
| `spots`    | 0.035   | 0.065   | Stable circular dots                |
| `worms`    | 0.078   | 0.061   | Squirming tendril-like structures   |
| `waves`    | 0.014   | 0.054   | Expanding concentric rings          |
| `bubbles`  | 0.012   | 0.05    | Negative spots (holes in substrate) |

### Rendering

- **Terminal** — V concentration is mapped to a 5-stop color gradient: black (no V) → blue → cyan → green → white (peak V). Cells above a threshold render as filled blocks.
- **PNG** — smooth 6-stop RGB gradient: black → blue → cyan → green → yellow → white, producing publication-quality continuous-tone output.
- **GIF** — quantized to the 5-color GIF palette.
- **Braille** — supported; color is chosen by majority vote of the 2×4 block.

### Interactions

- **HashLife** — incompatible (continuous values cannot use the quadtree memoization). Pressing `H` in Gray-Scott mode is blocked; switching to Gray-Scott via `R` auto-deactivates HashLife.
- **Randomize** (`r`) — re-seeds the U/V concentration grids with new random patches instead of binary randomization.
- **Status bar** — displays current `F=` and `k=` values with a `[<>]preset` hint.

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
| `grid.neighbours(r, c)` | Count live neighbours (topology-aware) |
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

## Compute Backend

The simulation engine has two backends and automatically selects the best one available:

- **NumPy/SciPy backend** — uses `scipy.signal.convolve2d` to compute all neighbor counts for the entire grid in a single vectorized operation. This delivers 50–200× speedups on large grids, making 1000×1000+ simulations interactive. The status bar shows `NumPy` when this backend is active.
- **Pure Python backend** — the original cell-by-cell engine. No dependencies beyond the standard library. Used automatically when NumPy/SciPy are not installed.

Both backends produce identical results — same cell aging and ruleset support. The NumPy backend uses `convolve2d(boundary="wrap")` which only supports toroidal wrapping; non-torus topologies automatically fall back to the Python engine. To enable the fast backend:

```bash
pip install numpy scipy
```

## Sound Synthesis

Press `S` to toggle real-time audio sonification of the simulation. The sound engine maps grid activity to audio parameters, letting you *hear* the difference between chaotic rulesets and stable configurations.

### Mappings

| Grid metric | Audio parameter | Details |
|---|---|---|
| **Population density** | Pitch | Cell density maps to frequency (80–880 Hz) with square-root scaling for a musical feel |
| **Spatial distribution** | Stereo panning | Center-of-mass column position drives constant-power left/right balance |
| **Growth rate** | Volume | Rapid population change = louder; stable grids are quiet |

The synthesizer generates a fundamental tone plus a second harmonic for a richer timbre, with fade envelopes at frame boundaries to prevent audio clicks.

### Requirements

Sound output requires one of these system audio players (auto-detected):

- `paplay` (PulseAudio)
- `aplay` (ALSA)
- `play` (SoX)

If no player is found, pressing `S` shows an error message. The status bar displays a `SOUND` indicator when audio is active.

### Technical Details

- **Pure Python** — 16-bit signed stereo PCM at 22050 Hz generated using `struct.pack_into`. No external dependencies.
- **Piped output** — raw PCM is written to the audio player's stdin, so there are no temporary files.
- **Graceful degradation** — if the audio player process dies, the sound engine silently deactivates.

## Genetic Algorithm Rule Discovery

The `--discover` flag launches an evolutionary search that automatically finds interesting cellular automaton rulesets. Instead of manually trying B/S combinations, the GA breeds a population of candidate rules, simulates each one, scores them on a multi-factor fitness function, and iteratively selects the best for crossover and mutation.

```bash
python3 life.py --discover                                    # default settings
python3 life.py --discover --ga-generations 100 --ga-pop-size 80   # deeper search
```

### How it works

1. **Population seeding** — starts with random B/S rulesets (random birth conditions from 1–8, survival from 0–8).
2. **Fitness evaluation** — each candidate runs a short simulation on a random grid. The fitness function scores six weighted metrics:
   - **Population balance** (25%) — Gaussian reward peaked at 25% density, penalizing both extinction and explosion.
   - **Oscillation** (20%) — coefficient of variation in population over time, rewarding dynamic behavior.
   - **Longevity** (20%) — fraction of the simulation the rule survived.
   - **Activity** (15%) — fraction of generations where the population changed.
   - **Survival bonus** (10%) — binary reward for not going extinct.
   - **Diversity** (10%) — number of distinct population levels observed.
3. **Selection** — tournament selection (pick 3, keep the best) for parent choice.
4. **Crossover** — uniform crossover of birth/survival condition bits between two parents.
5. **Mutation** — bit-flip at 15% rate per condition.
6. **Elitism** — top 6 candidates survive unchanged into the next generation.

### Discovery UI

The curses interface has two phases:

- **Evolution phase** — progress bar, current generation, best rule found so far, and a live leaderboard of top rules. Press `q` to skip ahead to results, `Esc` to quit.
- **Results phase** — scrollable list of the top 20 discovered rules with fitness scores and a live mini-preview animation of the selected rule. Press `Enter` to launch any rule directly in the full simulator.

| Key       | Action (results phase)            |
|-----------|-----------------------------------|
| `Up/Down` | Navigate rule list                |
| `Enter`   | Launch selected rule in simulator |
| `Space`   | Play/pause preview animation      |
| `r`       | Restart preview                   |
| `q`/`Esc` | Quit                              |

## Headless PNG Rendering

The `--render` flag runs the simulation headlessly (no terminal UI) and outputs high-resolution PNG frames — useful for creating wallpapers, poster prints, or feeding into `ffmpeg` for HD video.

```bash
# 100 frames of random pattern at 1920x1080 with ember palette
python3 life.py --render 100 --rows 135 --cols 240 --cell-size 8 --palette ember --output-dir hd_frames

# Wallpaper-quality single frame with grid lines
python3 life.py --render 1 --rows 50 --cols 80 --cell-size 32 --palette ocean --grid-lines

# Feed into ffmpeg for HD video
python3 life.py --render 300 --rows 67 --cols 120 --cell-size 16 --output-dir vid_frames
ffmpeg -framerate 30 -i vid_frames/frame_%03d.png -c:v libx264 output.mp4
```

### Color Palettes

| Palette   | Description                          |
|-----------|--------------------------------------|
| `classic` | Matches terminal colors (green→cyan→blue→magenta on black) |
| `ember`   | Warm fire tones (yellow→orange→red→crimson) |
| `ocean`   | Cool blues (sky→ocean→deep→ice on navy) |
| `mono`    | Greyscale (white→grey→dark grey on black) |
| `matrix`  | Green-on-black (bright→dim green) |

All palettes include Wireworld-specific colors for head, tail, and conductor states. Wireworld mode is auto-detected from the active rule.

### Anti-Aliasing

Edge pixels between cells of different states are blended for smooth transitions. This produces publication-quality output at any cell size ≥ 4px. Disable with `--no-aa` for pixel-perfect hard edges.

### Technical Details

- **Pure Python PNG encoder** — generates valid PNG files using only `zlib` (stdlib) for DEFLATE compression. No Pillow, no external dependencies.
- **CRC32 validation** on all chunks; IDAT data split into 32KB chunks for broad compatibility.
- **Arbitrary resolution** — cell size is configurable from 1px (thumbnail) to any size. A 240×135 grid at 8px/cell produces 1920×1080 frames.
- **Grid lines** — optional 1px separators between cells for a blueprint/schematic aesthetic.

## Braille Rendering Mode

Press `B` to toggle high-density Braille rendering. Unicode Braille characters (U+2800–U+28FF) encode a 2×4 dot matrix per terminal cell, meaning each character position represents 8 grid cells instead of 1. This gives 2× horizontal and 4× vertical resolution compared to the classic double-width block renderer.

| Mode    | Terminal 80×24 | Visible grid cells | Density |
|---------|----------------|--------------------|---------|
| Classic | 40×23 cells    | ~920               | 1×      |
| Braille | 160×92 cells   | ~14,720            | ~8×     |

This makes large-scale patterns — Gosper guns, pulsars, Wireworld circuits — dramatically more detailed without needing a larger terminal.

- **Color preservation** — each Braille cell picks its curses color via majority vote of the non-dead cells in its 2×4 block, preserving the age-based color gradient and Wireworld state colors.
- **Automatic fallback** — entering editor mode temporarily switches back to classic rendering (since editing requires per-cell precision), and Braille resumes when you exit the editor.
- **Status bar** — shows a `BRAILLE` indicator when active.

## HashLife Hyperspeed Mode

Press `H` to activate HashLife — a quadtree-memoized algorithm that can skip exponentially many generations in near-constant time. Instead of computing each generation cell-by-cell, HashLife represents the grid as a recursive quadtree where identical sub-patterns share the same node, and memoizes the future of every sub-pattern it has ever seen. For structured patterns like Gosper guns, this means millions or billions of generations can be computed in milliseconds.

### How it works

1. **Quadtree representation** — the grid is stored as a tree of `_HashLifeNode` objects. Level 0 = single cell, level k = 2^k × 2^k region. Identical sub-trees are canonicalized so they share a single node in memory.
2. **Result memoization** — `_step_node()` recursively computes the center half of a node advanced by 2^(k-2) generations, caching the result. The second time the same sub-pattern appears, the answer is instant.
3. **Exponential time leaps** — at level k, a single `step()` call advances by 2^(k-2) generations. The tree automatically expands when the pattern reaches its border, so unbounded growth is supported.

### Controls

| Key       | Action                                        |
|-----------|-----------------------------------------------|
| `H`       | Toggle HashLife on/off                        |
| `<`       | Decrease step exponent (slower, finer-grained)|
| `>`       | Increase step exponent (faster, bigger leaps) |
| `n`       | Single-step (1 generation) while paused       |

The status bar shows `HASHLIFE 2^N (M gens/step) [<>]speed` when active. The generation counter visibly rockets upward as the algorithm exploits pattern repetition.

### Limitations

- **Life-like rules only** — HashLife implements standard B3/S23 (Conway's Life). It automatically disables when switching to Wireworld or custom script rules.
- **No cell aging** — the quadtree tracks only alive/dead state, so exported grids show age=1 for all live cells.
- **Memory trade-off** — the canonical node cache and result cache grow with pattern complexity. Caches are cleared on rule changes and when toggling the mode off.

### Integration

- Toggling `H` imports the current grid into the quadtree engine and exports it back when deactivated.
- Editor changes, rule switches, randomization, and history forks automatically re-sync or deactivate HashLife.
- History recording is throttled during hyperspeed (only the latest frame is stored per step) to avoid filling the 10,000-generation buffer instantly.

## Grid Topology

Press `T` to cycle through four topological surface modes that change how the grid edges connect. Each topology produces fundamentally different emergent behavior — gliders that return mirror-flipped, oscillators that break symmetry, and patterns that interact with dead boundaries.

| Topology        | Description |
|-----------------|-------------|
| **Torus** (default) | Both axes wrap normally — the classic behavior. A glider leaving the right edge reappears on the left at the same row. |
| **Klein Bottle** | Both axes wrap, but the horizontal wrap reverses the row. A glider exiting right returns on the left *mirrored vertically*. |
| **Möbius Strip** | Horizontal axis wraps with row reversal (like Klein), but vertical edges are bounded — cells beyond the top/bottom are dead. |
| **Bounded** | No wrapping at all — all four edges are dead zones. Patterns that hit the boundary interact with emptiness. |

### Interactions

- **NumPy backend** — `scipy.signal.convolve2d` only supports toroidal wrapping, so non-torus topologies automatically fall back to the pure Python engine. The `NumPy` indicator in the status bar is hidden when a non-torus topology is active.
- **HashLife** — the quadtree engine assumes toroidal wrapping. Switching to a non-torus topology while HashLife is active automatically deactivates it and exports the grid back to the standard engine.
- **Status bar** — shows the topology name (e.g., `Klein Bottle`) when a non-default topology is selected. The torus label is hidden since it's the default.

## Design Notes

- **Toroidal grid** — the default topology wraps cells around all edges, so patterns don't die at boundaries. Three alternative topologies are available — see [Grid Topology](#grid-topology).
- **Cell aging with color gradients** — cells change color based on how many generations they've been alive, creating a visual heatmap that reveals stable structures vs. active frontiers at a glance:
  - **Green** (age 1–3) — newborn / active frontier
  - **Cyan** (age 4–8) — young
  - **Blue** (age 9–20) — mature
  - **Magenta** (age 21+) — ancient / stable structures
- **Curses rendering** — each live cell is drawn as a double-width block (`██`) for a square aspect ratio.
- **All standard library** — runs with zero external dependencies. Optionally uses `numpy` and `scipy` for the vectorized compute backend when available.
