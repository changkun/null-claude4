# Cellular Automaton — Terminal Simulator

A single-file Python implementation of cellular automata that runs in the terminal using `curses`. No external dependencies. Ships with 8 preset B/S rulesets (Conway's Life, HighLife, Day & Night, Seeds, Diamoeba, Morley, 2x2, Maze), the 4-state **Wireworld** automaton, the continuous-valued **Gray-Scott** reaction-diffusion model, **Lenia** continuous smooth-kernel cellular automata, **Langton's Ant** and generalized turmites, the **Wa-Tor** predator-prey ecosystem, the **Falling Sand** particle physics sandbox, **Physarum** slime mold transport networks, the **Abelian Sandpile** self-organized criticality model, **Diffusion-Limited Aggregation** fractal growth, the **Forest Fire** probabilistic cellular automaton, the **Ising Model** statistical mechanics spin simulation, the **Cyclic Cellular Automaton** (CCA) spiral wave generator, the **Chimera Grid** multi-rule coexistence mode, **Particle Life** emergent multi-species particle interactions, **Lattice Boltzmann** D2Q9 fluid dynamics, **Boids** flocking/swarming simulation, a **split-screen comparison mode** for watching two simulations side-by-side, and supports arbitrary rules via B/S notation.

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
python3 life.py --rule lenia                        # Lenia continuous CA (Orbium glider)
python3 life.py --rule lenia --lenia-preset geminium # self-replicating Lenia species
python3 life.py --rule lenia --lenia-preset smooth_life # organic SmoothLife soup
python3 life.py --rule elementary                   # 1D Elementary CA (Rule 30)
python3 life.py --rule elementary --eca-rule 110    # Turing-complete Rule 110
python3 life.py --rule elementary --eca-rule 90     # Sierpinski triangles
python3 life.py --rule turmite                      # Langton's Ant (classic RL)
python3 life.py --rule turmite --turmite-preset llrr # symmetric 4-color turmite
python3 life.py --rule turmite --turmite-preset highway4 # 4 ants interacting
python3 life.py --rule wator                          # Wa-Tor predator-prey ecosystem
python3 life.py --rule wator --wator-preset volatile  # fast boom-bust population cycles
python3 life.py --rule fallingsand                     # Falling Sand particle simulation
python3 life.py --rule fallingsand --fallingsand-preset volcano # volcanic eruption scene
python3 life.py --rule physarum                        # Physarum slime mold (dendritic)
python3 life.py --rule physarum --physarum-preset network # efficient transport paths
python3 life.py --rule sandpile                          # Abelian Sandpile (single-source)
python3 life.py --rule sandpile --sandpile-preset random-rain # uniform random grain drops
python3 life.py --rule dla                               # DLA fractal growth (snowflake)
python3 life.py --rule dla --dla-preset lightning         # bolt-like downward paths
python3 life.py --rule forestfire                          # Forest Fire (classic parameters)
python3 life.py --rule forestfire --forestfire-preset tinderbox # constant firestorms
python3 life.py --rule ising                                 # Ising Model (critical temperature)
python3 life.py --rule ising --ising-preset cold              # large ordered domains
python3 life.py --rule cca                                     # Cyclic CA (classic spirals)
python3 life.py --rule cca --cca-preset rainbow                # 20-state rainbow spirals
python3 life.py --rule cca --cca-preset turbulent              # fast 5-state chaotic cycling
python3 life.py --rule chimera                                    # Chimera Grid (Life vs HighLife)
python3 life.py --rule chimera --chimera-preset quad-mix          # four rulesets in quadrants
python3 life.py --rule chimera --chimera-preset diagonal-clash    # diagonal Life vs Diamoeba
python3 life.py --rule particlelife                                 # Particle Life (primordial soup)
python3 life.py --rule particlelife --particlelife-preset clusters   # sticky attraction clusters
python3 life.py --rule particlelife --particlelife-preset orbits     # asymmetric orbital dance
python3 life.py --rule fluid                                          # LBM fluid (lid-driven cavity)
python3 life.py --rule fluid --fluid-preset karman                    # Kármán vortex street
python3 life.py --rule fluid --fluid-preset convection                # Rayleigh-Bénard convection
python3 life.py --rule boids                                             # Boids flocking (classic flock)
python3 life.py --rule boids --boids-preset predator                     # predator evasion swarm
python3 life.py --rule boids --boids-preset murmuration                  # dense starling murmuration
python3 life.py --script probabilistic_life        # run a user script on startup
python3 life.py --script ~/my_script.py            # run a script from a file path
python3 life.py --compare life highlife              # split-screen: Life vs HighLife
python3 life.py --compare B36/S23 forestfire         # split-screen: custom rule vs Forest Fire
python3 life.py --compare ising grayscott            # split-screen: Ising Model vs Gray-Scott
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
| `--rule`    | `life`    | Rule preset, `wireworld`, `grayscott`, `lenia`, `elementary`, `turmite`, `wator`, `fallingsand`, `physarum`, `sandpile`, `dla`, `forestfire`, `ising`, `cca`, `chimera`, `particlelife`, `fluid`, `boids`, or B/S notation (e.g. `B36/S23`) |
| `--gs-preset` | `mitosis` | Gray-Scott parameter preset (`mitosis`, `coral`, `solitons`, `maze`, `spots`, `worms`, `waves`, `bubbles`) |
| `--lenia-preset` | `orbium` | Lenia species preset (`orbium`, `geminium`, `scutium`, `hydrogeminium`, `wanderer`, `smooth_life`) |
| `--eca-rule` | 30        | Wolfram rule number (0–255) for Elementary CA mode |
| `--turmite-preset` | `langton` | Turmite preset (`langton`, `highway4`, `llrr`, `lrrl`, `rllr`, `spiral`, `fibonacci`, `turmite_1`) |
| `--wator-preset` | `classic` | Wa-Tor ecosystem preset (`classic`, `fast_breed`, `sparse`, `sharks_rule`, `volatile`, `equilibrium`) |
| `--fallingsand-preset` | `hourglass` | Falling Sand preset (`hourglass`, `rain`, `volcano`, `garden`, `sandbox`, `cascade`) |
| `--physarum-preset` | `dendritic` | Physarum slime mold preset (`dendritic`, `fungal`, `network`, `rings`, `tendrils`, `lattice`) |
| `--sandpile-preset` | `single-source` | Abelian Sandpile preset (`single-source`, `random-rain`, `identity`, `max-stable`) |
| `--dla-preset` | `snowflake` | DLA fractal preset (`snowflake`, `electrode`, `coral`, `lightning`) |
| `--forestfire-preset` | `classic` | Forest Fire preset (`classic`, `tinderbox`, `old-growth`, `drought`, `rainforest`) |
| `--ising-preset` | `critical` | Ising Model preset (`critical`, `cold`, `hot`, `quench`, `ordered`) |
| `--cca-preset` | `classic` | Cyclic CA preset (`classic`, `sparse`, `von-neumann`, `rainbow`, `turbulent`) |
| `--chimera-preset` | `life-vs-highlife` | Chimera Grid preset (`life-vs-highlife`, `life-vs-seeds`, `quad-mix`, `stripes-3`, `diagonal-clash`) |
| `--particlelife-preset` | `primordial` | Particle Life preset (`primordial`, `clusters`, `orbits`, `swarm`, `chains`) |
| `--fluid-preset` | `cavity` | LBM Fluid preset (`cavity`, `karman`, `convection`) |
| `--boids-preset` | `flock` | Boids flocking preset (`flock`, `predator`, `obstacle`, `murmuration`, `vortex`) |
| `--script`  | —         | Run a Python script on startup (path or name from `~/.life-scripts/`) |
| `--discover` | off      | Launch genetic algorithm rule discovery mode |
| `--ga-generations` | 50 | Number of GA generations in discovery mode |
| `--ga-pop-size` | 60    | Population size per GA generation |
| `--ga-sim-depth` | 200  | Simulation steps per candidate evaluation |
| `--render`   | —         | Headless batch-render mode: run N generations and output PNG frames |
| `--cell-size`| 8         | Pixel size of each cell for PNG rendering |
| `--palette`  | `classic` | Color palette for PNG rendering (`classic`, `ember`, `ocean`, `mono`, `matrix`) |
| `--grid-lines`| off      | Draw 1px grid lines between cells in PNG output |
| `--compare`  | —         | Split-screen comparison: two rule names (e.g. `--compare life highlife`) |
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
| `<` / `>` | Decrease / increase HashLife step exponent; cycle Gray-Scott presets in GS mode; cycle Lenia species presets in Lenia mode; cycle notable ECA rules in Elementary mode; cycle turmite presets in Turmite mode; cycle Wa-Tor ecosystem presets in Wa-Tor mode; cycle Falling Sand presets in Falling Sand mode; cycle Physarum presets in Physarum mode; cycle Sandpile presets in Sandpile mode; cycle DLA presets in DLA mode; cycle Forest Fire presets in Forest Fire mode; cycle Ising presets in Ising mode; cycle CCA presets in Cyclic CA mode; cycle Particle Life presets in Particle Life mode; cycle LBM Fluid presets in Fluid mode; cycle Boids presets in Boids mode |
| `t` / `y` | Decrease / increase temperature in Ising Model mode |
| `W`       | Enter a specific Wolfram rule number (0–255) in Elementary CA mode |
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
| `lenia`    | *(continuous)* | Smooth-kernel CA — see [Lenia](#lenia-continuous-cellular-automata) below |
| `elementary`| *(1D Wolfram)* | 256 elementary CA rules — see [Elementary CA](#elementary-cellular-automata) below |
| `turmite`  | *(agent-based)* | Langton's Ant & turmites — see [Langton's Ant](#langtons-ant--turmites) below |
| `wator`    | *(ecosystem)* | Predator-prey dynamics — see [Wa-Tor](#wa-tor-predator-prey-ecosystem) below |
| `fallingsand` | *(particle physics)* | Gravity-driven sandbox — see [Falling Sand](#falling-sand-particle-simulation) below |
| `physarum`   | *(chemotaxis)* | Slime mold transport networks — see [Physarum](#physarum-slime-mold-transport-network) below |
| `sandpile`   | *(self-organized criticality)* | Abelian Sandpile — see [Sandpile](#abelian-sandpile) below |
| `chimera`    | *(multi-rule zones)* | Multiple B/S rules on one grid — see [Chimera Grid](#chimera-grid--multi-rule-coexistence) below |
| `particlelife` | *(continuous particles)* | Multi-species particle interactions — see [Particle Life](#particle-life--primordial-soup) below |
| `fluid`        | *(lattice Boltzmann)* | D2Q9 fluid dynamics — see [LBM Fluid Dynamics](#lbm-fluid-dynamics--lattice-boltzmann-method) below |
| `boids`          | *(agent-based)* | Flocking/swarming simulation — see [Boids](#boids--flocking-simulation) below |

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

## Elementary Cellular Automata

Elementary Cellular Automata (ECA) are the simplest class of one-dimensional cellular automata, studied extensively by Stephen Wolfram. Each of the 256 rules maps a 3-cell neighborhood (left, center, right) to a single output bit. The simulator renders them as scrolling space-time diagrams — each new generation appears as a row at the bottom, with history scrolling upward.

### Starting Elementary CA

```bash
python3 life.py --rule elementary                   # default Rule 30
python3 life.py --rule elementary --eca-rule 110    # Turing-complete Rule 110
python3 life.py --rule elementary --eca-rule 90     # Sierpinski triangle fractal
```

### Notable Rules

The simulator includes 16 notable rules for quick cycling with `<`/`>`:

| Rule | Character |
|------|-----------|
| **30** | Chaotic — used as a PRNG in Mathematica |
| **110** | Turing-complete — capable of universal computation |
| **90** | Produces Sierpinski triangle fractals |
| **184** | Traffic flow modeling |
| **150** | Additive rule with complex behavior |
| **73, 45, 105, 54, 60, 62, 126, 182, 225, 137, 169** | Various complex and class III/IV behaviors |

### Controls (Elementary CA mode)

| Key | Action |
|-----|--------|
| `<` / `>` | Cycle through notable rules (resets simulation) |
| `W` | Enter a specific rule number (0–255) via text prompt |
| `r` | Randomize initial conditions (random row instead of single center cell) |

### Initialization

By default, the 1D row starts with a single live cell in the center — the canonical initial condition that reveals each rule's intrinsic structure. Press `r` to switch to a random initial row, which produces different behavior for many rules (especially Class II rules that appear boring from a single cell).

### Interactions

- **HashLife** — incompatible (1D automaton). Switching to Elementary CA via `R` auto-deactivates HashLife.
- **Boundary conditions** — the 1D row wraps circularly (toroidal).
- **Status bar** — shows `Rule N [<>]cycle [W]rule#` with the current Wolfram rule number.
- **History** — the space-time diagram is capped at 10,000 rows to prevent unbounded memory growth.

## Lenia — Continuous Cellular Automata

Lenia generalizes Conway's Life into continuous space and time. Instead of binary alive/dead cells, each cell holds a continuous value (0.0–1.0). A smooth ring-shaped kernel computes each cell's neighborhood potential via convolution, and a Gaussian growth function maps that potential to a cell update — producing strikingly organic, creature-like patterns: smooth gliders that look like microorganisms, self-replicating blobs, and fluid structures.

The governing equations:

```
Kernel K: ring-shaped with Gaussian bumps at configurable radii
Potential U = K * A (convolution of kernel with cell state)
Growth G(u) = 2·exp(−(u−μ)² / 2σ²) − 1
Update A(t+dt) = clip(A(t) + dt·G(U), 0, 1)
```

### Starting Lenia

```bash
python3 life.py --rule lenia                            # default Orbium glider
python3 life.py --rule lenia --lenia-preset geminium     # self-replicating pair
python3 life.py --rule lenia --lenia-preset smooth_life  # organic SmoothLife soup
```

### Species Presets

Press `<` / `>` at runtime to cycle through presets. Each has tuned kernel radius (R), time resolution (T), growth parameters (μ, σ), and kernel ring structure (β):

| Preset           | Character                                    |
|------------------|----------------------------------------------|
| `orbium`         | Smooth glider — a single blob that drifts across the grid |
| `geminium`       | Self-replicating — splits into daughter organisms |
| `scutium`        | Shield crawler — compact crawling structure |
| `hydrogeminium`  | Fluid replicator — loose, flowing self-replication |
| `wanderer`       | Drifting blob with gentle motion |
| `smooth_life`    | Organic soup — emergent structures from random noise |

### Rendering

Lenia reuses the Gray-Scott continuous gradient color pipeline:

- **Terminal** — cells mapped to a color gradient: black (no activity) → blue → cyan → green → white (peak value). Cells above a threshold render as filled blocks.
- **PNG** — smooth 6-stop RGB gradient: black → blue → cyan → green → yellow → white.
- **GIF** — quantized to the 5-color GIF palette.
- **Braille** — supported; color chosen by majority vote of the 2×4 block.

### Interactions

- **HashLife** — incompatible (continuous values). Pressing `H` in Lenia mode is blocked; switching to Lenia via `R` auto-deactivates HashLife.
- **Randomize** (`r`) — re-seeds with the current preset's seed pattern.
- **Status bar** — displays current preset name.

## Langton's Ant / Turmites

Langton's Ant is an agent-based cellular automaton — fundamentally different from the field-update rules above. Instead of updating all cells simultaneously, one or more "ants" walk the grid, flipping cell colors and turning based on the cell they stand on. Classic Langton's Ant (rule "RL") produces chaotic behavior for ~10,000 steps before suddenly building an infinite diagonal "highway" — one of the most famous examples of emergent order from simple rules.

Generalized turmites extend this to multiple colors and multiple internal states, producing symmetric patterns, square-building behavior, spirals, and other complex structures.

### Starting Langton's Ant

```bash
python3 life.py --rule turmite                           # classic Langton's Ant (RL)
python3 life.py --rule turmite --turmite-preset highway4  # 4 ants interacting
python3 life.py --rule turmite --turmite-preset llrr      # symmetric 4-color pattern
python3 life.py --rule turmite --turmite-preset turmite_1 # 2-state generalized turmite
```

### Presets

Press `<` / `>` at runtime to cycle through presets:

| Preset       | Character                                              |
|--------------|--------------------------------------------------------|
| `langton`    | Classic RL — chaotic phase then emergent highway       |
| `highway4`   | 4 ants with classic RL rule — interacting highways     |
| `llrr`       | Symmetric (LLRR) — 4-color symmetric growth            |
| `lrrl`       | Square Builder (LRRL) — grows filled squares           |
| `rllr`       | Triangle (RLLR) — triangular symmetric pattern         |
| `spiral`     | Spiral (RLLLRLLL) — 8-color spiral structures          |
| `fibonacci`  | Fibonacci (RLR) — 3-color chaotic growth               |
| `turmite_1`  | 2-state turmite — complex behavior from internal state |

### Rendering

- **Terminal** — ant heads are rendered in red (color pair 21), multi-color cells use a gradient (green → cyan → blue → magenta → white).
- **Braille** — supported; turmite-specific color mapping via majority vote of each 2×4 block.
- **PNG** — headless rendering via `--render` is fully supported.

### Interactions

- **HashLife** — incompatible (agent-based simulation). Switching to turmite mode auto-deactivates HashLife.
- **Topology** — ants respect the active topology (torus, Klein bottle, Möbius strip, bounded). On bounded topology, ants that would step out of bounds stay in place but still turn.
- **Status bar** — shows ant count and `[<>]preset` hint.

## Wa-Tor Predator-Prey Ecosystem

Wa-Tor is A. K. Dewdney's classic predator-prey simulation. Fish and sharks coexist on a toroidal ocean. Fish breed after a set number of ticks; sharks hunt fish for energy and starve if they don't eat. The result is emergent boom-bust population waves — sweeping color fronts of predator and prey across the grid.

This is the first simulation mode based on *population dynamics* rather than pattern formation or signal propagation.

### Starting Wa-Tor

```bash
python3 life.py --rule wator                           # default Classic preset
python3 life.py --rule wator --wator-preset volatile   # fast boom-bust cycles
python3 life.py --rule wator --wator-preset sharks_rule # shark-dominated ocean
```

### Ecosystem Presets

Press `<` / `>` at runtime to cycle through presets. Each preset tunes fish breeding time, shark breeding time, shark starvation energy, and initial population densities:

| Preset        | Fish Breed | Shark Breed | Shark Starve | Character |
|---------------|-----------|-------------|-------------|-----------|
| `classic`     | 3         | 10          | 4           | Balanced predator-prey oscillation |
| `fast_breed`  | 2         | 6           | 3           | Rapid reproduction, volatile dynamics |
| `sparse`      | 5         | 15          | 6           | Low density, slow ecosystem |
| `sharks_rule` | 4         | 8           | 8           | High shark energy, predator-dominated |
| `volatile`    | 2         | 12          | 3           | Extreme boom-bust cycles |
| `equilibrium` | 4         | 12          | 5           | Tends toward stable coexistence |

### Rules

1. **Fish** move to a random empty Von Neumann neighbor each tick. After `fish_breed` ticks, a fish leaves an offspring in its old cell when it moves.
2. **Sharks** prefer fish neighbors (hunting) over empty ones. Eating a fish restores energy. After `shark_breed` ticks, a shark breeds like fish. Sharks lose 1 energy per tick and die when energy reaches 0.
3. All creatures are processed in shuffled random order each tick to prevent directional bias.

### Rendering

- **Terminal** — fish are green, sharks are red, ocean is dark blue. Each creature is drawn as a double-width filled block.
- **Braille** — supported; color is chosen by majority vote of the 2×4 block.
- **Status bar** — shows `Fish:N Sharks:N breed=F/S starve=E [<>]preset`.

### Interactions

- **HashLife** — incompatible (population dynamics simulation). Switching to Wa-Tor mode auto-deactivates HashLife.
- **Population stats** (`g`) — the sparkline graph shows the predator-prey oscillation, making boom-bust cycles clearly visible.
- **Randomize** (`r`) — re-initializes the ocean with the current preset's density parameters.

## Falling Sand Particle Simulation

Falling Sand is a gravity-driven particle physics sandbox — a fundamentally different simulation paradigm from the field-update cellular automata above. Instead of applying rules uniformly across the grid, each cell holds a material type with its own physics: sand falls and piles, water flows and fills containers, fire rises and spreads, smoke drifts and dissipates. The result is emergent behavior reminiscent of classic "powder game" sandboxes, rendered in the terminal.

### Starting Falling Sand

```bash
python3 life.py --rule fallingsand                            # default Hourglass preset
python3 life.py --rule fallingsand --fallingsand-preset volcano  # volcanic eruption
python3 life.py --rule fallingsand --fallingsand-preset garden   # plants growing near water
```

### Materials

Seven material types interact based on simple physical rules:

| Material  | Color   | Behavior |
|-----------|---------|----------|
| **Sand**  | Yellow  | Falls under gravity, piles up, slides diagonally off peaks, sinks through liquids |
| **Water** | Blue    | Falls, flows sideways to fill containers, displaced upward by sand |
| **Stone** | White   | Static — forms walls, floors, and structures |
| **Fire**  | Red     | Rises, spreads to adjacent plants and oil, produces smoke, burns out over time |
| **Smoke** | Magenta | Rises, drifts sideways randomly, dissipates after a set lifetime |
| **Plant** | Green   | Grows toward adjacent water (3% chance per tick), burns when fire is adjacent |
| **Oil**   | Cyan    | Liquid that floats on water, highly flammable — ignites on contact with fire |

### Presets

Press `<` / `>` at runtime to cycle through presets:

| Preset      | Character |
|-------------|-----------|
| `hourglass` | Sand fills the top half of a stone enclosure with a narrow neck — classic hourglass timer |
| `rain`      | Water continuously spawns from the top over stone platforms that redirect the flow |
| `volcano`   | Stone mountain with perpetual fire at the crater and oil pools at the base that catch fire |
| `garden`    | Plants along a stone floor with water pools that feed growth |
| `sandbox`   | Random scatter of all material types for free-form experimentation |
| `cascade`   | Layered stone shelves with gaps; different materials (sand, water, oil) on each level cascade through |

### Rendering

- **Terminal** — each material renders as a double-width filled block (`██`) with a distinct color: yellow (sand), blue (water), white (stone), red (fire), magenta (smoke), green (plant), cyan (oil).
- **Braille** — supported; color chosen by majority vote of the 2×4 block using the material color palette.

### Interactions

- **HashLife** — incompatible (particle physics simulation). Switching to Falling Sand via `R` auto-deactivates HashLife.
- **Randomize** (`r`) — re-initializes the grid with the current preset.
- **Status bar** — shows the current preset name.

## Physarum Slime Mold Transport Network

Physarum is an agent-based chemotaxis simulation inspired by *Physarum polycephalum* (slime mold). Thousands of particles move across a 2D trail map: each agent senses the chemical trail concentration at three positions (left, center, right), rotates toward the strongest signal, deposits more trail chemical, and advances one step. The trail map undergoes diffusion and decay each tick. The result is stunningly organic vein-like networks that self-organize into efficient transport structures — the project's first chemotaxis-driven simulation.

### Starting Physarum

```bash
python3 life.py --rule physarum                              # default dendritic preset
python3 life.py --rule physarum --physarum-preset fungal      # sprawling fungal bloom
python3 life.py --rule physarum --physarum-preset network     # efficient paths between food nodes
```

### Presets

Press `<` / `>` at runtime to cycle through presets. Each configures sensor angle, sensor distance, turn speed, deposit rate, decay rate, diffusion kernel, and initial seed pattern:

| Preset      | Character |
|-------------|-----------|
| `dendritic` | Tight vein-like structures — narrow dendritic branches radiating from a center cluster |
| `fungal`    | Sprawling bloom — wide sensor angles produce diffuse, organic fungal growth |
| `network`   | Efficient transport paths — agents connect food nodes with shortest-path networks |
| `rings`     | Pulsing concentric bands — high deposit and decay create rhythmic ring patterns |
| `tendrils`  | Sparse reaching tendrils — few agents with long sensor reach explore outward |
| `lattice`   | Ordered grid structure — tight parameters produce regular lattice-like patterns |

### How It Works

1. **Agents** occupy positions on the continuous (floating-point) grid. Each has a heading angle.
2. **Sense** — each agent samples the trail map at three points: left (heading − sensor_angle), center (heading), and right (heading + sensor_angle), each at sensor_distance ahead.
3. **Rotate** — the agent turns toward the direction with the highest trail concentration. If center is strongest, no turn. If left/right tie, the agent picks randomly.
4. **Move** — the agent advances one step in its current heading direction, wrapping at grid edges.
5. **Deposit** — the agent deposits chemical at its new position, strengthening the trail.
6. **Diffuse & decay** — the entire trail map is blurred (3×3 mean filter weighted by diffuse_k) and then decayed (multiplied by 1 − decay_rate), causing old trails to fade.

### Seed Patterns

| Seed           | Description |
|----------------|-------------|
| `center_circle` | Agents clustered in a circle at the grid center — produces radial branching |
| `scatter`       | Agents randomly distributed across the entire grid — produces global network formation |
| `food_nodes`    | Agents clustered at several discrete nodes — produces connecting transport paths |

### Rendering

- **Terminal** — trail concentration is mapped to the continuous gradient colormap (blue → cyan → green → white), shared with Gray-Scott and Lenia.
- **PNG** — smooth 6-stop RGB gradient: black → blue → cyan → green → yellow → white.
- **Braille** — supported; color chosen by majority vote of the 2×4 block.

### Interactions

- **HashLife** — incompatible (agent-based simulation). Switching to Physarum mode auto-deactivates HashLife.
- **Randomize** (`r`) — re-initializes agents and trail map with the current preset.
- **Status bar** — shows the current preset name.

## Abelian Sandpile

The Bak–Tang–Wiesenfeld sandpile model: the canonical example of **self-organized criticality**. Cells hold grain counts 0–3. When a cell reaches 4 grains it "topples", sending one grain to each of its four von Neumann neighbours. This trivially simple rule produces fractal diamond patterns and power-law avalanche distributions.

### Starting Sandpile

```bash
python3 life.py --rule sandpile                                  # default single-source preset
python3 life.py --rule sandpile --sandpile-preset random-rain    # uniform random grain drops
python3 life.py --rule sandpile --sandpile-preset identity       # identity element of sandpile group
python3 life.py --rule sandpile --sandpile-preset max-stable     # all 3s — one grain triggers massive avalanche
```

### Presets

| Preset | Description |
|--------|-------------|
| `single-source` | Drop grains at center — watch fractal diamonds emerge |
| `random-rain` | Uniform random grain drops across the grid |
| `identity` | The identity element of the sandpile group (all 6s toppled to stability) |
| `max-stable` | Every cell at 3 — one grain triggers a massive cascading avalanche |

Press `<`/`>` at runtime to cycle through presets.

### Colors

| Height | Color |
|--------|-------|
| 0 | Background (empty) |
| 1 | Cyan |
| 2 | Green |
| 3 | Yellow |

### Rendering

- **Terminal** — heights are rendered as filled blocks with height-mapped colors.
- **Braille** — supported; color chosen by majority vote of the 2×4 block.

### Interactions

- **HashLife** — incompatible (grid-free simulation). Switching to Sandpile mode auto-deactivates HashLife.
- **Randomize** (`r`) — re-initializes the sandpile with the current preset.
- **Status bar** — shows the current preset name.

## Diffusion-Limited Aggregation (DLA)

Random walkers diffuse through space and **stick on contact** with existing structure, producing stunning fractal dendrites — like frost on a window, mineral deposits, or lightning bolts. DLA is a classic **aggregation/growth** model, distinct from the cellular automata and population dynamics elsewhere in this project.

### Starting DLA

```bash
python3 life.py --rule dla                            # default snowflake preset
python3 life.py --rule dla --dla-preset electrode     # bottom-edge seed, upward growth
python3 life.py --rule dla --dla-preset coral          # multiple scattered seeds
python3 life.py --rule dla --dla-preset lightning      # top seed with downward bias
```

### Presets

| Preset | Description |
|--------|-------------|
| `snowflake` | Central seed grows radial fractal dendrites |
| `electrode` | Bottom-edge seed line grows upward dendrites |
| `coral` | Multiple scattered seeds grow into each other (80% sticking probability) |
| `lightning` | Top-edge seed with downward bias creates bolt-like paths (70% sticking) |

Press `<`/`>` at runtime to cycle through presets.

### How It Works

Each step releases a batch of random walkers from the grid edges. Walkers take random steps (with optional directional bias) until they land adjacent to existing structure. If a sticking-probability check passes, they join the aggregate; otherwise they keep walking. Walkers that leave the grid are discarded.

### Colors

Cells are colored by **aggregation order** (when they joined the structure):

| Age | Color |
|-----|-------|
| Newest tips | White |
| Young growth | Cyan |
| Mid growth | Blue |
| Older growth | Green |
| Old growth | Yellow |
| Core / seed | Red |

### Rendering

- **Terminal** — aggregated cells render as filled blocks with age-gradient colors.
- **Braille** — supported; color chosen by majority vote of the 2×4 block.

### Interactions

- **HashLife** — incompatible (grid-free simulation). Switching to DLA mode auto-deactivates HashLife.
- **Randomize** (`r`) — re-initializes DLA with the current preset.
- **Status bar** — shows the current preset name.

## Ising Model — Statistical Mechanics Spin Simulation

The 2D Ising model simulates a lattice of magnetic spins (+1 or −1) evolving under the Metropolis algorithm. Each spin interacts with its four nearest neighbors on a toroidal grid: aligned neighbors lower the energy, misaligned neighbors raise it. At each step, every spin is considered for flipping — if flipping reduces energy it always flips; otherwise it flips with probability exp(−ΔE/T), where T is the temperature. This produces three distinct regimes:

- **Low temperature** — large ordered ferromagnetic domains (most spins align)
- **Critical temperature** (T ≈ 2.269) — fractal-like domain boundaries with power-law correlations, the hallmark of a second-order phase transition
- **High temperature** — disordered paramagnetic noise (random-looking spins)

The user can adjust temperature in real-time to watch phase transitions unfold.

### Starting Ising Model

```bash
python3 life.py --rule ising                        # critical temperature (T ≈ 2.269)
python3 life.py --rule ising --ising-preset cold     # low T, ordered domains
python3 life.py --rule ising --ising-preset hot      # high T, paramagnetic noise
python3 life.py --rule ising --ising-preset quench   # random start, quench to T=1.5
python3 life.py --rule ising --ising-preset ordered  # all +1 spins, heat to critical
```

### Presets

| Preset     | Temperature | Initial State | Description |
|------------|-------------|---------------|-------------|
| `critical` | 2.269       | Random        | Near the critical point — fractal domain boundaries |
| `cold`     | 1.0         | Random        | Large ordered domains form quickly |
| `hot`      | 5.0         | Random        | Disordered paramagnetic noise |
| `quench`   | 1.5         | Random        | Watch domains coarsen from hot start |
| `ordered`  | 2.269       | All +1        | Heat aligned spins to see order break down |

### Controls (Ising mode)

| Key | Action |
|-----|--------|
| `t` | Cool down (decrease T by 0.1, min 0.1) |
| `y` | Heat up (increase T by 0.1, max 10.0) |
| `<` / `>` | Cycle through Ising presets |
| `r` | Re-initialize the spin lattice |

### Rendering

- **Spin +1** — rendered as red full blocks
- **Spin −1** — rendered as blue full blocks

### Implementation

Uses a **checkerboard decomposition** with NumPy (when available) for vectorized Metropolis sweeps, or falls back to pure-Python single-spin-flip updates with an exponential cache for the two possible positive ΔE values (4J and 8J).

### Interactions

- **HashLife** — incompatible. Switching to Ising mode auto-deactivates HashLife.
- **Randomize** (`r`) — re-initializes the spin lattice with the current preset.
- **Status bar** — shows current temperature and control hints.

## Chimera Grid — Multi-Rule Coexistence

The Chimera Grid partitions the grid into zones, each governed by a different B/S cellular automaton ruleset. Cells obey the birth/survival rule of their zone, but neighbor counts include cells from **all** adjacent zones — producing emergent boundary dynamics that don't exist in any single ruleset. A Life zone bordering a HighLife zone creates unique interface patterns as gliders from one system collide with the other's physics.

### Starting Chimera Grid

```bash
python3 life.py --rule chimera                                  # Life vs HighLife (halves)
python3 life.py --rule chimera --chimera-preset life-vs-seeds   # Life vs Seeds (halves)
python3 life.py --rule chimera --chimera-preset quad-mix        # 4 rules in quadrants
python3 life.py --rule chimera --chimera-preset stripes-3       # 3 rules in vertical stripes
python3 life.py --rule chimera --chimera-preset diagonal-clash  # diagonal Life vs Diamoeba
```

### Presets

| Preset | Layout | Zones | Description |
|--------|--------|-------|-------------|
| `life-vs-highlife` | Halves | Life, HighLife | Classic comparison — replicators emerge at the boundary |
| `life-vs-seeds` | Halves | Life, Seeds | Explosive Seeds growth crashes into stable Life structures |
| `quad-mix` | Quadrants | Life, HighLife, Morley, Maze | Four distinct dynamics with complex 4-way boundary interactions |
| `stripes-3` | Stripes | Life, DayNight, 2x2 | Three vertical bands with two boundary interfaces |
| `diagonal-clash` | Diagonal | Life, Diamoeba | Diagonal partition — amorphous Diamoeba blobs meet Life's precision |

### Zone Layouts

- **Halves** — left/right split at the midpoint
- **Quadrants** — four rectangular regions (top-left, top-right, bottom-left, bottom-right)
- **Stripes** — equal-width vertical bands, one per rule
- **Diagonal** — above/below the main diagonal

### Controls (Chimera mode)

| Key | Action |
|-----|--------|
| `<` / `>` | Cycle through Chimera presets |
| `r` | Re-randomize the grid (~25% density) |

### Rendering

Each zone is rendered with a distinct color so the partition boundaries are visible. Cell age is tracked — live cells increment age each surviving generation, providing visual depth within each zone.

### How It Works

1. The zone map is precomputed at initialization based on the selected layout.
2. Each cell starts dead or alive (~25% random density).
3. On each step, every cell counts its Moore neighbors across **all** zones (the key insight — cross-zone neighbor counting is what creates boundary dynamics).
4. The cell's own zone determines which B/S rule is applied to that count.

This reuses the entire existing B/S rule infrastructure without duplication.

### Interactions

- **HashLife** — incompatible (multi-rule). Switching to Chimera mode auto-deactivates HashLife.
- **Split-screen** — fully supported. Compare two different Chimera presets side-by-side.
- **Randomize** (`r`) — re-initializes with the current preset at ~25% density.
- **Status bar** — shows the current preset description.

## Particle Life — Primordial Soup

Particle Life is a continuous particle-based simulation where multiple species of particles attract and repel each other based on a randomized interaction matrix. Unlike every other mode in this simulator, it is **not grid-based** — particles have floating-point positions and velocities in a toroidal world, and the display grid is a density projection. The emergent behaviors — clusters, orbits, chains, and self-organizing life-like structures — arise purely from simple pairwise force rules applied to hundreds of particles.

Each species pair (i, j) has a force coefficient in [-1, 1]: positive means attraction, negative means repulsion. The force kernel is piecewise linear with short-range repulsion (preventing particles from collapsing onto each other) and medium-range attraction/repulsion (determined by the interaction matrix), creating stable equilibrium distances.

### Starting Particle Life

```bash
python3 life.py --rule particlelife                                 # random primordial soup
python3 life.py --rule particlelife --particlelife-preset clusters   # sticky attraction clusters
python3 life.py --rule particlelife --particlelife-preset orbits     # asymmetric orbital motion
python3 life.py --rule particlelife --particlelife-preset swarm      # high particle count swarm
python3 life.py --rule particlelife --particlelife-preset chains     # cyclic species chain formation
```

### Presets

| Preset | Particles | Species | Description |
|--------|-----------|---------|-------------|
| `primordial` | 400 | 6 | Fully random interaction matrix — classic primordial soup with unpredictable emergent structures |
| `clusters` | 500 | 4 | Attraction-biased matrix — particles form sticky clusters and blobs |
| `orbits` | 350 | 3 | Antisymmetric forces — species orbit each other in dynamic loops |
| `swarm` | 600 | 5 | High particle count with moderate friction — flocking and swarm behaviors |
| `chains` | 300 | 4 | Each species attracts the next in a cycle — produces chain and ring formations |

### Force Model

The force between two particles at distance *r* uses a piecewise linear kernel with two zones:

- **Repulsion zone** (r < 0.3 × r_max) — prevents particle overlap, creating a minimum separation distance
- **Attraction/repulsion zone** (0.3 × r_max < r < r_max) — magnitude and sign determined by the interaction matrix coefficient for the two species involved

Each preset configures the interaction radius (r_max), friction (velocity damping per tick), and force scale, producing distinctly different dynamics.

### Rendering

Each species is rendered in a distinct color:

| Species | Color |
|---------|-------|
| 0 | Green |
| 1 | Cyan |
| 2 | Magenta |
| 3 | Yellow |
| 4 | Red |
| 5 | Blue |

Particles are projected onto the display grid as solid blocks (`██`). Braille high-density rendering is fully supported with species-aware coloring.

### Implementation

- **Pure Python engine** — O(n²) pairwise force computation with toroidal distance wrapping
- **NumPy vectorized engine** — fully broadcast pairwise computation using NumPy arrays, automatically used when NumPy is available
- **World coordinates** — each grid cell maps to 4×4 world units for sub-cell resolution

### Interactions

- **HashLife** — incompatible (continuous particles, not grid cells). Switching to Particle Life auto-deactivates HashLife.
- **Split-screen** — fully supported. Full particle state is saved/restored for independent pane simulation.
- **Randomize** (`r`) — re-scatters all particles and generates a new interaction matrix.

## LBM Fluid Dynamics — Lattice Boltzmann Method

The Lattice Boltzmann Method (LBM) simulates 2D incompressible fluid flow using the D2Q9 lattice with a BGK (Bhatnagar-Gross-Krook) collision operator. Unlike the other grid-based automata which track discrete cell states, LBM tracks 9 distribution functions per cell representing particle populations moving in each lattice direction. Macroscopic quantities (density, velocity) emerge from these mesoscopic distributions, producing realistic fluid behavior — vortex shedding, recirculation zones, and convective instabilities — all in the terminal.

The governing update at each timestep:

```
f_i(x + e_i, t+1) = f_i(x, t) - (1/τ) · [f_i(x, t) - f_i^eq(x, t)]
```

where τ (relaxation time) controls viscosity, e_i are the 9 lattice velocities, and f_i^eq is the Maxwell-Boltzmann equilibrium distribution.

### Starting LBM Fluid

```bash
python3 life.py --rule fluid                                # lid-driven cavity (default)
python3 life.py --rule fluid --fluid-preset karman           # flow past a cylinder
python3 life.py --rule fluid --fluid-preset convection       # thermal convection cells
```

### Presets

| Preset | τ | Description |
|--------|---|-------------|
| `cavity` | 0.8 | Lid-driven cavity flow — top wall moves right, producing corner vortices and recirculation |
| `karman` | 0.55 | Kármán vortex street — uniform inflow past a cylindrical obstacle sheds alternating vortices |
| `convection` | 0.7 | Rayleigh-Bénard convection — hot bottom / cold top with buoyancy-driven convective rolls |

### Rendering

Visualization maps **vorticity** (curl of the velocity field) to color:

| Vorticity | Color |
|-----------|-------|
| Strong clockwise | Blue / Cyan |
| Quiescent | Dark / Black |
| Strong counter-clockwise | Red / Magenta |

This makes vortex structures, shear layers, and turbulent regions immediately visible.

### Implementation

- **Pure Python engine** — nested-loop collision, streaming, and boundary handling; slow but dependency-free
- **NumPy vectorized engine** — fully broadcast array operations for collision, streaming via `np.roll`, and vectorized boundary conditions; automatically used when NumPy is available
- **Boundary conditions** — bounce-back (no-slip) on solid obstacles, Zou-He velocity boundary for driven walls, periodic or inflow/outflow depending on preset

### Interactions

- **HashLife** — incompatible (continuous distributions, not discrete cells). Switching to Fluid mode auto-deactivates HashLife.
- **Split-screen** — fully supported. Complete LBM state (distributions, density, velocity, obstacles, temperature) is saved/restored for independent pane simulation.
- **Randomize** (`r`) — reinitializes the flow field to the current preset's initial conditions.

## Boids — Flocking Simulation

Craig Reynolds' classic Boids algorithm: each agent ("boid") follows three simple rules — **separation** (avoid crowding neighbors), **alignment** (steer toward average heading of neighbors), and **cohesion** (steer toward center of mass of neighbors). These three local rules produce mesmerizing emergent flocking and swarming behavior with no central coordination.

Unlike the grid-based automata, Boids tracks continuous positions and velocity vectors for each agent. The display grid renders each boid as a directional Unicode arrow (`→↗↑↖←↙↓↘`) showing its current heading, with `◆` for predators and solid blocks for obstacles.

### Starting Boids

```bash
python3 life.py --rule boids                                    # classic flock (default)
python3 life.py --rule boids --boids-preset predator             # predator evasion
python3 life.py --rule boids --boids-preset murmuration          # dense starling murmuration
```

### Presets

Press `<` / `>` at runtime to cycle through presets:

| Preset | Boids | Description |
|--------|-------|-------------|
| `flock` | 200 | Classic flock — separation, alignment, cohesion on a toroidal field |
| `predator` | 250 | Predator evasion — 3 predator agents chase the flock, boids flee |
| `obstacle` | 180 | Obstacle avoidance — circular obstacles with margin turning |
| `murmuration` | 400 | Murmuration — dense, fast flock with 1 predator producing starling-like waves |
| `vortex` | 300 | Vortex — strong alignment and margin turning create swirling formations |

### Rendering

- **Terminal** — each boid renders as a directional arrow based on its velocity angle (8 directions). Predators display as `◆` diamonds. Obstacles render as solid filled blocks. Boid color reflects heading direction.
- **Braille** — supported; boid positions are mapped to the 2×4 Braille sub-grid.

### Implementation

- **Pure Python engine** — O(n²) pairwise neighbor loop with toroidal distance wrapping; dependency-free
- **NumPy vectorized engine** — fully broadcast pairwise distance matrix, vectorized rule accumulation, and batch velocity clamping; automatically used when NumPy is available
- **Toroidal world** — boid positions wrap on a continuous toroidal field (4× grid resolution) so flocks flow seamlessly across edges
- **Predators** — separate agents that chase the nearest boid; boids within predator range apply a flee force
- **Obstacles** — circular obstacles that boids steer around; configurable margin turning pushes boids away from world edges

### Interactions

- **HashLife** — incompatible (continuous agent-based, not discrete cells). Switching to Boids mode auto-deactivates HashLife.
- **Split-screen** — fully supported. Complete Boids state (positions, velocities, predators, obstacles) is saved/restored for independent pane simulation.
- **Randomize** (`r`) — re-scatters all boids and predators to random positions with random headings.

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

## Split-Screen Comparison Mode

Run two simulations side-by-side in the same terminal to visually compare different rulesets, parameters, or topologies evolving from the same initial pattern.

```bash
python3 life.py --compare life highlife        # Conway's Life vs HighLife
python3 life.py --compare ising grayscott      # Ising Model vs Gray-Scott
python3 life.py --compare B36/S23 seeds        # custom B/S rule vs Seeds
```

The terminal is split into left and right panes separated by a `│` divider. Each pane runs its own independent simulation with its own generation counter, speed, pause state, history buffer, and module-level state (so specialized modes like Gray-Scott, Wa-Tor, Ising, etc. don't interfere with each other).

### Controls (Compare mode)

Press `Tab` to switch which pane receives input. The active pane is marked with `*` in its status bar.

| Key       | Action                                      |
|-----------|---------------------------------------------|
| `Tab`     | Switch active pane                          |
| `Space`   | Pause / resume the active pane              |
| `n`       | Step one generation (when paused)           |
| `+` / `-` | Speed up / slow down the active pane       |
| `r`       | Randomize the active pane's grid            |
| `R`       | Cycle to next ruleset in the active pane    |
| `[` / `]` | Scrub through history in the active pane   |
| `b`       | Jump to beginning of history                |
| `q`       | Quit                                        |

### How it works

Each pane maintains a fully independent simulation state. Before stepping a pane's simulation forward, the engine saves the other pane's module-level globals and restores the current pane's — this allows specialized modes that rely on module state (Gray-Scott concentrations, Wa-Tor population grids, Ising spin lattices, Physarum trail maps, etc.) to coexist without cross-contamination.

All 24+ simulation modes are supported, and you can mix any two freely — compare a B/S cellular automaton against a continuous reaction-diffusion system, watch two Ising models at different temperatures, or pit two Chimera Grid presets against each other.

## Design Notes

- **Toroidal grid** — the default topology wraps cells around all edges, so patterns don't die at boundaries. Three alternative topologies are available — see [Grid Topology](#grid-topology).
- **Cell aging with color gradients** — cells change color based on how many generations they've been alive, creating a visual heatmap that reveals stable structures vs. active frontiers at a glance:
  - **Green** (age 1–3) — newborn / active frontier
  - **Cyan** (age 4–8) — young
  - **Blue** (age 9–20) — mature
  - **Magenta** (age 21+) — ancient / stable structures
- **Curses rendering** — each live cell is drawn as a double-width block (`██`) for a square aspect ratio.
- **All standard library** — runs with zero external dependencies. Optionally uses `numpy` and `scipy` for the vectorized compute backend when available.
