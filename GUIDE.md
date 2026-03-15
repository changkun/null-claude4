# Simulation Guide

A scientific and historical companion to each simulation mode in cellsim.
For usage instructions (CLI flags, controls, presets), see [README.md](README.md).

---

## Table of Contents

- [Conway's Game of Life and B/S Rulesets](#conways-game-of-life-and-bs-rulesets)
- [Wireworld](#wireworld)
- [Gray-Scott Reaction-Diffusion](#gray-scott-reaction-diffusion)
- [Elementary Cellular Automata](#elementary-cellular-automata)
- [Lenia](#lenia)
- [Langton's Ant and Turmites](#langtons-ant-and-turmites)
- [Wa-Tor Predator-Prey Ecosystem](#wa-tor-predator-prey-ecosystem)
- [Falling Sand](#falling-sand)
- [Physarum Slime Mold](#physarum-slime-mold)
- [Abelian Sandpile](#abelian-sandpile)
- [Diffusion-Limited Aggregation](#diffusion-limited-aggregation)
- [Forest Fire Model](#forest-fire-model)
- [Ising Model](#ising-model)
- [Cyclic Cellular Automata](#cyclic-cellular-automata)
- [Chimera Grid](#chimera-grid)
- [Particle Life](#particle-life)
- [Lattice Boltzmann Fluid Dynamics](#lattice-boltzmann-fluid-dynamics)
- [Boids Flocking](#boids-flocking)
- [Wave Function Collapse](#wave-function-collapse)
- [2D Wave Equation](#2d-wave-equation)
- [Smoothed Particle Hydrodynamics](#smoothed-particle-hydrodynamics)
- [References](#references)

---

## Conway's Game of Life and B/S Rulesets

### Historical background

The Game of Life was invented by the British mathematician John Horton Conway in 1970 and popularized by Martin Gardner's column in *Scientific American* [1]. Conway was searching for a simple set of rules that could produce unpredictable, complex behavior from a two-dimensional grid of cells — a question inspired by John von Neumann's earlier work on self-reproducing automata in the 1940s.

The rules are famously simple: on an infinite grid of square cells, each cell is either alive or dead. At each discrete time step, every cell simultaneously updates according to the number of its eight live neighbors (Moore neighborhood):

- A dead cell with exactly 3 live neighbors becomes alive (**birth**).
- A live cell with 2 or 3 live neighbors stays alive (**survival**).
- All other live cells die (underpopulation or overcrowding).

Despite this simplicity, Conway's Life supports a remarkably rich taxonomy of structures:

- **Still lifes** — stable configurations (block, beehive, loaf)
- **Oscillators** — periodic patterns (blinker with period 2, pulsar with period 3)
- **Spaceships** — patterns that translate across the grid (glider, lightweight spaceship)
- **Guns** — stationary patterns that emit spaceships (Gosper's glider gun, 1970)
- **Breeders** — patterns whose population grows quadratically

In 1982, Conway proved that Life is **Turing-complete**: any computation that can be performed by a conventional computer can, in principle, be carried out by a sufficiently large Life pattern [2]. This was demonstrated constructively by building logic gates from glider collisions.

### Birth/Survival notation

The B/S notation generalizes Life's rules to an entire family of "Life-like" cellular automata. A rule written as B*x*/S*y* means: a dead cell is born if it has exactly *x* neighbors, and a live cell survives if it has exactly *y* neighbors. Conway's Life is B3/S23.

This notation was systematized in the 1990s and has since been used to catalog thousands of distinct rules. The eight presets in this simulator span the major behavioral classes:

| Rule | B/S | Discovery | Notable property |
|------|-----|-----------|-----------------|
| **Life** | B3/S23 | Conway, 1970 | Turing-complete, gliders, guns |
| **HighLife** | B36/S23 | Nathan Thompson, 1994 | Supports a natural replicator |
| **Day & Night** | B3678/S34678 | Nathan Thompson | Dead/alive symmetry |
| **Seeds** | B2/S | — | Every cell dies; explosive chaotic growth |
| **Diamoeba** | B35678/S5678 | — | Amoeba-like blob dynamics |
| **Morley (Move)** | B368/S245 | Dean Hickerson | Rich in natural gliders |
| **2x2** | B36/S125 | — | Forms 2x2 block structures |
| **Maze** | B3/S12345 | — | Generates maze-like corridors |

### Mathematical formulation

```
N(i,j,t) = Σ a(i+di, j+dj, t)    for (di,dj) ∈ {-1,0,1}² \ {(0,0)}

a(i,j,t+1) = 1   if a(i,j,t) = 0  and  N(i,j,t) ∈ β      (birth)
            = 1   if a(i,j,t) = 1  and  N(i,j,t) ∈ σ      (survival)
            = 0   otherwise                                  (death)

where:
  a(i,j,t) ∈ {0, 1}  — state of cell at column i, row j, generation t
                         (0 = dead, 1 = alive)
  N(i,j,t) ∈ {0..8}  — count of live cells in the 8-cell Moore neighborhood
  β ⊆ {0..8}          — birth set: neighbor counts that cause a dead cell to
                         become alive (e.g., β = {3} for Conway's Life)
  σ ⊆ {0..8}          — survival set: neighbor counts that keep a live cell
                         alive (e.g., σ = {2,3} for Conway's Life)
  (di,dj)             — offset pairs to the 8 surrounding cells
```

The grid uses toroidal boundary conditions by default (indices wrap), so the effective grid is a discrete torus.

### Real-world connections

While the Game of Life is abstract, its dynamics appear in models of:

- **Crystal growth** — nucleation and stable configurations
- **Population ecology** — overcrowding and underpopulation thresholds
- **Neural network firing** — excitable media with refractory periods
- **Theoretical computer science** — universality and decidability questions

---

## Wireworld

### Historical background

Wireworld was created by Brian Silverman in 1987 as a cellular automaton specifically designed for modeling electronic circuits [3]. Unlike Life-like rules where all cells are equivalent, Wireworld introduces **asymmetric state semantics**: cells represent empty space, copper conductors, and propagating electron signals.

The four states and their transition rules:

```
Transition rules (applied simultaneously each step):
  empty         → empty
  electron_head → electron_tail
  electron_tail → conductor
  conductor     → electron_head  if N_heads ∈ {1, 2}
                → conductor      otherwise

where:
  state ∈ {empty, electron_head, electron_tail, conductor}
  N_heads  — count of electron_head cells in the Moore neighborhood (8 neighbors)
  empty    — vacuum; never changes (structural background)
  conductor — copper wire; potential carrier of signals
  electron_head — leading edge of an electron signal (rendered blue)
  electron_tail — trailing edge, refractory period (rendered red)
```

This rule set is sufficient to build all fundamental digital logic components: wires (conductor loops), diodes (asymmetric junctions), AND/OR/NOT gates, clocks (small conductor loops with a single electron), and even complete CPUs. David Moore and Mark Owen demonstrated a Wireworld computer capable of performing addition and subtraction [4].

### Why it matters

Wireworld is pedagogically important because it bridges the gap between abstract cellular automata and practical digital electronics. Every signal propagates at exactly 1 cell per generation, timing is deterministic, and circuit layout follows intuitive "wiring" principles — making it an ideal environment for teaching digital logic without the analog complexities of real electronics.

### Computational universality

Wireworld is Turing-complete. Since you can build arbitrary logic circuits (including memory and conditional branching), you can in principle implement any algorithm. The Wireworld computer is one of the most elegant demonstrations of computation emerging from simple local rules.

---

## Gray-Scott Reaction-Diffusion

### Historical background

The Gray-Scott model belongs to the family of **reaction-diffusion systems** first proposed by Alan Turing in his landmark 1952 paper *The Chemical Basis of Morphogenesis* [5]. Turing showed mathematically that two interacting chemicals diffusing at different rates can spontaneously break spatial symmetry, producing stable patterns from a homogeneous initial state — a mechanism now called **Turing instability** or **diffusion-driven instability**.

The specific Gray-Scott model was introduced by Peter Gray and Stephen Scott in 1983–1984 to describe autocatalytic reactions in a continuously stirred tank reactor (CSTR) [6]. John Pearson's 1993 numerical study revealed that the model produces an astonishing diversity of patterns depending on two control parameters (feed rate $F$ and kill rate $k$) [7].

### Mathematical formulation

The system tracks concentrations of two chemical species on a 2D domain. The continuous PDEs and their discrete update:

```
Continuous form:
  ∂u/∂t = Du ∇²u − u v² + F (1 − u)
  ∂v/∂t = Dv ∇²v + u v² − (F + k) v

Discrete update (Euler forward, 5-point Laplacian):
  u(i,j,t+1) = u(i,j,t) + Δt · [Du · L(u) − u·v² + F·(1 − u)]
  v(i,j,t+1) = v(i,j,t) + Δt · [Dv · L(v) + u·v² − (F + k)·v]

  L(u) = u(i+1,j) + u(i−1,j) + u(i,j+1) + u(i,j−1) − 4·u(i,j)

where:
  u(i,j,t) ∈ [0,1]  — concentration of substrate species U at cell (i,j), step t
  v(i,j,t) ∈ [0,1]  — concentration of autocatalyst species V at cell (i,j), step t
  Du = 0.21          — diffusion coefficient of U (how fast U spreads spatially)
  Dv = 0.105         — diffusion coefficient of V (Du = 2·Dv enables Turing instability)
  F ∈ [0.01, 0.08]   — feed rate (replenishes U from an external reservoir; higher F
                        means faster substrate renewal)
  k ∈ [0.04, 0.07]   — kill rate (removes V from the system; controls pattern type)
  ∇²                 — Laplacian operator (spatial second derivative, approximated
                        by the 5-point stencil L)
  u·v²               — autocatalytic reaction term: U + 2V → 3V
  Δt = 1.0           — time step (one Euler step per generation)
```

The parameter space (F, k) contains distinct regions producing qualitatively different behaviors: spots, stripes, spirals, mitotic splitting, traveling waves, and spatiotemporal chaos.

### Real-world connections

Reaction-diffusion mechanisms have been identified in:

- **Animal coat patterns** — zebra stripes, leopard spots, angelfish markings (Kondo & Asai, 1995 [8])
- **Chemical oscillators** — Belousov-Zhabotinsky reaction
- **Embryonic development** — digit formation, feather patterning
- **Coral growth** — branching morphologies resemble Gray-Scott coral preset

---

## Elementary Cellular Automata

### Historical background

Elementary Cellular Automata (ECA) are the simplest possible one-dimensional cellular automata, systematically studied by Stephen Wolfram beginning in 1983 [9]. Each rule maps a 3-cell binary neighborhood (left, center, right — 8 possible configurations) to a single output bit. Since each of the 8 inputs can independently map to 0 or 1, there are exactly $2^8 = 256$ possible rules, numbered 0–255 by interpreting the output bits as a binary number (Wolfram's numbering convention).

Despite their extreme simplicity, ECAs exhibit the full spectrum of dynamical behavior. Wolfram classified them into four classes:

| Class | Behavior | Examples |
|-------|----------|---------|
| I | Homogeneous fixed point | Rule 0, 32 |
| II | Simple periodic structures | Rule 4, 108 |
| III | Chaotic, aperiodic | Rule 30, 45 |
| IV | Complex, localized structures | Rule 110, 54 |

### Notable rules

**Rule 30** generates chaotic behavior from a single cell. Its center column passes statistical tests for randomness and has been used as a pseudorandom number generator in *Mathematica* since 1987. The pattern on the shell of the textile cone snail (*Conus textile*) closely resembles a Rule 30 space-time diagram [10].

**Rule 110** was proven Turing-complete by Matthew Cook in 2004 [11], settling a long-standing conjecture. This means the simplest possible 1D cellular automaton capable of universal computation has only 256 possible rule tables — and one of them is already universal.

**Rule 90** produces exact Sierpinski triangles (Pascal's triangle modulo 2), connecting cellular automata to classical fractal geometry.

### Mathematical formulation

```
n = 4·a(i−1, t) + 2·a(i, t) + a(i+1, t)

a(i, t+1) = floor(R / 2^n) mod 2

where:
  a(i, t) ∈ {0, 1}  — state of cell i at generation t (0 = dead, 1 = alive)
  i                  — cell index on a 1D row (wraps circularly)
  t                  — discrete generation number
  n ∈ {0, 1, …, 7}  — neighborhood configuration encoded as a 3-bit integer
                       from the triple (left, center, right)
  R ∈ {0, 1, …, 255} — Wolfram rule number; its binary representation is
                       the 8-entry lookup table mapping each n to an output bit
  floor(R / 2^n) mod 2 — extracts the n-th bit of R
```

That is, the n-th bit of R determines the output for neighborhood configuration n. The 256 possible rules exhaustively enumerate all 1D nearest-neighbor binary automata.

### Wolfram's contribution

Wolfram's study of ECAs led to his 2002 book *A New Kind of Science* [12], which argues that simple programs (not equations) are the fundamental objects for understanding complexity in nature. While controversial in scope, the book's systematic computational exploration of rule spaces has been influential in complexity science and digital physics.

---

## Lenia

### Historical background

Lenia was created by Bert Wang-Chak Chan in 2018–2019 as a continuous generalization of Conway's Life [13]. Where Life uses binary states, discrete time, and a fixed counting kernel, Lenia introduces:

- **Continuous cell states** in [0, 1] (rather than {0, 1})
- **Continuous time** via a time resolution parameter $T$
- **Smooth ring-shaped convolution kernels** with configurable radii and bump structure
- **Smooth growth/decay functions** (Gaussian curves replacing step thresholds)

The result is an extraordinarily rich space of "artificial life" organisms — smooth gliders that look like microscopic organisms, self-replicating blobs, and complex multi-cellular structures.

### Mathematical formulation

```
1. Potential:    U(x) = K ∗ A(x, t)          (convolution of kernel with field)
2. Growth:       G(u) = 2·exp(−(u − μ)² / (2σ²)) − 1
3. Update:       A(x, t+dt) = clip(A(x, t) + dt · G(U(x)),  0,  1)

Kernel shape:    K(r) = Σ βₖ · exp(−((r/R − rₖ)² / (2·wₖ²)))
                 normalized so that ΣK = 1

where:
  A(x, t) ∈ [0, 1]  — continuous cell state at position x and time t
                        (0 = empty, 1 = fully alive)
  K                   — ring-shaped convolution kernel; zero at center, peaked
                        at characteristic radius R, with Gaussian bumps
  ∗                   — 2D discrete convolution (implemented via FFT when
                        NumPy/SciPy available, nested loops otherwise)
  U(x) ∈ [0, 1]      — local potential: weighted average of neighbors' states
  G(u) ∈ [−1, +1]    — growth function: maps potential to growth rate
                        (+1 = maximum growth, −1 = maximum decay)
  μ ∈ (0, 1)          — growth center: the potential at which growth is maximized
                        (e.g., μ = 0.15 for Orbium)
  σ > 0               — growth width: tolerance around μ
                        (e.g., σ = 0.017 for Orbium)
  R ∈ {5, …, 20}      — kernel radius in cells (e.g., R = 13 for Orbium)
  T ∈ {1, …, 20}      — time resolution: dt = 1/T (e.g., T = 10 → dt = 0.1)
  βₖ                  — kernel ring weights: control the number and relative
                        strength of concentric rings in the kernel
  clip(v, lo, hi)     — clamps v to the interval [lo, hi]
```

### Species and taxonomy

Chan documented a taxonomy of Lenia organisms analogous to biological classification [14]:

- **Orbium** — a smooth, asymmetric glider that moves diagonally
- **Geminium** — a self-replicating organism that splits into daughter cells
- **Scutium** — a compact "shield" structure that crawls across the field
- **Hydrogeminium** — a loose, fluid replicator

These species emerge from specific parameter combinations ($R$, $T$, $\mu$, $\sigma$, $\beta$) and exhibit robustness to perturbation — they can recover from damage, interact with each other, and display behavior reminiscent of biological organisms.

### Significance

Lenia demonstrates that the boundary between "alive" and "not alive" in artificial systems may be less sharp than previously thought. It has contributed to artificial life research and raised questions about whether simple continuous dynamical systems can exhibit open-ended evolution.

---

## Langton's Ant and Turmites

### Historical background

Langton's Ant was invented by Chris Langton in 1986 [15] as a two-dimensional Turing machine — an agent-based system where a single "ant" walks on an infinite grid, flipping cell colors and turning based on the cell it stands on:

```
Langton's Ant (rule string "RL"):
  1. Read color c of current cell
  2. If c = 0 (white): turn 90° clockwise   (R)
     If c = 1 (black): turn 90° counter-clockwise (L)
  3. Flip cell: c ← 1 − c
  4. Move forward one cell in current heading direction

Generalized multi-color ant (rule string of length N):
  1. Read color c ∈ {0, 1, …, N−1} of current cell
  2. Turn according to rule_string[c]:  'R' = 90° CW, 'L' = 90° CCW
  3. Set cell color: c ← (c + 1) mod N
  4. Move forward one cell

where:
  (x, y) ∈ ℤ²        — ant position on the integer grid
  heading ∈ {N,E,S,W} — ant facing direction (4 cardinal directions)
  c ∈ {0, …, N−1}    — cell color (N = length of rule string)
  rule_string         — sequence of 'R' and 'L' characters defining turn
                        direction for each color (e.g., "RL", "LLRR", "LRRL")
```

The ant's behavior is famously divided into three phases:

1. **Simplicity** (~first 500 steps) — a small symmetric pattern forms
2. **Chaos** (~500 to ~10,000 steps) — a seemingly random pseudorandom region grows
3. **Emergent order** (after ~10,000 steps) — the ant begins building a diagonal "highway," an infinitely repeating corridor, with period 104

This transition from chaos to order is one of the most striking examples of emergent behavior in simple systems. It has been conjectured (but not proven) that the highway always eventually appears from any finite initial configuration.

### Generalized turmites

Greg Turk generalized Langton's Ant to **turmites** (the name, a portmanteau of "Turk" and "termite," was coined by A. K. Dewdney in 1989 [16]) — agents with multiple internal states operating on grids with multiple colors [16]. A turmite's behavior is specified by a transition table: for each (current state, current cell color) pair, the table specifies a new cell color, a turn direction, and a new internal state.

The rule string notation encodes multi-color ants concisely. For example:
- **RL** (Langton's original) — 2 colors, turn R on white, L on black
- **LLRR** — 4 colors, producing symmetric diamond-like growth
- **LRRL** — 4 colors, builds filled squares
- **RLLR** — 4 colors, produces triangular structures

Multi-state turmites (with internal state beyond color) can produce even more complex behavior, including structures that appear to "compute" in some informal sense.

### Mathematical connection

Langton's Ant is equivalent to a specific Turing machine and is therefore capable of universal computation. It connects cellular automata to the theory of computation, demonstrating that a single mobile agent with no memory beyond its position and heading can, given the right initial conditions, perform arbitrary computations.

---

## Wa-Tor Predator-Prey Ecosystem

### Historical background

Wa-Tor was introduced by Alexander K. Dewdney in the December 1984 issue of *Scientific American*'s "Computer Recreations" column [17]. The name refers to a fictional toroidal planet covered entirely by ocean, populated by fish and sharks.

Wa-Tor is a spatial implementation of the **Lotka-Volterra equations**, the fundamental model of predator-prey dynamics introduced independently by Alfred Lotka (1925) and Vito Volterra (1926) [18]. The mean-field (non-spatial) Lotka-Volterra equations are:

```
dx/dt = α·x − β·x·y       (prey growth minus predation)
dy/dt = δ·x·y − γ·y       (predator reproduction minus starvation)

where:
  x(t) ≥ 0    — prey (fish) population at time t
  y(t) ≥ 0    — predator (shark) population at time t
  α > 0       — prey birth rate (intrinsic growth without predators)
  β > 0       — predation rate (prey consumed per predator encounter)
  δ > 0       — predator reproduction efficiency (offspring per prey eaten)
  γ > 0       — predator death rate (starvation rate without prey)
```

These produce closed-orbit population oscillations in the (x, y) phase plane.

### Spatial dynamics

Wa-Tor adds spatial structure to Lotka-Volterra by placing individual fish and sharks on a toroidal grid:

```
Fish rules (each tick):
  1. Move to a random adjacent empty cell (von Neumann neighborhood)
  2. Increment age; if age ≥ breed_time, spawn a new fish in the vacated cell
     and reset age to 0

Shark rules (each tick):
  1. If any adjacent cell contains a fish, move there and eat it (energy += 1)
     Otherwise, move to a random adjacent empty cell
  2. Decrement energy by 1; if energy ≤ 0, the shark dies (cell becomes empty)
  3. Increment age; if age ≥ breed_time, spawn a new shark in the vacated cell

where:
  breed_time (fish)  — ticks before a fish reproduces (e.g., 3 for "classic")
  breed_time (shark) — ticks before a shark reproduces (e.g., 10 for "classic")
  initial_energy     — energy a shark starts with (e.g., 3 for "classic")
  von Neumann neighborhood — the 4 orthogonal neighbors (N, S, E, W)
```

The spatial structure produces traveling population waves — bands of fish and pursuing sharks sweeping across the toroid — that are absent from the mean-field model. These spatial waves can stabilize coexistence even when the non-spatial model would predict extinction of one species.

### Ecological significance

Wa-Tor demonstrates several important ecological concepts:

- **Boom-bust cycles** — predator populations crash after consuming prey, allowing prey to recover
- **Spatial refugia** — prey can survive in regions not yet reached by predators
- **Extinction risk** — if sharks are too efficient, they can drive fish to extinction and then starve
- **Wave phenomena** — population fronts that propagate through space

---

## Falling Sand

### Historical background

Falling sand simulations originated in the early 2000s as browser-based "powder toys." The genre became widely popular through Flash-based implementations (2005–2010) and later the open-source project *The Powder Toy* (2010) [19]. These simulations model granular materials and their interactions using simple per-particle rules.

### Physics model

Each cell holds a material type with physical properties:

- **Sand** — falls under gravity, piles at an angle of repose (displaces sideways if directly blocked)
- **Water** — flows downward and spreads horizontally to fill containers
- **Stone** — static solid, forms walls and obstacles
- **Fire** — rises upward (negative gravity), ignites adjacent plant material
- **Plant** — static organic material, burns when adjacent to fire
- **Steam** — rises and dissipates over time, produced when water meets fire

The update rules approximate real granular physics:

1. Gravity pulls dense particles downward
2. Particles check below, then diagonally below-left/right (angle of repose)
3. Liquids additionally spread horizontally
4. Temperature interactions: fire + water → steam, fire + plant → more fire

### Real-world connections

Granular physics is a serious area of study in physics and engineering. Real sand exhibits phenomena including:

- **Angle of repose** — the steepest angle a pile can maintain (simulated by diagonal falling)
- **Segregation** — different-sized particles separate when shaken (Brazil nut effect)
- **Avalanches** — sandpiles exhibit self-organized criticality (see [Abelian Sandpile](#abelian-sandpile))
- **Fluidization** — sand can behave like a fluid under certain conditions

---

## Physarum Slime Mold

### Historical background

*Physarum polycephalum* is a single-celled organism that forms complex vein-like transport networks connecting food sources. Despite having no nervous system, Physarum can solve shortest-path problems, build efficient networks, and exhibit primitive forms of learning and memory [20].

The computational simulation is based on Jeff Jones' 2010 agent-based model [21], where thousands of particles perform **chemotaxis** — moving in response to chemical gradients they themselves produce. This positive feedback loop creates self-reinforcing trails that evolve into stable transport networks.

### Algorithm

```
For each agent a with position (x, y) and heading θ:

  1. SENSE:
     F_L = T(x + SD·cos(θ − SA), y + SD·sin(θ − SA))   (left sensor)
     F_C = T(x + SD·cos(θ),       y + SD·sin(θ))        (center sensor)
     F_R = T(x + SD·cos(θ + SA), y + SD·sin(θ + SA))   (right sensor)

  2. ROTATE:
     if F_C > F_L and F_C > F_R:  no turn (center strongest)
     if F_L > F_R:                 θ ← θ − RA           (turn left)
     if F_R > F_L:                 θ ← θ + RA           (turn right)
     if F_L = F_R:                 θ ← θ ± RA (random)  (tie-break)

  3. MOVE:
     x ← x + cos(θ),  y ← y + sin(θ)    (wraps at grid edges)

  4. DEPOSIT:
     T(round(x), round(y)) += deposit_rate

  5. DIFFUSE AND DECAY (applied to entire trail map T):
     T ← convolve(T, 3×3_mean_kernel) · (1 − decay_rate)

where:
  (x, y) ∈ ℝ²       — continuous agent position on the grid
  θ ∈ [0, 2π)        — agent heading angle (radians)
  T(i, j) ≥ 0        — trail map: chemical concentration at cell (i, j)
  SA                  — sensor angle: offset from heading for left/right
                        sensors (e.g., π/4 = 45° for "dendritic")
  SD                  — sensor distance: how far ahead the agent samples
                        (e.g., 9 cells for "dendritic")
  RA                  — rotation angle: how sharply the agent turns
                        (e.g., π/4 for "dendritic")
  deposit_rate        — amount of chemical deposited per step (e.g., 5.0)
  decay_rate ∈ [0,1]  — fraction of trail removed per step (e.g., 0.1)
  3×3_mean_kernel     — uniform 3×3 averaging filter for spatial diffusion
```

The interplay between deposition (positive feedback) and decay (negative feedback) determines the network morphology:

- High deposit / low decay → thick, stable veins
- Low deposit / high decay → thin, exploratory tendrils
- Wide sensor angles → diffuse, fungal-like growth
- Narrow sensor angles → tight, dendritic branching

### Scientific significance

In 2010, Tero et al. demonstrated that Physarum networks connecting food sources placed at the locations of Tokyo-area cities reproduced the topology of the actual Tokyo rail network [22]. This showed that biological optimization, operating with purely local rules, can match human-engineered infrastructure.

Physarum-inspired algorithms have since been applied to:

- **Network design** — telecommunications, road planning
- **Combinatorial optimization** — approximate solutions to NP-hard problems
- **Unconventional computing** — using actual slime mold as a computational substrate

---

## Abelian Sandpile

### Historical background

The Abelian Sandpile Model (ASM) was introduced by Per Bak, Chao Tang, and Kurt Wiesenfeld in 1987 as the first concrete model of **self-organized criticality** (SOC) [23]. SOC describes systems that naturally evolve to a critical state without any tuning of parameters — unlike phase transitions in physics, which require precise temperature control.

### Rules

```
Toppling rule:
  if z(i,j) ≥ 4:
    z(i,j)   ← z(i,j) − 4
    z(i±1,j) ← z(i±1,j) + 1
    z(i,j±1) ← z(i,j±1) + 1

Driving (single-source preset):
  z(center) ← z(center) + 1   each step

where:
  z(i,j) ∈ {0, 1, 2, …}  — grain count at cell (i, j)
  4                        — toppling threshold (= number of von Neumann neighbors)
  (i±1, j), (i, j±1)      — the 4 orthogonal neighbors
  center                   — the grid center cell (rows//2, cols//2)
```

Toppling can trigger neighboring cells to exceed threshold, producing **avalanches** that range from single cells to system-spanning cascades. Grains that topple off the grid boundary are lost (open boundary conditions).

### Mathematical properties

The ASM has remarkable algebraic structure:

- **Abelian property** — the final configuration is independent of the order in which cells topple. This is non-obvious and makes the model mathematically tractable.
- **Sandpile group** — the set of recurrent configurations forms a finite Abelian group under pointwise addition and relaxation. The identity element of this group produces striking fractal patterns.
- **Power-law avalanches** — avalanche sizes follow a power-law distribution P(s) ~ s^(-τ), the hallmark of criticality. There is no characteristic scale (τ ≈ 1.2 in 2D).
- **Fractal structure** — the single-source sandpile on an infinite grid produces a perfect fractal diamond pattern with self-similar internal structure.

### Self-organized criticality

SOC has been proposed as a unifying framework for explaining power-law distributions in nature:

- **Earthquakes** — the Gutenberg-Richter law ($\log N \sim -bM$)
- **Solar flares** — power-law energy distribution
- **Neuronal avalanches** — cascading activity in cortical networks
- **Forest fires** — size distribution of burned areas (see [Forest Fire Model](#forest-fire-model))
- **Financial markets** — power-law distribution of price changes

---

## Diffusion-Limited Aggregation

### Historical background

Diffusion-Limited Aggregation (DLA) was introduced by Tom Witten and Leonard Sander in 1981 [24]. In DLA, particles undergoing random walks (Brownian motion) stick irreversibly upon contact with a growing aggregate. The resulting structures are **fractal dendrites** — branching, tree-like shapes with a well-defined fractal dimension.

### Fractal properties

```
Mass-radius scaling:  M(r) ~ r^Df

where:
  M(r)           — number of aggregate particles within distance r of the seed
  r              — radial distance from the seed point
  Df ≈ 1.71      — fractal dimension of 2D DLA clusters (not known exactly;
                    numerically estimated from large-scale simulations)
  ~              — asymptotic proportionality for large r
```

For comparison, a solid disk has Df = 2 and a line has Df = 1. The intermediate value 1.71 reflects the branching, porous structure of the aggregate.

The branching structure arises from a screening effect: the outermost tips of the aggregate are most likely to capture incoming random walkers, because walkers approaching from far away are unlikely to penetrate deep into the fjords of the structure. This creates a positive feedback loop — tips grow faster, creating more screening, which makes tips grow even faster.

### Real-world connections

DLA-like processes govern the morphology of many natural structures:

- **Electrodeposition** — metal crystals grown by electrochemical deposition
- **Mineral dendrites** — manganese oxide formations in rock (often mistaken for fossils)
- **Dielectric breakdown** — lightning bolt paths and Lichtenberg figures
- **Bacterial colony growth** — certain bacteria form DLA-like colony shapes on nutrient-poor media
- **Frost and snowflakes** — ice crystal growth on cold surfaces (with anisotropic sticking)

---

## Forest Fire Model

### Historical background

The Forest Fire model was introduced by Drossel and Schwabl in 1992 [25] as a simplified model of self-organized criticality. Unlike the sandpile model where criticality arises from deterministic rules, the forest fire model uses stochastic rules — trees grow randomly and lightning strikes ignite random cells.

### Rules

```
State transitions (applied simultaneously each step):

  burning → empty                                        (burnout)
  tree    → burning   if any von Neumann neighbor is burning  (fire spread)
  tree    → burning   with probability f                 (lightning strike)
  empty   → tree      with probability p                 (regrowth)

where:
  state ∈ {empty, tree, burning}  — cell state
  p ∈ (0, 1)     — tree growth probability per empty cell per step
                    (e.g., p = 0.05 for "classic")
  f ∈ (0, 1)     — lightning probability per tree per step
                    (e.g., f = 0.0001 for "classic"; f ≪ p always)
  p/f            — controls cluster size at criticality; larger ratio →
                    bigger forests before fire, larger avalanches
```

When f ≪ p, large connected clusters of trees form before being destroyed by fire, producing power-law distributions of fire sizes.

### Ecological connections

While simplified, the forest fire model captures key dynamics of real fire ecology:

- **Fire size distributions** — real wildfire sizes follow approximate power laws
- **Fuel accumulation** — long periods without fire allow fuel to build up, leading to larger fires
- **Mosaic landscapes** — fires create a patchwork of different-aged vegetation
- **Critical connectivity** — the tree density at which fires can span the landscape relates to percolation theory

The model also connects to **percolation theory** — the study of connected clusters in random media. The tree density at the critical state is close to the site percolation threshold for the square lattice (~0.593), at which a spanning cluster first appears.

---

## Ising Model

### Historical background

The Ising model was proposed by Wilhelm Lenz in 1920 and solved in one dimension by his student Ernst Ising in 1924 [26]. Ising's 1D solution showed no phase transition, leading him to (incorrectly) conclude that the model could not explain ferromagnetism. Lars Onsager's exact solution of the 2D Ising model in 1944 [27] — one of the great triumphs of mathematical physics — proved that a sharp phase transition does occur in two dimensions at a critical temperature:

### Mathematical formulation

```
Hamiltonian (energy):
  H = −J · Σ⟨i,j⟩ sᵢ · sⱼ

Critical temperature (Onsager, 1944):
  Tc = 2J / (kB · ln(1 + √2)) ≈ 2.269 J/kB

Metropolis update:
  ΔE = 2J · sᵢ · Σ(neighbors j) sⱼ
  P(flip) = min(1, exp(−ΔE / (kB · T)))

where:
  sᵢ ∈ {−1, +1}   — spin at lattice site i (+1 = "up", −1 = "down")
  J = 1.0           — coupling constant (ferromagnetic; J > 0 means
                       aligned neighbors are energetically favorable)
  ⟨i,j⟩             — sum over nearest-neighbor pairs on the square lattice
                       (each site has 4 neighbors)
  H                  — total energy of the spin configuration
  T > 0              — temperature (user-adjustable; measured in units of J/kB)
  kB                 — Boltzmann constant (set to 1 in the simulation,
                       so T is in natural units)
  Tc ≈ 2.269         — critical temperature: the exact phase transition point
  ΔE                 — energy change if spin sᵢ is flipped
  P(flip) ∈ [0, 1]  — probability of accepting the proposed flip;
                       always accepted if ΔE ≤ 0 (lowers energy)
  exp(−ΔE/(kB·T))   — Boltzmann factor: thermal fluctuations allow
                       energetically unfavorable flips at higher T
```

The implementation uses a **checkerboard decomposition** for vectorized updates when NumPy is available: even and odd sublattices are updated alternately, since sites on the same sublattice are not neighbors and can be flipped simultaneously.

### Phase transition

The 2D Ising model undergoes a **second-order (continuous) phase transition** at $T_c$:

- **Below $T_c$** — spontaneous magnetization: most spins align, forming large ferromagnetic domains
- **At $T_c$** — critical fluctuations: fractal-like domain boundaries with power-law correlations spanning all length scales
- **Above $T_c$** — paramagnetic disorder: thermal fluctuations randomize spin orientations

At the critical point, the system exhibits **universality** — its statistical properties (critical exponents) depend only on dimensionality and symmetry, not on microscopic details. The 2D Ising universality class is shared by many apparently unrelated systems, from binary alloys to lattice gases to certain fluid mixtures.

### Significance

The Ising model is one of the most studied models in all of physics. It serves as:

- A pedagogical introduction to statistical mechanics and phase transitions
- A benchmark for Monte Carlo simulation methods
- A prototype for more complex magnetic models (Potts model, Heisenberg model, XY model)
- A connection between physics and machine learning (Boltzmann machines, restricted Boltzmann machines)

---

## Cyclic Cellular Automata

### Historical background

Cyclic Cellular Automata (CCA) were studied by Robert Fisch, Janko Gravner, and David Griffeath in the late 1980s and 1990s [28]. In a CCA with $N$ states, each cell holds a value in $\{0, 1, \ldots, N-1\}$. A cell in state $k$ can only be "consumed" by a neighbor in state $(k+1) \mod N$ — creating a cyclic predation hierarchy analogous to a generalized rock-paper-scissors game.

### Rules

```
Update rule:
  if any neighbor of cell (i,j) has state (k + 1) mod N:
    state(i,j) ← (k + 1) mod N          (consumed by successor)
  else:
    state(i,j) ← k                       (unchanged)

where:
  state(i,j) ∈ {0, 1, …, N−1}  — current state of cell (i, j)
  k = state(i,j)                 — shorthand for current state
  N ∈ {3, …, 20}                — number of states (e.g., N = 14 for "classic")
  (k + 1) mod N                  — the successor state that can "consume" state k
                                   (cyclic: 0 → 1 → … → N−1 → 0)
  neighbor                       — Moore neighborhood (8 surrounding cells) by default;
                                   von Neumann (4 cells) for the "von-neumann" preset
  threshold = 1                  — minimum number of successor-state neighbors
                                   required to trigger advancement (fixed at 1)
```

This asymmetric predation rule produces **spiral waves** — rotating patterns that are a hallmark of excitable media.

### Mathematical connection

CCAs are a discrete analog of **excitable media**, which arise in many physical and biological contexts:

- **Cardiac tissue** — electrical excitation waves spiral through heart muscle; spiral wave breakup is linked to cardiac fibrillation
- **Belousov-Zhabotinsky reaction** — the famous chemical oscillator produces visible spiral waves in a petri dish
- **Dictyostelium** (social amoeba) — chemotactic spiral waves coordinate aggregation
- **Neural tissue** — cortical spreading depression propagates as a wave

The number of states $N$ and the neighborhood type (Moore vs. von Neumann) control the wave characteristics: more states produce thinner, more tightly wound spirals, while fewer states produce broader, more turbulent patterns.

---

## Chimera Grid

### Background

The Chimera Grid is inspired by the concept of **chimera states** in dynamical systems — spatiotemporal patterns where coherent (synchronized) and incoherent (desynchronized) regions coexist in a system of identical coupled oscillators [29]. First discovered by Yoshiki Kuramoto and Dorjsuren Battogtokh in 2002, chimera states were initially considered paradoxical: how can identical elements under identical coupling spontaneously break into ordered and disordered groups?

### Implementation

In this simulator, the chimera concept is adapted to cellular automata: the grid is partitioned into spatial zones, each governed by a different B/S ruleset. Cells obey their zone's rule, but their neighbor counts include cells from all adjacent zones regardless of rule boundaries. This creates emergent interface dynamics — gliders from one system interact with a different system's physics at zone boundaries, producing patterns that exist in neither rule alone.

### Significance

The chimera grid demonstrates a general principle in complex systems: **boundary effects and heterogeneity can produce emergent behaviors that don't exist in any homogeneous subsystem**. This is relevant to:

- **Ecological boundaries** (ecotones) where different biomes meet
- **Material interfaces** in condensed matter physics
- **Cultural contact zones** in social dynamics

---

## Particle Life

### Historical background

Particle Life (also called "Primordial Soup" or "Clusters") was popularized by Jeffrey Ventrella and later by Tom Mohr and Hunar Ahmad in online interactive demonstrations (2018–2022) [30]. It is a minimalist model of emergent complexity: multiple species of particles interact via pairwise attraction/repulsion forces, with each species pair having a different interaction strength.

### Force model

```
Force kernel between particle of species i and particle of species j at distance r:

  F(r) = repulsion · (1 − r/r_min)              if r < r_min        (hard core)
       = α(i,j) · (r − r_min) / (r_max − r_min) if r_min ≤ r ≤ r_max (interaction)
       = 0                                        if r > r_max        (out of range)

Velocity update (symplectic Euler):
  v ← v + Σ F(r) · r̂ · force_scale · dt
  v ← v · (1 − friction)                        (velocity damping)
  x ← x + v · dt                                (position update, toroidal wrap)

where:
  r = |xᵢ − xⱼ|        — distance between two particles (toroidal metric)
  r̂                     — unit vector from particle j toward particle i
  r_min = 0.3 · r_max   — repulsion radius: prevents particle overlap
  r_max                  — interaction radius (e.g., 80 world units for "primordial")
  α(i,j) ∈ [−1, +1]     — interaction matrix entry: +1 = full attraction,
                           −1 = full repulsion. Note: α(i,j) ≠ α(j,i) in general
                           (asymmetric interactions enable pursuit/evasion)
  force_scale            — global force multiplier (e.g., 1.0)
  friction ∈ [0, 1]     — velocity damping per step (e.g., 0.1 for "primordial")
  dt = 1.0              — time step
```

The interaction matrix α is the key parameter: a random matrix produces unpredictable "primordial soup" dynamics, while carefully chosen matrices produce clusters, orbits, chains, and swarm behaviors.

### Significance

Particle Life demonstrates how **complex, life-like behavior can emerge from simple pairwise interactions** without any explicit programming of higher-level behavior. The asymmetry of the interaction matrix ($\alpha_{ij} \neq \alpha_{ji}$) is crucial — it breaks Newton's third law and enables pursuit/evasion dynamics similar to predator-prey systems.

This relates to broader questions in artificial life about the minimal conditions for open-ended complexity and self-organization.

---

## Lattice Boltzmann Fluid Dynamics

### Historical background

The Lattice Boltzmann Method (LBM) evolved from lattice gas automata (LGA) in the late 1980s and early 1990s [31]. While the Navier-Stokes equations describe fluid motion at the macroscopic level, LBM operates at the **mesoscopic** level — tracking statistical distributions of particle velocities on a discrete lattice, from which macroscopic behavior (density, velocity, pressure) emerges.

The D2Q9 model (2 dimensions, 9 velocity directions) uses a square lattice where each cell stores 9 distribution functions $f_i$, one for each lattice velocity (center, 4 cardinal directions, 4 diagonals).

### Mathematical formulation

```
Lattice Boltzmann equation (BGK collision + streaming):

  Collision: f̃ᵢ(x, t)  = fᵢ(x, t) − (1/τ) · [fᵢ(x, t) − fᵢᵉᑫ(x, t)]
  Streaming: fᵢ(x + eᵢ, t+1) = f̃ᵢ(x, t)

Equilibrium distribution:
  fᵢᵉᑫ = wᵢ · ρ · [1 + (eᵢ · u)/cs² + (eᵢ · u)²/(2·cs⁴) − (u · u)/(2·cs²)]

Macroscopic quantities (moments):
  ρ   = Σᵢ fᵢ               (density)
  ρ·u = Σᵢ fᵢ · eᵢ          (momentum → velocity u = Σfᵢeᵢ / ρ)

where:
  fᵢ(x, t)           — distribution function for velocity direction i at
                        lattice position x and time step t. Represents the
                        probability of finding a particle moving in direction eᵢ.
  i ∈ {0, 1, …, 8}   — index over the 9 lattice velocities (D2Q9 model):
                        i=0: rest (0,0); i=1–4: cardinal (±1,0), (0,±1);
                        i=5–8: diagonal (±1,±1)
  eᵢ                  — lattice velocity vector for direction i
  τ > 0.5             — relaxation time; controls kinematic viscosity via
                        ν = cs² · (τ − 0.5). Smaller τ → lower viscosity →
                        higher Reynolds number. Implementation values:
                        τ = 0.8 (cavity), 0.55 (karman), 0.7 (convection)
  wᵢ                  — lattice weights: w₀ = 4/9, w₁₋₄ = 1/9, w₅₋₈ = 1/36
  cs² = 1/3           — lattice speed of sound squared
  ρ                   — macroscopic fluid density at position x
  u = (ux, uy)        — macroscopic fluid velocity at position x
  fᵢᵉᑫ                — local equilibrium distribution (Maxwell-Boltzmann
                        expanded to second order in Mach number)
```

Boundary conditions use **bounce-back** (no-slip) on solid walls and **Zou-He** velocity boundaries for driven surfaces.

### Presets

The three presets demonstrate canonical problems in computational fluid dynamics:

- **Lid-driven cavity** — a classic benchmark: the top wall moves rightward, creating corner vortices through viscous coupling
- **Kármán vortex street** — flow past a bluff body (cylinder) at moderate Reynolds number sheds alternating vortices, producing a periodic wake structure. Named after Theodore von Kármán (1911)
- **Rayleigh-Bénard convection** — a fluid heated from below becomes unstable above a critical Rayleigh number, forming convective rolls. This is a fundamental process in atmospheric and oceanic circulation

### Why LBM?

LBM is widely used in computational physics and engineering because:

- It naturally handles complex geometries (bounce-back boundary conditions)
- It is inherently parallel (each cell updates independently during collision)
- It can incorporate multiphase flows, thermal transport, and other physics naturally
- The streaming step is exact (no numerical diffusion)

---

## Boids Flocking

### Historical background

The Boids algorithm was invented by Craig Reynolds in 1986 and presented at SIGGRAPH 1987 [32]. Reynolds demonstrated that realistic flocking behavior could emerge from three simple rules applied to each individual agent ("boid"):

1. **Separation** — steer to avoid crowding local flockmates
2. **Alignment** — steer toward the average heading of local flockmates
3. **Cohesion** — steer toward the average position (center of mass) of local flockmates

Each rule operates only on neighbors within a limited perception radius, meaning boids have no knowledge of the global flock state. The emergent behavior — coordinated turns, splitting around obstacles, re-merging — arises purely from local interactions.

### Mathematical formulation

```
For each boid i with position pᵢ and velocity vᵢ:

  Separation:  F_sep   = −Σⱼ (pⱼ − pᵢ) / |pⱼ − pᵢ|²     (avoid crowding)
  Alignment:   F_align = (1/|Nᵢ|) · Σⱼ vⱼ − vᵢ           (match heading)
  Cohesion:    F_coh   = (1/|Nᵢ|) · Σⱼ pⱼ − pᵢ           (steer to center)

  Total force: F = ws · F_sep + wa · F_align + wc · F_coh

  Velocity update:
    vᵢ ← vᵢ + F
    vᵢ ← vᵢ · min(1, v_max / |vᵢ|)      (clamp to max speed)
    pᵢ ← pᵢ + vᵢ                          (toroidal wrap)

where:
  pᵢ = (x, y) ∈ ℝ²     — continuous position of boid i
  vᵢ = (vx, vy) ∈ ℝ²   — velocity vector of boid i
  Nᵢ                     — set of boids within perception radius of boid i
                           (e.g., radius = 60 world units for "flock")
  |Nᵢ|                   — number of neighbors (sums exclude self)
  Σⱼ                     — sum over all j ∈ Nᵢ
  ws, wa, wc              — steering weights:
                           ws = separation weight (e.g., 0.05 for "flock")
                           wa = alignment weight  (e.g., 0.05 for "flock")
                           wc = cohesion weight   (e.g., 0.005 for "flock")
  v_max                   — maximum speed (e.g., 4.0 world units per step)
```

### Extensions

The simulator implements several extensions beyond the original model:

- **Predators** — special agents that chase the nearest boid; boids within flight distance apply a flee force, creating realistic evasion behavior
- **Obstacles** — boids detect and steer around circular obstacles
- **Murmurations** — dense flocks with predator perturbation produce the mesmerizing cloud-like patterns seen in starling flocks at dusk

### Real-world applications

Reynolds' boids model has been applied to:

- **Computer animation** — flocking behavior in films (the first use was the bat swarm in *Batman Returns*, 1992)
- **Robotics** — swarm coordination for drone fleets and autonomous vehicles
- **Crowd simulation** — pedestrian movement in architectural planning and game design
- **Ecology** — modeling fish schools, bird flocks, and insect swarms

---

## Wave Function Collapse

### Historical background

The Wave Function Collapse (WFC) algorithm was created by Maxim Gumin in 2016 [33], inspired by quantum mechanics but operating as a classical constraint-satisfaction algorithm for procedural generation. The name refers to the analogy with quantum superposition: each cell starts in a "superposition" of all possible tiles and "collapses" to a definite state through observation and constraint propagation.

### Algorithm

```
1. INITIALIZE:
   For each cell (i, j):  possible(i,j) ← {all tiles}

2. OBSERVE (select lowest-entropy uncollapsed cell):
   (i*, j*) = argmin  H(i, j)   over all uncollapsed cells
   H(i, j)  = −Σₜ wₜ · log(wₜ)   (Shannon entropy)

3. COLLAPSE:
   Choose tile t ∈ possible(i*, j*) with probability ∝ wₜ
   possible(i*, j*) ← {t}

4. PROPAGATE (worklist-based constraint propagation):
   Add (i*, j*) to worklist
   While worklist not empty:
     Pop cell (i, j)
     For each neighbor (i', j') in {N, S, E, W}:
       Remove any tile t' from possible(i', j') that is incompatible
         with all remaining tiles in possible(i, j) for that direction
       If possible(i', j') changed, add (i', j') to worklist
       If possible(i', j') = ∅, CONTRADICTION → restart

5. REPEAT steps 2–4 until all cells collapsed

where:
  possible(i, j)  — set of tiles still allowed at cell (i, j)
  wₜ > 0          — weight of tile t (controls relative frequency;
                     higher weight → more likely to be chosen)
  H(i, j)         — Shannon entropy: measures uncertainty at cell (i, j);
                     lower H = more constrained = selected first
  adjacency rules — per-preset lookup table: for each tile and each
                     direction (N/S/E/W), which tiles are allowed as neighbors
  contradiction   — a cell with zero remaining possibilities; triggers restart
```

### Connection to constraint satisfaction

WFC is essentially a specialized constraint-satisfaction solver optimized for tile-based procedural generation. It relates to:

- **Arc consistency** algorithms from AI (Mackworth, 1977)
- **Belief propagation** on factor graphs
- **Sudoku solving** — WFC can be viewed as a generalized Sudoku solver

### Applications

WFC has been widely adopted in game development and creative coding:

- **Procedural level generation** — Caves of Qud, Bad North, Townscaper
- **Texture synthesis** — generating tileable textures from example images
- **Architecture** — generating building layouts and floor plans
- **Music** — generating note sequences that satisfy harmonic constraints

---

## 2D Wave Equation

### Historical background

The wave equation is one of the oldest and most fundamental partial differential equations in physics, first derived by Jean le Rond d'Alembert in 1747 for vibrating strings [34]. The 2D wave equation describes vibrations of membranes (drumheads), shallow water waves, electromagnetic wave propagation, and acoustic pressure fields.

### Mathematical formulation

```
Continuous PDE (damped 2D wave equation):
  ∂²u/∂t² = c² · (∂²u/∂x² + ∂²u/∂y²) − γ · ∂u/∂t

Discrete update (Verlet integration with 5-point Laplacian):
  L(i,j) = u(i+1,j) + u(i−1,j) + u(i,j+1) + u(i,j−1) − 4·u(i,j)

  u_new(i,j) = 2·u(i,j) − u_prev(i,j) + c²·L(i,j) − γ·(u(i,j) − u_prev(i,j))

Boundary conditions:
  u(i,j) = 0   for all edge cells (Dirichlet / fixed boundary)

where:
  u(i, j, t) ∈ ℝ     — displacement of the membrane at cell (i, j), step t
                         (positive = crest, negative = trough, 0 = quiescent)
  u_prev(i, j)        — displacement at the previous time step (Verlet requires
                         two time levels)
  c ∈ (0, 0.5]        — wave propagation speed (CFL stability requires c ≤ 0.5
                         on a unit grid). Preset values:
                         ripple: 0.30, pluck: 0.40, drum: 0.25, ocean: 0.35,
                         resonance: 0.45
  γ ≥ 0               — damping coefficient (energy dissipation per step).
                         Preset values:
                         ripple: 0.002, pluck: 0.001, drum: 0.003, ocean: 0.0005,
                         resonance: 0.0002
  L(i,j)              — discrete Laplacian: 5-point stencil approximation of
                         ∇²u = ∂²u/∂x² + ∂²u/∂y²
  Dirichlet boundary   — edges are clamped at zero displacement, causing
                         reflection with phase inversion (like a drumhead rim)
```

### Wave phenomena

The simulation demonstrates several fundamental wave phenomena:

- **Circular wavefronts** — point sources create expanding rings (Huygens' principle)
- **Reflection** — waves bounce off fixed boundaries with phase inversion
- **Interference** — constructive and destructive superposition of multiple waves
- **Standing waves** — resonant modes of the bounded membrane (low damping)
- **Diffraction** — waves bending around obstacles and through gaps

### Real-world connections

The 2D wave equation governs:

- **Drum vibrations** — the modes of a circular or rectangular drumhead
- **Shallow water waves** — tsunami propagation in the linear regime
- **Electromagnetic waves** — Maxwell's equations reduce to the wave equation in free space
- **Seismology** — surface wave propagation during earthquakes

---

## Smoothed Particle Hydrodynamics

### Historical background

Smoothed Particle Hydrodynamics (SPH) was independently developed by Robert Gingold and Joseph Monaghan [35] and by Leon Lucy [36] in 1977, originally for astrophysical simulations (star formation, galaxy collisions). SPH is a **meshless Lagrangian method**: instead of solving fluid equations on a fixed grid, it tracks individual fluid parcels ("particles") that carry mass, velocity, density, and pressure.

### Mathematical formulation

```
SPH field approximation:
  A(r) ≈ Σⱼ mⱼ · (Aⱼ / ρⱼ) · W(r − rⱼ, h)

Density estimation (Poly6 kernel):
  ρᵢ = Σⱼ mⱼ · W_poly6(|rᵢ − rⱼ|, h)
  W_poly6(r, h) = (315 / 64πh⁹) · (h² − r²)³     for r ≤ h, else 0

Pressure force (Spiky gradient):
  F_pressure = −Σⱼ mⱼ · (Pᵢ/ρᵢ² + Pⱼ/ρⱼ²) · ∇W_spiky(rᵢ − rⱼ, h)
  ∇W_spiky(r, h) = −(45 / πh⁶) · (h − r)² · r̂    for r ≤ h, else 0

Viscous force (Viscosity Laplacian):
  F_viscosity = μ · Σⱼ mⱼ · (vⱼ − vᵢ)/ρⱼ · ∇²W_visc(|rᵢ − rⱼ|, h)
  ∇²W_visc(r, h) = (45 / πh⁶) · (h − r)           for r ≤ h, else 0

Equation of state:
  P = k · (ρ − ρ₀)

Total acceleration:
  dvᵢ/dt = F_pressure + F_viscosity + g

where:
  rᵢ = (x, y) ∈ ℝ²      — position of particle i
  vᵢ = (vx, vy) ∈ ℝ²    — velocity of particle i
  mⱼ                      — mass of particle j (uniform, = 1.0)
  ρᵢ > 0                  — density at particle i (computed from neighbors)
  ρ₀                       — rest density (target density; e.g., 1.0)
  Pᵢ                       — pressure at particle i (from equation of state)
  k > 0                    — stiffness constant (bulk modulus; e.g., 200.0;
                             higher k → less compressible fluid)
  h > 0                    — smoothing radius: support of all kernels
                             (e.g., h = 16 world units; particles beyond h
                             have zero influence)
  r = |rᵢ − rⱼ|           — distance between particles i and j
  r̂                        — unit vector from particle j to particle i
  μ > 0                    — dynamic viscosity coefficient (e.g., 0.8 for "dam";
                             higher μ → thicker, more viscous fluid)
  g = (0, gravity)         — gravitational acceleration (e.g., gravity = 0.4
                             for "dam" preset; downward)
  W, ∇W, ∇²W              — smoothing kernel, its gradient, and its Laplacian
                             (each kernel variant is optimized for a specific
                             physical quantity — see kernel descriptions above)
  Σⱼ                       — sum over all particles j within distance h of
                             particle i (O(n²) pairwise in implementation)
```

### Comparison with LBM

This simulator includes both Eulerian ([LBM](#lattice-boltzmann-fluid-dynamics)) and Lagrangian (SPH) fluid solvers, demonstrating the two fundamental perspectives in computational fluid dynamics:

| Property | LBM (Eulerian) | SPH (Lagrangian) |
|----------|----------------|-------------------|
| Grid | Fixed lattice | No grid (particles) |
| Tracks | Distribution functions at fixed points | Individual fluid parcels |
| Free surfaces | Difficult | Natural |
| Complex boundaries | Easy (bounce-back) | Moderate |
| Best for | Internal flows, porous media | Splashing, free-surface, astrophysics |

### Real-world applications

SPH is used in:

- **Astrophysics** — galaxy formation, supernova explosions, neutron star mergers
- **Engineering** — dam break analysis, sloshing in fuel tanks, coastal wave impact
- **Computer graphics** — real-time fluid effects in films and games
- **Geophysics** — landslide and debris flow simulation

---

## References

[1] M. Gardner, "The Fantastic Combinations of John Conway's New Solitaire Game 'Life'," *Scientific American*, vol. 223, no. 4, pp. 120–123, October 1970.

[2] E. R. Berlekamp, J. H. Conway, and R. K. Guy, *Winning Ways for Your Mathematical Plays*, vol. 2, Academic Press, 1982, ch. 25.

[3] B. Silverman, "Wireworld," originally implemented at the MIT Media Lab, 1987. Described in A. K. Dewdney, "Computer Recreations: The cellular automata programs that create Wireworld, Rugworld and other diversions," *Scientific American*, vol. 262, no. 1, pp. 146–149, January 1990.

[4] D. Moore and M. Owen, "The Wireworld Computer," 2004. Available: https://www.quinapalus.com/wi-index.html

[5] A. M. Turing, "The Chemical Basis of Morphogenesis," *Philosophical Transactions of the Royal Society of London B*, vol. 237, no. 641, pp. 37–72, 1952.

[6] P. Gray and S. K. Scott, "Autocatalytic reactions in the isothermal, continuous stirred tank reactor: Oscillations and instabilities in the system A + 2B → 3B; B → C," *Chemical Engineering Science*, vol. 39, no. 6, pp. 1087–1097, 1984.

[7] J. E. Pearson, "Complex Patterns in a Simple System," *Science*, vol. 261, no. 5118, pp. 189–192, July 1993.

[8] S. Kondo and R. Asai, "A reaction-diffusion wave on the skin of the marine angelfish *Pomacanthus*," *Nature*, vol. 376, pp. 765–768, 1995.

[9] S. Wolfram, "Statistical mechanics of cellular automata," *Reviews of Modern Physics*, vol. 55, no. 3, pp. 601–644, July 1983.

[10] C. G. Langton, "Studying artificial life with cellular automata," *Physica D*, vol. 22, no. 1–3, pp. 120–149, 1986.

[11] M. Cook, "Universality in Elementary Cellular Automata," *Complex Systems*, vol. 15, no. 1, pp. 1–40, 2004.

[12] S. Wolfram, *A New Kind of Science*, Wolfram Media, 2002.

[13] B. W.-C. Chan, "Lenia: Biology of Artificial Life," *Complex Systems*, vol. 28, no. 3, pp. 251–286, 2019.

[14] B. W.-C. Chan, "Lenia and Expanded Universe," in *Proceedings of the 2020 Conference on Artificial Life (ALIFE 2020)*, pp. 221–229, MIT Press, 2020.

[15] C. G. Langton, "Studying artificial life with cellular automata," *Physica D*, vol. 22, pp. 120–149, 1986.

[16] A. K. Dewdney, "Computer Recreations: Two-dimensional Turing machines and Tur-mites make tracks on a plane," *Scientific American*, vol. 261, no. 3, pp. 180–183, September 1989. (Turmites named after Greg Turk's work on 2D Turing machines.)

[17] A. K. Dewdney, "Computer Recreations: Sharks and fish wage an ecological war on the toroidal planet Wa-Tor," *Scientific American*, vol. 251, no. 6, pp. 14–22, December 1984.

[18] A. J. Lotka, *Elements of Physical Biology*, Williams & Wilkins, 1925. V. Volterra, "Variazioni e fluttuazioni del numero d'individui in specie animali conviventi," *Memorie della Regia Accademia Nazionale dei Lincei*, vol. 2, pp. 31–113, 1926.

[19] S. K. Skowronek et al., *The Powder Toy*, open-source falling-sand physics sandbox, https://powdertoy.co.uk, 2008–present.

[20] T. Nakagaki, H. Yamada, and Á. Tóth, "Intelligence: Maze-solving by an amoeboid organism," *Nature*, vol. 407, p. 470, 2000.

[21] J. Jones, "Characteristics of pattern formation and evolution in approximations of Physarum transport networks," *Artificial Life*, vol. 16, no. 2, pp. 127–153, 2010.

[22] A. Tero, S. Takagi, T. Saigusa, K. Ito, D. P. Bebber, M. D. Fricker, K. Yumiki, R. Kobayashi, and T. Nakagaki, "Rules for Biologically Inspired Adaptive Network Design," *Science*, vol. 327, no. 5964, pp. 439–442, January 2010.

[23] P. Bak, C. Tang, and K. Wiesenfeld, "Self-organized criticality: An explanation of the 1/f noise," *Physical Review Letters*, vol. 59, no. 4, pp. 381–384, July 1987.

[24] T. A. Witten and L. M. Sander, "Diffusion-Limited Aggregation, a Kinetic Critical Phenomenon," *Physical Review Letters*, vol. 47, no. 19, pp. 1400–1403, November 1981.

[25] B. Drossel and F. Schwabl, "Self-organized critical forest-fire model," *Physical Review Letters*, vol. 69, no. 11, pp. 1629–1632, September 1992.

[26] E. Ising, "Beitrag zur Theorie des Ferromagnetismus," *Zeitschrift für Physik*, vol. 31, pp. 253–258, 1925.

[27] L. Onsager, "Crystal Statistics. I. A Two-Dimensional Model with an Order-Disorder Transition," *Physical Review*, vol. 65, no. 3–4, pp. 117–149, February 1944.

[28] R. Fisch, J. Gravner, and D. Griffeath, "Threshold-range scaling of excitable cellular automata," *Statistics and Computing*, vol. 1, no. 1, pp. 23–39, 1991.

[29] Y. Kuramoto and D. Battogtokh, "Coexistence of Coherence and Incoherence in Nonlocally Coupled Phase Oscillators," *Nonlinear Phenomena in Complex Systems*, vol. 5, no. 4, pp. 380–385, 2002.

[30] J. Ventrella, *Clusters*, interactive particle life simulation, http://www.ventrella.com/Clusters/. H. Ahmad, "Particle Life," https://particle-life.com, 2022.

[31] S. Chen and G. D. Doolen, "Lattice Boltzmann Method for Fluid Flows," *Annual Review of Fluid Mechanics*, vol. 30, pp. 329–364, 1998.

[32] C. W. Reynolds, "Flocks, herds and schools: A distributed behavioral model," *Computer Graphics (SIGGRAPH '87)*, vol. 21, no. 4, pp. 25–34, 1987.

[33] M. Gumin, "WaveFunctionCollapse," GitHub repository, 2016. Available: https://github.com/mxgmn/WaveFunctionCollapse

[34] J. d'Alembert, "Recherches sur la courbe que forme une corde tendue mise en vibration," *Histoire de l'Académie Royale des Sciences et Belles Lettres de Berlin*, vol. 3, pp. 214–219, 1747.

[35] R. A. Gingold and J. J. Monaghan, "Smoothed particle hydrodynamics: theory and application to non-spherical stars," *Monthly Notices of the Royal Astronomical Society*, vol. 181, no. 3, pp. 375–389, 1977.

[36] L. B. Lucy, "A numerical approach to the testing of the fission hypothesis," *The Astronomical Journal*, vol. 82, pp. 1013–1024, December 1977.
