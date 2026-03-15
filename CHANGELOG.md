# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-03-15

### Simulation modes (28 total)

- **Conway's Game of Life** — Classic B3/S23 with glider, pulsar, gosper gun patterns
- **HighLife** (B36/S23), **Day & Night** (B3678/S34678), **Seeds** (B2/S),
  **Diamoeba** (B35678/S5678), **Morley** (B368/S245), **2x2** (B36/S125),
  **Maze** (B3/S12345) — 8 preset B/S rulesets plus arbitrary B/S notation
- **Wireworld** — 4-state logic circuit automaton with built-in gates
- **Gray-Scott** — Continuous reaction-diffusion (8 presets: mitosis, coral, solitons, etc.)
- **Lenia** — Smooth-kernel continuous CA (6 species: orbium, geminium, etc.)
- **Elementary CA** — All 256 Wolfram rules with space-time diagrams
- **Langton's Ant / Turmites** — Agent-based walkers (8 presets)
- **Wa-Tor** — Predator-prey ecosystem dynamics (6 presets)
- **Falling Sand** — Gravity-driven particle physics sandbox (6 presets)
- **Physarum** — Slime mold chemotaxis transport networks (6 presets)
- **Abelian Sandpile** — Self-organized criticality with fractal avalanches (4 presets)
- **DLA** — Diffusion-limited aggregation fractal growth (4 presets)
- **Forest Fire** — Stochastic probabilistic burning (5 presets)
- **Ising Model** — Statistical mechanics spin simulation (5 presets)
- **Cyclic CA** — Spiral wave generation (5 presets)
- **Chimera Grid** — Multi-rule coexistence zones (5 presets)
- **Particle Life** — Emergent multi-species particle interactions (5 presets)
- **LBM Fluid** — Lattice Boltzmann D2Q9 fluid dynamics (3 presets)
- **Boids** — Flocking/swarming simulation (5 presets)
- **Wave Function Collapse** — Constraint-based procedural generation (4 presets)
- **2D Wave Equation** — Damped membrane simulation (5 presets)
- **SPH Fluid** — Smoothed particle hydrodynamics (4 presets)

### Features

- Interactive terminal UI via curses with real-time controls
- Cell editor with select, copy/paste, rotate, flip, pattern stamps
- Save/load patterns in RLE and `.cells` formats
- Cell aging with color gradients
- Population statistics dashboard with live graph
- Time-travel: rewind, scrub, and fork history (up to 10,000 generations)
- Animated GIF export (pure Python encoder)
- Headless PNG batch rendering with 5 color palettes
- High-density Braille rendering mode (8x resolution)
- HashLife quadtree engine for exponential-speed generation skipping
- Alternative topologies: torus, Klein bottle, Mobius strip, bounded
- Vectorized NumPy/SciPy backend with automatic fallback
- Scripting engine for user-programmable automation
- Real-time pattern recognition (gliders, oscillators, still lifes)
- Sound synthesis mode (sonifies CA activity)
- Multiplayer collaborative editing over TCP
- Genetic algorithm rule discovery mode
- Split-screen comparison mode
- Demo reel screensaver (auto-cycles all modes)
