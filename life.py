#!/usr/bin/env python3
"""Terminal-based cellular automaton simulator with multiple rulesets."""

import argparse
import copy
import curses
import json
import math
import os
import queue
import re
import select
import socket
import struct
import threading
import time
import zlib

# --- Optional NumPy/SciPy for vectorized compute backend ---

try:
    import numpy as np
    from scipy.signal import convolve2d
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# --- Rulesets (Birth/Survival notation) ---

RULES = {
    "life":      {"b": {3}, "s": {2, 3}, "name": "Conway's Life (B3/S23)"},
    "highlife":  {"b": {3, 6}, "s": {2, 3}, "name": "HighLife (B36/S23)"},
    "daynight":  {"b": {3, 6, 7, 8}, "s": {3, 4, 6, 7, 8}, "name": "Day & Night (B3678/S34678)"},
    "seeds":     {"b": {2}, "s": set(), "name": "Seeds (B2/S)"},
    "diamoeba":  {"b": {3, 5, 6, 7, 8}, "s": {5, 6, 7, 8}, "name": "Diamoeba (B35678/S5678)"},
    "morley":    {"b": {3, 6, 8}, "s": {2, 4, 5}, "name": "Morley (B368/S245)"},
    "2x2":       {"b": {3, 6}, "s": {1, 2, 5}, "name": "2x2 (B36/S125)"},
    "maze":      {"b": {3}, "s": {1, 2, 3, 4, 5}, "name": "Maze (B3/S12345)"},
    "wireworld": {"b": set(), "s": set(), "name": "Wireworld", "wireworld": True},
    "grayscott": {"b": set(), "s": set(), "name": "Gray-Scott (Mitosis)", "grayscott": True},
    "elementary": {"b": set(), "s": set(), "name": "Elementary CA (Rule 30)", "elementary": True},
    "lenia":      {"b": set(), "s": set(), "name": "Lenia (Orbium)", "lenia": True},
    "turmite":    {"b": set(), "s": set(), "name": "Langton's Ant", "turmite": True},
    "wator":      {"b": set(), "s": set(), "name": "Wa-Tor (Classic)", "wator": True},
    "fallingsand": {"b": set(), "s": set(), "name": "Falling Sand", "fallingsand": True},
    "physarum": {"b": set(), "s": set(), "name": "Physarum (dendritic)", "physarum": True},
}

RULE_NAMES = list(RULES.keys())

# --- Topology Modes ---
# Each topology defines how coordinates wrap at grid boundaries.
TOPO_TORUS = "torus"          # both axes wrap normally
TOPO_KLEIN = "klein"          # horizontal wraps with row-reversal (Klein bottle)
TOPO_MOBIUS = "mobius"        # horizontal wraps with row-reversal, vertical bounded
TOPO_BOUNDED = "bounded"      # no wrapping — edges are dead

TOPOLOGIES = [TOPO_TORUS, TOPO_KLEIN, TOPO_MOBIUS, TOPO_BOUNDED]

TOPOLOGY_LABELS = {
    TOPO_TORUS: "Torus",
    TOPO_KLEIN: "Klein Bottle",
    TOPO_MOBIUS: "Möbius Strip",
    TOPO_BOUNDED: "Bounded",
}

# Current topology — module-level default so step functions can access it.
_topology = TOPO_TORUS


def _wrap_coords(r, c, rows, cols, topology=None):
    """Map (r, c) to valid grid coordinates under the given topology.

    Returns (nr, nc) or None if the cell is out-of-bounds (bounded mode).
    For Klein bottle, wrapping horizontally reverses the row.
    For Möbius strip, wrapping horizontally reverses the row; vertical is bounded.
    """
    if topology is None:
        topology = _topology

    if topology == TOPO_TORUS:
        return r % rows, c % cols

    if topology == TOPO_KLEIN:
        # Vertical axis wraps normally
        r = r % rows
        # Horizontal axis: if we crossed a boundary, flip row
        if c < 0 or c >= cols:
            c = c % cols
            r = (rows - 1 - r)
        return r, c

    if topology == TOPO_MOBIUS:
        # Vertical axis: bounded (no wrap)
        if r < 0 or r >= rows:
            return None
        # Horizontal axis: wraps with row reversal
        if c < 0 or c >= cols:
            c = c % cols
            r = (rows - 1 - r)
        return r, c

    if topology == TOPO_BOUNDED:
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return None
        return r, c

    # Fallback: torus
    return r % rows, c % cols


# --- Wireworld Cell States ---
WW_EMPTY = 0       # empty / background
WW_HEAD = 1         # electron head
WW_TAIL = 2         # electron tail
WW_CONDUCTOR = 3    # conductor (wire)


def _is_wireworld(rule):
    """Check if the current rule is the Wireworld automaton."""
    return rule.get("wireworld", False)


def _is_grayscott(rule):
    """Check if the current rule is the Gray-Scott reaction-diffusion model."""
    return rule.get("grayscott", False)


def _is_elementary(rule):
    """Check if the current rule is a 1D Elementary Cellular Automaton."""
    return rule.get("elementary", False)


def _is_lenia(rule):
    """Check if the current rule is a Lenia continuous cellular automaton."""
    return rule.get("lenia", False)


def _is_turmite(rule):
    """Check if the current rule is a Langton's Ant / turmite."""
    return rule.get("turmite", False)


def _is_wator(rule):
    """Check if the current rule is the Wa-Tor predator-prey simulation."""
    return rule.get("wator", False)


def _is_fallingsand(rule):
    """Check if the current rule is the Falling Sand particle simulation."""
    return rule.get("fallingsand", False)


def _is_physarum(rule):
    """Check if the current rule is the Physarum slime mold simulation."""
    return rule.get("physarum", False)


# --- Wa-Tor Predator-Prey Ecosystem ---
# A. K. Dewdney's Wa-Tor simulation: fish and sharks on a toroidal ocean.
# Fish breed after a set number of ticks.  Sharks hunt fish for energy and
# starve if they don't eat.  Produces emergent boom-bust population waves.

WATOR_PRESETS = {
    "classic":    {"fish_breed": 3, "shark_breed": 10, "shark_starve": 4,
                   "fish_pct": 0.30, "shark_pct": 0.05,
                   "name": "Classic"},
    "fast_breed": {"fish_breed": 2, "shark_breed": 6, "shark_starve": 3,
                   "fish_pct": 0.35, "shark_pct": 0.08,
                   "name": "Fast Breed"},
    "sparse":     {"fish_breed": 5, "shark_breed": 15, "shark_starve": 6,
                   "fish_pct": 0.15, "shark_pct": 0.03,
                   "name": "Sparse Ocean"},
    "sharks_rule":{"fish_breed": 4, "shark_breed": 8, "shark_starve": 8,
                   "fish_pct": 0.25, "shark_pct": 0.12,
                   "name": "Sharks Rule"},
    "volatile":   {"fish_breed": 2, "shark_breed": 12, "shark_starve": 3,
                   "fish_pct": 0.40, "shark_pct": 0.06,
                   "name": "Volatile"},
    "equilibrium":{"fish_breed": 4, "shark_breed": 12, "shark_starve": 5,
                   "fish_pct": 0.20, "shark_pct": 0.04,
                   "name": "Equilibrium"},
}
WATOR_PRESET_NAMES = list(WATOR_PRESETS.keys())

# Cell types
_WATOR_EMPTY = 0
_WATOR_FISH = 1
_WATOR_SHARK = 2

# Module-level state
_wator_grid = None       # 2D array: 0=empty, 1=fish, 2=shark
_wator_fish_age = None   # 2D array: ticks since last breed (fish only)
_wator_shark_age = None  # 2D array: ticks since last breed (shark only)
_wator_shark_energy = None  # 2D array: energy counter (shark only)
_wator_preset_idx = 0
_wator_fish_breed = 3
_wator_shark_breed = 10
_wator_shark_starve = 4
_wator_rows = 0
_wator_cols = 0


def _wator_init(rows, cols, preset_name=None):
    """Initialize the Wa-Tor ocean with fish and sharks."""
    import random as _rnd
    global _wator_grid, _wator_fish_age, _wator_shark_age, _wator_shark_energy
    global _wator_fish_breed, _wator_shark_breed, _wator_shark_starve
    global _wator_rows, _wator_cols, _wator_preset_idx

    if preset_name is None:
        preset_name = WATOR_PRESET_NAMES[_wator_preset_idx]
    preset = WATOR_PRESETS[preset_name]
    _wator_fish_breed = preset["fish_breed"]
    _wator_shark_breed = preset["shark_breed"]
    _wator_shark_starve = preset["shark_starve"]
    _wator_rows = rows
    _wator_cols = cols

    _wator_grid = [[_WATOR_EMPTY] * cols for _ in range(rows)]
    _wator_fish_age = [[0] * cols for _ in range(rows)]
    _wator_shark_age = [[0] * cols for _ in range(rows)]
    _wator_shark_energy = [[0] * cols for _ in range(rows)]

    fish_pct = preset["fish_pct"]
    shark_pct = preset["shark_pct"]
    for r in range(rows):
        for c in range(cols):
            roll = _rnd.random()
            if roll < shark_pct:
                _wator_grid[r][c] = _WATOR_SHARK
                _wator_shark_age[r][c] = _rnd.randint(0, _wator_shark_breed - 1)
                _wator_shark_energy[r][c] = _rnd.randint(1, _wator_shark_starve)
            elif roll < shark_pct + fish_pct:
                _wator_grid[r][c] = _WATOR_FISH
                _wator_fish_age[r][c] = _rnd.randint(0, _wator_fish_breed - 1)


def _wator_step():
    """Advance Wa-Tor simulation by one generation."""
    import random as _rnd
    global _wator_grid, _wator_fish_age, _wator_shark_age, _wator_shark_energy

    rows, cols = _wator_rows, _wator_cols
    grid = _wator_grid
    fish_age = _wator_fish_age
    shark_age = _wator_shark_age
    shark_energy = _wator_shark_energy

    # Build shuffled list of all creatures to process in random order
    fish_list = []
    shark_list = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == _WATOR_FISH:
                fish_list.append((r, c))
            elif grid[r][c] == _WATOR_SHARK:
                shark_list.append((r, c))

    # Track which cells have already been moved-to this step
    moved = [[False] * cols for _ in range(rows)]

    # --- Fish move first ---
    _rnd.shuffle(fish_list)
    for r, c in fish_list:
        if grid[r][c] != _WATOR_FISH or moved[r][c]:
            continue  # eaten or already moved
        # Find empty neighbors (Von Neumann)
        neighbors = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = (r + dr) % rows, (c + dc) % cols
            if grid[nr][nc] == _WATOR_EMPTY:
                neighbors.append((nr, nc))
        fish_age[r][c] += 1
        if neighbors:
            nr, nc = _rnd.choice(neighbors)
            # Move fish
            grid[nr][nc] = _WATOR_FISH
            fish_age[nr][nc] = fish_age[r][c]
            moved[nr][nc] = True
            # Breed?
            if fish_age[r][c] >= _wator_fish_breed:
                # Leave offspring behind
                grid[r][c] = _WATOR_FISH
                fish_age[r][c] = 0
                fish_age[nr][nc] = 0
                moved[r][c] = True
            else:
                grid[r][c] = _WATOR_EMPTY
                fish_age[r][c] = 0
        else:
            moved[r][c] = True  # stayed in place

    # --- Sharks move second ---
    _rnd.shuffle(shark_list)
    for r, c in shark_list:
        if grid[r][c] != _WATOR_SHARK or moved[r][c]:
            continue  # already processed
        shark_age[r][c] += 1
        shark_energy[r][c] -= 1
        # Starved?
        if shark_energy[r][c] <= 0:
            grid[r][c] = _WATOR_EMPTY
            shark_age[r][c] = 0
            shark_energy[r][c] = 0
            continue
        # Look for fish neighbors first (hunt)
        fish_neighbors = []
        empty_neighbors = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = (r + dr) % rows, (c + dc) % cols
            if grid[nr][nc] == _WATOR_FISH:
                fish_neighbors.append((nr, nc))
            elif grid[nr][nc] == _WATOR_EMPTY:
                empty_neighbors.append((nr, nc))
        if fish_neighbors:
            nr, nc = _rnd.choice(fish_neighbors)
            # Eat the fish
            fish_age[nr][nc] = 0
            grid[nr][nc] = _WATOR_SHARK
            shark_age[nr][nc] = shark_age[r][c]
            shark_energy[nr][nc] = shark_energy[r][c] + _wator_shark_starve
            moved[nr][nc] = True
            # Breed?
            if shark_age[r][c] >= _wator_shark_breed:
                grid[r][c] = _WATOR_SHARK
                shark_age[r][c] = 0
                shark_energy[r][c] = _wator_shark_starve
                shark_age[nr][nc] = 0
                moved[r][c] = True
            else:
                grid[r][c] = _WATOR_EMPTY
                shark_age[r][c] = 0
                shark_energy[r][c] = 0
        elif empty_neighbors:
            nr, nc = _rnd.choice(empty_neighbors)
            grid[nr][nc] = _WATOR_SHARK
            shark_age[nr][nc] = shark_age[r][c]
            shark_energy[nr][nc] = shark_energy[r][c]
            moved[nr][nc] = True
            if shark_age[r][c] >= _wator_shark_breed:
                grid[r][c] = _WATOR_SHARK
                shark_age[r][c] = 0
                shark_energy[r][c] = _wator_shark_starve
                shark_age[nr][nc] = 0
                moved[r][c] = True
            else:
                grid[r][c] = _WATOR_EMPTY
                shark_age[r][c] = 0
                shark_energy[r][c] = 0
        else:
            moved[r][c] = True  # stayed in place


def _wator_to_grid(rows, cols):
    """Convert Wa-Tor state to display grid.

    Encoding: 0=empty, 1-49=fish (age mapped), 50-99=shark (energy mapped).
    """
    grid = [[0] * cols for _ in range(rows)]
    for r in range(min(rows, _wator_rows)):
        for c in range(min(cols, _wator_cols)):
            cell = _wator_grid[r][c]
            if cell == _WATOR_FISH:
                # Fish: values 1-49 (age-based brightness)
                age = min(_wator_fish_age[r][c], 48) + 1
                grid[r][c] = age
            elif cell == _WATOR_SHARK:
                # Shark: values 50-99 (energy-based brightness)
                energy = min(_wator_shark_energy[r][c], 49) + 50
                grid[r][c] = energy
    return grid


def _wator_color(val):
    """Return curses color pair for a Wa-Tor cell value."""
    if val == 0:
        return 19       # dark blue — ocean
    elif val < 50:
        # Fish: green
        return 1        # green
    else:
        # Shark: red
        return 21       # red


def _wator_population(grid):
    """Count fish and shark populations from display grid."""
    fish = 0
    sharks = 0
    for row in grid:
        for cell in row:
            if 1 <= cell < 50:
                fish += 1
            elif cell >= 50:
                sharks += 1
    return fish, sharks


# --- Falling Sand Particle Simulation ---
# Gravity-driven particle physics sandbox.  Each cell holds a material type
# (sand, water, fire, plant, stone, smoke, oil) that obeys simple movement
# rules: sand falls and piles, water flows, fire rises and burns, smoke
# drifts upward and fades, plants grow near water and burn near fire.

# Particle type constants
_FS_EMPTY = 0
_FS_SAND = 1
_FS_WATER = 2
_FS_STONE = 3
_FS_FIRE = 4
_FS_SMOKE = 5
_FS_PLANT = 6
_FS_OIL = 7

FALLINGSAND_PRESETS = {
    "hourglass":  {"layout": "hourglass",
                   "name": "Hourglass"},
    "rain":       {"layout": "rain",
                   "name": "Rainstorm"},
    "volcano":    {"layout": "volcano",
                   "name": "Volcano"},
    "garden":     {"layout": "garden",
                   "name": "Garden"},
    "sandbox":    {"layout": "sandbox",
                   "name": "Sandbox"},
    "cascade":    {"layout": "cascade",
                   "name": "Cascade"},
}
FALLINGSAND_PRESET_NAMES = list(FALLINGSAND_PRESETS.keys())

# Module-level state
_fs_grid = None          # 2D array of particle types
_fs_lifetime = None      # 2D array: ticks since particle placed (for fire/smoke decay)
_fs_preset_idx = 0
_fs_rows = 0
_fs_cols = 0


def _fs_init(rows, cols, preset_name=None):
    """Initialize the falling sand simulation grid."""
    import random as _rnd
    global _fs_grid, _fs_lifetime, _fs_rows, _fs_cols, _fs_preset_idx

    if preset_name is None:
        preset_name = FALLINGSAND_PRESET_NAMES[_fs_preset_idx]
    preset = FALLINGSAND_PRESETS[preset_name]
    _fs_rows = rows
    _fs_cols = cols

    _fs_grid = [[_FS_EMPTY] * cols for _ in range(rows)]
    _fs_lifetime = [[0] * cols for _ in range(rows)]

    layout = preset["layout"]

    if layout == "hourglass":
        # Stone walls forming an hourglass, sand in top half
        mid_c = cols // 2
        mid_r = rows // 2
        # Build walls
        for r in range(rows):
            _fs_grid[r][0] = _FS_STONE
            _fs_grid[r][cols - 1] = _FS_STONE
        for c in range(cols):
            _fs_grid[0][c] = _FS_STONE
            _fs_grid[rows - 1][c] = _FS_STONE
        # Hourglass neck walls
        neck_width = max(2, cols // 20)
        for c in range(cols):
            dist = abs(c - mid_c)
            if dist > neck_width:
                _fs_grid[mid_r][c] = _FS_STONE
                if mid_r - 1 >= 0:
                    _fs_grid[mid_r - 1][c] = _FS_STONE
        # Fill top half with sand
        for r in range(2, mid_r - 1):
            for c in range(2, cols - 2):
                _fs_grid[r][c] = _FS_SAND

    elif layout == "rain":
        # Stone floor, water spawns from top (handled in step)
        for c in range(cols):
            _fs_grid[rows - 1][c] = _FS_STONE
            _fs_grid[rows - 2][c] = _FS_STONE
        # A few stone platforms
        for c in range(cols // 4, cols // 4 + cols // 3):
            if c < cols:
                _fs_grid[rows // 2][c] = _FS_STONE
        for c in range(cols // 2, cols // 2 + cols // 4):
            if c < cols:
                _fs_grid[rows // 3][c] = _FS_STONE

    elif layout == "volcano":
        # Stone mountain with fire at the top
        mid_c = cols // 2
        base_r = rows - 1
        # Build mountain
        for c in range(cols):
            _fs_grid[base_r][c] = _FS_STONE
        mountain_h = rows // 3
        for layer in range(mountain_h):
            r = base_r - layer
            half_w = (mountain_h - layer) * cols // (2 * mountain_h)
            for c in range(mid_c - half_w, mid_c + half_w + 1):
                if 0 <= c < cols and 0 <= r < rows:
                    _fs_grid[r][c] = _FS_STONE
        # Fire at crater
        crater_r = base_r - mountain_h
        for dc in range(-2, 3):
            c = mid_c + dc
            if 0 <= c < cols and 0 <= crater_r < rows:
                _fs_grid[crater_r][c] = _FS_FIRE
                _fs_lifetime[crater_r][c] = 1
        # Oil pools at base
        for c in range(3, cols // 4):
            _fs_grid[base_r - 1][c] = _FS_OIL

    elif layout == "garden":
        # Floor with plants and a water source
        for c in range(cols):
            _fs_grid[rows - 1][c] = _FS_STONE
        # Plant row
        for c in range(2, cols - 2, 3):
            _fs_grid[rows - 2][c] = _FS_PLANT
        # Water pools
        for c in range(cols // 3, cols // 3 + 5):
            if c < cols:
                _fs_grid[rows - 2][c] = _FS_WATER

    elif layout == "sandbox":
        # Random scatter of materials
        for c in range(cols):
            _fs_grid[rows - 1][c] = _FS_STONE
        for r in range(rows - 1):
            for c in range(cols):
                roll = _rnd.random()
                if roll < 0.08:
                    _fs_grid[r][c] = _FS_SAND
                elif roll < 0.12:
                    _fs_grid[r][c] = _FS_WATER
                elif roll < 0.14:
                    _fs_grid[r][c] = _FS_STONE
                elif roll < 0.155:
                    _fs_grid[r][c] = _FS_PLANT
                elif roll < 0.165:
                    _fs_grid[r][c] = _FS_OIL

    elif layout == "cascade":
        # Layered shelves with different materials
        for c in range(cols):
            _fs_grid[rows - 1][c] = _FS_STONE
        shelf_gap = max(4, rows // 5)
        materials = [_FS_SAND, _FS_WATER, _FS_OIL, _FS_SAND]
        for i, mat in enumerate(materials):
            shelf_r = shelf_gap * (i + 1)
            if shelf_r >= rows - 1:
                break
            # Shelf with gap
            gap_start = cols // 3 + i * (cols // 8)
            gap_end = gap_start + max(3, cols // 10)
            for c in range(cols):
                if shelf_r < rows and (c < gap_start or c > gap_end):
                    _fs_grid[shelf_r][c] = _FS_STONE
            # Material on top of shelf
            for c in range(1, cols - 1):
                if shelf_r - 1 >= 0 and _fs_grid[shelf_r][c] == _FS_STONE:
                    _fs_grid[shelf_r - 1][c] = mat


def _fs_step():
    """Advance the falling sand simulation by one tick."""
    import random as _rnd
    global _fs_grid, _fs_lifetime

    rows, cols = _fs_rows, _fs_cols
    grid = _fs_grid
    life = _fs_lifetime

    # Process bottom-to-top so falling particles move correctly
    for r in range(rows - 2, -1, -1):
        # Alternate left-to-right and right-to-left each row for fairness
        if r % 2 == 0:
            col_range = range(cols)
        else:
            col_range = range(cols - 1, -1, -1)
        for c in col_range:
            p = grid[r][c]
            if p == _FS_EMPTY or p == _FS_STONE:
                continue

            if p == _FS_SAND:
                # Sand: fall down, then diag-left/right
                if r + 1 < rows and grid[r + 1][c] == _FS_EMPTY:
                    grid[r + 1][c] = _FS_SAND
                    grid[r][c] = _FS_EMPTY
                elif r + 1 < rows and grid[r + 1][c] == _FS_WATER:
                    # Sand sinks through water
                    grid[r + 1][c] = _FS_SAND
                    grid[r][c] = _FS_WATER
                elif r + 1 < rows and grid[r + 1][c] == _FS_OIL:
                    grid[r + 1][c] = _FS_SAND
                    grid[r][c] = _FS_OIL
                else:
                    # Try diagonal
                    dirs = [(-1, 1)] if _rnd.random() < 0.5 else [(1, -1)]
                    dirs = [(-1, 1), (1, -1)] if _rnd.random() < 0.5 else [(1, -1), (-1, 1)]
                    # Actually: down-left / down-right
                    dl = (r + 1, c - 1)
                    dr = (r + 1, c + 1)
                    opts = []
                    if dl[1] >= 0 and dl[0] < rows and grid[dl[0]][dl[1]] in (_FS_EMPTY, _FS_WATER, _FS_OIL):
                        opts.append(dl)
                    if dr[1] < cols and dr[0] < rows and grid[dr[0]][dr[1]] in (_FS_EMPTY, _FS_WATER, _FS_OIL):
                        opts.append(dr)
                    if opts:
                        nr, nc = _rnd.choice(opts)
                        displaced = grid[nr][nc]
                        grid[nr][nc] = _FS_SAND
                        grid[r][c] = displaced

            elif p == _FS_WATER:
                # Water: fall, then flow sideways
                if r + 1 < rows and grid[r + 1][c] == _FS_EMPTY:
                    grid[r + 1][c] = _FS_WATER
                    grid[r][c] = _FS_EMPTY
                elif r + 1 < rows and grid[r + 1][c] == _FS_OIL:
                    # Water sinks below oil
                    grid[r + 1][c] = _FS_WATER
                    grid[r][c] = _FS_OIL
                else:
                    # Try down-diagonal
                    dl = (r + 1, c - 1)
                    dr = (r + 1, c + 1)
                    opts = []
                    if dl[1] >= 0 and dl[0] < rows and grid[dl[0]][dl[1]] == _FS_EMPTY:
                        opts.append(dl)
                    if dr[1] < cols and dr[0] < rows and grid[dr[0]][dr[1]] == _FS_EMPTY:
                        opts.append(dr)
                    if opts:
                        nr, nc = _rnd.choice(opts)
                        grid[nr][nc] = _FS_WATER
                        grid[r][c] = _FS_EMPTY
                    else:
                        # Flow sideways
                        sides = []
                        if c - 1 >= 0 and grid[r][c - 1] == _FS_EMPTY:
                            sides.append((r, c - 1))
                        if c + 1 < cols and grid[r][c + 1] == _FS_EMPTY:
                            sides.append((r, c + 1))
                        if sides:
                            nr, nc = _rnd.choice(sides)
                            grid[nr][nc] = _FS_WATER
                            grid[r][c] = _FS_EMPTY

            elif p == _FS_OIL:
                # Oil: like water but lighter (floats on water)
                if r + 1 < rows and grid[r + 1][c] == _FS_EMPTY:
                    grid[r + 1][c] = _FS_OIL
                    grid[r][c] = _FS_EMPTY
                else:
                    dl = (r + 1, c - 1)
                    dr = (r + 1, c + 1)
                    opts = []
                    if dl[1] >= 0 and dl[0] < rows and grid[dl[0]][dl[1]] == _FS_EMPTY:
                        opts.append(dl)
                    if dr[1] < cols and dr[0] < rows and grid[dr[0]][dr[1]] == _FS_EMPTY:
                        opts.append(dr)
                    if opts:
                        nr, nc = _rnd.choice(opts)
                        grid[nr][nc] = _FS_OIL
                        grid[r][c] = _FS_EMPTY
                    else:
                        sides = []
                        if c - 1 >= 0 and grid[r][c - 1] == _FS_EMPTY:
                            sides.append((r, c - 1))
                        if c + 1 < cols and grid[r][c + 1] == _FS_EMPTY:
                            sides.append((r, c + 1))
                        if sides:
                            nr, nc = _rnd.choice(sides)
                            grid[nr][nc] = _FS_OIL
                            grid[r][c] = _FS_EMPTY

            elif p == _FS_FIRE:
                life[r][c] += 1
                # Fire burns out after a while
                if life[r][c] > 15 + _rnd.randint(0, 10):
                    grid[r][c] = _FS_SMOKE
                    life[r][c] = 0
                    continue
                # Spread fire to adjacent flammable materials
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        neighbor = grid[nr][nc]
                        if neighbor == _FS_PLANT and _rnd.random() < 0.15:
                            grid[nr][nc] = _FS_FIRE
                            life[nr][nc] = 0
                        elif neighbor == _FS_OIL and _rnd.random() < 0.30:
                            grid[nr][nc] = _FS_FIRE
                            life[nr][nc] = 0
                # Fire rises
                if r - 1 >= 0 and grid[r - 1][c] == _FS_EMPTY and _rnd.random() < 0.3:
                    grid[r - 1][c] = _FS_FIRE
                    life[r - 1][c] = 0
                    grid[r][c] = _FS_SMOKE
                    life[r][c] = 0

            elif p == _FS_SMOKE:
                life[r][c] += 1
                # Smoke dissipates
                if life[r][c] > 8 + _rnd.randint(0, 6):
                    grid[r][c] = _FS_EMPTY
                    life[r][c] = 0
                    continue
                # Smoke rises
                if r - 1 >= 0 and grid[r - 1][c] == _FS_EMPTY:
                    grid[r - 1][c] = _FS_SMOKE
                    life[r - 1][c] = life[r][c]
                    grid[r][c] = _FS_EMPTY
                    life[r][c] = 0
                elif r - 1 >= 0:
                    # Drift sideways
                    sides = []
                    if c - 1 >= 0 and grid[r - 1][c - 1] == _FS_EMPTY:
                        sides.append((r - 1, c - 1))
                    if c + 1 < cols and grid[r - 1][c + 1] == _FS_EMPTY:
                        sides.append((r - 1, c + 1))
                    if sides:
                        nr, nc = _rnd.choice(sides)
                        grid[nr][nc] = _FS_SMOKE
                        life[nr][nc] = life[r][c]
                        grid[r][c] = _FS_EMPTY
                        life[r][c] = 0

            elif p == _FS_PLANT:
                # Plants grow near water
                has_water = False
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == _FS_WATER:
                        has_water = True
                        break
                if has_water and _rnd.random() < 0.03:
                    # Grow into an adjacent empty cell
                    grow_opts = []
                    for dr, dc in ((-1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == _FS_EMPTY:
                            grow_opts.append((nr, nc))
                    if grow_opts:
                        nr, nc = _rnd.choice(grow_opts)
                        grid[nr][nc] = _FS_PLANT

    # Rain preset: spawn water drops at top
    preset_name = FALLINGSAND_PRESET_NAMES[_fs_preset_idx]
    if preset_name == "rain":
        for _ in range(max(1, cols // 15)):
            c = _rnd.randint(0, cols - 1)
            if grid[0][c] == _FS_EMPTY:
                grid[0][c] = _FS_WATER
    # Volcano preset: replenish fire at crater
    elif preset_name == "volcano":
        mid_c = cols // 2
        base_r = rows - 1
        mountain_h = rows // 3
        crater_r = base_r - mountain_h
        if 0 <= crater_r < rows:
            for dc in range(-1, 2):
                cc = mid_c + dc
                if 0 <= cc < cols and grid[crater_r][cc] == _FS_EMPTY:
                    if _rnd.random() < 0.4:
                        grid[crater_r][cc] = _FS_FIRE
                        life[crater_r][cc] = 0


def _fs_to_grid(rows, cols):
    """Convert falling sand state to display grid.

    Encoding: 0=empty, 1-14=sand, 15-28=water, 29-42=stone,
              43-56=fire, 57-70=smoke, 71-84=plant, 85-98=oil.
    """
    grid = [[0] * cols for _ in range(rows)]
    for r in range(min(rows, _fs_rows)):
        for c in range(min(cols, _fs_cols)):
            p = _fs_grid[r][c]
            if p == _FS_EMPTY:
                continue
            elif p == _FS_SAND:
                grid[r][c] = 1 + min(_fs_lifetime[r][c], 13)
            elif p == _FS_WATER:
                grid[r][c] = 15
            elif p == _FS_STONE:
                grid[r][c] = 29
            elif p == _FS_FIRE:
                grid[r][c] = 43 + min(_fs_lifetime[r][c], 13)
            elif p == _FS_SMOKE:
                grid[r][c] = 57 + min(_fs_lifetime[r][c], 13)
            elif p == _FS_PLANT:
                grid[r][c] = 71
            elif p == _FS_OIL:
                grid[r][c] = 85
    return grid


def _fs_color(val):
    """Return curses color pair for a falling sand cell value."""
    if val == 0:
        return 1        # empty (default green, won't be shown)
    elif val < 15:
        return 15       # sand: yellow
    elif val < 29:
        return 19       # water: blue
    elif val < 43:
        return 2        # stone: white
    elif val < 57:
        return 21       # fire: red
    elif val < 71:
        return 7        # smoke: magenta
    elif val < 85:
        return 1        # plant: green
    else:
        return 5        # oil: cyan


# --- Langton's Ant / Generalized Turmites ---
# Agent-based cellular automaton: one or more "ants" walk the grid, flipping
# cell colors and turning based on the cell color and the ant's internal state.
# Classic Langton's Ant (RL) produces the famous emergent "highway" after ~10k
# chaotic steps.  Generalized turmites use multi-state, multi-color transition
# tables and produce stunning symmetric patterns.

# Ant direction constants: 0=N, 1=E, 2=S, 3=W
_ANT_DR = [-1, 0, 1, 0]
_ANT_DC = [0, 1, 0, -1]

# Turn codes for transition tables
_TURN_L = 0   # turn left (counter-clockwise)
_TURN_R = 1   # turn right (clockwise)
_TURN_U = 2   # U-turn (180 degrees)
_TURN_N = 3   # no turn (continue straight)

_TURN_MAP = {"L": _TURN_L, "R": _TURN_R, "U": _TURN_U, "N": _TURN_N}

# Turmite presets: each defines a transition table and number of colors/states.
# Transition table format: table[state][color] = (new_color, turn, new_state)
# Classic Langton's Ant: 1 state, 2 colors, rule string "RL"
TURMITE_PRESETS = {
    "langton": {
        "name": "Langton's Ant (RL)",
        "colors": 2,
        "states": 1,
        "table": {0: {0: (1, _TURN_R, 0), 1: (0, _TURN_L, 0)}},
        "ants": 1,
    },
    "highway4": {
        "name": "4-Ant Highway",
        "colors": 2,
        "states": 1,
        "table": {0: {0: (1, _TURN_R, 0), 1: (0, _TURN_L, 0)}},
        "ants": 4,
    },
    "llrr": {
        "name": "Symmetric (LLRR)",
        "colors": 4,
        "states": 1,
        "table": {0: {0: (1, _TURN_L, 0), 1: (2, _TURN_L, 0),
                       2: (3, _TURN_R, 0), 3: (0, _TURN_R, 0)}},
        "ants": 1,
    },
    "lrrl": {
        "name": "Square Builder (LRRL)",
        "colors": 4,
        "states": 1,
        "table": {0: {0: (1, _TURN_L, 0), 1: (2, _TURN_R, 0),
                       2: (3, _TURN_R, 0), 3: (0, _TURN_L, 0)}},
        "ants": 1,
    },
    "rllr": {
        "name": "Triangle (RLLR)",
        "colors": 4,
        "states": 1,
        "table": {0: {0: (1, _TURN_R, 0), 1: (2, _TURN_L, 0),
                       2: (3, _TURN_L, 0), 3: (0, _TURN_R, 0)}},
        "ants": 1,
    },
    "spiral": {
        "name": "Spiral (RLLLRLLL)",
        "colors": 8,
        "states": 1,
        "table": {0: {0: (1, _TURN_R, 0), 1: (2, _TURN_L, 0),
                       2: (3, _TURN_L, 0), 3: (4, _TURN_L, 0),
                       4: (5, _TURN_R, 0), 5: (6, _TURN_L, 0),
                       6: (7, _TURN_L, 0), 7: (0, _TURN_L, 0)}},
        "ants": 1,
    },
    "fibonacci": {
        "name": "Fibonacci (RLR)",
        "colors": 3,
        "states": 1,
        "table": {0: {0: (1, _TURN_R, 0), 1: (2, _TURN_L, 0),
                       2: (0, _TURN_R, 0)}},
        "ants": 1,
    },
    "turmite_1": {
        "name": "Turmite (2-state)",
        "colors": 2,
        "states": 2,
        "table": {0: {0: (1, _TURN_R, 1), 1: (1, _TURN_L, 0)},
                  1: {0: (1, _TURN_L, 0), 1: (0, _TURN_R, 1)}},
        "ants": 1,
    },
}

TURMITE_PRESET_NAMES = list(TURMITE_PRESETS.keys())

# Module-level state for the turmite simulation
_turmite_grid = None       # 2D list of color values (0..num_colors-1)
_turmite_ants = []         # list of (row, col, direction, state)
_turmite_table = None      # transition table
_turmite_num_colors = 2
_turmite_preset_idx = 0


def _turmite_init(rows, cols, preset_name=None):
    """Initialize turmite grid and ants."""
    global _turmite_grid, _turmite_ants, _turmite_table, _turmite_num_colors
    if preset_name is None:
        preset_name = TURMITE_PRESET_NAMES[_turmite_preset_idx]
    preset = TURMITE_PRESETS[preset_name]
    _turmite_table = preset["table"]
    _turmite_num_colors = preset["colors"]
    _turmite_grid = [[0] * cols for _ in range(rows)]
    num_ants = preset.get("ants", 1)
    _turmite_ants = []
    cr, cc = rows // 2, cols // 2
    for i in range(num_ants):
        # Spread multiple ants around center
        if num_ants == 1:
            ar, ac = cr, cc
        else:
            offset = 3
            if i == 0:
                ar, ac = cr - offset, cc - offset
            elif i == 1:
                ar, ac = cr - offset, cc + offset
            elif i == 2:
                ar, ac = cr + offset, cc - offset
            else:
                ar, ac = cr + offset, cc + offset
        _turmite_ants.append([ar % rows, ac % cols, 0, 0])  # row, col, dir, state


def _turmite_step():
    """Advance all ants by one step using the transition table."""
    global _turmite_grid, _turmite_ants
    rows = len(_turmite_grid)
    cols = len(_turmite_grid[0])
    for ant in _turmite_ants:
        r, c, d, s = ant
        color = _turmite_grid[r][c]
        new_color, turn, new_state = _turmite_table[s][color]
        _turmite_grid[r][c] = new_color
        # Apply turn
        if turn == _TURN_R:
            d = (d + 1) % 4
        elif turn == _TURN_L:
            d = (d - 1) % 4
        elif turn == _TURN_U:
            d = (d + 2) % 4
        # else _TURN_N: no change
        # Move forward
        nr = r + _ANT_DR[d]
        nc = c + _ANT_DC[d]
        # Wrap using topology
        wrapped = _wrap_coords(nr, nc, rows, cols)
        if wrapped is None:
            # Bounded topology: ant stays in place but still turns
            ant[2] = d
            ant[3] = new_state
            continue
        ant[0], ant[1] = wrapped
        ant[2] = d
        ant[3] = new_state


def _turmite_to_grid(rows, cols):
    """Convert turmite state to a display grid.

    Maps color values to age-like values for rendering.
    Ant positions are marked with a high value for visibility.
    """
    # Scale colors to distinct display values
    grid = [[0] * cols for _ in range(rows)]
    if _turmite_num_colors <= 2:
        # Classic binary: 0 = dead, color 1 = alive (age-like value)
        for r in range(rows):
            for c in range(cols):
                grid[r][c] = _turmite_grid[r][c] * 5
    else:
        # Multi-color: map each color to a distinct age range
        step_val = max(1, 100 // _turmite_num_colors)
        for r in range(rows):
            for c in range(cols):
                color = _turmite_grid[r][c]
                if color > 0:
                    grid[r][c] = 1 + color * step_val
    # Mark ant positions with a special high value
    for ant in _turmite_ants:
        r, c = ant[0], ant[1]
        if 0 <= r < rows and 0 <= c < cols:
            grid[r][c] = 99  # special marker for ant head
    return grid


def _turmite_color(val):
    """Return curses color pair for a turmite cell value."""
    if val == 99:
        return 21       # ant head — bright red
    if val == 0:
        return 19       # background — dark
    if val <= 5:
        return 1        # green — color 1 (classic white)
    if val <= 15:
        return 5        # cyan
    if val <= 30:
        return 6        # blue
    if val <= 50:
        return 7        # magenta
    return 20           # white — high color values


# --- 1D Elementary Cellular Automata (Wolfram Rules) ---
# Each of the 256 rules maps a 3-cell neighborhood (left, center, right) to 0 or 1.
# The space-time diagram scrolls upward: new generations appear at the bottom.

# Notable rules for quick cycling
ECA_NOTABLE_RULES = [30, 110, 90, 184, 150, 73, 45, 105, 54, 60, 62, 126, 182, 225, 137, 169]

_eca_rule_num = 30          # current Wolfram rule number (0-255)
_eca_state = None           # current 1D row (list of 0/1, length = cols)
_eca_history = []           # list of past rows for the space-time diagram
_eca_notable_idx = 0        # index into ECA_NOTABLE_RULES for cycling


def _eca_lookup_table(rule_num):
    """Build a lookup table for the 8 possible 3-cell neighborhoods."""
    return [(rule_num >> i) & 1 for i in range(8)]


def _eca_init(cols, init_type="center"):
    """Initialize the 1D ECA state and clear history."""
    global _eca_state, _eca_history
    _eca_state = [0] * cols
    if init_type == "center":
        _eca_state[cols // 2] = 1
    elif init_type == "random":
        import random
        _eca_state = [random.randint(0, 1) for _ in range(cols)]
    _eca_history = [list(_eca_state)]


def _eca_step():
    """Advance the ECA by one generation using the current rule."""
    global _eca_state, _eca_history
    table = _eca_lookup_table(_eca_rule_num)
    n = len(_eca_state)
    new_state = [0] * n
    for i in range(n):
        left = _eca_state[(i - 1) % n]
        center = _eca_state[i]
        right = _eca_state[(i + 1) % n]
        idx = (left << 2) | (center << 1) | right
        new_state[i] = table[idx]
    _eca_state = new_state
    _eca_history.append(list(_eca_state))
    # Cap internal history to prevent unbounded memory growth;
    # the main loop's history[] handles time-travel independently.
    if len(_eca_history) > 10000:
        _eca_history = _eca_history[-10000:]


def _eca_to_grid(rows, cols):
    """Convert ECA history into a 2D grid (space-time diagram).

    Most recent generation at the bottom, history scrolling upward.
    Each cell is 0 (dead) or 1 (alive) — age is not tracked.
    """
    grid = [[0] * cols for _ in range(rows)]
    history_len = len(_eca_history)
    # Fill grid from bottom to top with most recent history
    for r in range(rows):
        hist_row_idx = history_len - (rows - r)
        if hist_row_idx >= 0:
            src = _eca_history[hist_row_idx]
            src_len = len(src)
            for c in range(min(cols, src_len)):
                grid[r][c] = src[c]
    return grid


# --- Gray-Scott Reaction-Diffusion ---
# Continuous-valued reaction-diffusion model:
#   du/dt = Du*laplacian(u) - u*v^2 + F*(1-u)
#   dv/dt = Dv*laplacian(v) + u*v^2 - (F+k)*v

GS_DU = 0.2097   # diffusion rate of U
GS_DV = 0.105    # diffusion rate of V
GS_DT = 1.0      # time step

GS_PRESETS = {
    "mitosis":   {"F": 0.0367, "k": 0.0649, "name": "Mitosis (cell splitting)"},
    "coral":     {"F": 0.0545, "k": 0.062,  "name": "Coral (branching growth)"},
    "solitons":  {"F": 0.03,   "k": 0.06,   "name": "Solitons (pulsing dots)"},
    "maze":      {"F": 0.029,  "k": 0.057,  "name": "Maze-like (labyrinthine)"},
    "spots":     {"F": 0.035,  "k": 0.065,  "name": "Spots (stable dots)"},
    "worms":     {"F": 0.078,  "k": 0.061,  "name": "Worms (squirming tendrils)"},
    "waves":     {"F": 0.014,  "k": 0.054,  "name": "Waves (expanding rings)"},
    "bubbles":   {"F": 0.012,  "k": 0.05,   "name": "Bubbles (negative spots)"},
}

GS_PRESET_NAMES = list(GS_PRESETS.keys())

# Module-level Gray-Scott state: two 2D float arrays (U, V concentrations)
_gs_u = None  # numpy array or list-of-lists of floats
_gs_v = None
_gs_preset_idx = 0
_gs_feed = GS_PRESETS["mitosis"]["F"]
_gs_kill = GS_PRESETS["mitosis"]["k"]


def _gs_init(rows, cols, seed_type="center"):
    """Initialize Gray-Scott U/V concentration grids.

    U starts at 1.0 everywhere, V starts at 0.0 with seeded perturbation regions.
    """
    global _gs_u, _gs_v
    import random
    if _HAS_NUMPY:
        _gs_u = np.ones((rows, cols), dtype=np.float64)
        _gs_v = np.zeros((rows, cols), dtype=np.float64)
        # Seed: place several small square patches of V=0.5, U=0.5
        num_seeds = max(3, (rows * cols) // 800)
        for _ in range(num_seeds):
            sr = random.randint(2, rows - 6)
            sc = random.randint(2, cols - 6)
            sz = random.randint(2, 5)
            _gs_u[sr:sr+sz, sc:sc+sz] = 0.5
            _gs_v[sr:sr+sz, sc:sc+sz] = 0.25
            # Add small random noise to break symmetry
            _gs_u[sr:sr+sz, sc:sc+sz] += np.random.uniform(-0.01, 0.01, (sz, sz))
            _gs_v[sr:sr+sz, sc:sc+sz] += np.random.uniform(-0.01, 0.01, (sz, sz))
    else:
        _gs_u = [[1.0] * cols for _ in range(rows)]
        _gs_v = [[0.0] * cols for _ in range(rows)]
        num_seeds = max(3, (rows * cols) // 800)
        for _ in range(num_seeds):
            sr = random.randint(2, rows - 6)
            sc = random.randint(2, cols - 6)
            sz = random.randint(2, 5)
            for dr in range(sz):
                for dc in range(sz):
                    _gs_u[sr+dr][sc+dc] = 0.5 + random.uniform(-0.01, 0.01)
                    _gs_v[sr+dr][sc+dc] = 0.25 + random.uniform(-0.01, 0.01)


def _gs_to_grid(rows, cols):
    """Convert Gray-Scott V concentration to an integer grid for display.

    Maps V concentration [0, max_v] to integer values 0-100 for color mapping.
    """
    grid = make_grid(rows, cols)
    if _gs_v is None:
        return grid
    if _HAS_NUMPY:
        # Quantize V into 0-100 range
        v = np.array(_gs_v)
        max_v = max(v.max(), 0.001)
        quantized = np.clip((v / max_v * 100), 0, 100).astype(int)
        return quantized.tolist()
    else:
        max_v = max(max(row) for row in _gs_v) if _gs_v else 0.001
        max_v = max(max_v, 0.001)
        for r in range(rows):
            for c in range(cols):
                grid[r][c] = max(0, min(100, int(_gs_v[r][c] / max_v * 100)))
        return grid


def _step_grayscott_numpy():
    """Gray-Scott step using NumPy vectorized Laplacian."""
    global _gs_u, _gs_v
    if _gs_u is None:
        return
    u, v = _gs_u, _gs_v
    # Laplacian via convolution (5-point stencil)
    laplacian_kernel = np.array([[0, 1, 0],
                                  [1, -4, 1],
                                  [0, 1, 0]], dtype=np.float64)
    lap_u = convolve2d(u, laplacian_kernel, mode="same", boundary="wrap")
    lap_v = convolve2d(v, laplacian_kernel, mode="same", boundary="wrap")
    uvv = u * v * v
    du = GS_DU * lap_u - uvv + _gs_feed * (1.0 - u)
    dv = GS_DV * lap_v + uvv - (_gs_feed + _gs_kill) * v
    _gs_u = np.clip(u + du * GS_DT, 0.0, 1.0)
    _gs_v = np.clip(v + dv * GS_DT, 0.0, 1.0)


def _step_grayscott_python():
    """Gray-Scott step using pure Python — cell by cell."""
    global _gs_u, _gs_v
    if _gs_u is None:
        return
    rows = len(_gs_u)
    cols = len(_gs_u[0])
    new_u = [[0.0] * cols for _ in range(rows)]
    new_v = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            # 5-point Laplacian with wrapping
            lap_u = (_gs_u[(r-1) % rows][c] + _gs_u[(r+1) % rows][c]
                     + _gs_u[r][(c-1) % cols] + _gs_u[r][(c+1) % cols]
                     - 4.0 * _gs_u[r][c])
            lap_v = (_gs_v[(r-1) % rows][c] + _gs_v[(r+1) % rows][c]
                     + _gs_v[r][(c-1) % cols] + _gs_v[r][(c+1) % cols]
                     - 4.0 * _gs_v[r][c])
            u = _gs_u[r][c]
            v = _gs_v[r][c]
            uvv = u * v * v
            new_u[r][c] = max(0.0, min(1.0, u + (GS_DU * lap_u - uvv + _gs_feed * (1.0 - u)) * GS_DT))
            new_v[r][c] = max(0.0, min(1.0, v + (GS_DV * lap_v + uvv - (_gs_feed + _gs_kill) * v) * GS_DT))
    _gs_u = new_u
    _gs_v = new_v


# --- Physarum: Slime Mold Transport Network ---
# Agent-based model inspired by Physarum polycephalum.  Thousands of particles
# (agents) move across a 2D trail map.  Each agent senses the trail
# concentration ahead at three positions (left, center, right), rotates toward
# the strongest signal, deposits trail chemical, and advances one step.
# The trail map undergoes diffusion and decay each tick, creating organic
# vein-like transport networks that self-organize into efficient structures.

PHYSARUM_PRESETS = {
    "dendritic": {
        "name": "Dendritic (tight veins)",
        "sensor_angle": 22.5,   # degrees
        "sensor_dist": 9,
        "turn_speed": 45.0,     # degrees per step
        "deposit": 5.0,
        "decay": 0.1,
        "diffuse_k": 0.1,      # fraction diffused to neighbors
        "agent_pct": 0.15,      # fraction of cells occupied by agents
        "seed": "center_circle",
    },
    "fungal": {
        "name": "Fungal bloom (sprawling)",
        "sensor_angle": 45.0,
        "sensor_dist": 5,
        "turn_speed": 22.5,
        "deposit": 5.0,
        "decay": 0.05,
        "diffuse_k": 0.15,
        "agent_pct": 0.10,
        "seed": "scatter",
    },
    "network": {
        "name": "Network (efficient paths)",
        "sensor_angle": 30.0,
        "sensor_dist": 12,
        "turn_speed": 60.0,
        "deposit": 5.0,
        "decay": 0.15,
        "diffuse_k": 0.05,
        "agent_pct": 0.12,
        "seed": "food_nodes",
    },
    "rings": {
        "name": "Rings (pulsing bands)",
        "sensor_angle": 60.0,
        "sensor_dist": 7,
        "turn_speed": 10.0,
        "deposit": 8.0,
        "decay": 0.2,
        "diffuse_k": 0.2,
        "agent_pct": 0.20,
        "seed": "center_circle",
    },
    "tendrils": {
        "name": "Tendrils (sparse reaching)",
        "sensor_angle": 15.0,
        "sensor_dist": 15,
        "turn_speed": 35.0,
        "deposit": 4.0,
        "decay": 0.08,
        "diffuse_k": 0.08,
        "agent_pct": 0.05,
        "seed": "scatter",
    },
    "lattice": {
        "name": "Lattice (ordered grid)",
        "sensor_angle": 90.0,
        "sensor_dist": 4,
        "turn_speed": 90.0,
        "deposit": 5.0,
        "decay": 0.12,
        "diffuse_k": 0.1,
        "agent_pct": 0.15,
        "seed": "scatter",
    },
}

PHYSARUM_PRESET_NAMES = list(PHYSARUM_PRESETS.keys())

# Module-level Physarum state
_phys_trail = None          # 2D float array — trail concentration
_phys_agents = None         # list of (row, col, angle_radians) floats
_phys_rows = 0
_phys_cols = 0
_phys_preset_idx = 0
_phys_sensor_angle = 22.5
_phys_sensor_dist = 9
_phys_turn_speed = 45.0
_phys_deposit = 5.0
_phys_decay = 0.1
_phys_diffuse_k = 0.1


def _phys_apply_preset(name):
    """Apply a Physarum preset's parameters to module-level state."""
    global _phys_sensor_angle, _phys_sensor_dist, _phys_turn_speed
    global _phys_deposit, _phys_decay, _phys_diffuse_k
    p = PHYSARUM_PRESETS[name]
    _phys_sensor_angle = p["sensor_angle"]
    _phys_sensor_dist = p["sensor_dist"]
    _phys_turn_speed = p["turn_speed"]
    _phys_deposit = p["deposit"]
    _phys_decay = p["decay"]
    _phys_diffuse_k = p["diffuse_k"]


def _phys_init(rows, cols, preset_name=None):
    """Initialize the Physarum trail map and agent population."""
    import random as _rnd
    global _phys_trail, _phys_agents, _phys_rows, _phys_cols, _phys_preset_idx

    if preset_name is None:
        preset_name = PHYSARUM_PRESET_NAMES[_phys_preset_idx]
    _phys_apply_preset(preset_name)
    preset = PHYSARUM_PRESETS[preset_name]
    _phys_rows = rows
    _phys_cols = cols

    if _HAS_NUMPY:
        _phys_trail = np.zeros((rows, cols), dtype=np.float64)
    else:
        _phys_trail = [[0.0] * cols for _ in range(rows)]

    # Create agents
    num_agents = max(1, int(rows * cols * preset["agent_pct"]))
    seed = preset.get("seed", "scatter")
    _phys_agents = []
    TWO_PI = 2.0 * math.pi

    if seed == "center_circle":
        cr, cc = rows / 2.0, cols / 2.0
        radius = min(rows, cols) / 6.0
        for _ in range(num_agents):
            a = _rnd.random() * TWO_PI
            r_off = _rnd.random() * radius
            ar = cr + math.sin(a) * r_off
            ac = cc + math.cos(a) * r_off
            ar = ar % rows
            ac = ac % cols
            _phys_agents.append([ar, ac, _rnd.random() * TWO_PI])
    elif seed == "food_nodes":
        # Place agents in several clusters to form networks between them
        n_nodes = max(3, min(8, (rows * cols) // 1500))
        centers = []
        for _ in range(n_nodes):
            centers.append((_rnd.randint(rows // 6, rows * 5 // 6),
                            _rnd.randint(cols // 6, cols * 5 // 6)))
        per_node = num_agents // n_nodes
        for cx, cy in centers:
            for _ in range(per_node):
                ar = (cx + _rnd.gauss(0, min(rows, cols) / 12.0)) % rows
                ac = (cy + _rnd.gauss(0, min(rows, cols) / 12.0)) % cols
                _phys_agents.append([ar, ac, _rnd.random() * TWO_PI])
        # Remainder agents scattered
        for _ in range(num_agents - per_node * n_nodes):
            _phys_agents.append([_rnd.random() * rows,
                                 _rnd.random() * cols,
                                 _rnd.random() * TWO_PI])
    else:  # scatter
        for _ in range(num_agents):
            _phys_agents.append([_rnd.random() * rows,
                                 _rnd.random() * cols,
                                 _rnd.random() * TWO_PI])


def _phys_step():
    """Advance the Physarum simulation by one tick."""
    global _phys_trail, _phys_agents
    if _phys_trail is None or _phys_agents is None:
        return

    rows = _phys_rows
    cols = _phys_cols
    sa_rad = math.radians(_phys_sensor_angle)
    ts_rad = math.radians(_phys_turn_speed)
    sd = _phys_sensor_dist
    dep = _phys_deposit
    decay = _phys_decay
    dk = _phys_diffuse_k

    if _HAS_NUMPY:
        _phys_step_numpy(rows, cols, sa_rad, ts_rad, sd, dep, decay, dk)
    else:
        _phys_step_python(rows, cols, sa_rad, ts_rad, sd, dep, decay, dk)


def _phys_step_numpy(rows, cols, sa_rad, ts_rad, sd, dep, decay, dk):
    """Physarum step with NumPy-accelerated diffusion."""
    global _phys_trail, _phys_agents
    import random as _rnd

    trail = _phys_trail

    # --- Agent sense-rotate-deposit-move ---
    for agent in _phys_agents:
        ar, ac, angle = agent[0], agent[1], agent[2]

        # Sense at three positions: left, center, right
        def _sense(a):
            sr = (ar + math.sin(a) * sd) % rows
            sc = (ac + math.cos(a) * sd) % cols
            return trail[int(sr)][int(sc)]

        s_left = _sense(angle - sa_rad)
        s_center = _sense(angle)
        s_right = _sense(angle + sa_rad)

        # Rotate toward strongest signal
        if s_center >= s_left and s_center >= s_right:
            pass  # keep going straight
        elif s_left > s_right:
            angle -= ts_rad
        elif s_right > s_left:
            angle += ts_rad
        else:
            # left == right and both > center: pick randomly
            angle += ts_rad if _rnd.random() < 0.5 else -ts_rad

        # Move forward
        nr = (ar + math.sin(angle)) % rows
        nc = (ac + math.cos(angle)) % cols
        agent[0] = nr
        agent[1] = nc
        agent[2] = angle

        # Deposit trail at new position
        ri, ci = int(nr), int(nc)
        trail[ri][ci] += dep

    # --- Diffusion (3x3 mean filter blend) ---
    kernel = np.ones((3, 3), dtype=np.float64) / 9.0
    blurred = convolve2d(trail, kernel, mode="same", boundary="wrap")
    _phys_trail = trail * (1.0 - dk) + blurred * dk

    # --- Decay ---
    _phys_trail = np.maximum(_phys_trail - decay, 0.0)


def _phys_step_python(rows, cols, sa_rad, ts_rad, sd, dep, decay, dk):
    """Physarum step using pure Python — cell by cell."""
    global _phys_trail, _phys_agents
    import random as _rnd

    trail = _phys_trail

    # --- Agent sense-rotate-deposit-move ---
    for agent in _phys_agents:
        ar, ac, angle = agent[0], agent[1], agent[2]

        def _sense(a):
            sr = int(ar + math.sin(a) * sd) % rows
            sc = int(ac + math.cos(a) * sd) % cols
            return trail[sr][sc]

        s_left = _sense(angle - sa_rad)
        s_center = _sense(angle)
        s_right = _sense(angle + sa_rad)

        if s_center >= s_left and s_center >= s_right:
            pass
        elif s_left > s_right:
            angle -= ts_rad
        elif s_right > s_left:
            angle += ts_rad
        else:
            angle += ts_rad if _rnd.random() < 0.5 else -ts_rad

        nr = (ar + math.sin(angle)) % rows
        nc = (ac + math.cos(angle)) % cols
        agent[0] = nr
        agent[1] = nc
        agent[2] = angle

        ri, ci = int(nr), int(nc)
        trail[ri][ci] += dep

    # --- Diffusion ---
    new_trail = [[0.0] * cols for _ in range(rows)]
    w_self = 1.0 - dk
    w_nb = dk / 9.0
    for r in range(rows):
        for c in range(cols):
            total = 0.0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    total += trail[(r + dr) % rows][(c + dc) % cols]
            new_trail[r][c] = trail[r][c] * w_self + total * w_nb

    # --- Decay ---
    for r in range(rows):
        for c in range(cols):
            new_trail[r][c] = max(0.0, new_trail[r][c] - decay)
    _phys_trail = new_trail


def _phys_to_grid(rows, cols):
    """Convert Physarum trail map to an integer grid (0-100) for display."""
    grid = make_grid(rows, cols)
    if _phys_trail is None:
        return grid
    if _HAS_NUMPY:
        t = np.array(_phys_trail)
        max_t = max(t.max(), 0.001)
        quantized = np.clip((t / max_t * 100), 0, 100).astype(int)
        return quantized.tolist()
    else:
        max_t = 0.001
        for r in range(rows):
            for c in range(cols):
                if _phys_trail[r][c] > max_t:
                    max_t = _phys_trail[r][c]
        for r in range(rows):
            for c in range(cols):
                grid[r][c] = max(0, min(100, int(_phys_trail[r][c] / max_t * 100)))
        return grid


# --- Lenia: Continuous Smooth-Kernel Cellular Automata ---
# Generalizes Conway's Life into continuous space and time using smooth
# ring-shaped kernels and a Gaussian growth function.
#   Kernel K: ring-shaped with Gaussian bumps at specified radii
#   Potential U = K * A (convolution of kernel with cell state)
#   Growth G(u) = 2 * exp(-((u - mu)^2) / (2 * sigma^2)) - 1
#   Update A(t+dt) = clip(A(t) + dt * G(U), 0, 1)

LENIA_PRESETS = {
    "orbium": {
        "name": "Orbium (smooth glider)",
        "R": 13, "T": 10, "mu": 0.15, "sigma": 0.015,
        "beta": [1],
        "seed": "orbium",
    },
    "geminium": {
        "name": "Geminium (self-replicating)",
        "R": 10, "T": 10, "mu": 0.14, "sigma": 0.014,
        "beta": [1, 0.5],
        "seed": "geminium",
    },
    "scutium": {
        "name": "Scutium (shield crawler)",
        "R": 12, "T": 10, "mu": 0.16, "sigma": 0.02,
        "beta": [1, 0.3, 0.7],
        "seed": "random_blobs",
    },
    "hydrogeminium": {
        "name": "Hydrogeminium (fluid replicator)",
        "R": 14, "T": 10, "mu": 0.15, "sigma": 0.016,
        "beta": [1, 0.6, 0.2],
        "seed": "random_blobs",
    },
    "wanderer": {
        "name": "Wanderer (drifting blob)",
        "R": 10, "T": 10, "mu": 0.12, "sigma": 0.012,
        "beta": [1],
        "seed": "random_blobs",
    },
    "smooth_life": {
        "name": "SmoothLife (organic soup)",
        "R": 8, "T": 5, "mu": 0.3, "sigma": 0.03,
        "beta": [1, 0.5],
        "seed": "random_noise",
    },
}

LENIA_PRESET_NAMES = list(LENIA_PRESETS.keys())

_lenia_A = None       # 2D state array (float 0.0-1.0)
_lenia_kernel = None  # precomputed convolution kernel (numpy) or kernel params
_lenia_preset_idx = 0
_lenia_R = 13
_lenia_T = 10
_lenia_mu = 0.15
_lenia_sigma = 0.015
_lenia_beta = [1]


def _lenia_bell(x, mu, sigma):
    """Gaussian bell function for kernel and growth."""
    return math.exp(-((x - mu) ** 2) / (2.0 * sigma ** 2))


def _lenia_build_kernel(R, beta):
    """Build the Lenia ring-shaped kernel with Gaussian bumps.

    The kernel is a 2D array of size (2R+1) x (2R+1), normalized to sum to 1.
    beta is a list of peak heights for concentric rings.
    """
    size = 2 * R + 1
    n_rings = len(beta)
    if _HAS_NUMPY:
        kernel = np.zeros((size, size), dtype=np.float64)
        for y in range(size):
            for x in range(size):
                dy = y - R
                dx = x - R
                r = math.sqrt(dy * dy + dx * dx) / R
                if r <= 1.0:
                    ring_idx = min(int(r * n_rings), n_rings - 1)
                    # Gaussian bump centered at (ring_idx + 0.5) / n_rings
                    ring_center = (ring_idx + 0.5) / n_rings
                    ring_width = 0.5 / n_rings
                    kernel[y, x] = beta[ring_idx] * _lenia_bell(r, ring_center, ring_width)
        total = kernel.sum()
        if total > 0:
            kernel /= total
        return kernel
    else:
        kernel = [[0.0] * size for _ in range(size)]
        total = 0.0
        for y in range(size):
            for x in range(size):
                dy = y - R
                dx = x - R
                r = math.sqrt(dy * dy + dx * dx) / R
                if r <= 1.0:
                    ring_idx = min(int(r * n_rings), n_rings - 1)
                    ring_center = (ring_idx + 0.5) / n_rings
                    ring_width = 0.5 / n_rings
                    val = beta[ring_idx] * _lenia_bell(r, ring_center, ring_width)
                    kernel[y][x] = val
                    total += val
        if total > 0:
            for y in range(size):
                for x in range(size):
                    kernel[y][x] /= total
        return kernel


def _lenia_growth(u, mu, sigma):
    """Lenia growth function: maps potential to cell update rate."""
    return 2.0 * math.exp(-((u - mu) ** 2) / (2.0 * sigma ** 2)) - 1.0


def _lenia_init(rows, cols, seed_type="orbium"):
    """Initialize Lenia state array and precompute kernel."""
    global _lenia_A, _lenia_kernel
    import random

    _lenia_kernel = _lenia_build_kernel(_lenia_R, _lenia_beta)

    if _HAS_NUMPY:
        _lenia_A = np.zeros((rows, cols), dtype=np.float64)
    else:
        _lenia_A = [[0.0] * cols for _ in range(rows)]

    if seed_type == "orbium":
        # Place a circular blob in the center — approximation of the Orbium glider
        cr, cc = rows // 2, cols // 2
        R = _lenia_R
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                r2 = dy * dy + dx * dx
                if r2 <= R * R:
                    nr, nc = (cr + dy) % rows, (cc + dx) % cols
                    # Gaussian profile
                    dist = math.sqrt(r2) / R
                    val = max(0.0, 1.0 - dist * dist)
                    if _HAS_NUMPY:
                        _lenia_A[nr, nc] = val
                    else:
                        _lenia_A[nr][nc] = val
    elif seed_type == "geminium":
        # Place two adjacent blobs to encourage splitting/replication
        cr, cc = rows // 2, cols // 2
        R = _lenia_R
        for offset_c in [-R, R]:
            for dy in range(-R, R + 1):
                for dx in range(-R, R + 1):
                    r2 = dy * dy + dx * dx
                    if r2 <= R * R:
                        nr = (cr + dy) % rows
                        nc = (cc + offset_c + dx) % cols
                        dist = math.sqrt(r2) / R
                        val = max(0.0, 0.8 * (1.0 - dist * dist))
                        if _HAS_NUMPY:
                            _lenia_A[nr, nc] = max(_lenia_A[nr, nc], val)
                        else:
                            _lenia_A[nr][nc] = max(_lenia_A[nr][nc], val)
    elif seed_type == "random_blobs":
        # Scatter several Gaussian blobs
        num_blobs = max(3, (rows * cols) // 1500)
        for _ in range(num_blobs):
            br = random.randint(0, rows - 1)
            bc = random.randint(0, cols - 1)
            blob_r = random.randint(max(3, _lenia_R // 2), _lenia_R)
            for dy in range(-blob_r, blob_r + 1):
                for dx in range(-blob_r, blob_r + 1):
                    r2 = dy * dy + dx * dx
                    if r2 <= blob_r * blob_r:
                        nr = (br + dy) % rows
                        nc = (bc + dx) % cols
                        dist = math.sqrt(r2) / blob_r
                        val = random.uniform(0.5, 1.0) * max(0.0, 1.0 - dist * dist)
                        if _HAS_NUMPY:
                            _lenia_A[nr, nc] = min(1.0, _lenia_A[nr, nc] + val)
                        else:
                            _lenia_A[nr][nc] = min(1.0, _lenia_A[nr][nc] + val)
    elif seed_type == "random_noise":
        # Fill with low random noise — good for SmoothLife-style emergence
        if _HAS_NUMPY:
            _lenia_A = np.random.uniform(0.0, 0.3, (rows, cols))
        else:
            _lenia_A = [[random.uniform(0.0, 0.3) for _ in range(cols)] for _ in range(rows)]


def _lenia_to_grid(rows, cols):
    """Convert Lenia state to an integer grid (0-100) for display."""
    grid = make_grid(rows, cols)
    if _lenia_A is None:
        return grid
    if _HAS_NUMPY:
        quantized = np.clip(np.array(_lenia_A) * 100, 0, 100).astype(int)
        return quantized.tolist()
    else:
        for r in range(rows):
            for c in range(cols):
                grid[r][c] = max(0, min(100, int(_lenia_A[r][c] * 100)))
        return grid


def _step_lenia_numpy():
    """Lenia step using NumPy/SciPy convolution."""
    global _lenia_A
    if _lenia_A is None:
        return
    # Convolve state with kernel to get potential field
    U = convolve2d(_lenia_A, _lenia_kernel, mode="same", boundary="wrap")
    # Vectorized growth function
    G = 2.0 * np.exp(-((_lenia_mu - U) ** 2) / (2.0 * _lenia_sigma ** 2)) - 1.0
    # Update with time step
    dt = 1.0 / _lenia_T
    _lenia_A = np.clip(_lenia_A + dt * G, 0.0, 1.0)


def _lenia_apply_preset(preset_name):
    """Apply a Lenia preset's parameters to the module-level state."""
    global _lenia_R, _lenia_T, _lenia_mu, _lenia_sigma, _lenia_beta
    preset = LENIA_PRESETS[preset_name]
    _lenia_R = preset["R"]
    _lenia_T = preset["T"]
    _lenia_mu = preset["mu"]
    _lenia_sigma = preset["sigma"]
    _lenia_beta = preset["beta"]


def _step_lenia_python():
    """Lenia step using pure Python — cell by cell convolution."""
    global _lenia_A
    if _lenia_A is None:
        return
    rows = len(_lenia_A)
    cols = len(_lenia_A[0])
    R = _lenia_R
    ksize = 2 * R + 1
    dt = 1.0 / _lenia_T

    new_A = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            # Compute potential U via kernel convolution
            potential = 0.0
            for ky in range(ksize):
                for kx in range(ksize):
                    kval = _lenia_kernel[ky][kx]
                    if kval == 0.0:
                        continue
                    nr = (r + ky - R) % rows
                    nc = (c + kx - R) % cols
                    potential += kval * _lenia_A[nr][nc]
            # Growth and update
            g = _lenia_growth(potential, _lenia_mu, _lenia_sigma)
            new_A[r][c] = max(0.0, min(1.0, _lenia_A[r][c] + dt * g))
    _lenia_A = new_A


def parse_rule_string(rule_str):
    """Parse a rule string like 'B36/S23' into birth/survival sets."""
    rule_str = rule_str.upper().replace(" ", "")
    if "/" in rule_str:
        parts = rule_str.split("/")
    else:
        # Try Bx/Sy format without slash: B36S23
        idx = rule_str.find("S")
        if idx == -1:
            raise ValueError(f"Invalid rule format: {rule_str}")
        parts = [rule_str[:idx], rule_str[idx:]]
    birth = set()
    survival = set()
    for part in parts:
        if part.startswith("B"):
            birth = {int(ch) for ch in part[1:] if ch.isdigit()}
        elif part.startswith("S"):
            survival = {int(ch) for ch in part[1:] if ch.isdigit()}
    return {"b": birth, "s": survival, "name": rule_str}


# --- Starter Patterns (relative coordinates) ---

PATTERNS = {
    "glider": [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
    "pulsar": [
        # Quarter-symmetric; full pattern listed explicitly
        (2, 4), (2, 5), (2, 6), (2, 10), (2, 11), (2, 12),
        (4, 2), (4, 7), (4, 9), (4, 14),
        (5, 2), (5, 7), (5, 9), (5, 14),
        (6, 2), (6, 7), (6, 9), (6, 14),
        (7, 4), (7, 5), (7, 6), (7, 10), (7, 11), (7, 12),
        (9, 4), (9, 5), (9, 6), (9, 10), (9, 11), (9, 12),
        (10, 2), (10, 7), (10, 9), (10, 14),
        (11, 2), (11, 7), (11, 9), (11, 14),
        (12, 2), (12, 7), (12, 9), (12, 14),
        (14, 4), (14, 5), (14, 6), (14, 10), (14, 11), (14, 12),
    ],
    "gosper": [
        # Gosper glider gun
        (5, 1), (5, 2), (6, 1), (6, 2),
        (5, 11), (6, 11), (7, 11),
        (4, 12), (8, 12),
        (3, 13), (9, 13),
        (3, 14), (9, 14),
        (6, 15),
        (4, 16), (8, 16),
        (5, 17), (6, 17), (7, 17),
        (6, 18),
        (3, 21), (4, 21), (5, 21),
        (3, 22), (4, 22), (5, 22),
        (2, 23), (6, 23),
        (1, 25), (2, 25), (6, 25), (7, 25),
        (3, 35), (4, 35), (3, 36), (4, 36),
    ],
    "random": [],  # handled specially
}

# --- Wireworld Built-in Patterns ---
# Stored as list of (row, col, state) tuples
WIREWORLD_PATTERNS = {
    "ww_diode": [
        # A diode — signal flows left-to-right only
        #   ..HTC..
        #   .C...C.
        #   ..CCC..
        (0, 2, WW_HEAD), (0, 3, WW_TAIL), (0, 4, WW_CONDUCTOR),
        (1, 1, WW_CONDUCTOR), (1, 5, WW_CONDUCTOR),
        (2, 2, WW_CONDUCTOR), (2, 3, WW_CONDUCTOR), (2, 4, WW_CONDUCTOR),
        # Input wire
        (0, 0, WW_CONDUCTOR), (0, 1, WW_CONDUCTOR),
        # Output wire
        (0, 5, WW_CONDUCTOR), (0, 6, WW_CONDUCTOR), (0, 7, WW_CONDUCTOR),
    ],
    "ww_clock": [
        # A simple clock — a 6-cell loop generating periodic signals
        # .CCC.
        # C...C
        # .CHT.
        # Output wire extends right from top
        (0, 1, WW_CONDUCTOR), (0, 2, WW_CONDUCTOR), (0, 3, WW_CONDUCTOR),
        (1, 0, WW_CONDUCTOR), (1, 4, WW_CONDUCTOR),
        (2, 1, WW_CONDUCTOR), (2, 2, WW_HEAD), (2, 3, WW_TAIL),
        # Output wire from top-right corner
        (0, 4, WW_CONDUCTOR), (0, 5, WW_CONDUCTOR), (0, 6, WW_CONDUCTOR),
        (0, 7, WW_CONDUCTOR),
    ],
    "ww_or_gate": [
        # OR gate — output fires if either input has a signal
        # Two input wires converge to a single output wire
        # Input A (top)
        (0, 0, WW_CONDUCTOR), (0, 1, WW_CONDUCTOR), (0, 2, WW_CONDUCTOR),
        (0, 3, WW_CONDUCTOR),
        # Input B (bottom)
        (4, 0, WW_CONDUCTOR), (4, 1, WW_CONDUCTOR), (4, 2, WW_CONDUCTOR),
        (4, 3, WW_CONDUCTOR),
        # Junction
        (1, 3, WW_CONDUCTOR), (2, 3, WW_CONDUCTOR), (3, 3, WW_CONDUCTOR),
        # Output wire
        (2, 4, WW_CONDUCTOR), (2, 5, WW_CONDUCTOR), (2, 6, WW_CONDUCTOR),
        (2, 7, WW_CONDUCTOR),
        # Signal on input A
        (0, 0, WW_HEAD), (0, 1, WW_TAIL),
    ],
    "ww_and_gate": [
        # AND gate — output fires only if both inputs have signals
        # Based on the classic Wireworld AND gate design
        # Input A (top)
        (0, 0, WW_CONDUCTOR), (0, 1, WW_CONDUCTOR), (0, 2, WW_CONDUCTOR),
        (1, 2, WW_CONDUCTOR),
        # Input B (bottom)
        (4, 0, WW_CONDUCTOR), (4, 1, WW_CONDUCTOR), (4, 2, WW_CONDUCTOR),
        (3, 2, WW_CONDUCTOR),
        # Central column (the AND logic)
        (2, 2, WW_CONDUCTOR),
        # Output wire
        (2, 3, WW_CONDUCTOR), (2, 4, WW_CONDUCTOR), (2, 5, WW_CONDUCTOR),
        (2, 6, WW_CONDUCTOR),
    ],
}


CELLS_DIR = os.path.expanduser("~/.life-patterns")
SCRIPTS_DIR = os.path.expanduser("~/.life-scripts")


# --- Scripting Engine ---

class ScriptEngine:
    """Safe Python DSL sandbox for user-programmable automation and custom rules.

    Scripts are plain Python files executed in a restricted namespace with access
    to a grid API, pattern placement, custom rule definitions, and challenge mode.
    """

    # Whitelisted modules scripts may import
    SAFE_MODULES = {"math", "random", "itertools", "functools", "collections"}

    # Whitelisted builtins available to scripts
    SAFE_BUILTINS = {
        "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
        "enumerate": enumerate, "filter": filter, "float": float, "int": int,
        "len": len, "list": list, "map": map, "max": max, "min": min,
        "print": print, "range": range, "reversed": reversed, "round": round,
        "set": set, "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
        "zip": zip, "True": True, "False": False, "None": None,
        "isinstance": isinstance, "type": type,
    }

    def __init__(self):
        self.custom_rule_fn = None
        self.on_step_fn = None
        self.challenge_target = None
        self.challenge_max_gens = None
        self.challenge_active = False
        self.challenge_won = False
        self.challenge_lost = False
        self.log_lines = []
        self.script_name = ""
        self._grid = None
        self._grid_rows = 0
        self._grid_cols = 0
        self._actions = []  # deferred actions to apply

    def bind_grid(self, grid):
        """Bind the engine to a live grid reference."""
        self._grid = grid
        self._grid_rows = len(grid)
        self._grid_cols = len(grid[0])

    def _log(self, *args):
        line = " ".join(str(a) for a in args)
        self.log_lines.append(line)
        if len(self.log_lines) > 50:
            self.log_lines.pop(0)

    def _safe_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        """Restricted import that only allows whitelisted modules."""
        if name not in self.SAFE_MODULES:
            raise ImportError(f"Module '{name}' is not allowed in scripts. "
                              f"Allowed: {', '.join(sorted(self.SAFE_MODULES))}")
        import importlib
        return importlib.import_module(name)

    def _build_namespace(self):
        """Build the restricted execution namespace for scripts."""
        engine = self

        class GridAPI:
            """Proxy object giving scripts safe access to the grid."""
            @property
            def rows(self_):
                return engine._grid_rows

            @property
            def cols(self_):
                return engine._grid_cols

            def get(self_, r, c):
                """Get cell value at (r, c). Returns 0 if out of bounds."""
                if 0 <= r < engine._grid_rows and 0 <= c < engine._grid_cols:
                    return engine._grid[r][c]
                return 0

            def set(self_, r, c, val):
                """Set cell value at (r, c)."""
                if 0 <= r < engine._grid_rows and 0 <= c < engine._grid_cols:
                    engine._grid[r][c] = int(val)

            def clear(self_):
                """Clear the entire grid."""
                for r in range(engine._grid_rows):
                    for c in range(engine._grid_cols):
                        engine._grid[r][c] = 0

            def population(self_):
                """Count live cells."""
                return sum(1 for r in range(engine._grid_rows)
                           for c in range(engine._grid_cols)
                           if engine._grid[r][c])

            def neighbours(self_, r, c):
                """Count live neighbours of cell (r, c) with topology-aware wrapping."""
                rows, cols = engine._grid_rows, engine._grid_cols
                count = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        coords = _wrap_coords(r + dr, c + dc, rows, cols)
                        if coords is not None and engine._grid[coords[0]][coords[1]]:
                            count += 1
                return count

            def fill_random(self_, density=0.5):
                """Fill grid randomly with given density (0.0-1.0)."""
                import random as _rnd
                for r in range(engine._grid_rows):
                    for c in range(engine._grid_cols):
                        engine._grid[r][c] = 1 if _rnd.random() < density else 0

            def place(self_, pattern_name, row=None, col=None):
                """Place a named built-in pattern at (row, col) or centered."""
                if pattern_name not in PATTERNS:
                    engine._log(f"Unknown pattern: {pattern_name}")
                    return
                place_pattern(engine._grid, pattern_name, row, col)

            def stamp(self_, cells, row=0, col=0):
                """Stamp a 2D list of 0/1 onto the grid at (row, col)."""
                for r in range(len(cells)):
                    for c in range(len(cells[0])):
                        gr, gc = row + r, col + c
                        if 0 <= gr < engine._grid_rows and 0 <= gc < engine._grid_cols:
                            if cells[r][c]:
                                engine._grid[gr][gc] = 1

            def rect(self_, r1, c1, r2, c2, val=1):
                """Fill a rectangle with the given value."""
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        if 0 <= r < engine._grid_rows and 0 <= c < engine._grid_cols:
                            engine._grid[r][c] = int(val)

            def line(self_, r1, c1, r2, c2, val=1):
                """Draw a line using Bresenham's algorithm."""
                dr = abs(r2 - r1)
                dc = abs(c2 - c1)
                sr = 1 if r1 < r2 else -1
                sc = 1 if c1 < c2 else -1
                err = dr - dc
                r, c = r1, c1
                while True:
                    if 0 <= r < engine._grid_rows and 0 <= c < engine._grid_cols:
                        engine._grid[r][c] = int(val)
                    if r == r2 and c == c2:
                        break
                    e2 = 2 * err
                    if e2 > -dc:
                        err -= dc
                        r += sr
                    if e2 < dr:
                        err += dr
                        c += sc

            def circle(self_, cr, cc, radius, val=1):
                """Draw a circle outline centered at (cr, cc)."""
                for angle in range(360):
                    rad = math.radians(angle)
                    r = int(round(cr + radius * math.sin(rad)))
                    c = int(round(cc + radius * math.cos(rad)))
                    if 0 <= r < engine._grid_rows and 0 <= c < engine._grid_cols:
                        engine._grid[r][c] = int(val)

        def set_rule(birth, survival, name=None):
            """Set the active rule using birth/survival sets.

            Example: set_rule({3}, {2, 3}) for Conway's Life.
            """
            engine._actions.append(("rule", {
                "b": set(birth), "s": set(survival),
                "name": name or f"Script (B{''.join(map(str, sorted(birth)))}/S{''.join(map(str, sorted(survival)))})"
            }))

        def custom_rule(fn):
            """Register a custom step function.

            The function receives (alive, neighbours, age, row, col) and must
            return the new cell value (0 for dead, positive int for alive/age).

            Examples:
                # Probabilistic death for isolated cells
                def my_rule(alive, n, age, r, c):
                    if alive and n < 2:
                        import random
                        return (age + 1) if random.random() < 0.5 else 0
                    if alive and n in (2, 3):
                        return age + 1
                    if not alive and n == 3:
                        return 1
                    return 0
                custom_rule(my_rule)
            """
            if callable(fn):
                engine.custom_rule_fn = fn
                engine._log("Custom rule registered")
            else:
                engine._log("custom_rule() requires a callable")
            return fn

        def on_step(fn):
            """Register a callback invoked after each simulation step.

            The function receives (generation, population).

            Example:
                @on_step
                def check(gen, pop):
                    if pop == 0:
                        log("Everything died at gen", gen)
            """
            if callable(fn):
                engine.on_step_fn = fn
            return fn

        def challenge(target_pop, max_gens, description=""):
            """Activate challenge mode.

            The user must reach target_pop population within max_gens generations.
            """
            engine.challenge_target = target_pop
            engine.challenge_max_gens = max_gens
            engine.challenge_active = True
            engine.challenge_won = False
            engine.challenge_lost = False
            desc = description or f"Reach population {target_pop} within {max_gens} generations"
            engine._log(f"CHALLENGE: {desc}")

        def log(*args):
            """Log a message to the script console."""
            engine._log(*args)

        ns = {
            "__builtins__": {**self.SAFE_BUILTINS, "__import__": self._safe_import},
            "grid": GridAPI(),
            "set_rule": set_rule,
            "custom_rule": custom_rule,
            "on_step": on_step,
            "challenge": challenge,
            "log": log,
            "math": math,
            "PATTERNS": list(PATTERNS.keys()),
        }
        return ns

    def load_and_run(self, filepath, grid):
        """Load a script file and execute it."""
        self.bind_grid(grid)
        self.custom_rule_fn = None
        self.on_step_fn = None
        self.challenge_active = False
        self.challenge_won = False
        self.challenge_lost = False
        self.log_lines = []
        self._actions = []
        self.script_name = os.path.basename(filepath)

        try:
            with open(filepath, "r") as f:
                source = f.read()
        except OSError as e:
            self.log_lines.append(f"Error loading script: {e}")
            return None

        ns = self._build_namespace()
        try:
            code = compile(source, filepath, "exec")
            exec(code, ns)
        except Exception as e:
            self.log_lines.append(f"Script error: {type(e).__name__}: {e}")

        # Return any deferred actions (like rule changes)
        actions = self._actions
        self._actions = []
        return actions

    def run_step_callback(self, generation, population):
        """Called after each simulation step to run on_step and check challenge."""
        if self.on_step_fn:
            try:
                self.on_step_fn(generation, population)
            except Exception as e:
                self._log(f"on_step error: {e}")

        if self.challenge_active and not self.challenge_won and not self.challenge_lost:
            if population >= self.challenge_target:
                self.challenge_won = True
                self._log(f"CHALLENGE WON at gen {generation}! (pop={population})")
            elif generation >= self.challenge_max_gens:
                self.challenge_lost = True
                self._log(f"CHALLENGE FAILED at gen {generation} (pop={population}, needed {self.challenge_target})")

    def custom_step(self, grid):
        """Run one simulation step using the custom rule function.

        Returns a new grid, or None if no custom rule is set.
        """
        if not self.custom_rule_fn:
            return None
        self.bind_grid(grid)
        rows, cols = len(grid), len(grid[0])
        new = make_grid(rows, cols)
        fn = self.custom_rule_fn
        for r in range(rows):
            for c in range(cols):
                age = grid[r][c]
                alive = age > 0
                n = _neighbours(grid, r, c, rows, cols)
                try:
                    result = fn(alive, n, age, r, c)
                    new[r][c] = max(0, int(result))
                except Exception:
                    new[r][c] = 0
        return new


def list_scripts():
    """List .py script files from the scripts directory."""
    if not os.path.isdir(SCRIPTS_DIR):
        return []
    files = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py")]
    files.sort()
    return files


def save_cells(grid, filepath, rule=None):
    """Save grid to a .cells plaintext file."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    rows, cols = len(grid), len(grid[0])
    ww = rule is not None and _is_wireworld(rule)
    # Find bounding box of non-empty cells to trim empty borders
    min_r = min_c = float("inf")
    max_r = max_c = float("-inf")
    for r in range(rows):
        for c in range(cols):
            if grid[r][c]:
                min_r = min(min_r, r)
                max_r = max(max_r, r)
                min_c = min(min_c, c)
                max_c = max(max_c, c)
    with open(filepath, "w") as f:
        f.write(f"!Name: {os.path.splitext(os.path.basename(filepath))[0]}\n")
        if ww:
            f.write("!Rule: Wireworld\n")
        if min_r == float("inf"):
            # Empty grid
            f.write(".\n")
            return
        for r in range(min_r, max_r + 1):
            line = ""
            for c in range(min_c, max_c + 1):
                if ww:
                    # Wireworld: .=empty, H=head, T=tail, C=conductor
                    v = grid[r][c]
                    line += {WW_EMPTY: ".", WW_HEAD: "H", WW_TAIL: "T", WW_CONDUCTOR: "C"}.get(v, ".")
                else:
                    line += "O" if grid[r][c] else "."
            f.write(line.rstrip(".") + "\n")


def load_cells(filepath, rows, cols):
    """Load a .cells plaintext file into a new grid, centred."""
    pattern_rows = []
    is_wireworld = False
    with open(filepath, "r") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line.startswith("!"):
                if "wireworld" in line.lower():
                    is_wireworld = True
                continue
            row = []
            for ch in line:
                if is_wireworld:
                    row.append({"H": WW_HEAD, "T": WW_TAIL, "C": WW_CONDUCTOR}.get(ch, WW_EMPTY))
                else:
                    row.append(1 if ch == "O" else 0)
            pattern_rows.append(row)
    if not pattern_rows:
        return make_grid(rows, cols), is_wireworld
    p_rows = len(pattern_rows)
    p_cols = max(len(r) for r in pattern_rows)
    grid = make_grid(rows, cols)
    off_r = (rows - p_rows) // 2
    off_c = (cols - p_cols) // 2
    for r, row in enumerate(pattern_rows):
        for c, val in enumerate(row):
            nr, nc = r + off_r, c + off_c
            if 0 <= nr < rows and 0 <= nc < cols:
                grid[nr][nc] = val
    return grid, is_wireworld


def parse_rle(text):
    """Parse RLE-encoded pattern text into (rows_2d, name, rule_string).

    Returns a list of rows (each a list of 0/1), the pattern name (or ""),
    and the rule string from the header (or "").
    """
    lines = text.splitlines()
    name = ""
    rule_str = ""
    header_found = False
    width = height = 0
    pattern_data = ""

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # Metadata comments
            if stripped.startswith("#N"):
                name = stripped[2:].strip()
            continue
        if not header_found and stripped.startswith("x"):
            # Header line: x = W, y = H[, rule = ...]
            header_found = True
            m = re.search(r"x\s*=\s*(\d+)", stripped)
            if m:
                width = int(m.group(1))
            m = re.search(r"y\s*=\s*(\d+)", stripped)
            if m:
                height = int(m.group(1))
            m = re.search(r"rule\s*=\s*(\S+)", stripped, re.IGNORECASE)
            if m:
                rule_str = m.group(1)
            continue
        # Accumulate pattern data (ignore whitespace)
        pattern_data += stripped
        if "!" in stripped:
            break

    # Remove anything after '!'
    pattern_data = pattern_data.split("!")[0]

    # Detect if this is a Wireworld or multi-state rule
    is_wireworld = "wireworld" in rule_str.lower() if rule_str else False

    # Decode the run-length data
    rows_2d = []
    current_row = []
    i = 0
    while i < len(pattern_data):
        # Parse optional run count
        run_count = 0
        while i < len(pattern_data) and pattern_data[i].isdigit():
            run_count = run_count * 10 + int(pattern_data[i])
            i += 1
        if run_count == 0:
            run_count = 1
        if i >= len(pattern_data):
            break
        ch = pattern_data[i]
        i += 1
        if ch == "b" or ch == ".":
            current_row.extend([0] * run_count)
        elif ch == "o" or ch == "A":
            current_row.extend([1] * run_count)
        elif ch == "B":
            current_row.extend([2] * run_count)
        elif ch == "C":
            current_row.extend([3] * run_count)
        elif ch == "$":
            rows_2d.append(current_row)
            # '$' can have a run count meaning multiple row-ends
            for _ in range(run_count - 1):
                rows_2d.append([])
            current_row = []

    # Flush last row
    if current_row:
        rows_2d.append(current_row)

    # Normalise row widths (pad with 0s to the declared width or max width)
    target_w = max(width, max((len(r) for r in rows_2d), default=0))
    for row in rows_2d:
        if len(row) < target_w:
            row.extend([0] * (target_w - len(row)))

    return rows_2d, name, rule_str


def encode_rle(stamp, name="", rule_str="B3/S23"):
    """Encode a 2D list of cell values into RLE format text.

    Supports multi-state: 0=b, 1=o, 2=B, 3=C (for Wireworld etc.)
    """
    if not stamp or not stamp[0]:
        return ""
    height = len(stamp)
    width = max(len(r) for r in stamp)

    # Detect if multi-state (values > 1 present)
    _state_chars = {0: "b", 1: "o", 2: "B", 3: "C"}

    lines = []
    if name:
        lines.append(f"#N {name}")
    lines.append(f"x = {width}, y = {height}, rule = {rule_str}")

    # Build the pattern data
    data = ""
    for r_idx, row in enumerate(stamp):
        # Pad row to full width
        padded = list(row) + [0] * (width - len(row))
        # Strip trailing dead cells (they're implicit)
        while padded and padded[-1] == 0:
            padded.pop()

        # Run-length encode this row
        i = 0
        while i < len(padded):
            val = padded[i]
            count = 1
            while i + count < len(padded) and padded[i + count] == val:
                count += 1
            ch = _state_chars.get(val, "o")
            if count > 1:
                data += f"{count}{ch}"
            else:
                data += ch
            i += count

        if r_idx < height - 1:
            data += "$"

    data += "!"

    # Wrap lines at 70 characters
    while len(data) > 70:
        lines.append(data[:70])
        data = data[70:]
    lines.append(data)

    return "\n".join(lines) + "\n"


def load_rle(filepath, rows, cols):
    """Load an RLE file into a new grid, centred."""
    with open(filepath, "r") as f:
        text = f.read()
    pattern_rows, _name, rule_str = parse_rle(text)
    is_wireworld = "wireworld" in rule_str.lower() if rule_str else False
    if not pattern_rows:
        return make_grid(rows, cols), is_wireworld
    p_rows = len(pattern_rows)
    p_cols = max(len(r) for r in pattern_rows)
    grid = make_grid(rows, cols)
    off_r = (rows - p_rows) // 2
    off_c = (cols - p_cols) // 2
    for r, row in enumerate(pattern_rows):
        for c, val in enumerate(row):
            nr, nc = r + off_r, c + off_c
            if 0 <= nr < rows and 0 <= nc < cols:
                grid[nr][nc] = val
    return grid, is_wireworld


def save_rle(grid, filepath, rule=None):
    """Save grid to an RLE file."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    rows, cols = len(grid), len(grid[0])
    ww = rule is not None and _is_wireworld(rule)
    # Find bounding box of non-empty cells
    min_r = min_c = float("inf")
    max_r = max_c = float("-inf")
    for r in range(rows):
        for c in range(cols):
            if grid[r][c]:
                min_r = min(min_r, r)
                max_r = max(max_r, r)
                min_c = min(min_c, c)
                max_c = max(max_c, c)
    name = os.path.splitext(os.path.basename(filepath))[0]
    if min_r == float("inf"):
        # Empty grid
        with open(filepath, "w") as f:
            f.write(encode_rle([[0]], name=name))
        return
    # Extract the bounding box as a stamp
    stamp = []
    for r in range(min_r, max_r + 1):
        row = []
        for c in range(min_c, max_c + 1):
            if ww:
                row.append(grid[r][c])  # preserve state value
            else:
                row.append(1 if grid[r][c] else 0)
        stamp.append(row)
    if ww:
        rule_str = "Wireworld"
    elif rule:
        b = "".join(str(d) for d in sorted(rule["b"]))
        s = "".join(str(d) for d in sorted(rule["s"]))
        rule_str = f"B{b}/S{s}"
    else:
        rule_str = "B3/S23"
    with open(filepath, "w") as f:
        f.write(encode_rle(stamp, name=name, rule_str=rule_str))


def _load_pattern_file(filepath, rows, cols):
    """Load a pattern file (.cells or .rle) based on extension.

    Returns (grid, is_wireworld).
    """
    if filepath.lower().endswith(".rle"):
        return load_rle(filepath, rows, cols)
    return load_cells(filepath, rows, cols)


def curses_input(stdscr, prompt, max_y, max_x):
    """Get a line of text input from the user in curses."""
    curses.curs_set(1)
    stdscr.nodelay(False)
    buf = ""
    while True:
        # Draw prompt
        try:
            stdscr.move(max_y - 1, 0)
            stdscr.clrtoeol()
            display = (prompt + buf)[:max_x - 1]
            stdscr.addstr(max_y - 1, 0, display, curses.color_pair(2) | curses.A_REVERSE)
        except curses.error:
            pass
        stdscr.refresh()
        key = stdscr.getch()
        if key in (ord("\n"), curses.KEY_ENTER):
            break
        elif key == 27:  # Escape
            buf = ""
            break
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 32 <= key <= 126:
            buf += chr(key)
    curses.curs_set(0)
    stdscr.nodelay(True)
    return buf


def list_saved_patterns():
    """Return list of .cells and .rle files in the patterns directory."""
    if not os.path.isdir(CELLS_DIR):
        return []
    return sorted(f for f in os.listdir(CELLS_DIR) if f.endswith(".cells") or f.endswith(".rle"))


def make_grid(rows, cols):
    return [[0] * cols for _ in range(rows)]


def place_wireworld_pattern(grid, name, row_off=None, col_off=None):
    """Place a Wireworld pattern (with multi-state cells) onto the grid."""
    rows, cols = len(grid), len(grid[0])
    cells = WIREWORLD_PATTERNS[name]
    if not cells:
        return
    max_r = max(r for r, c, s in cells)
    max_c = max(c for r, c, s in cells)
    if row_off is None:
        row_off = (rows - max_r) // 2
    if col_off is None:
        col_off = (cols - max_c) // 2
    for r, c, s in cells:
        nr, nc = r + row_off, c + col_off
        if 0 <= nr < rows and 0 <= nc < cols:
            grid[nr][nc] = s


def _wireworld_pattern_to_stamp(name):
    """Convert a Wireworld pattern to a 2D stamp (list of lists with state values)."""
    cells = WIREWORLD_PATTERNS.get(name)
    if not cells:
        return None
    max_r = max(r for r, c, s in cells) + 1
    max_c = max(c for r, c, s in cells) + 1
    stamp = [[0] * max_c for _ in range(max_r)]
    for r, c, s in cells:
        stamp[r][c] = s
    return stamp


def place_pattern(grid, name, row_off=None, col_off=None):
    rows, cols = len(grid), len(grid[0])
    cells = PATTERNS[name]

    if name == "random":
        import random
        for r in range(rows):
            for c in range(cols):
                grid[r][c] = random.randint(0, 1)
        return

    # Centre the pattern if no offset given
    if cells:
        max_r = max(r for r, c in cells)
        max_c = max(c for r, c in cells)
        if row_off is None:
            row_off = (rows - max_r) // 2
        if col_off is None:
            col_off = (cols - max_c) // 2
        for r, c in cells:
            nr, nc = r + row_off, c + col_off
            if 0 <= nr < rows and 0 <= nc < cols:
                grid[nr][nc] = 1


def step(grid, rule=None):
    if rule is None:
        rule = RULES["life"]
    if _is_physarum(rule):
        rows, cols = len(grid), len(grid[0])
        _phys_step()
        return _phys_to_grid(rows, cols)
    if _is_fallingsand(rule):
        rows, cols = len(grid), len(grid[0])
        _fs_step()
        return _fs_to_grid(rows, cols)
    if _is_wator(rule):
        rows, cols = len(grid), len(grid[0])
        _wator_step()
        return _wator_to_grid(rows, cols)
    if _is_turmite(rule):
        rows, cols = len(grid), len(grid[0])
        _turmite_step()
        return _turmite_to_grid(rows, cols)
    if _is_elementary(rule):
        rows, cols = len(grid), len(grid[0])
        _eca_step()
        return _eca_to_grid(rows, cols)
    if _is_lenia(rule):
        rows, cols = len(grid), len(grid[0])
        if _HAS_NUMPY:
            _step_lenia_numpy()
        else:
            _step_lenia_python()
        return _lenia_to_grid(rows, cols)
    if _is_grayscott(rule):
        rows, cols = len(grid), len(grid[0])
        if _HAS_NUMPY:
            _step_grayscott_numpy()
        else:
            _step_grayscott_python()
        return _gs_to_grid(rows, cols)
    if _is_wireworld(rule):
        if _HAS_NUMPY:
            return _step_wireworld_numpy(grid)
        return _step_wireworld(grid)
    if _HAS_NUMPY:
        return _step_numpy(grid, rule)
    return _step_python(grid, rule)


def _step_numpy(grid, rule):
    """Vectorized backend using SciPy 2D convolution — O(1) per cell."""
    # For non-torus topologies, fall back to the Python engine which handles
    # Klein bottle, Möbius strip, and bounded topologies correctly.
    if _topology != TOPO_TORUS:
        return _step_python(grid, rule)
    birth, survival = rule["b"], rule["s"]
    rows, cols = len(grid), len(grid[0])
    # Build age array and binary alive mask
    age = np.array(grid, dtype=np.int32)
    alive = (age > 0).astype(np.int32)
    # Neighbor kernel (Moore neighbourhood)
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]], dtype=np.int32)
    # Wrap boundary matches the toroidal topology of the Python engine
    neighbors = convolve2d(alive, kernel, mode="same", boundary="wrap")
    # Birth / survival masks
    birth_mask = np.zeros(9, dtype=bool)
    for b in birth:
        birth_mask[b] = True
    surv_mask = np.zeros(9, dtype=bool)
    for s in survival:
        surv_mask[s] = True
    born = (~alive.astype(bool)) & birth_mask[neighbors]
    survives = alive.astype(bool) & surv_mask[neighbors]
    # New age grid: survivors increment age, newborns get age 1, rest 0
    new_age = np.where(survives, age + 1, np.where(born, 1, 0))
    return new_age.tolist()


def _step_python(grid, rule):
    """Original cell-by-cell backend — no dependencies required."""
    birth, survival = rule["b"], rule["s"]
    rows, cols = len(grid), len(grid[0])
    new = make_grid(rows, cols)
    for r in range(rows):
        for c in range(cols):
            n = _neighbours(grid, r, c, rows, cols)
            if grid[r][c]:
                new[r][c] = (grid[r][c] + 1) if n in survival else 0
            else:
                new[r][c] = 1 if n in birth else 0
    return new


def _neighbours(grid, r, c, rows, cols):
    count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            coords = _wrap_coords(r + dr, c + dc, rows, cols)
            if coords is not None:
                count += 1 if grid[coords[0]][coords[1]] else 0
    return count


def _step_wireworld(grid):
    """Wireworld step function — pure Python backend."""
    rows, cols = len(grid), len(grid[0])
    new = make_grid(rows, cols)
    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            if cell == WW_EMPTY:
                new[r][c] = WW_EMPTY
            elif cell == WW_HEAD:
                new[r][c] = WW_TAIL
            elif cell == WW_TAIL:
                new[r][c] = WW_CONDUCTOR
            elif cell == WW_CONDUCTOR:
                # Count electron head neighbours
                heads = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        coords = _wrap_coords(r + dr, c + dc, rows, cols)
                        if coords is not None and grid[coords[0]][coords[1]] == WW_HEAD:
                            heads += 1
                new[r][c] = WW_HEAD if heads in (1, 2) else WW_CONDUCTOR
    return new


def _step_wireworld_numpy(grid):
    """Wireworld step function — vectorized NumPy backend."""
    if _topology != TOPO_TORUS:
        return _step_wireworld(grid)
    arr = np.array(grid, dtype=np.int32)
    rows, cols = arr.shape
    # Count electron head neighbours for each cell
    head_mask = (arr == WW_HEAD).astype(np.int32)
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]], dtype=np.int32)
    head_neighbors = convolve2d(head_mask, kernel, mode="same", boundary="wrap")
    new = np.zeros_like(arr)
    # Empty stays empty
    # Head -> Tail
    new[arr == WW_HEAD] = WW_TAIL
    # Tail -> Conductor
    new[arr == WW_TAIL] = WW_CONDUCTOR
    # Conductor -> Head if 1 or 2 head neighbours, else stays Conductor
    conductor_mask = arr == WW_CONDUCTOR
    becomes_head = conductor_mask & ((head_neighbors == 1) | (head_neighbors == 2))
    stays_conductor = conductor_mask & ~becomes_head
    new[becomes_head] = WW_HEAD
    new[stays_conductor] = WW_CONDUCTOR
    return new.tolist()


# --- HashLife Engine (Quadtree-memoized hypercomputation) ---


class _HashLifeNode:
    """Immutable quadtree node for HashLife.

    Level 0: a single cell (0 or 1).
    Level k >= 1: four children (nw, ne, sw, se), each level k-1.
    Represents a 2^k × 2^k region.
    """
    __slots__ = ("nw", "ne", "sw", "se", "level", "population", "_hash")

    def __init__(self, nw=None, ne=None, sw=None, se=None, level=0, population=0):
        self.nw = nw
        self.ne = ne
        self.sw = sw
        self.se = se
        self.level = level
        self.population = population
        if level == 0:
            self._hash = hash(population)
        else:
            self._hash = hash((id(nw), id(ne), id(sw), id(se)))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if self is other:
            return True
        if self.level != other.level:
            return False
        if self.level == 0:
            return self.population == other.population
        return (self.nw is other.nw and self.ne is other.ne and
                self.sw is other.sw and self.se is other.se)


class HashLifeEngine:
    """HashLife engine — computes Life generations in O(log N) time via
    quadtree memoization.  Can skip 2^(k-2) generations per step at level k.
    """

    def __init__(self):
        # Canonical node cache: (nw, ne, sw, se) -> node  or  pop -> leaf
        self._memo = {}
        # Result cache: node -> result_node (center after 2^(k-2) gens)
        self._result_cache = {}
        # Pre-create canonical leaf nodes
        self._dead = self._leaf(0)
        self._alive = self._leaf(1)
        self.root = None
        self.generation = 0
        # Offset: where grid (0,0) sits inside the quadtree
        self._origin_row = 0
        self._origin_col = 0
        # Step size control: 0 = max speed (2^(k-2)), can be reduced
        self._step_exponent = None  # None = max

    def _leaf(self, pop):
        """Return canonical level-0 node."""
        key = ("leaf", pop)
        if key in self._memo:
            return self._memo[key]
        n = _HashLifeNode(level=0, population=pop)
        self._memo[key] = n
        return n

    def _node(self, nw, ne, sw, se):
        """Return canonical internal node, creating if needed."""
        key = (id(nw), id(ne), id(sw), id(se))
        if key in self._memo:
            return self._memo[key]
        level = nw.level + 1
        pop = nw.population + ne.population + sw.population + se.population
        n = _HashLifeNode(nw, ne, sw, se, level, pop)
        self._memo[key] = n
        return n

    def _empty_tree(self, level):
        """Return a canonical empty (all-dead) tree at the given level."""
        if level == 0:
            return self._dead
        sub = self._empty_tree(level - 1)
        return self._node(sub, sub, sub, sub)

    def _expand(self, node):
        """Add a border of empty cells around the node (increase level by 1)."""
        empty = self._empty_tree(node.level - 1)
        return self._node(
            self._node(empty, empty, empty, node.nw),
            self._node(empty, empty, node.ne, empty),
            self._node(empty, node.sw, empty, empty),
            self._node(node.se, empty, empty, empty),
        )

    def _cell_value(self, node, row, col):
        """Get cell value at (row, col) within node's 2^level grid."""
        if node.level == 0:
            return node.population
        half = 1 << (node.level - 1)
        if row < half:
            if col < half:
                return self._cell_value(node.nw, row, col)
            else:
                return self._cell_value(node.ne, row, col - half)
        else:
            if col < half:
                return self._cell_value(node.sw, row - half, col)
            else:
                return self._cell_value(node.se, row - half, col - half)

    def _set_cell(self, node, row, col, val):
        """Return new node with cell at (row, col) set to val."""
        if node.level == 0:
            return self._leaf(val)
        half = 1 << (node.level - 1)
        if row < half:
            if col < half:
                return self._node(self._set_cell(node.nw, row, col, val),
                                  node.ne, node.sw, node.se)
            else:
                return self._node(node.nw, self._set_cell(node.ne, row, col - half, val),
                                  node.sw, node.se)
        else:
            if col < half:
                return self._node(node.nw, node.ne,
                                  self._set_cell(node.sw, row - half, col, val), node.se)
            else:
                return self._node(node.nw, node.ne, node.sw,
                                  self._set_cell(node.se, row - half, col - half, val))

    def _centred_sub(self, node):
        """Return the centre half-size node (the inner 2^(k-1) region)."""
        return self._node(node.nw.se, node.ne.sw, node.sw.ne, node.se.nw)

    def _centred_horizontal(self, west, east):
        """Return the centre of two horizontally adjacent nodes."""
        return self._node(west.ne.se, east.nw.sw, west.se.ne, east.sw.nw)

    def _centred_vertical(self, north, south):
        """Return the centre of two vertically adjacent nodes."""
        return self._node(north.sw.se, north.se.sw, south.nw.ne, south.ne.nw)

    def _centred_sub_sub(self, node):
        """Return the centre of the centre (inner quarter)."""
        return self._node(node.nw.se.se, node.ne.sw.sw,
                          node.sw.ne.ne, node.se.nw.nw)

    def _slow_simulation(self, node):
        """Base case: compute next generation for a 4x4 node (level 2).
        Returns the 2x2 centre after 1 step."""
        # Collect all 16 cells of the 4x4 grid
        def get(n, r, c):
            return self._cell_value(n, r, c)

        # Build flat 4x4 grid
        cells = [[0] * 4 for _ in range(4)]
        for r in range(4):
            for c in range(4):
                cells[r][c] = get(node, r, c)

        # Compute next state for 2x2 centre (rows 1-2, cols 1-2)
        result = [[0, 0], [0, 0]]
        for r in range(1, 3):
            for c in range(1, 3):
                count = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        count += cells[r + dr][c + dc]
                alive = cells[r][c]
                if alive:
                    result[r - 1][c - 1] = 1 if count in (2, 3) else 0
                else:
                    result[r - 1][c - 1] = 1 if count == 3 else 0

        return self._node(
            self._leaf(result[0][0]), self._leaf(result[0][1]),
            self._leaf(result[1][0]), self._leaf(result[1][1]))

    def _step_node(self, node):
        """Recursively compute the result of a node.
        For level k, returns centre 2^(k-1) region advanced by 2^step_exp gens.
        """
        if node in self._result_cache:
            return self._result_cache[node]

        if node.population == 0:
            result = self._empty_tree(node.level - 1)
            self._result_cache[node] = result
            return result

        if node.level == 2:
            result = self._slow_simulation(node)
            self._result_cache[node] = result
            return result

        fast = (self._step_exponent is None or
                self._step_exponent >= node.level - 2)

        if fast:
            # Phase 1 (fast): advance children by 2^(k-3) gens first
            n00 = self._step_node(node.nw)
            n01 = self._step_node(self._node(
                node.nw.ne, node.ne.nw, node.nw.se, node.ne.sw))
            n02 = self._step_node(node.ne)
            n10 = self._step_node(self._node(
                node.nw.sw, node.nw.se, node.sw.nw, node.sw.ne))
            n11 = self._step_node(self._node(
                node.nw.se, node.ne.sw, node.sw.ne, node.se.nw))
            n12 = self._step_node(self._node(
                node.ne.sw, node.ne.se, node.se.nw, node.se.ne))
            n20 = self._step_node(node.sw)
            n21 = self._step_node(self._node(
                node.sw.ne, node.se.nw, node.sw.se, node.se.sw))
            n22 = self._step_node(node.se)
        else:
            # Phase 1 (slow): just extract centres, no advancement
            n00 = self._centred_sub(node.nw)
            n01 = self._centred_horizontal(node.nw, node.ne)
            n02 = self._centred_sub(node.ne)
            n10 = self._centred_vertical(node.nw, node.sw)
            n11 = self._centred_sub_sub(node)
            n12 = self._centred_vertical(node.ne, node.se)
            n20 = self._centred_sub(node.sw)
            n21 = self._centred_horizontal(node.sw, node.se)
            n22 = self._centred_sub(node.se)

        # Phase 2: advance the 4 overlapping sub-squares by 2^(k-3) gens
        result = self._node(
            self._step_node(self._node(n00, n01, n10, n11)),
            self._step_node(self._node(n01, n02, n11, n12)),
            self._step_node(self._node(n10, n11, n20, n21)),
            self._step_node(self._node(n11, n12, n21, n22)))

        self._result_cache[node] = result
        return result

    def _generations_per_step(self):
        """How many generations the current step will advance."""
        if self.root is None:
            return 0
        if self._step_exponent is not None:
            return 1 << self._step_exponent
        return 1 << (self.root.level - 2)

    def from_grid(self, grid, rule):
        """Import a 2D list grid into the quadtree. Only supports B3/S23 (Life)."""
        self._memo.clear()
        self._result_cache.clear()
        self._dead = self._leaf(0)
        self._alive = self._leaf(1)

        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0

        # Determine level needed: 2^level >= 2*max(rows, cols) to leave border room
        size = max(rows, cols, 4) * 2
        level = 2
        while (1 << level) < size:
            level += 1

        # Center the grid within the tree
        full_size = 1 << level
        self._origin_row = (full_size - rows) // 2
        self._origin_col = (full_size - cols) // 2

        # Build tree from cells
        self.root = self._empty_tree(level)
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] > 0:
                    self.root = self._set_cell(self.root,
                                               r + self._origin_row,
                                               c + self._origin_col, 1)

    def to_grid(self, rows, cols):
        """Export the quadtree back to a 2D list grid (clipped to rows x cols).
        Alive cells get age=1 (HashLife tracks only alive/dead)."""
        grid = [[0] * cols for _ in range(rows)]
        if self.root is None:
            return grid
        # Offset: tree position (or, oc) maps to grid (0, 0)
        self._extract(self.root, -self._origin_row, -self._origin_col,
                       grid, rows, cols)
        return grid

    def _extract(self, node, top, left, grid, rows, cols):
        """Recursively extract cells from quadtree into grid.
        top/left = position of this node's top-left corner in grid coordinates."""
        if node.population == 0:
            return
        size = 1 << node.level
        # Skip if entirely outside viewport
        if top >= rows or left >= cols or top + size <= 0 or left + size <= 0:
            return
        if node.level == 0:
            if 0 <= top < rows and 0 <= left < cols:
                grid[top][left] = node.population
            return
        half = size >> 1
        self._extract(node.nw, top, left, grid, rows, cols)
        self._extract(node.ne, top, left + half, grid, rows, cols)
        self._extract(node.sw, top + half, left, grid, rows, cols)
        self._extract(node.se, top + half, left + half, grid, rows, cols)

    def step(self):
        """Advance the universe by 2^(k-2) generations (or less if throttled).
        Returns the number of generations advanced."""
        if self.root is None:
            return 0

        # Ensure root is large enough: need at least level 3, and pattern
        # must not touch the border (expand if needed)
        while self.root.level < 3:
            self.root = self._expand(self.root)
            pad = 1 << (self.root.level - 2)
            self._origin_row += pad
            self._origin_col += pad

        # Expand if any border quadrant is non-empty to avoid clipping
        while True:
            nw, ne, sw, se = self.root.nw, self.root.ne, self.root.sw, self.root.se
            border_pop = (nw.nw.population + nw.ne.population + nw.sw.population +
                          ne.nw.population + ne.ne.population + ne.se.population +
                          sw.nw.population + sw.sw.population + sw.se.population +
                          se.ne.population + se.sw.population + se.se.population)
            if border_pop == 0:
                break
            self.root = self._expand(self.root)
            pad = 1 << (self.root.level - 2)
            self._origin_row += pad
            self._origin_col += pad

        gens = self._generations_per_step()
        # _step_node returns center (level-1), then expand restores level.
        # Net effect on coordinates: _step_node shifts origin by -quarter,
        # expand shifts it back by +quarter — so origin is unchanged.
        self.root = self._step_node(self.root)
        self.root = self._expand(self.root)
        self.generation += gens
        return gens

    def set_step_exponent(self, exp):
        """Set the step size to 2^exp generations. None = maximum."""
        if exp is not None and exp < 0:
            exp = 0
        self._step_exponent = exp
        # Clear result cache when step size changes
        self._result_cache.clear()

    def get_step_exponent(self):
        return self._step_exponent

    def get_max_exponent(self):
        if self.root is None:
            return 0
        return max(0, self.root.level - 2)

    def get_population(self):
        if self.root is None:
            return 0
        return self.root.population

    def clear_caches(self):
        """Free memory by clearing memoization caches."""
        self._result_cache.clear()


def _age_color(age):
    """Return curses color pair number based on cell age."""
    if age <= 3:
        return 1   # green — newborn
    elif age <= 8:
        return 5   # cyan — young
    elif age <= 20:
        return 6   # blue — mature
    else:
        return 7   # magenta — ancient


def _wireworld_color(state):
    """Return curses color pair number for a Wireworld cell state."""
    if state == WW_HEAD:
        return 14      # blue — electron head
    elif state == WW_TAIL:
        return 13      # red — electron tail
    elif state == WW_CONDUCTOR:
        return 15      # yellow — conductor/wire
    return 1           # fallback


def _grayscott_color(val):
    """Return curses color pair number for a Gray-Scott concentration value (0-100)."""
    if val <= 5:
        return 19       # near-black background (very low V)
    elif val <= 20:
        return 6        # blue — low concentration
    elif val <= 45:
        return 5        # cyan — medium concentration
    elif val <= 70:
        return 1        # green — high concentration
    else:
        return 20       # bright white — peak concentration


# --- Braille Rendering ---

# Unicode Braille encodes a 2×4 dot matrix per character (U+2800–U+28FF).
# Dot positions map to bits as follows:
#   (0,0)=0x01  (1,0)=0x08
#   (0,1)=0x02  (1,1)=0x10
#   (0,2)=0x04  (1,2)=0x20
#   (0,3)=0x40  (1,3)=0x80

_BRAILLE_BASE = 0x2800
_BRAILLE_DOT = [
    [0x01, 0x08],
    [0x02, 0x10],
    [0x04, 0x20],
    [0x40, 0x80],
]


def _render_braille_grid(grid, rows, cols, term_rows, term_cols):
    """Render grid as Braille characters.

    Each terminal cell maps to a 2×4 block of grid cells, yielding
    effective resolution of (term_cols*2) × (term_rows*4).

    Returns a list of strings, one per terminal row.
    """
    lines = []
    for tr in range(term_rows):
        row_chars = []
        for tc in range(term_cols):
            code = 0
            for dy in range(4):
                for dx in range(2):
                    gr = tr * 4 + dy
                    gc = tc * 2 + dx
                    if gr < rows and gc < cols and grid[gr][gc]:
                        code |= _BRAILLE_DOT[dy][dx]
            row_chars.append(chr(_BRAILLE_BASE + code))
        lines.append("".join(row_chars))
    return lines


def _braille_dominant_color(grid, rows, cols, tr, tc, ww, gs=False, turmite=False, wator=False, fallingsand=False):
    """Pick the curses color pair for a Braille cell based on majority vote.

    Examines the 2×4 block of grid cells that map to terminal position (tr, tc)
    and returns the color pair of the most common non-dead state.
    """
    counts = {}  # color_pair -> count
    for dy in range(4):
        for dx in range(2):
            gr = tr * 4 + dy
            gc = tc * 2 + dx
            if gr < rows and gc < cols:
                age = grid[gr][gc]
                if gs:
                    cp = _grayscott_color(age)
                    counts[cp] = counts.get(cp, 0) + 1
                elif fallingsand:
                    if age:
                        cp = _fs_color(age)
                        counts[cp] = counts.get(cp, 0) + 1
                elif wator:
                    if age:
                        cp = _wator_color(age)
                        counts[cp] = counts.get(cp, 0) + 1
                elif turmite:
                    if age:
                        cp = _turmite_color(age)
                        counts[cp] = counts.get(cp, 0) + 1
                elif age:
                    if ww:
                        cp = _wireworld_color(age)
                    else:
                        cp = _age_color(age)
                    counts[cp] = counts.get(cp, 0) + 1
    if not counts:
        return 19 if gs else 1
    return max(counts, key=counts.get)


# --- Animated GIF Export ---

# RGB palette matching the terminal aging colors
_GIF_PALETTE = [
    (0, 0, 0),        # 0: dead cell (black)
    (0, 200, 0),      # 1: age 1-3, green (newborn)
    (0, 200, 200),    # 2: age 4-8, cyan (young)
    (0, 80, 255),     # 3: age 9-20, blue (mature)
    (200, 0, 200),    # 4: age 21+, magenta (ancient)
    (0, 80, 255),     # 5: Wireworld: electron head (blue)
    (200, 0, 0),      # 6: Wireworld: electron tail (red)
    (200, 200, 0),    # 7: Wireworld: conductor (yellow)
]


def _age_to_gif_index(age):
    """Map cell age to GIF palette index."""
    if age == 0:
        return 0
    elif age <= 3:
        return 1
    elif age <= 8:
        return 2
    elif age <= 20:
        return 3
    else:
        return 4


def _gs_to_gif_index(val):
    """Map Gray-Scott concentration value (0-100) to GIF palette index."""
    if val <= 5:
        return 0       # black
    elif val <= 25:
        return 3       # blue
    elif val <= 50:
        return 2       # cyan
    elif val <= 75:
        return 1       # green
    else:
        return 4       # magenta (high)


def _wireworld_to_gif_index(state):
    """Map Wireworld cell state to GIF palette index."""
    if state == WW_HEAD:
        return 5
    elif state == WW_TAIL:
        return 6
    elif state == WW_CONDUCTOR:
        return 7
    return 0


def _lzw_compress(pixels, min_code_size):
    """LZW-compress pixel data for GIF encoding."""
    clear_code = 1 << min_code_size
    eoi_code = clear_code + 1

    # Build initial table
    table = {}
    for i in range(clear_code):
        table[(i,)] = i
    next_code = eoi_code + 1
    code_size = min_code_size + 1
    max_code = (1 << code_size)

    # Output bit-packing state
    bit_buffer = 0
    bits_in_buffer = 0
    output = bytearray()

    def emit(code):
        nonlocal bit_buffer, bits_in_buffer
        bit_buffer |= code << bits_in_buffer
        bits_in_buffer += code_size
        while bits_in_buffer >= 8:
            output.append(bit_buffer & 0xFF)
            bit_buffer >>= 8
            bits_in_buffer -= 8

    emit(clear_code)

    if not pixels:
        emit(eoi_code)
        if bits_in_buffer > 0:
            output.append(bit_buffer & 0xFF)
        return bytes(output)

    current = (pixels[0],)
    for pixel in pixels[1:]:
        candidate = current + (pixel,)
        if candidate in table:
            current = candidate
        else:
            emit(table[current])
            if next_code < 4096:
                table[candidate] = next_code
                next_code += 1
                if next_code > max_code and code_size < 12:
                    code_size += 1
                    max_code = 1 << code_size
            else:
                # Table full, emit clear code and reset
                emit(clear_code)
                table = {}
                for i in range(clear_code):
                    table[(i,)] = i
                next_code = eoi_code + 1
                code_size = min_code_size + 1
                max_code = 1 << code_size
            current = (pixel,)
    emit(table[current])
    emit(eoi_code)

    if bits_in_buffer > 0:
        output.append(bit_buffer & 0xFF)

    return bytes(output)


def _gif_sub_blocks(data):
    """Split data into GIF sub-blocks (max 255 bytes each), terminated by 0."""
    result = bytearray()
    offset = 0
    while offset < len(data):
        chunk = data[offset:offset + 255]
        result.append(len(chunk))
        result.extend(chunk)
        offset += 255
    result.append(0)  # block terminator
    return bytes(result)


def export_gif(history_frames, rows, cols, filepath, cell_size=4, delay_cs=10, wireworld=False, grayscott=False, lenia=False):
    """Export a list of grid snapshots as an animated GIF.

    Args:
        history_frames: list of 2D grids (each grid[r][c] = age int)
        rows, cols: grid dimensions
        filepath: output .gif path
        cell_size: pixel size of each cell (default 4)
        delay_cs: delay between frames in centiseconds (default 10 = 100ms)
        wireworld: if True, use Wireworld color mapping
    """
    width = cols * cell_size
    height = rows * cell_size
    min_code_size = 3  # 8-color palette -> 3 bits

    buf = bytearray()

    # --- Header ---
    buf.extend(b"GIF89a")

    # --- Logical Screen Descriptor ---
    buf.extend(struct.pack("<HH", width, height))
    # Packed field: GCT flag=1, color res=2 (3 bits), sort=0, GCT size=2 (8 colors)
    buf.append(0b10000010)
    buf.append(0)  # background color index
    buf.append(0)  # pixel aspect ratio

    # --- Global Color Table (8 entries, 3 bytes each) ---
    for r, g, b in _GIF_PALETTE:
        buf.extend(bytes([r, g, b]))

    # --- NETSCAPE Application Extension (infinite loop) ---
    buf.extend(b"\x21\xFF\x0B")
    buf.extend(b"NETSCAPE2.0")
    buf.extend(b"\x03\x01")
    buf.extend(struct.pack("<H", 0))  # loop count 0 = infinite
    buf.append(0)  # block terminator

    # --- Frames ---
    for frame_grid in history_frames:
        # Graphic Control Extension
        buf.extend(b"\x21\xF9\x04")
        buf.append(0x00)  # packed: disposal=0, no user input, no transparency
        buf.extend(struct.pack("<H", delay_cs))
        buf.append(0)  # transparent color index (unused)
        buf.append(0)  # block terminator

        # Image Descriptor
        buf.extend(b"\x2C")
        buf.extend(struct.pack("<HHHH", 0, 0, width, height))
        buf.append(0)  # packed: no local color table, not interlaced

        # Build pixel data (row by row, cell_size pixels per cell)
        pixels = []
        for r in range(rows):
            row_pixels = []
            for c in range(cols):
                if wireworld:
                    idx = _wireworld_to_gif_index(frame_grid[r][c])
                elif grayscott or lenia:
                    idx = _gs_to_gif_index(frame_grid[r][c])
                else:
                    idx = _age_to_gif_index(frame_grid[r][c])
                row_pixels.extend([idx] * cell_size)
            for _ in range(cell_size):
                pixels.extend(row_pixels)

        # LZW compress and write as sub-blocks
        compressed = _lzw_compress(pixels, min_code_size)
        buf.append(min_code_size)
        buf.extend(_gif_sub_blocks(compressed))

    # --- Trailer ---
    buf.append(0x3B)

    with open(filepath, "wb") as f:
        f.write(buf)


# --- High-Resolution PNG Rendering ---

# Named color palettes: each maps (dead, age1-3, age4-8, age9-20, age21+,
#                                    ww_head, ww_tail, ww_conductor)
_PNG_PALETTES = {
    "classic": [
        (0, 0, 0),          # dead (black)
        (0, 200, 0),        # newborn (green)
        (0, 200, 200),      # young (cyan)
        (0, 80, 255),       # mature (blue)
        (200, 0, 200),      # ancient (magenta)
        (0, 80, 255),       # WW head (blue)
        (200, 0, 0),        # WW tail (red)
        (200, 200, 0),      # WW conductor (yellow)
    ],
    "ember": [
        (10, 10, 10),       # dead (near-black)
        (255, 200, 50),     # newborn (bright yellow)
        (255, 130, 20),     # young (orange)
        (220, 40, 10),      # mature (red)
        (120, 10, 50),      # ancient (dark crimson)
        (255, 255, 100),    # WW head
        (180, 60, 20),      # WW tail
        (100, 100, 100),    # WW conductor
    ],
    "ocean": [
        (5, 10, 30),        # dead (deep navy)
        (80, 220, 255),     # newborn (sky blue)
        (30, 160, 220),     # young (ocean blue)
        (10, 80, 180),      # mature (deep blue)
        (120, 200, 255),    # ancient (ice blue)
        (0, 255, 200),      # WW head (teal)
        (0, 100, 120),      # WW tail
        (40, 60, 100),      # WW conductor
    ],
    "mono": [
        (0, 0, 0),          # dead (black)
        (255, 255, 255),    # newborn (white)
        (200, 200, 200),    # young (light grey)
        (140, 140, 140),    # mature (grey)
        (80, 80, 80),       # ancient (dark grey)
        (255, 255, 255),    # WW head
        (140, 140, 140),    # WW tail
        (80, 80, 80),       # WW conductor
    ],
    "matrix": [
        (0, 0, 0),          # dead (black)
        (0, 255, 0),        # newborn (bright green)
        (0, 200, 0),        # young (green)
        (0, 140, 0),        # mature (dark green)
        (0, 80, 0),         # ancient (dim green)
        (0, 255, 100),      # WW head
        (0, 120, 0),        # WW tail
        (0, 60, 0),         # WW conductor
    ],
}


def _png_age_to_index(age):
    """Map cell age to PNG palette index."""
    if age == 0:
        return 0
    elif age <= 3:
        return 1
    elif age <= 8:
        return 2
    elif age <= 20:
        return 3
    else:
        return 4


def _png_ww_to_index(state):
    """Map Wireworld cell state to PNG palette index."""
    if state == WW_HEAD:
        return 5
    elif state == WW_TAIL:
        return 6
    elif state == WW_CONDUCTOR:
        return 7
    return 0


def _gs_value_to_rgb(val):
    """Map Gray-Scott quantized value (0-100) to an RGB color tuple.

    Uses a smooth gradient: black -> blue -> cyan -> green -> yellow -> white.
    """
    if val <= 0:
        return (0, 0, 0)
    elif val <= 20:
        t = val / 20.0
        return (0, 0, int(180 * t))
    elif val <= 40:
        t = (val - 20) / 20.0
        return (0, int(200 * t), 180 + int(20 * t))
    elif val <= 60:
        t = (val - 40) / 20.0
        return (0, 200 + int(55 * t), int(200 * (1 - t)))
    elif val <= 80:
        t = (val - 60) / 20.0
        return (int(255 * t), 255, 0)
    else:
        t = (val - 80) / 20.0
        return (255, 255, int(255 * t))


def _blend_rgb(c1, c2, t):
    """Linearly blend two RGB tuples by factor t (0.0=c1, 1.0=c2)."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def _png_chunk(chunk_type, data):
    """Build a PNG chunk: length + type + data + CRC32."""
    raw = chunk_type + data
    return struct.pack(">I", len(data)) + raw + struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)


def render_png(grid, rows, cols, filepath, cell_size=8, palette_name="classic",
               grid_lines=False, grid_line_color=None, wireworld=False, aa=True,
               grayscott=False, lenia=False):
    """Render a single grid frame as a high-resolution PNG image.

    Args:
        grid: 2D grid (grid[r][c] = age int or WW state or GS val 0-100)
        rows, cols: grid dimensions
        filepath: output .png path
        cell_size: pixel size of each cell (default 8)
        palette_name: color palette name (default "classic")
        grid_lines: if True, draw 1px grid lines between cells
        grid_line_color: RGB tuple for grid lines (default: dark grey)
        wireworld: if True, use Wireworld color mapping
        aa: if True, apply anti-aliasing at cell boundaries
    """
    palette = _PNG_PALETTES.get(palette_name, _PNG_PALETTES["classic"])
    if grid_line_color is None:
        grid_line_color = (40, 40, 40)

    line_w = 1 if grid_lines else 0
    width = cols * cell_size + (cols + 1) * line_w if grid_lines else cols * cell_size
    height = rows * cell_size + (rows + 1) * line_w if grid_lines else rows * cell_size

    # Build color index map for the grid
    # For Gray-Scott, color_map stores direct RGB tuples instead of indices
    if grayscott or lenia:
        color_map = [[(0, 0, 0)] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                color_map[r][c] = _gs_value_to_rgb(grid[r][c])
    else:
        color_map = [[0] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                if wireworld:
                    color_map[r][c] = _png_ww_to_index(grid[r][c])
                else:
                    color_map[r][c] = _png_age_to_index(grid[r][c])

    # Build raw pixel rows (each row: filter byte + RGB triples)
    raw_data = bytearray()
    aa_radius = 1 if (aa and cell_size >= 4) else 0

    for py in range(height):
        raw_data.append(0)  # PNG filter: None
        for px in range(width):
            # Determine which cell this pixel belongs to
            if grid_lines:
                # Check if pixel is on a grid line
                gx = px % (cell_size + line_w)
                gy = py % (cell_size + line_w)
                cell_c = px // (cell_size + line_w)
                cell_r = py // (cell_size + line_w)
                on_line = gx < line_w or gy < line_w
                if on_line or cell_r >= rows or cell_c >= cols:
                    raw_data.extend(grid_line_color)
                    continue
                local_x = gx - line_w
                local_y = gy - line_w
            else:
                cell_c = px // cell_size
                cell_r = py // cell_size
                local_x = px % cell_size
                local_y = py % cell_size
                if cell_r >= rows or cell_c >= cols:
                    raw_data.extend(palette[0])
                    continue

            cm = color_map[cell_r][cell_c]
            if grayscott or lenia:
                base_color = cm  # already RGB tuple
            else:
                base_color = palette[cm]

            # Anti-aliasing: blend edge pixels with neighbouring cell colors
            if aa_radius and cell_size >= 4:
                blend_total = (0.0, 0.0, 0.0)
                weight_total = 0.0

                # Check proximity to each cell edge
                edges = []
                if local_x < aa_radius and cell_c > 0:
                    t = 1.0 - local_x / aa_radius
                    edges.append((cell_r, cell_c - 1, t * 0.5))
                if local_x >= cell_size - aa_radius and cell_c < cols - 1:
                    t = 1.0 - (cell_size - 1 - local_x) / aa_radius
                    edges.append((cell_r, cell_c + 1, t * 0.5))
                if local_y < aa_radius and cell_r > 0:
                    t = 1.0 - local_y / aa_radius
                    edges.append((cell_r - 1, cell_c, t * 0.5))
                if local_y >= cell_size - aa_radius and cell_r < rows - 1:
                    t = 1.0 - (cell_size - 1 - local_y) / aa_radius
                    edges.append((cell_r + 1, cell_c, t * 0.5))

                if edges:
                    base_w = 1.0
                    br, bg, bb = float(base_color[0]), float(base_color[1]), float(base_color[2])
                    for nr, nc, w in edges:
                        ncm = color_map[nr][nc]
                        n_color = ncm if (grayscott or lenia) else palette[ncm]
                        if n_color != base_color:
                            br += n_color[0] * w
                            bg += n_color[1] * w
                            bb += n_color[2] * w
                            base_w += w
                    raw_data.extend((
                        min(255, int(br / base_w)),
                        min(255, int(bg / base_w)),
                        min(255, int(bb / base_w)),
                    ))
                    continue

            raw_data.extend(base_color)

    # Encode as PNG
    buf = bytearray()

    # PNG signature
    buf.extend(b"\x89PNG\r\n\x1a\n")

    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    buf.extend(_png_chunk(b"IHDR", ihdr_data))

    # IDAT chunk(s) - compress raw pixel data with zlib
    compressed = zlib.compress(bytes(raw_data), 9)
    # Split into 32KB IDAT chunks for compatibility
    offset = 0
    while offset < len(compressed):
        chunk_data = compressed[offset:offset + 32768]
        buf.extend(_png_chunk(b"IDAT", chunk_data))
        offset += 32768

    # IEND chunk
    buf.extend(_png_chunk(b"IEND", b""))

    with open(filepath, "wb") as f:
        f.write(buf)


def run_headless_render(rows, cols, speed, rule, pattern, load_path, generations,
                        cell_size, palette_name, grid_lines, grid_line_color,
                        output_dir, wireworld=False, aa=True):
    """Run the simulation headlessly and render PNG frames.

    Args:
        rows, cols: grid dimensions
        speed: not used (headless runs as fast as possible)
        rule: rule dict (b/s sets + name)
        pattern: pattern name to place
        load_path: path to load pattern from (or None)
        generations: number of generations to render
        cell_size: pixel size per cell
        palette_name: color palette name
        grid_lines: whether to draw grid lines
        grid_line_color: RGB tuple for grid lines
        output_dir: directory to write PNG files
        wireworld: if True, use Wireworld color mapping
        aa: if True, anti-alias cell boundaries
    """
    os.makedirs(output_dir, exist_ok=True)

    ww = wireworld or _is_wireworld(rule)
    gs = _is_grayscott(rule)
    ln = _is_lenia(rule)
    tm = _is_turmite(rule)
    ph = _is_physarum(rule)

    # Initialize grid
    grid = make_grid(rows, cols)
    if load_path:
        path = load_path
        if not os.path.isfile(path):
            for ext in ("", ".rle", ".cells"):
                candidate = os.path.join(CELLS_DIR, path + ext)
                if os.path.isfile(candidate):
                    path = candidate
                    break
        grid, loaded_ww = _load_pattern_file(path, rows, cols)
        if loaded_ww:
            ww = True
    elif ph:
        _phys_init(rows, cols)
        grid = _phys_to_grid(rows, cols)
    elif tm:
        _turmite_init(rows, cols)
        grid = _turmite_to_grid(rows, cols)
    elif ln:
        preset = LENIA_PRESETS[LENIA_PRESET_NAMES[_lenia_preset_idx]]
        _lenia_init(rows, cols, preset.get("seed", "orbium"))
        grid = _lenia_to_grid(rows, cols)
    elif gs:
        _gs_init(rows, cols)
        grid = _gs_to_grid(rows, cols)
    elif ww and not load_path:
        place_wireworld_pattern(grid, "ww_clock")
    else:
        place_pattern(grid, pattern)

    # Render frames
    digits = len(str(generations))
    print(f"Rendering {generations} frames at {cols * cell_size}x{rows * cell_size}px "
          f"(cell_size={cell_size}, palette={palette_name})")
    print(f"Output directory: {os.path.abspath(output_dir)}")

    for gen in range(generations):
        fname = f"frame_{str(gen).zfill(digits)}.png"
        fpath = os.path.join(output_dir, fname)
        render_png(grid, rows, cols, fpath,
                   cell_size=cell_size, palette_name=palette_name,
                   grid_lines=grid_lines, grid_line_color=grid_line_color,
                   wireworld=ww, aa=aa, grayscott=gs or ph, lenia=ln)

        if gen % 10 == 0 or gen == generations - 1:
            print(f"  [{gen + 1}/{generations}] {fname}")

        grid = step(grid, rule)

    print(f"Done. {generations} PNG frames written to {os.path.abspath(output_dir)}/")


# --- Sound Synthesis Mode ---


class SoundEngine:
    """Pure-Python PCM sound synthesis that sonifies cellular automaton activity.

    Maps:
      - Population density → pitch (more cells = higher frequency)
      - Spatial distribution → stereo panning (center of mass → L/R balance)
      - Growth rate → volume (rapid change = louder)

    Uses struct-based 16-bit stereo PCM at 22050 Hz, piped to aplay/paplay/afplay.
    """

    SAMPLE_RATE = 22050
    CHANNELS = 2
    SAMPLE_WIDTH = 2  # 16-bit signed

    # Frequency range (Hz)
    FREQ_MIN = 80.0
    FREQ_MAX = 880.0

    # Volume range (0.0 - 1.0)
    VOL_MIN = 0.05
    VOL_MAX = 0.6

    def __init__(self):
        self.active = False
        self._process = None
        self._phase = 0.0  # continuous oscillator phase
        self._prev_pop = 0
        self._player_cmd = None

    def _find_player(self):
        """Find an available PCM audio player on the system."""
        import shutil
        import subprocess
        # Try common Linux/macOS audio players
        candidates = [
            # Linux PulseAudio
            ["paplay", "--raw", "--format=s16le", "--rate=22050", "--channels=2"],
            # Linux ALSA
            ["aplay", "-q", "-f", "S16_LE", "-r", "22050", "-c", "2", "-t", "raw"],
            # macOS (SOX play)
            ["play", "-q", "-t", "raw", "-b", "16", "-e", "signed-integer",
             "-r", "22050", "-c", "2", "-"],
        ]
        for cmd in candidates:
            if shutil.which(cmd[0]):
                return cmd
        return None

    def start(self):
        """Start the audio output stream."""
        import subprocess
        if self._process and self._process.poll() is None:
            return True  # already running
        self._player_cmd = self._find_player()
        if not self._player_cmd:
            return False
        try:
            self._process = subprocess.Popen(
                self._player_cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
            self.active = True
            self._phase = 0.0
            return True
        except (OSError, subprocess.SubprocessError):
            self._process = None
            return False

    def stop(self):
        """Stop the audio output stream."""
        self.active = False
        if self._process:
            try:
                self._process.stdin.close()
            except (OSError, BrokenPipeError):
                pass
            try:
                self._process.wait(timeout=1)
            except Exception:
                try:
                    self._process.kill()
                except OSError:
                    pass
            self._process = None

    def toggle(self):
        """Toggle sound on/off. Returns (new_active_state, error_msg_or_None)."""
        if self.active:
            self.stop()
            return False, None
        else:
            ok = self.start()
            if ok:
                return True, None
            else:
                return False, "No audio player found (need aplay/paplay/play)"

    def generate_frame(self, grid, rows, cols, duration):
        """Generate and write one audio frame based on current grid state.

        Args:
            grid: 2D grid where cell > 0 means alive
            rows, cols: grid dimensions
            duration: frame duration in seconds (matches simulation delay)
        """
        if not self.active or not self._process or self._process.poll() is not None:
            if self.active:
                self.active = False
            return

        # --- Analyze grid ---
        pop = 0
        sum_r = 0.0
        sum_c = 0.0
        for r in range(rows):
            for c in range(cols):
                if grid[r][c]:
                    pop += 1
                    sum_r += r
                    sum_c += c

        total_cells = rows * cols
        density = pop / total_cells if total_cells > 0 else 0.0

        # Spatial center of mass → stereo panning (-1.0 = left, +1.0 = right)
        if pop > 0:
            center_c = sum_c / pop
            pan = (center_c / (cols - 1)) * 2.0 - 1.0 if cols > 1 else 0.0
        else:
            pan = 0.0
        pan = max(-1.0, min(1.0, pan))

        # Growth rate → volume
        if self._prev_pop > 0:
            growth_rate = abs(pop - self._prev_pop) / self._prev_pop
        else:
            growth_rate = 1.0 if pop > 0 else 0.0
        self._prev_pop = pop

        # Map density to frequency (log scale for musical feel)
        freq = self.FREQ_MIN + (self.FREQ_MAX - self.FREQ_MIN) * (density ** 0.5)

        # Map growth rate to volume (clamped)
        vol = self.VOL_MIN + (self.VOL_MAX - self.VOL_MIN) * min(growth_rate, 1.0)
        if pop == 0:
            vol = 0.0

        # Left/right volume from panning (constant power panning)
        pan_angle = (pan + 1.0) * math.pi / 4.0  # 0 to pi/2
        vol_l = vol * math.cos(pan_angle)
        vol_r = vol * math.sin(pan_angle)

        # --- Generate PCM samples ---
        # Limit frame to avoid buffer buildup
        frame_dur = min(duration, 0.15)
        num_samples = max(1, int(self.SAMPLE_RATE * frame_dur))
        buf = bytearray(num_samples * self.CHANNELS * self.SAMPLE_WIDTH)

        phase = self._phase
        phase_inc = freq / self.SAMPLE_RATE

        # Add a secondary harmonic for richer tone
        harm_ratio = 0.3  # harmonic amplitude relative to fundamental
        harm_mult = 2.0   # second harmonic

        for i in range(num_samples):
            # Fundamental + harmonic
            t = phase + i * phase_inc
            sample = math.sin(2.0 * math.pi * t)
            sample += harm_ratio * math.sin(2.0 * math.pi * t * harm_mult)
            sample /= (1.0 + harm_ratio)

            # Apply envelope (tiny fade at edges to prevent clicks)
            if i < 64:
                sample *= i / 64.0
            elif i > num_samples - 64:
                sample *= (num_samples - i) / 64.0

            left = int(sample * vol_l * 32000)
            right = int(sample * vol_r * 32000)
            left = max(-32768, min(32767, left))
            right = max(-32768, min(32767, right))

            offset = i * 4
            struct.pack_into("<hh", buf, offset, left, right)

        self._phase = (phase + num_samples * phase_inc) % 1.0

        # Write to player
        try:
            self._process.stdin.write(bytes(buf))
            self._process.stdin.flush()
        except (OSError, BrokenPipeError):
            self.active = False
            self._process = None


# --- Pattern Recognition ---


def _normalize_cells(cells):
    """Normalize cell coordinates to start at (0,0), return as frozenset."""
    if not cells:
        return frozenset()
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return frozenset((r - min_r, c - min_c) for r, c in cells)


def _pattern_d4_variants(cells):
    """Generate all D4 symmetry variants (rotations + reflections) of a pattern."""
    variants = set()
    coords = list(cells)
    for _ in range(4):
        norm = _normalize_cells(coords)
        variants.add(norm)
        reflected = [(r, -c) for r, c in coords]
        variants.add(_normalize_cells(reflected))
        coords = [(c, -r) for r, c in coords]
    return variants


def _build_recognition_catalog():
    """Build a lookup table: frozenset of normalized coords -> pattern name."""
    pattern_defs = {
        # Still lifes
        "block": [[(0, 0), (0, 1), (1, 0), (1, 1)]],
        "beehive": [[(0, 1), (0, 2), (1, 0), (1, 3), (2, 1), (2, 2)]],
        "loaf": [[(0, 1), (0, 2), (1, 0), (1, 3), (2, 1), (2, 3), (3, 2)]],
        "boat": [[(0, 0), (0, 1), (1, 0), (1, 2), (2, 1)]],
        "tub": [[(0, 1), (1, 0), (1, 2), (2, 1)]],
        "pond": [[(0, 1), (0, 2), (1, 0), (1, 3), (2, 0), (2, 3), (3, 1), (3, 2)]],
        # Oscillators (all phases)
        "blinker": [
            [(0, 0), (0, 1), (0, 2)],
        ],
        "toad": [
            [(0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2)],
            [(0, 2), (1, 0), (1, 3), (2, 0), (2, 3), (3, 1)],
        ],
        "beacon": [
            [(0, 0), (0, 1), (1, 0), (1, 1), (2, 2), (2, 3), (3, 2), (3, 3)],
            [(0, 0), (0, 1), (1, 0), (2, 3), (3, 2), (3, 3)],
        ],
        "pulsar": [
            # Phase 1 only (period-3, D4-symmetric)
            [(0, 2), (0, 3), (0, 4), (0, 8), (0, 9), (0, 10),
             (2, 0), (2, 5), (2, 7), (2, 12),
             (3, 0), (3, 5), (3, 7), (3, 12),
             (4, 0), (4, 5), (4, 7), (4, 12),
             (5, 2), (5, 3), (5, 4), (5, 8), (5, 9), (5, 10),
             (7, 2), (7, 3), (7, 4), (7, 8), (7, 9), (7, 10),
             (8, 0), (8, 5), (8, 7), (8, 12),
             (9, 0), (9, 5), (9, 7), (9, 12),
             (10, 0), (10, 5), (10, 7), (10, 12),
             (12, 2), (12, 3), (12, 4), (12, 8), (12, 9), (12, 10)],
        ],
        # Spaceships (all 4 phases)
        "glider": [
            [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
            [(0, 0), (0, 2), (1, 1), (1, 2), (2, 1)],
            [(0, 2), (1, 0), (1, 2), (2, 1), (2, 2)],
            [(0, 0), (1, 1), (1, 2), (2, 0), (2, 1)],
        ],
        "LWSS": [
            [(0, 1), (0, 4), (1, 0), (2, 0), (2, 4), (3, 0), (3, 1), (3, 2), (3, 3)],
        ],
    }
    catalog = {}
    for name, phases in pattern_defs.items():
        for phase in phases:
            for variant in _pattern_d4_variants(phase):
                if variant not in catalog:
                    catalog[variant] = name
    return catalog


_PATTERN_CATALOG = _build_recognition_catalog()


def _detect_patterns(grid):
    """Detect known patterns via connected component analysis (no wrapping).

    Returns dict: pattern_name -> list of (min_r, min_c, h, w, cell_set).
    """
    rows, cols = len(grid), len(grid[0])
    visited = [[False] * cols for _ in range(rows)]
    results = {}

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] and not visited[r][c]:
                component = []
                stack = [(r, c)]
                while stack:
                    cr, cc = stack.pop()
                    if visited[cr][cc]:
                        continue
                    visited[cr][cc] = True
                    component.append((cr, cc))
                    for dr in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            if dr == 0 and dc == 0:
                                continue
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc] and grid[nr][nc]:
                                stack.append((nr, nc))

                if len(component) > 50:
                    continue

                norm = _normalize_cells(component)
                name = _PATTERN_CATALOG.get(norm)
                if name:
                    min_r = min(cr for cr, cc in component)
                    min_c = min(cc for cr, cc in component)
                    max_r = max(cr for cr, cc in component)
                    max_c = max(cc for cr, cc in component)
                    if name not in results:
                        results[name] = []
                    results[name].append((min_r, min_c,
                                          max_r - min_r + 1,
                                          max_c - min_c + 1,
                                          set(component)))

    return results


def _count_population(grid):
    """Count the number of live cells in the grid."""
    return sum(1 for row in grid for cell in row if cell)


def _draw_stats_panel(stdscr, pop_history, generation, panel_width, max_y, max_x, detected_patterns=None):
    """Draw the population statistics side panel."""
    panel_x = max_x - panel_width
    chart_height = max(max_y - 12, 5)  # Reserve rows for stats below chart

    # Draw vertical border
    for y in range(max_y - 1):
        try:
            stdscr.addstr(y, panel_x - 1, "\u2502", curses.color_pair(2))
        except curses.error:
            pass

    # Current stats
    cur_pop = pop_history[-1] if pop_history else 0
    peak_pop = max(pop_history) if pop_history else 0
    peak_gen = pop_history.index(peak_pop) if pop_history else 0
    # Adjust peak_gen to absolute generation number
    first_gen = generation - len(pop_history) + 1
    peak_gen_abs = first_gen + peak_gen

    # Growth rate (compare to previous generation)
    if len(pop_history) >= 2:
        prev = pop_history[-2]
        if prev > 0:
            growth = ((cur_pop - prev) / prev) * 100
        else:
            growth = 100.0 if cur_pop > 0 else 0.0
        growth_str = f"{growth:+.1f}%"
    else:
        growth_str = "N/A"

    # Title
    try:
        stdscr.addstr(0, panel_x + 1, " POPULATION STATS ", curses.color_pair(2) | curses.A_REVERSE | curses.A_BOLD)
    except curses.error:
        pass

    # Stats lines
    stats = [
        f"Population: {cur_pop}",
        f"Peak:       {peak_pop} (gen {peak_gen_abs})",
        f"Growth:     {growth_str}",
        f"Generation: {generation}",
    ]
    for i, line in enumerate(stats):
        try:
            stdscr.addstr(2 + i, panel_x + 1, line[:panel_width - 2], curses.color_pair(2))
        except curses.error:
            pass

    # Sparkline chart
    chart_top = 7
    chart_w = panel_width - 4  # leave margins
    if chart_w < 3 or chart_height < 3:
        return

    # Use the most recent chart_w data points
    data = list(pop_history[-chart_w:])
    if not data:
        return

    data_max = max(data) if max(data) > 0 else 1

    # Chart title
    try:
        stdscr.addstr(chart_top, panel_x + 1, "Population over time:", curses.color_pair(2))
    except curses.error:
        pass

    # Y-axis labels and bars
    chart_start_y = chart_top + 1
    bar_chars = [" ", "\u2581", "\u2582", "\u2583", "\u2584", "\u2585", "\u2586", "\u2587", "\u2588"]

    # Draw the chart using vertical bar characters (one column per data point)
    for col_i, val in enumerate(data):
        bar_height = (val / data_max) * chart_height if data_max > 0 else 0
        full_blocks = int(bar_height)
        frac = bar_height - full_blocks

        for row_i in range(chart_height):
            y = chart_start_y + chart_height - 1 - row_i
            x = panel_x + 2 + col_i
            if x >= max_x - 1 or y >= max_y - 1:
                continue
            if row_i < full_blocks:
                ch = "\u2588"
                color = curses.color_pair(1)
            elif row_i == full_blocks and frac > 0.1:
                idx = int(frac * 8)
                ch = bar_chars[max(1, min(idx, 8))]
                color = curses.color_pair(1)
            else:
                ch = " "
                color = curses.color_pair(2)
            try:
                stdscr.addstr(y, x, ch, color)
            except curses.error:
                pass

    # Y-axis scale labels
    try:
        top_label = str(data_max)
        stdscr.addstr(chart_start_y, panel_x + 2 + chart_w, top_label[:5], curses.color_pair(2))
        stdscr.addstr(chart_start_y + chart_height - 1, panel_x + 2 + chart_w, "0", curses.color_pair(2))
    except curses.error:
        pass

    # Detected patterns section
    if detected_patterns:
        pat_y = chart_start_y + chart_height + 1
        if pat_y < max_y - 2:
            try:
                stdscr.addstr(pat_y, panel_x + 1, " DETECTED PATTERNS ",
                              curses.color_pair(12) | curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
            pat_y += 1
            # Sort by count descending
            sorted_pats = sorted(detected_patterns.items(), key=lambda x: -len(x[1]))
            total = sum(len(v) for v in detected_patterns.values())
            try:
                stdscr.addstr(pat_y, panel_x + 1,
                              f"Total: {total} structure{'s' if total != 1 else ''}"[:panel_width - 2],
                              curses.color_pair(2))
            except curses.error:
                pass
            pat_y += 1
            for name, instances in sorted_pats:
                if pat_y >= max_y - 1:
                    break
                count = len(instances)
                line = f"  {count}\u00d7 {name}"
                try:
                    stdscr.addstr(pat_y, panel_x + 1, line[:panel_width - 2],
                                  curses.color_pair(12))
                except curses.error:
                    pass
                pat_y += 1


def _extract_region(grid, r1, c1, r2, c2):
    """Extract a rectangular region from the grid as a 2D list of 0/1."""
    min_r, max_r = min(r1, r2), max(r1, r2)
    min_c, max_c = min(c1, c2), max(c1, c2)
    region = []
    for r in range(min_r, max_r + 1):
        row = []
        for c in range(min_c, max_c + 1):
            row.append(1 if grid[r][c] else 0)
        region.append(row)
    return region


def _rotate_cw(stamp):
    """Rotate a 2D stamp 90° clockwise."""
    if not stamp or not stamp[0]:
        return stamp
    r, c = len(stamp), len(stamp[0])
    return [[stamp[r - 1 - j][i] for j in range(r)] for i in range(c)]


def _rotate_ccw(stamp):
    """Rotate a 2D stamp 90° counter-clockwise."""
    if not stamp or not stamp[0]:
        return stamp
    r, c = len(stamp), len(stamp[0])
    return [[stamp[j][c - 1 - i] for j in range(r)] for i in range(c)]


def _flip_h(stamp):
    """Flip a 2D stamp horizontally."""
    return [row[::-1] for row in stamp]


def _flip_v(stamp):
    """Flip a 2D stamp vertically."""
    return stamp[::-1]


def _pattern_to_stamp(name):
    """Convert a PATTERNS entry to a 2D stamp."""
    cells = PATTERNS[name]
    if not cells or name == "random":
        return None
    max_r = max(r for r, c in cells)
    max_c = max(c for r, c in cells)
    stamp = [[0] * (max_c + 1) for _ in range(max_r + 1)]
    for r, c in cells:
        stamp[r][c] = 1
    return stamp


# --- Multiplayer Networking ---

class NetworkPeer:
    """Handles peer-to-peer networking for multiplayer mode.

    Either hosts (server) or connects (client) over TCP.
    Messages are newline-delimited JSON.
    """

    def __init__(self):
        self.sock = None          # The peer socket (connected to the other player)
        self.server_sock = None   # Server socket (host only)
        self.inbox = queue.Queue()  # Messages received from peer
        self._send_lock = threading.Lock()
        self._running = False
        self._thread = None
        self._buf = b""
        self.is_host = False
        self.connected = False
        self.peer_cursor = (0, 0)  # Remote player's cursor position
        self.player_id = 0         # 0 = host, 1 = client

    def host(self, port):
        """Start listening for a peer connection."""
        self.is_host = True
        self.player_id = 0
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("0.0.0.0", port))
        self.server_sock.listen(1)
        self._running = True
        self._thread = threading.Thread(target=self._host_loop, daemon=True)
        self._thread.start()

    def connect(self, host, port):
        """Connect to a host."""
        self.is_host = False
        self.player_id = 1
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.setblocking(False)
        self.connected = True
        self._running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def _host_loop(self):
        """Wait for a connection, then receive messages."""
        self.server_sock.settimeout(1.0)
        while self._running and not self.connected:
            try:
                self.sock, _addr = self.server_sock.accept()
                self.sock.setblocking(False)
                self.connected = True
            except socket.timeout:
                continue
            except OSError:
                break
        self._recv_loop()

    def _recv_loop(self):
        """Read messages from peer socket."""
        while self._running and self.sock:
            try:
                ready, _, _ = select.select([self.sock], [], [], 0.5)
                if not ready:
                    continue
                data = self.sock.recv(65536)
                if not data:
                    self.connected = False
                    break
                self._buf += data
                while b"\n" in self._buf:
                    line, self._buf = self._buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode("utf-8"))
                        self.inbox.put(msg)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            except (OSError, ValueError):
                self.connected = False
                break

    def send(self, msg):
        """Send a JSON message to the peer."""
        if not self.connected or not self.sock:
            return
        try:
            data = json.dumps(msg, separators=(",", ":")).encode("utf-8") + b"\n"
            with self._send_lock:
                self.sock.sendall(data)
        except OSError:
            self.connected = False

    def send_grid_sync(self, grid, generation, rule):
        """Send full grid state to peer (used on initial connect)."""
        if rule.get("wireworld"):
            flat = [list(row) for row in grid]
            rule_str = "Wireworld"
        else:
            # Convert grid to 0/1 (strip age info for sync)
            flat = [[1 if c else 0 for c in row] for row in grid]
            b = "".join(str(d) for d in sorted(rule["b"]))
            s = "".join(str(d) for d in sorted(rule["s"]))
            rule_str = f"B{b}/S{s}"
        self.send({
            "t": "sync",
            "g": flat,
            "gen": generation,
            "rule": rule_str,
            "name": rule.get("name", ""),
        })

    def send_cell_toggle(self, r, c, val):
        """Notify peer of a cell toggle."""
        self.send({"t": "cell", "r": r, "c": c, "v": val})

    def send_cursor(self, r, c):
        """Send cursor position to peer."""
        self.send({"t": "cur", "r": r, "c": c})

    def send_step(self, grid, generation):
        """Host sends grid state after a simulation step."""
        flat = [list(row) for row in grid]
        self.send({"t": "step", "g": flat, "gen": generation})

    def send_clear(self):
        self.send({"t": "clear"})

    def send_pause(self, paused):
        self.send({"t": "pause", "p": paused})

    def send_rule_change(self, rule, rule_idx):
        if rule.get("wireworld"):
            rule_str = "Wireworld"
        else:
            b = "".join(str(d) for d in sorted(rule["b"]))
            s = "".join(str(d) for d in sorted(rule["s"]))
            rule_str = f"B{b}/S{s}"
        self.send({
            "t": "rule",
            "rule": rule_str,
            "name": rule.get("name", ""),
            "idx": rule_idx,
        })

    def close(self):
        self._running = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
        self.connected = False

    def drain_messages(self):
        """Yield all queued messages (non-blocking)."""
        while True:
            try:
                yield self.inbox.get_nowait()
            except queue.Empty:
                break


def run(stdscr, grid, speed, rule=None, network=None, script_engine=None):
    if rule is None:
        rule = RULES["life"]
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)       # age 1-3: newborn (bright green)
    curses.init_pair(2, curses.COLOR_WHITE, -1)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW)   # cursor on dead cell
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)    # cursor on live cell
    curses.init_pair(5, curses.COLOR_CYAN, -1)        # age 4-8: young (cyan)
    curses.init_pair(6, curses.COLOR_BLUE, -1)        # age 9-20: mature (blue)
    curses.init_pair(7, curses.COLOR_MAGENTA, -1)     # age 21+: ancient (magenta)
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_CYAN)    # selection highlight
    curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_MAGENTA) # paste preview
    curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_RED)    # remote cursor on dead
    curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_RED)    # remote cursor on live
    curses.init_pair(12, curses.COLOR_YELLOW, -1)                # detected pattern highlight
    curses.init_pair(13, curses.COLOR_RED, -1)                   # Wireworld: electron tail
    curses.init_pair(14, curses.COLOR_BLUE, -1)                  # Wireworld: electron head
    curses.init_pair(15, curses.COLOR_YELLOW, -1)                # Wireworld: conductor
    curses.init_pair(16, curses.COLOR_BLACK, curses.COLOR_BLUE)  # cursor on head
    curses.init_pair(17, curses.COLOR_BLACK, curses.COLOR_RED)   # cursor on tail
    curses.init_pair(18, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # cursor on conductor
    curses.init_pair(19, curses.COLOR_BLUE, -1)                    # Gray-Scott: very low V
    curses.init_pair(20, curses.COLOR_WHITE, -1)                   # Gray-Scott: peak V
    curses.init_pair(21, curses.COLOR_RED, -1)                     # Turmite: ant head

    # Multiplayer state
    mp = network is not None
    remote_cursor = (-1, -1)   # peer's cursor position
    mp_synced = False           # True once initial sync is done (client)
    mp_sent_sync = False        # True once host has sent sync to peer
    last_cursor_send = 0.0      # throttle cursor updates

    rows, cols = len(grid), len(grid[0])
    generation = 0
    paused = False
    editing = False
    show_stats = False
    detect_enabled = False
    braille_mode = False
    cursor_r, cursor_c = rows // 2, cols // 2
    delay = speed
    pop_history = []
    max_pop_history = 500  # Rolling window of population data

    # Clipboard / stamp system
    clipboard = None        # 2D list (rows of 0/1) or None
    selecting = False       # True when in select mode
    sel_anchor_r = 0        # Selection anchor (where 'v' was pressed)
    sel_anchor_c = 0
    pasting = False         # True when in paste-preview mode

    # Time-travel history
    history = [copy.deepcopy(grid)]  # history[0] = initial state
    hist_idx = 0                     # current position in history
    max_history = 10000              # max stored generations
    browsing_history = False         # True when viewing a past state

    # HashLife hyperspeed engine
    hashlife = HashLifeEngine()
    hashlife_active = False          # True when H key enables hyperspeed

    # Sound synthesis engine
    sound = SoundEngine()

    # Topology mode
    global _topology, _gs_preset_idx, _gs_feed, _gs_kill, _eca_rule_num, _eca_notable_idx, _fs_preset_idx
    topo_idx = 0  # index into TOPOLOGIES
    _topology = TOPOLOGIES[topo_idx]

    # Script engine state
    se = script_engine or ScriptEngine()
    se.bind_grid(grid)

    # Find current rule index for cycling
    rule_idx = -1
    for i, name in enumerate(RULE_NAMES):
        if RULES[name] is rule:
            rule_idx = i
            break

    while True:
        ww = _is_wireworld(rule)
        gs = _is_grayscott(rule)
        eca = _is_elementary(rule)
        lenia = _is_lenia(rule)
        turmite = _is_turmite(rule)
        wator = _is_wator(rule)
        fallingsand = _is_fallingsand(rule)
        physarum = _is_physarum(rule)

        # Track population
        pop = _count_population(grid)
        if not browsing_history:
            pop_history.append(pop)
            if len(pop_history) > max_pop_history:
                pop_history.pop(0)

        # Pattern detection
        detected = {}
        detected_cells = set()
        if detect_enabled:
            detected = _detect_patterns(grid)
            for instances in detected.values():
                for (_mr, _mc, _h, _w, cells) in instances:
                    detected_cells.update(cells)

        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # Calculate panel width and available grid space
        panel_width = 35
        if show_stats and max_x > panel_width + 20:
            grid_max_x = max_x - panel_width
        else:
            grid_max_x = max_x

        # In Braille mode (non-editing), each terminal cell = 2×4 grid cells
        braille_term_rows = 0
        braille_term_cols = 0
        if braille_mode and not editing:
            vis_rows_term = max_y - 1
            vis_cols_term = grid_max_x - 1
            vis_rows = min(rows, vis_rows_term * 4)
            vis_cols = min(cols, vis_cols_term * 2)
            braille_term_rows = (vis_rows + 3) // 4
            braille_term_cols = (vis_cols + 1) // 2
        else:
            vis_rows = min(rows, max_y - 1)
            vis_cols = min(cols, (grid_max_x - 1) // 2)

        # Precompute selection bounds
        sel_min_r = sel_max_r = sel_min_c = sel_max_c = -1
        if editing and selecting:
            sel_min_r, sel_max_r = min(sel_anchor_r, cursor_r), max(sel_anchor_r, cursor_r)
            sel_min_c, sel_max_c = min(sel_anchor_c, cursor_c), max(sel_anchor_c, cursor_c)

        # Precompute paste preview cells
        paste_cells = set()
        if editing and pasting and clipboard:
            stamp_h, stamp_w = len(clipboard), len(clipboard[0])
            for pr in range(stamp_h):
                for pc in range(stamp_w):
                    gr, gc = cursor_r + pr, cursor_c + pc
                    if 0 <= gr < rows and 0 <= gc < cols and clipboard[pr][pc]:
                        paste_cells.add((gr, gc))

        # Draw grid
        if braille_mode and not editing:
            # High-density Braille rendering: 2×4 grid cells per terminal cell
            braille_lines = _render_braille_grid(grid, rows, cols,
                                                  braille_term_rows,
                                                  braille_term_cols)
            for tr in range(len(braille_lines)):
                for tc in range(len(braille_lines[tr])):
                    ch = braille_lines[tr][tc]
                    if ch == chr(_BRAILLE_BASE):
                        continue  # empty — skip for speed
                    cp = _braille_dominant_color(grid, rows, cols, tr, tc, ww, gs or lenia or physarum, turmite=turmite, wator=wator, fallingsand=fallingsand)
                    try:
                        stdscr.addstr(tr, tc, ch, curses.color_pair(cp))
                    except curses.error:
                        pass
        else:
            for r in range(vis_rows):
                for c in range(vis_cols):
                    age = grid[r][c]
                    cell_str = "\u2588\u2588" if age else "  "
                    if editing and r == cursor_r and c == cursor_c and not pasting:
                        if ww:
                            if age == WW_HEAD:
                                attr = curses.color_pair(16)
                            elif age == WW_TAIL:
                                attr = curses.color_pair(17)
                            elif age == WW_CONDUCTOR:
                                attr = curses.color_pair(18)
                            else:
                                attr = curses.color_pair(3)
                        else:
                            attr = curses.color_pair(4) if age else curses.color_pair(3)
                    elif (r, c) in paste_cells:
                        attr = curses.color_pair(9)
                        cell_str = "\u2588\u2588"
                    elif editing and pasting and r == cursor_r and c == cursor_c:
                        attr = curses.color_pair(9)
                    elif selecting and sel_min_r <= r <= sel_max_r and sel_min_c <= c <= sel_max_c:
                        attr = curses.color_pair(8)
                    elif detected_cells and (r, c) in detected_cells:
                        attr = curses.color_pair(12)
                    elif fallingsand:
                        attr = curses.color_pair(_fs_color(age))
                        cell_str = "\u2588\u2588" if age else "  "
                    elif wator:
                        attr = curses.color_pair(_wator_color(age))
                        cell_str = "\u2588\u2588" if age else "  "
                    elif turmite:
                        attr = curses.color_pair(_turmite_color(age))
                        cell_str = "\u2588\u2588" if age else "  "
                    elif gs or lenia or physarum:
                        attr = curses.color_pair(_grayscott_color(age))
                        cell_str = "\u2588\u2588" if age > 3 else "  "
                    elif ww:
                        attr = curses.color_pair(_wireworld_color(age)) if age else curses.color_pair(1)
                    else:
                        attr = curses.color_pair(_age_color(age)) if age else curses.color_pair(1)
                    try:
                        stdscr.addstr(r, c * 2, cell_str, attr)
                    except curses.error:
                        pass

        # Draw pattern labels on grid (not in Braille mode — coordinates differ)
        if detect_enabled and detected and not (braille_mode and not editing):
            for name, instances in detected.items():
                for (mr, mc, h, w, _cells) in instances:
                    label_r = mr - 1 if mr > 0 else mr + h
                    label_c = mc * 2
                    if 0 <= label_r < vis_rows and label_c < grid_max_x - 1:
                        disp = name[:max((grid_max_x - label_c) // 1, 0)]
                        if disp:
                            try:
                                stdscr.addstr(label_r, label_c, disp,
                                              curses.color_pair(12) | curses.A_BOLD)
                            except curses.error:
                                pass

        # Draw stats panel if enabled
        if show_stats and max_x > panel_width + 20:
            _draw_stats_panel(stdscr, pop_history, generation, panel_width, max_y, max_x,
                              detected_patterns=detected if detect_enabled else None)

        # Status bar
        rule_label = rule.get("name", "Custom")
        if se.custom_rule_fn:
            rule_label = "Script Rule"
        hist_str = ""
        if browsing_history:
            hist_str = f" | HISTORY {hist_idx}/{len(history)-1}"
        challenge_str = ""
        if se.challenge_active:
            if se.challenge_won:
                challenge_str = " | CHALLENGE WON!"
            elif se.challenge_lost:
                challenge_str = " | CHALLENGE FAILED"
            else:
                challenge_str = f" | TARGET: pop {se.challenge_target} in {se.challenge_max_gens} gens"
        script_str = f" | Script: {se.script_name}" if se.script_name else ""
        if editing and pasting:
            stamp_h, stamp_w = len(clipboard), len(clipboard[0]) if clipboard else (0, 0)
            status = f" PASTE ({cursor_r},{cursor_c}) {stamp_h}x{stamp_w} | [arrows]move [enter]confirm [>/<]rotate [f/F]flip h/v [esc]cancel"
        elif editing and selecting:
            sel_h = abs(cursor_r - sel_anchor_r) + 1
            sel_w = abs(cursor_c - sel_anchor_c) + 1
            status = f" SELECT ({sel_anchor_r},{sel_anchor_c})->({cursor_r},{cursor_c}) {sel_h}x{sel_w} | [arrows]resize [y]ank [x]cut [esc]cancel"
        elif editing:
            if ww:
                ww_state_name = {WW_EMPTY: "empty", WW_HEAD: "HEAD", WW_TAIL: "TAIL", WW_CONDUCTOR: "wire"}.get(grid[cursor_r][cursor_c], "?")
                status = f" EDITOR ({cursor_r},{cursor_c}) [{ww_state_name}] | Gen {generation} | {rule_label} | [arrows]move [enter/space]cycle(empty>wire>head>tail) [v]select [p]aste [P]attern [s]ave [l]oad [c]lear [R]ule [e]xit [q]uit"
            else:
                status = f" EDITOR ({cursor_r},{cursor_c}) | Gen {generation} | {rule_label} | [arrows]move [enter/space]toggle [v]select [p]aste [P]attern [s]ave(rle/cells) [l]oad [c]lear [R]ule [e]xit [q]uit"
        else:
            pop_str = f" | Pop {pop}" if not show_stats else ""
            state_str = 'REWOUND' if browsing_history else ('PAUSED' if paused else 'Running')
            detect_str = " | DETECT" if detect_enabled else ""
            engine_str = " | NumPy" if (_HAS_NUMPY and not hashlife_active and _topology == TOPO_TORUS) else ""
            sound_str = " | SOUND" if sound.active else ""
            braille_str = " | BRAILLE" if braille_mode else ""
            topo_str = f" | {TOPOLOGY_LABELS[_topology]}" if _topology != TOPO_TORUS else ""
            if hashlife_active:
                hl_exp = hashlife.get_step_exponent()
                if hl_exp is None:
                    hl_exp = hashlife.get_max_exponent()
                hl_gens = 1 << hl_exp if hl_exp >= 0 else 1
                hashlife_str = f" | HASHLIFE 2^{hl_exp} ({hl_gens} gens/step) [<>]speed"
            else:
                hashlife_str = ""
            gs_str = f" | F={_gs_feed:.4f} k={_gs_kill:.4f} [<>]preset" if gs else ""
            eca_str = f" | Rule {_eca_rule_num} [<>]cycle [W]rule#" if eca else ""
            turmite_str = f" | {len(_turmite_ants)} ant(s) [<>]preset" if turmite else ""
            if wator:
                _wf, _ws = _wator_population(grid)
                wator_str = f" | Fish:{_wf} Sharks:{_ws} breed={_wator_fish_breed}/{_wator_shark_breed} starve={_wator_shark_starve} [<>]preset"
            else:
                wator_str = ""
            status = f" Gen {generation} | Delay {delay:.2f}s | {rule_label} | {state_str}{hist_str}{pop_str}{detect_str}{sound_str}{braille_str}{topo_str}{hashlife_str}{gs_str}{eca_str}{turmite_str}{wator_str}{challenge_str}{script_str}{engine_str} | [space]pause [e]dit [g]raph [d]etect [S]ound [B]raille [T]opo [H]ashLife [+/-]speed [r]andom [R]ule [L]ua [n]ext [[][]]scrub [b]eginning [G]IF [q]uit"
        try:
            stdscr.addstr(min(rows, max_y - 1), 0, status[:max_x - 1], curses.color_pair(2) | curses.A_REVERSE)
        except curses.error:
            pass

        # Multiplayer: show remote cursor
        if mp and remote_cursor[0] >= 0 and not (braille_mode and not editing):
            rr, rc = remote_cursor
            if 0 <= rr < vis_rows and 0 <= rc < vis_cols:
                age = grid[rr][rc]
                cell_str = "\u2588\u2588" if age else "  "
                attr = curses.color_pair(11) if age else curses.color_pair(10)
                try:
                    stdscr.addstr(rr, rc * 2, cell_str, attr)
                except curses.error:
                    pass

        # Multiplayer: show connection status in status bar area
        if mp:
            mp_status = ""
            if not network.connected:
                mp_status = " [Waiting for peer...]" if network.is_host else " [Connecting...]"
            else:
                role = "HOST" if network.is_host else "CLIENT"
                mp_status = f" [MP:{role}]"
            try:
                sx = min(len(status), max_x - len(mp_status) - 2)
                stdscr.addstr(min(rows, max_y - 1), sx, mp_status[:max_x - sx - 1],
                              curses.color_pair(10) | curses.A_BOLD)
            except curses.error:
                pass

        # Script engine: show log overlay (last few lines, top-right)
        if se.log_lines:
            log_x = 2
            log_y_start = 1
            log_count = min(len(se.log_lines), max(1, max_y - 5))
            for li, line in enumerate(se.log_lines[-log_count:]):
                ly = log_y_start + li
                if ly < max_y - 1:
                    disp = line[:max_x - log_x - 2]
                    try:
                        stdscr.addstr(ly, log_x, disp, curses.color_pair(2) | curses.A_DIM)
                    except curses.error:
                        pass

        stdscr.refresh()

        # Multiplayer: process incoming network messages
        if mp:
            # Host: send initial sync once peer connects
            if network.is_host and network.connected and not mp_sent_sync:
                network.send_grid_sync(grid, generation, rule)
                network.send_pause(paused)
                mp_sent_sync = True

            for msg in network.drain_messages():
                mt = msg.get("t")
                if mt == "sync":
                    # Full grid sync (client receives this on connect)
                    new_grid = msg["g"]
                    if len(new_grid) == rows and len(new_grid[0]) == cols:
                        for r2 in range(rows):
                            for c2 in range(cols):
                                grid[r2][c2] = new_grid[r2][c2]
                    generation = msg.get("gen", 0)
                    # Parse rule from sync
                    rule_s = msg.get("rule", "")
                    if rule_s:
                        if rule_s.lower() == "wireworld":
                            rule = RULES["wireworld"]
                        else:
                            try:
                                rule = parse_rule_string(rule_s)
                                rn = msg.get("name", "")
                                if rn:
                                    rule["name"] = rn
                            except ValueError:
                                pass
                    # Find matching rule_idx
                    rule_idx = -1
                    for i, rname in enumerate(RULE_NAMES):
                        if RULES[rname] is rule:
                            rule_idx = i
                            break
                        elif not rule.get("wireworld") and RULES[rname]["b"] == rule["b"] and RULES[rname]["s"] == rule["s"]:
                            rule_idx = i
                            break
                    history = [copy.deepcopy(grid)]
                    hist_idx = 0
                    browsing_history = False
                    pop_history = []
                    mp_synced = True
                elif mt == "cell":
                    r2, c2, v = msg["r"], msg["c"], msg["v"]
                    if 0 <= r2 < rows and 0 <= c2 < cols:
                        grid[r2][c2] = v
                elif mt == "cur":
                    remote_cursor = (msg.get("r", -1), msg.get("c", -1))
                elif mt == "step":
                    new_grid = msg.get("g")
                    if new_grid and len(new_grid) == rows and len(new_grid[0]) == cols:
                        for r2 in range(rows):
                            for c2 in range(cols):
                                grid[r2][c2] = new_grid[r2][c2]
                    generation = msg.get("gen", generation)
                    if not browsing_history:
                        history.append(copy.deepcopy(grid))
                        hist_idx = len(history) - 1
                        if len(history) > max_history:
                            history.pop(0)
                            hist_idx -= 1
                elif mt == "clear":
                    for r2 in range(rows):
                        for c2 in range(cols):
                            grid[r2][c2] = 0
                    generation = 0
                    history = [copy.deepcopy(grid)]
                    hist_idx = 0
                    browsing_history = False
                    pop_history = []
                elif mt == "pause":
                    paused = msg.get("p", paused)
                elif mt == "rule":
                    rule_s = msg.get("rule", "")
                    if rule_s:
                        if rule_s.lower() == "wireworld":
                            rule = RULES["wireworld"]
                        else:
                            try:
                                rule = parse_rule_string(rule_s)
                                rn = msg.get("name", "")
                                if rn:
                                    rule["name"] = rn
                            except ValueError:
                                pass
                    ridx = msg.get("idx", -1)
                    if ridx >= 0:
                        rule_idx = ridx

        # Handle input
        key = stdscr.getch()
        if key == ord("q"):
            sound.stop()
            if mp:
                network.close()
            break

        if editing and pasting:
            # Paste-preview mode controls
            if key == curses.KEY_UP:
                cursor_r = (cursor_r - 1) % rows
            elif key == curses.KEY_DOWN:
                cursor_r = (cursor_r + 1) % rows
            elif key == curses.KEY_LEFT:
                cursor_c = (cursor_c - 1) % cols
            elif key == curses.KEY_RIGHT:
                cursor_c = (cursor_c + 1) % cols
            elif key in (ord("\n"), curses.KEY_ENTER):
                # Confirm paste: stamp clipboard onto grid
                if clipboard:
                    for pr in range(len(clipboard)):
                        for pc in range(len(clipboard[0])):
                            gr, gc = cursor_r + pr, cursor_c + pc
                            if 0 <= gr < rows and 0 <= gc < cols and clipboard[pr][pc]:
                                grid[gr][gc] = clipboard[pr][pc]
                                if mp:
                                    network.send_cell_toggle(gr, gc, grid[gr][gc])
                pasting = False
            elif key == 27:  # Escape
                pasting = False
            elif key == ord(">") or key == ord("."):
                clipboard = _rotate_cw(clipboard)
            elif key == ord("<") or key == ord(","):
                clipboard = _rotate_ccw(clipboard)
            elif key == ord("f"):
                clipboard = _flip_h(clipboard)
            elif key == ord("F"):
                clipboard = _flip_v(clipboard)
        elif editing and selecting:
            # Selection mode controls
            if key == curses.KEY_UP:
                cursor_r = (cursor_r - 1) % rows
            elif key == curses.KEY_DOWN:
                cursor_r = (cursor_r + 1) % rows
            elif key == curses.KEY_LEFT:
                cursor_c = (cursor_c - 1) % cols
            elif key == curses.KEY_RIGHT:
                cursor_c = (cursor_c + 1) % cols
            elif key == ord("y"):
                # Yank (copy) selected region
                clipboard = _extract_region(grid, sel_anchor_r, sel_anchor_c, cursor_r, cursor_c)
                selecting = False
            elif key == ord("x"):
                # Cut selected region
                clipboard = _extract_region(grid, sel_anchor_r, sel_anchor_c, cursor_r, cursor_c)
                min_r, max_r2 = min(sel_anchor_r, cursor_r), max(sel_anchor_r, cursor_r)
                min_c, max_c2 = min(sel_anchor_c, cursor_c), max(sel_anchor_c, cursor_c)
                for r2 in range(min_r, max_r2 + 1):
                    for c2 in range(min_c, max_c2 + 1):
                        if mp and grid[r2][c2]:
                            network.send_cell_toggle(r2, c2, 0)
                        grid[r2][c2] = 0
                selecting = False
            elif key == 27:  # Escape
                selecting = False
        elif editing:
            # Editor-mode controls
            if key == curses.KEY_UP:
                cursor_r = (cursor_r - 1) % rows
            elif key == curses.KEY_DOWN:
                cursor_r = (cursor_r + 1) % rows
            elif key == curses.KEY_LEFT:
                cursor_c = (cursor_c - 1) % cols
            elif key == curses.KEY_RIGHT:
                cursor_c = (cursor_c + 1) % cols
            elif key in (ord("\n"), ord(" "), curses.KEY_ENTER):
                if ww:
                    # Cycle: empty -> conductor -> head -> tail -> empty
                    cur = grid[cursor_r][cursor_c]
                    grid[cursor_r][cursor_c] = {
                        WW_EMPTY: WW_CONDUCTOR, WW_CONDUCTOR: WW_HEAD,
                        WW_HEAD: WW_TAIL, WW_TAIL: WW_EMPTY,
                    }.get(cur, WW_EMPTY)
                else:
                    grid[cursor_r][cursor_c] = 0 if grid[cursor_r][cursor_c] else 1
                if mp:
                    network.send_cell_toggle(cursor_r, cursor_c, grid[cursor_r][cursor_c])
            elif key == ord("v"):
                # Enter select mode
                selecting = True
                sel_anchor_r = cursor_r
                sel_anchor_c = cursor_c
            elif key == ord("p"):
                # Paste from clipboard
                if clipboard:
                    pasting = True
            elif key == ord("P"):
                # Pattern stamp picker: load a built-in pattern to clipboard
                if ww:
                    stamp_names = list(WIREWORLD_PATTERNS.keys())
                else:
                    stamp_names = [n for n in PATTERNS if n != "random"]
                if stamp_names:
                    sel = 0
                    picking = True
                    stdscr.nodelay(False)
                    while picking:
                        stdscr.erase()
                        try:
                            stdscr.addstr(0, 0, "Pick stamp (arrows to select, enter to load, esc to cancel):",
                                          curses.color_pair(2))
                        except curses.error:
                            pass
                        for i, sn in enumerate(stamp_names):
                            if i + 2 >= max_y - 1:
                                break
                            attr = curses.A_REVERSE if i == sel else 0
                            if ww:
                                cells = WIREWORLD_PATTERNS[sn]
                                dims = ""
                                if cells:
                                    mr = max(r for r, c, s in cells) + 1
                                    mc = max(c for r, c, s in cells) + 1
                                    dims = f"  ({mr}x{mc})"
                            else:
                                cells = PATTERNS[sn]
                                dims = ""
                                if cells:
                                    mr = max(r for r, c in cells) + 1
                                    mc = max(c for r, c in cells) + 1
                                    dims = f"  ({mr}x{mc})"
                            try:
                                stdscr.addstr(i + 2, 2, sn + dims, attr)
                            except curses.error:
                                pass
                        stdscr.refresh()
                        pk = stdscr.getch()
                        if pk == curses.KEY_UP:
                            sel = (sel - 1) % len(stamp_names)
                        elif pk == curses.KEY_DOWN:
                            sel = (sel + 1) % len(stamp_names)
                        elif pk in (ord("\n"), curses.KEY_ENTER):
                            if ww:
                                clipboard = _wireworld_pattern_to_stamp(stamp_names[sel])
                            else:
                                clipboard = _pattern_to_stamp(stamp_names[sel])
                            if clipboard:
                                pasting = True
                            picking = False
                        elif pk == 27:
                            picking = False
                    stdscr.nodelay(True)
            elif key == ord("c"):
                for r2 in range(rows):
                    for c2 in range(cols):
                        grid[r2][c2] = 0
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
                if mp:
                    network.send_clear()
            elif key == ord("s"):
                max_y, max_x = stdscr.getmaxyx()
                fmt = curses_input(stdscr, "Format [r]le / [c]ells (default: rle): ", max_y, max_x).strip().lower()
                if fmt == "" or fmt == "r" or fmt == "rle":
                    ext, use_rle = ".rle", True
                else:
                    ext, use_rle = ".cells", False
                name = curses_input(stdscr, "Save as (name, no ext): ", max_y, max_x)
                if name:
                    os.makedirs(CELLS_DIR, exist_ok=True)
                    filepath = os.path.join(CELLS_DIR, name + ext)
                    if use_rle:
                        save_rle(grid, filepath, rule)
                    else:
                        save_cells(grid, filepath, rule)
            elif key == ord("l"):
                max_y, max_x = stdscr.getmaxyx()
                patterns = list_saved_patterns()
                if patterns:
                    # Show pattern picker
                    sel = 0
                    picking = True
                    stdscr.nodelay(False)
                    while picking:
                        stdscr.erase()
                        try:
                            stdscr.addstr(0, 0, "Load pattern (arrows to select, enter to load, esc to cancel):",
                                          curses.color_pair(2))
                        except curses.error:
                            pass
                        for i, p in enumerate(patterns):
                            if i + 2 >= max_y - 1:
                                break
                            attr = curses.A_REVERSE if i == sel else 0
                            try:
                                stdscr.addstr(i + 2, 2, p, attr)
                            except curses.error:
                                pass
                        stdscr.refresh()
                        pk = stdscr.getch()
                        if pk == curses.KEY_UP:
                            sel = (sel - 1) % len(patterns)
                        elif pk == curses.KEY_DOWN:
                            sel = (sel + 1) % len(patterns)
                        elif pk in (ord("\n"), curses.KEY_ENTER):
                            filepath = os.path.join(CELLS_DIR, patterns[sel])
                            grid, loaded_ww = _load_pattern_file(filepath, rows, cols)
                            if loaded_ww:
                                rule = RULES["wireworld"]
                                rule_idx = RULE_NAMES.index("wireworld")
                            generation = 0
                            history = [copy.deepcopy(grid)]
                            hist_idx = 0
                            browsing_history = False
                            pop_history = []
                            picking = False
                        elif pk == 27:
                            picking = False
                    stdscr.nodelay(True)
                else:
                    # No saved patterns; prompt for a file path
                    path = curses_input(stdscr, "Load file path: ", max_y, max_x)
                    if path and os.path.isfile(path):
                        grid, loaded_ww = _load_pattern_file(path, rows, cols)
                        if loaded_ww:
                            rule = RULES["wireworld"]
                            rule_idx = RULE_NAMES.index("wireworld")
                        generation = 0
                        history = [copy.deepcopy(grid)]
                        hist_idx = 0
                        browsing_history = False
                        pop_history = []
            elif key == ord("R"):
                was_ww = ww
                was_gs = gs
                was_eca = eca
                was_lenia = lenia
                was_turmite = turmite
                was_wator = wator
                was_fs = fallingsand
                was_phys = physarum
                if rule_idx >= 0:
                    rule_idx = (rule_idx + 1) % len(RULE_NAMES)
                    rule = RULES[RULE_NAMES[rule_idx]]
                else:
                    rule_idx = 0
                    rule = RULES[RULE_NAMES[0]]
                new_ww = _is_wireworld(rule)
                new_gs = _is_grayscott(rule)
                new_eca = _is_elementary(rule)
                new_lenia = _is_lenia(rule)
                new_turmite = _is_turmite(rule)
                new_wator = _is_wator(rule)
                new_fs = _is_fallingsand(rule)
                new_phys = _is_physarum(rule)
                if new_ww or new_gs or new_eca or new_lenia or new_turmite or new_wator or new_fs or new_phys:
                    hashlife_active = False
                # Mode transition: clear grid and re-initialize
                if was_ww != new_ww or was_gs != new_gs or was_eca != new_eca or was_lenia != new_lenia or was_turmite != new_turmite or was_wator != new_wator or was_fs != new_fs or was_phys != new_phys:
                    for r2 in range(rows):
                        for c2 in range(cols):
                            grid[r2][c2] = 0
                    if new_ww:
                        place_wireworld_pattern(grid, "ww_clock")
                    elif new_gs:
                        _gs_init(rows, cols)
                        grid = _gs_to_grid(rows, cols)
                    elif new_eca:
                        _eca_init(cols)
                        grid = _eca_to_grid(rows, cols)
                    elif new_lenia:
                        preset = LENIA_PRESETS[LENIA_PRESET_NAMES[_lenia_preset_idx]]
                        _lenia_init(rows, cols, preset.get("seed", "orbium"))
                        grid = _lenia_to_grid(rows, cols)
                    elif new_turmite:
                        _turmite_init(rows, cols)
                        grid = _turmite_to_grid(rows, cols)
                    elif new_wator:
                        _wator_init(rows, cols)
                        grid = _wator_to_grid(rows, cols)
                    elif new_fs:
                        _fs_init(rows, cols)
                        grid = _fs_to_grid(rows, cols)
                    elif new_phys:
                        _phys_init(rows, cols)
                        grid = _phys_to_grid(rows, cols)
                    generation = 0
                    history = [copy.deepcopy(grid)]
                    hist_idx = 0
                    browsing_history = False
                    pop_history = []
                if hashlife_active:
                    # Re-sync HashLife with new rule
                    hashlife.from_grid(grid, rule)
                    hashlife.generation = generation
                if mp:
                    network.send_rule_change(rule, rule_idx)
            elif key == ord("g"):
                show_stats = not show_stats
            elif key == ord("d"):
                detect_enabled = not detect_enabled
            elif key == ord("L"):
                # Load and run a script
                scripts = list_scripts()
                if scripts:
                    sel = 0
                    picking = True
                    stdscr.nodelay(False)
                    while picking:
                        stdscr.erase()
                        try:
                            stdscr.addstr(0, 0, "Load script (arrows to select, enter to run, esc to cancel):",
                                          curses.color_pair(2))
                        except curses.error:
                            pass
                        for i, sn in enumerate(scripts):
                            if i + 2 >= max_y - 1:
                                break
                            attr = curses.A_REVERSE if i == sel else 0
                            try:
                                stdscr.addstr(i + 2, 2, sn, attr)
                            except curses.error:
                                pass
                        stdscr.refresh()
                        pk = stdscr.getch()
                        if pk == curses.KEY_UP:
                            sel = (sel - 1) % len(scripts)
                        elif pk == curses.KEY_DOWN:
                            sel = (sel + 1) % len(scripts)
                        elif pk in (ord("\n"), curses.KEY_ENTER):
                            filepath = os.path.join(SCRIPTS_DIR, scripts[sel])
                            actions = se.load_and_run(filepath, grid)
                            if actions:
                                for action_type, action_data in actions:
                                    if action_type == "rule":
                                        rule = action_data
                                        rule_idx = -1
                            picking = False
                        elif pk == 27:
                            picking = False
                    stdscr.nodelay(True)
                else:
                    max_y, max_x = stdscr.getmaxyx()
                    path = curses_input(stdscr, f"Script path (or save to {SCRIPTS_DIR}/): ", max_y, max_x)
                    if path:
                        if not os.path.isfile(path):
                            candidate = os.path.join(SCRIPTS_DIR, path)
                            if not candidate.endswith(".py"):
                                candidate += ".py"
                            if os.path.isfile(candidate):
                                path = candidate
                        if os.path.isfile(path):
                            actions = se.load_and_run(path, grid)
                            if actions:
                                for action_type, action_data in actions:
                                    if action_type == "rule":
                                        rule = action_data
                                        rule_idx = -1
            elif key == ord("e"):
                editing = False
                if hashlife_active:
                    hashlife.from_grid(grid, rule)
                    hashlife.generation = generation
        else:
            # Normal-mode controls
            if key == ord(" ") and not browsing_history:
                paused = not paused
                if mp:
                    network.send_pause(paused)
            elif key == ord("+") or key == ord("="):
                delay = max(0.01, delay - 0.05)
            elif key == ord("-") or key == ord("_"):
                delay = min(2.0, delay + 0.05)
            elif key == ord("r"):
                if wator:
                    _wator_init(rows, cols)
                    grid = _wator_to_grid(rows, cols)
                elif gs:
                    _gs_init(rows, cols)
                    grid = _gs_to_grid(rows, cols)
                elif eca:
                    _eca_init(cols, init_type="random")
                    grid = _eca_to_grid(rows, cols)
                elif physarum:
                    _phys_init(rows, cols)
                    grid = _phys_to_grid(rows, cols)
                else:
                    import random
                    for r2 in range(rows):
                        for c2 in range(cols):
                            grid[r2][c2] = random.randint(0, 1)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
                hashlife_active = False
                if mp:
                    network.send_grid_sync(grid, generation, rule)
            elif key == ord("R"):
                was_ww = ww
                was_gs = gs
                was_eca = eca
                was_lenia = lenia
                was_turmite = turmite
                was_wator = wator
                was_fs = fallingsand
                was_phys = physarum
                if rule_idx >= 0:
                    rule_idx = (rule_idx + 1) % len(RULE_NAMES)
                    rule = RULES[RULE_NAMES[rule_idx]]
                else:
                    rule_idx = 0
                    rule = RULES[RULE_NAMES[0]]
                new_ww = _is_wireworld(rule)
                new_gs = _is_grayscott(rule)
                new_eca = _is_elementary(rule)
                new_lenia = _is_lenia(rule)
                new_turmite = _is_turmite(rule)
                new_wator = _is_wator(rule)
                new_fs = _is_fallingsand(rule)
                new_phys = _is_physarum(rule)
                if new_ww or new_gs or new_eca or new_lenia or new_turmite or new_wator or new_fs or new_phys:
                    hashlife_active = False
                if was_ww != new_ww or was_gs != new_gs or was_eca != new_eca or was_lenia != new_lenia or was_turmite != new_turmite or was_wator != new_wator or was_fs != new_fs or was_phys != new_phys:
                    for r2 in range(rows):
                        for c2 in range(cols):
                            grid[r2][c2] = 0
                    if new_ww:
                        place_wireworld_pattern(grid, "ww_clock")
                    elif new_gs:
                        _gs_init(rows, cols)
                        grid = _gs_to_grid(rows, cols)
                    elif new_eca:
                        _eca_init(cols)
                        grid = _eca_to_grid(rows, cols)
                    elif new_lenia:
                        preset = LENIA_PRESETS[LENIA_PRESET_NAMES[_lenia_preset_idx]]
                        _lenia_init(rows, cols, preset.get("seed", "orbium"))
                        grid = _lenia_to_grid(rows, cols)
                    elif new_turmite:
                        _turmite_init(rows, cols)
                        grid = _turmite_to_grid(rows, cols)
                    elif new_wator:
                        _wator_init(rows, cols)
                        grid = _wator_to_grid(rows, cols)
                    elif new_fs:
                        _fs_init(rows, cols)
                        grid = _fs_to_grid(rows, cols)
                    elif new_phys:
                        _phys_init(rows, cols)
                        grid = _phys_to_grid(rows, cols)
                    generation = 0
                    history = [copy.deepcopy(grid)]
                    hist_idx = 0
                    browsing_history = False
                    pop_history = []
                if hashlife_active:
                    # Re-sync HashLife with new rule
                    hashlife.from_grid(grid, rule)
                    hashlife.generation = generation
                if mp:
                    network.send_rule_change(rule, rule_idx)
            elif key == ord("n") and (paused or browsing_history):
                # Single-step forward: fork from current point if browsing
                if browsing_history:
                    # Fork: discard future, resume from this point
                    del history[hist_idx + 1:]
                    grid = copy.deepcopy(history[hist_idx])
                    browsing_history = False
                    pop_history = [_count_population(h) for h in history[-max_pop_history:]]
                if hashlife_active:
                    hashlife.from_grid(grid, rule)
                    hashlife.generation = generation
                    hashlife.set_step_exponent(0)  # single step = 1 gen
                    hashlife.step()
                    generation = hashlife.generation
                    grid = hashlife.to_grid(rows, cols)
                else:
                    custom_grid = se.custom_step(grid)
                    if custom_grid is not None:
                        grid = custom_grid
                    else:
                        grid = step(grid, rule)
                    generation += 1
                se.bind_grid(grid)
                se.run_step_callback(generation, _count_population(grid))
                history.append(copy.deepcopy(grid))
                hist_idx = len(history) - 1
                if len(history) > max_history:
                    history.pop(0)
                    hist_idx -= 1
            elif key == ord("["):
                # Rewind one generation
                if hist_idx > 0:
                    if not browsing_history:
                        browsing_history = True
                        paused = True
                    hist_idx -= 1
                    grid = copy.deepcopy(history[hist_idx])
                    generation = hist_idx
            elif key == ord("]"):
                # Forward one generation in history
                if browsing_history and hist_idx < len(history) - 1:
                    hist_idx += 1
                    grid = copy.deepcopy(history[hist_idx])
                    generation = hist_idx
                    if hist_idx == len(history) - 1:
                        browsing_history = False
            elif key == ord("b"):
                # Jump to beginning of history
                if len(history) > 1:
                    browsing_history = True
                    paused = True
                    hist_idx = 0
                    grid = copy.deepcopy(history[hist_idx])
                    generation = 0
            elif key == ord("g"):
                show_stats = not show_stats
            elif key == ord("d"):
                detect_enabled = not detect_enabled
            elif key == ord("S"):
                new_state, err = sound.toggle()
                if err:
                    try:
                        stdscr.addstr(min(rows, max_y - 1), 0,
                                      f" Sound: {err}"[:max_x - 1],
                                      curses.color_pair(2) | curses.A_REVERSE)
                        stdscr.refresh()
                    except curses.error:
                        pass
                    stdscr.nodelay(False)
                    stdscr.getch()
                    stdscr.nodelay(True)
            elif key == ord("B"):
                braille_mode = not braille_mode
            elif key == ord("T"):
                # Cycle topology: Torus -> Klein Bottle -> Möbius Strip -> Bounded
                topo_idx = (topo_idx + 1) % len(TOPOLOGIES)
                _topology = TOPOLOGIES[topo_idx]
                # Disable HashLife for non-torus topologies (it assumes torus)
                if _topology != TOPO_TORUS and hashlife_active:
                    grid = hashlife.to_grid(rows, cols)
                    generation = hashlife.generation
                    hashlife_active = False
            elif key == ord("H"):
                # Toggle HashLife hyperspeed mode (only for Life-like B/S rules)
                if not ww and not gs and not lenia and not se.custom_rule_fn:
                    if not hashlife_active:
                        # Activate: import grid into quadtree
                        hashlife = HashLifeEngine()
                        hashlife.from_grid(grid, rule)
                        hashlife.generation = generation
                        hashlife.set_step_exponent(0)  # Start at 1 gen/step
                        hashlife_active = True
                    else:
                        # Deactivate: export quadtree back to grid
                        grid = hashlife.to_grid(rows, cols)
                        generation = hashlife.generation
                        hashlife_active = False
                        # Reset history from current state
                        history = [copy.deepcopy(grid)]
                        hist_idx = 0
                        browsing_history = False
            elif key == ord("<") and hashlife_active:
                # Decrease HashLife step size
                exp = hashlife.get_step_exponent()
                if exp is None:
                    exp = hashlife.get_max_exponent()
                if exp > 0:
                    hashlife.set_step_exponent(exp - 1)
            elif key == ord(">") and hashlife_active:
                # Increase HashLife step size
                exp = hashlife.get_step_exponent()
                if exp is None:
                    exp = hashlife.get_max_exponent()
                else:
                    max_exp = hashlife.get_max_exponent()
                    if exp < max_exp:
                        hashlife.set_step_exponent(exp + 1)
                    else:
                        hashlife.set_step_exponent(None)  # Max speed
            elif key == ord("<") and gs:
                # Previous Gray-Scott preset
                _gs_preset_idx = (_gs_preset_idx - 1) % len(GS_PRESET_NAMES)
                preset = GS_PRESETS[GS_PRESET_NAMES[_gs_preset_idx]]
                _gs_feed = preset["F"]
                _gs_kill = preset["k"]
                rule["name"] = f"Gray-Scott ({preset['name']})"
                _gs_init(rows, cols)
                grid = _gs_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord(">") and gs:
                # Next Gray-Scott preset
                _gs_preset_idx = (_gs_preset_idx + 1) % len(GS_PRESET_NAMES)
                preset = GS_PRESETS[GS_PRESET_NAMES[_gs_preset_idx]]
                _gs_feed = preset["F"]
                _gs_kill = preset["k"]
                rule["name"] = f"Gray-Scott ({preset['name']})"
                _gs_init(rows, cols)
                grid = _gs_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord("<") and eca:
                # Previous notable ECA rule
                _eca_notable_idx = (_eca_notable_idx - 1) % len(ECA_NOTABLE_RULES)
                _eca_rule_num = ECA_NOTABLE_RULES[_eca_notable_idx]
                rule["name"] = f"Elementary CA (Rule {_eca_rule_num})"
                _eca_init(cols)
                grid = _eca_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord(">") and eca:
                # Next notable ECA rule
                _eca_notable_idx = (_eca_notable_idx + 1) % len(ECA_NOTABLE_RULES)
                _eca_rule_num = ECA_NOTABLE_RULES[_eca_notable_idx]
                rule["name"] = f"Elementary CA (Rule {_eca_rule_num})"
                _eca_init(cols)
                grid = _eca_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord("<") and lenia:
                # Previous Lenia preset
                _lenia_preset_idx = (_lenia_preset_idx - 1) % len(LENIA_PRESET_NAMES)
                _lenia_apply_preset(LENIA_PRESET_NAMES[_lenia_preset_idx])
                rule["name"] = f"Lenia ({LENIA_PRESETS[LENIA_PRESET_NAMES[_lenia_preset_idx]]['name']})"
                preset = LENIA_PRESETS[LENIA_PRESET_NAMES[_lenia_preset_idx]]
                _lenia_init(rows, cols, preset.get("seed", "orbium"))
                grid = _lenia_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord(">") and lenia:
                # Next Lenia preset
                _lenia_preset_idx = (_lenia_preset_idx + 1) % len(LENIA_PRESET_NAMES)
                _lenia_apply_preset(LENIA_PRESET_NAMES[_lenia_preset_idx])
                rule["name"] = f"Lenia ({LENIA_PRESETS[LENIA_PRESET_NAMES[_lenia_preset_idx]]['name']})"
                preset = LENIA_PRESETS[LENIA_PRESET_NAMES[_lenia_preset_idx]]
                _lenia_init(rows, cols, preset.get("seed", "orbium"))
                grid = _lenia_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord("<") and turmite:
                # Previous turmite preset
                _turmite_preset_idx = (_turmite_preset_idx - 1) % len(TURMITE_PRESET_NAMES)
                preset_name = TURMITE_PRESET_NAMES[_turmite_preset_idx]
                rule["name"] = TURMITE_PRESETS[preset_name]["name"]
                _turmite_init(rows, cols, preset_name)
                grid = _turmite_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord(">") and turmite:
                # Next turmite preset
                _turmite_preset_idx = (_turmite_preset_idx + 1) % len(TURMITE_PRESET_NAMES)
                preset_name = TURMITE_PRESET_NAMES[_turmite_preset_idx]
                rule["name"] = TURMITE_PRESETS[preset_name]["name"]
                _turmite_init(rows, cols, preset_name)
                grid = _turmite_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord("<") and wator:
                # Previous Wa-Tor preset
                _wator_preset_idx = (_wator_preset_idx - 1) % len(WATOR_PRESET_NAMES)
                preset_name = WATOR_PRESET_NAMES[_wator_preset_idx]
                rule["name"] = f"Wa-Tor ({WATOR_PRESETS[preset_name]['name']})"
                _wator_init(rows, cols, preset_name)
                grid = _wator_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord(">") and wator:
                # Next Wa-Tor preset
                _wator_preset_idx = (_wator_preset_idx + 1) % len(WATOR_PRESET_NAMES)
                preset_name = WATOR_PRESET_NAMES[_wator_preset_idx]
                rule["name"] = f"Wa-Tor ({WATOR_PRESETS[preset_name]['name']})"
                _wator_init(rows, cols, preset_name)
                grid = _wator_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord("<") and fallingsand:
                # Previous Falling Sand preset
                _fs_preset_idx = (_fs_preset_idx - 1) % len(FALLINGSAND_PRESET_NAMES)
                preset_name = FALLINGSAND_PRESET_NAMES[_fs_preset_idx]
                rule["name"] = f"Falling Sand ({FALLINGSAND_PRESETS[preset_name]['name']})"
                _fs_init(rows, cols, preset_name)
                grid = _fs_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord(">") and fallingsand:
                # Next Falling Sand preset
                _fs_preset_idx = (_fs_preset_idx + 1) % len(FALLINGSAND_PRESET_NAMES)
                preset_name = FALLINGSAND_PRESET_NAMES[_fs_preset_idx]
                rule["name"] = f"Falling Sand ({FALLINGSAND_PRESETS[preset_name]['name']})"
                _fs_init(rows, cols, preset_name)
                grid = _fs_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord("<") and physarum:
                # Previous Physarum preset
                _phys_preset_idx = (_phys_preset_idx - 1) % len(PHYSARUM_PRESET_NAMES)
                preset_name = PHYSARUM_PRESET_NAMES[_phys_preset_idx]
                rule["name"] = f"Physarum ({PHYSARUM_PRESETS[preset_name]['name']})"
                _phys_init(rows, cols, preset_name)
                grid = _phys_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord(">") and physarum:
                # Next Physarum preset
                _phys_preset_idx = (_phys_preset_idx + 1) % len(PHYSARUM_PRESET_NAMES)
                preset_name = PHYSARUM_PRESET_NAMES[_phys_preset_idx]
                rule["name"] = f"Physarum ({PHYSARUM_PRESETS[preset_name]['name']})"
                _phys_init(rows, cols, preset_name)
                grid = _phys_to_grid(rows, cols)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
            elif key == ord("W") and eca:
                # Enter a specific ECA rule number (0-255)
                paused = True
                max_y2, max_x2 = stdscr.getmaxyx()
                num_str = curses_input(stdscr, f"Enter rule number (0-255) [{_eca_rule_num}]: ", max_y2, max_x2)
                if num_str.strip():
                    try:
                        num = int(num_str.strip())
                        if 0 <= num <= 255:
                            _eca_rule_num = num
                            rule["name"] = f"Elementary CA (Rule {_eca_rule_num})"
                            # Update notable index if it matches
                            if _eca_rule_num in ECA_NOTABLE_RULES:
                                _eca_notable_idx = ECA_NOTABLE_RULES.index(_eca_rule_num)
                            _eca_init(cols)
                            grid = _eca_to_grid(rows, cols)
                            generation = 0
                            history = [copy.deepcopy(grid)]
                            hist_idx = 0
                            browsing_history = False
                            pop_history = []
                    except ValueError:
                        pass
            elif key == ord("G"):
                # Export history as animated GIF
                if len(history) > 1:
                    paused = True
                    gif_path = os.path.join(os.getcwd(), f"life_gen{generation}.gif")
                    # Show exporting message
                    try:
                        msg = f" Exporting {len(history)} frames to GIF..."
                        stdscr.addstr(min(rows, max_y - 1), 0,
                                      msg[:max_x - 1],
                                      curses.color_pair(2) | curses.A_REVERSE)
                        stdscr.refresh()
                    except curses.error:
                        pass
                    try:
                        export_gif(history, rows, cols, gif_path,
                                   cell_size=4, delay_cs=max(1, int(delay * 100)),
                                   wireworld=ww, grayscott=gs, lenia=lenia)
                        export_msg = f" Saved {gif_path}"
                    except (OSError, IOError) as exc:
                        export_msg = f" GIF export failed: {exc}"
                    # Show result and wait for keypress
                    try:
                        stdscr.addstr(min(rows, max_y - 1), 0,
                                      export_msg[:max_x - 1],
                                      curses.color_pair(2) | curses.A_REVERSE)
                        stdscr.refresh()
                    except curses.error:
                        pass
                    stdscr.nodelay(False)
                    stdscr.getch()  # wait for any key
                    stdscr.nodelay(True)
            elif key == ord("L"):
                # Load and run a script (normal mode)
                paused = True
                scripts = list_scripts()
                if scripts:
                    sel = 0
                    picking = True
                    stdscr.nodelay(False)
                    while picking:
                        stdscr.erase()
                        try:
                            stdscr.addstr(0, 0, "Load script (arrows to select, enter to run, esc to cancel):",
                                          curses.color_pair(2))
                        except curses.error:
                            pass
                        for i, sn in enumerate(scripts):
                            if i + 2 >= max_y - 1:
                                break
                            attr = curses.A_REVERSE if i == sel else 0
                            try:
                                stdscr.addstr(i + 2, 2, sn, attr)
                            except curses.error:
                                pass
                        stdscr.refresh()
                        pk = stdscr.getch()
                        if pk == curses.KEY_UP:
                            sel = (sel - 1) % len(scripts)
                        elif pk == curses.KEY_DOWN:
                            sel = (sel + 1) % len(scripts)
                        elif pk in (ord("\n"), curses.KEY_ENTER):
                            filepath = os.path.join(SCRIPTS_DIR, scripts[sel])
                            actions = se.load_and_run(filepath, grid)
                            if actions:
                                for action_type, action_data in actions:
                                    if action_type == "rule":
                                        rule = action_data
                                        rule_idx = -1
                            generation = 0
                            history = [copy.deepcopy(grid)]
                            hist_idx = 0
                            browsing_history = False
                            pop_history = []
                            picking = False
                        elif pk == 27:
                            picking = False
                    stdscr.nodelay(True)
                else:
                    max_y2, max_x2 = stdscr.getmaxyx()
                    path = curses_input(stdscr, f"Script path (or save to {SCRIPTS_DIR}/): ", max_y2, max_x2)
                    if path:
                        if not os.path.isfile(path):
                            candidate = os.path.join(SCRIPTS_DIR, path)
                            if not candidate.endswith(".py"):
                                candidate += ".py"
                            if os.path.isfile(candidate):
                                path = candidate
                        if os.path.isfile(path):
                            actions = se.load_and_run(path, grid)
                            if actions:
                                for action_type, action_data in actions:
                                    if action_type == "rule":
                                        rule = action_data
                                        rule_idx = -1
                            generation = 0
                            history = [copy.deepcopy(grid)]
                            hist_idx = 0
                            browsing_history = False
                            pop_history = []
            elif key == ord("e"):
                paused = True
                editing = True
            elif key == ord(" ") and browsing_history:
                # Unpause from history: fork from current point
                del history[hist_idx + 1:]
                grid = copy.deepcopy(history[hist_idx])
                generation = hist_idx
                browsing_history = False
                paused = False
                # Rebuild pop_history up to this point
                pop_history = [_count_population(h) for h in history[-max_pop_history:]]
                if hashlife_active:
                    hashlife.from_grid(grid, rule)
                    hashlife.generation = generation

        # Multiplayer: send cursor position (throttled)
        if mp and network.connected and editing:
            now = time.monotonic()
            if now - last_cursor_send > 0.05:
                network.send_cursor(cursor_r, cursor_c)
                last_cursor_send = now

        if not paused and not editing and not browsing_history:
            # In multiplayer, only the host drives simulation
            if not mp or network.is_host:
                if hashlife_active:
                    # HashLife hyperspeed step
                    gens_advanced = hashlife.step()
                    generation = hashlife.generation
                    grid = hashlife.to_grid(rows, cols)
                    se.bind_grid(grid)
                    se.run_step_callback(generation, hashlife.get_population())
                    # Don't store every frame in history during hyperspeed
                    if len(history) == 0 or gens_advanced <= 1:
                        history.append(copy.deepcopy(grid))
                        hist_idx = len(history) - 1
                        if len(history) > max_history:
                            history.pop(0)
                            hist_idx -= 1
                else:
                    # Use custom rule from script engine if available
                    custom_grid = se.custom_step(grid)
                    if custom_grid is not None:
                        grid = custom_grid
                    else:
                        grid = step(grid, rule)
                    generation += 1
                    se.bind_grid(grid)
                    se.run_step_callback(generation, _count_population(grid))
                    history.append(copy.deepcopy(grid))
                    hist_idx = len(history) - 1
                    if len(history) > max_history:
                        history.pop(0)
                        hist_idx -= 1
                if mp and network.connected:
                    network.send_step(grid, generation)

        # Sound synthesis: generate audio frame for current grid state
        if sound.active:
            sound.generate_frame(grid, rows, cols, delay)

        time.sleep(delay)


# --- Genetic Algorithm Rule Discovery ---

import random as _random


class GeneticRuleDiscovery:
    """Evolves interesting cellular automaton rulesets using a genetic algorithm.

    Maintains a population of candidate B/S rulesets, runs short simulations of
    each, scores them on a fitness function that rewards sustained complexity,
    and iteratively selects, crosses over, and mutates the best candidates.
    """

    def __init__(self, pop_size=60, grid_rows=40, grid_cols=60,
                 sim_generations=200, elite_count=6, mutation_rate=0.15,
                 seed_density=0.35):
        self.pop_size = pop_size
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.sim_generations = sim_generations
        self.elite_count = elite_count
        self.mutation_rate = mutation_rate
        self.seed_density = seed_density
        self.population = []       # list of {"b": set, "s": set}
        self.fitness_scores = []   # parallel list of floats
        self.generation = 0
        self.best_ever = []        # top rules across all generations
        self._init_population()

    def _init_population(self):
        """Seed the initial population with random rulesets."""
        self.population = []
        for _ in range(self.pop_size):
            self.population.append(self._random_rule())

    def _random_rule(self):
        """Generate a random B/S ruleset."""
        birth = set()
        survival = set()
        # Birth conditions: pick from 1-8 (0 neighbours birth is degenerate)
        for n in range(1, 9):
            if _random.random() < 0.25:
                birth.add(n)
        # Survival conditions: pick from 0-8
        for n in range(9):
            if _random.random() < 0.3:
                survival.add(n)
        # Ensure at least one birth condition
        if not birth:
            birth.add(_random.randint(1, 8))
        return {"b": birth, "s": survival}

    def _make_seed_grid(self):
        """Create a deterministic random grid for fair fitness comparison."""
        grid = make_grid(self.grid_rows, self.grid_cols)
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                if _random.random() < self.seed_density:
                    grid[r][c] = 1
        return grid

    def evaluate_fitness(self, rule):
        """Run a short simulation and score the ruleset on complexity metrics.

        Fitness rewards:
        - Sustained moderate population (not extinct, not exploding)
        - Population oscillation (sign of interesting dynamics)
        - Diversity of population levels over time
        - Longevity (not dying out quickly)

        Fitness penalties:
        - Rapid extinction (population drops to 0)
        - Unbounded growth (population fills the grid)
        - Static population (frozen / boring)
        """
        total_cells = self.grid_rows * self.grid_cols
        full_rule = {"b": rule["b"], "s": rule["s"], "name": "candidate"}
        grid = self._make_seed_grid()

        pop_history = []
        for gen in range(self.sim_generations):
            pop = _count_population(grid)
            pop_history.append(pop)
            # Early termination: extinction
            if pop == 0:
                break
            # Early termination: total saturation
            if pop >= total_cells * 0.95:
                break
            grid = step(grid, full_rule)

        if not pop_history:
            return 0.0

        # --- Scoring components ---
        final_pop = pop_history[-1]
        generations_survived = len(pop_history)
        avg_pop = sum(pop_history) / len(pop_history)
        density = avg_pop / total_cells

        # 1. Longevity score: reward surviving many generations
        longevity = generations_survived / self.sim_generations

        # 2. Population balance: reward moderate density (peak around 0.15-0.40)
        if density < 0.01:
            balance = density * 10  # very sparse — low score
        elif density > 0.80:
            balance = max(0, 1.0 - (density - 0.80) * 5)  # too dense
        else:
            # Bell curve centered around 0.25
            balance = math.exp(-((density - 0.25) ** 2) / (2 * 0.12 ** 2))

        # 3. Oscillation: reward population variance (sign of dynamics)
        if len(pop_history) > 10:
            mean_pop = avg_pop
            variance = sum((p - mean_pop) ** 2 for p in pop_history) / len(pop_history)
            std_dev = math.sqrt(variance)
            # Normalize by mean to get coefficient of variation
            cv = std_dev / max(mean_pop, 1)
            oscillation = min(cv * 3, 1.0)  # cap at 1.0
        else:
            oscillation = 0.0

        # 4. Activity: reward changes between consecutive generations
        if len(pop_history) > 1:
            changes = sum(1 for i in range(1, len(pop_history))
                          if pop_history[i] != pop_history[i - 1])
            activity = changes / (len(pop_history) - 1)
        else:
            activity = 0.0

        # 5. Non-extinction bonus
        alive_bonus = 1.0 if final_pop > 0 else 0.0

        # 6. Diversity: number of distinct population levels
        unique_pops = len(set(pop_history))
        diversity = min(unique_pops / 50.0, 1.0)

        # Weighted combination
        fitness = (
            longevity * 0.20 +
            balance * 0.25 +
            oscillation * 0.20 +
            activity * 0.15 +
            alive_bonus * 0.10 +
            diversity * 0.10
        )
        return fitness

    def evaluate_all(self):
        """Evaluate fitness for the entire population."""
        # Use the same seed grid for all candidates in this generation
        seed_state = _random.getstate()
        self.fitness_scores = []
        for rule in self.population:
            _random.setstate(seed_state)
            score = self.evaluate_fitness(rule)
            self.fitness_scores.append(score)

    def select_parent(self, ranked):
        """Tournament selection: pick 3 random candidates, return the best."""
        contestants = _random.sample(ranked, min(3, len(ranked)))
        return max(contestants, key=lambda x: x[1])[0]

    def crossover(self, parent_a, parent_b):
        """Uniform crossover of birth/survival conditions."""
        child_b = set()
        child_s = set()
        for n in range(9):
            # Birth
            if n in parent_a["b"] and n in parent_b["b"]:
                child_b.add(n)
            elif n in parent_a["b"] or n in parent_b["b"]:
                if _random.random() < 0.5:
                    child_b.add(n)
            # Survival
            if n in parent_a["s"] and n in parent_b["s"]:
                child_s.add(n)
            elif n in parent_a["s"] or n in parent_b["s"]:
                if _random.random() < 0.5:
                    child_s.add(n)
        if not child_b:
            child_b.add(_random.randint(1, 8))
        return {"b": child_b, "s": child_s}

    def mutate(self, rule):
        """Flip random birth/survival bits."""
        new_b = set(rule["b"])
        new_s = set(rule["s"])
        for n in range(1, 9):
            if _random.random() < self.mutation_rate:
                new_b.symmetric_difference_update({n})
        for n in range(9):
            if _random.random() < self.mutation_rate:
                new_s.symmetric_difference_update({n})
        if not new_b:
            new_b.add(_random.randint(1, 8))
        return {"b": new_b, "s": new_s}

    def evolve_one_generation(self):
        """Run one generation of the GA: evaluate, select, crossover, mutate."""
        self.evaluate_all()

        # Rank population by fitness
        ranked = list(zip(self.population, self.fitness_scores))
        ranked.sort(key=lambda x: x[1], reverse=True)

        # Track best-ever rules
        for rule, score in ranked[:3]:
            rule_str = _rule_to_str(rule)
            existing = {_rule_to_str(r): s for r, s in self.best_ever}
            if rule_str not in existing or existing[rule_str] < score:
                self.best_ever = [(r, s) for r, s in self.best_ever
                                  if _rule_to_str(r) != rule_str]
                self.best_ever.append((dict(rule), score))
        self.best_ever.sort(key=lambda x: x[1], reverse=True)
        self.best_ever = self.best_ever[:20]  # keep top 20 all-time

        # Elitism: keep top performers unchanged
        new_population = [dict(r) for r, _ in ranked[:self.elite_count]]

        # Fill rest with offspring
        while len(new_population) < self.pop_size:
            parent_a = self.select_parent(ranked)
            parent_b = self.select_parent(ranked)
            child = self.crossover(parent_a, parent_b)
            child = self.mutate(child)
            new_population.append(child)

        self.population = new_population
        self.generation += 1

    def get_top_rules(self, n=10):
        """Return the top n rules from the all-time best list."""
        return self.best_ever[:n]


def _rule_to_str(rule):
    """Convert a rule dict to B/S notation string."""
    b_str = "".join(str(n) for n in sorted(rule["b"]))
    s_str = "".join(str(n) for n in sorted(rule["s"]))
    return f"B{b_str}/S{s_str}"


def run_discovery(stdscr, rows, cols, ga_generations=50, pop_size=60,
                  sim_generations=200):
    """Curses UI for the genetic algorithm rule discovery mode."""
    curses.curs_set(0)
    stdscr.nodelay(False)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_WHITE, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(8, curses.COLOR_BLUE, -1)
    curses.init_pair(9, curses.COLOR_RED, -1)

    ga = GeneticRuleDiscovery(
        pop_size=pop_size,
        grid_rows=rows,
        grid_cols=cols,
        sim_generations=sim_generations,
    )

    phase = "evolving"   # "evolving" or "results"
    selected_idx = 0
    preview_grid = None
    preview_gen = 0
    preview_running = False

    def draw_evolving(ga_gen, best_score, best_rule, progress):
        """Draw the evolution progress screen."""
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        title = "GENETIC RULE DISCOVERY"
        try:
            stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title,
                          curses.A_BOLD | curses.color_pair(4))
        except curses.error:
            pass

        info_lines = [
            f"GA Generation: {ga_gen}/{ga_generations}",
            f"Population: {pop_size} candidates",
            f"Simulation depth: {sim_generations} steps each",
            "",
            f"Evaluating candidate {progress}/{pop_size}..." if progress > 0 else "Starting evaluation...",
            "",
        ]
        for i, line in enumerate(info_lines):
            try:
                stdscr.addstr(2 + i, 2, line, curses.color_pair(2))
            except curses.error:
                pass

        # Progress bar
        bar_y = 2 + len(info_lines)
        bar_width = min(max_x - 6, 50)
        if ga_generations > 0:
            pct = ga_gen / ga_generations
        else:
            pct = 0
        filled = int(bar_width * pct)
        bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
        try:
            stdscr.addstr(bar_y, 2, bar, curses.color_pair(1))
            stdscr.addstr(bar_y, bar_width + 4, f"{pct * 100:.0f}%",
                          curses.color_pair(1))
        except curses.error:
            pass

        # Best rule so far
        if best_rule:
            try:
                stdscr.addstr(bar_y + 2, 2, "Best rule so far:",
                              curses.A_BOLD | curses.color_pair(3))
                stdscr.addstr(bar_y + 3, 4,
                              f"{_rule_to_str(best_rule)}  (fitness: {best_score:.4f})",
                              curses.color_pair(4))
            except curses.error:
                pass

        # Top rules leaderboard
        top = ga.get_top_rules(8)
        if top:
            lb_y = bar_y + 5
            try:
                stdscr.addstr(lb_y, 2, "Leaderboard:",
                              curses.A_BOLD | curses.color_pair(3))
            except curses.error:
                pass
            for i, (rule, score) in enumerate(top):
                if lb_y + 1 + i >= max_y - 1:
                    break
                try:
                    stdscr.addstr(lb_y + 1 + i, 4,
                                  f"{i + 1:2d}. {_rule_to_str(rule):20s}  fitness: {score:.4f}",
                                  curses.color_pair(2))
                except curses.error:
                    pass

        try:
            stdscr.addstr(max_y - 1, 2, "Press 'q' to skip to results  |  Esc to quit",
                          curses.color_pair(5))
        except curses.error:
            pass
        stdscr.refresh()

    def draw_results():
        """Draw the results exploration screen."""
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        top = ga.get_top_rules(20)
        if not top:
            try:
                stdscr.addstr(1, 2, "No rules discovered.", curses.color_pair(9))
            except curses.error:
                pass
            stdscr.refresh()
            return

        title = "DISCOVERED RULES — Select one to explore"
        try:
            stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title,
                          curses.A_BOLD | curses.color_pair(4))
        except curses.error:
            pass

        # Left panel: rule list
        list_width = 42
        for i, (rule, score) in enumerate(top):
            if 2 + i >= max_y - 2:
                break
            rule_str = f"{i + 1:2d}. {_rule_to_str(rule):20s} fit: {score:.4f}"
            if i == selected_idx:
                attr = curses.A_BOLD | curses.color_pair(6)
            else:
                attr = curses.color_pair(2)
            try:
                stdscr.addstr(2 + i, 2, rule_str.ljust(list_width), attr)
            except curses.error:
                pass

        # Right panel: mini preview of selected rule
        if preview_grid is not None:
            prev_x = list_width + 5
            prev_max_w = max_x - prev_x - 1
            prev_max_h = max_y - 4
            try:
                sel_rule = top[selected_idx][0]
                stdscr.addstr(1, prev_x, f"Preview: {_rule_to_str(sel_rule)}  gen={preview_gen}",
                              curses.A_BOLD | curses.color_pair(3))
            except curses.error:
                pass

            for r in range(min(len(preview_grid), prev_max_h)):
                row_str = ""
                for c in range(min(len(preview_grid[0]), prev_max_w)):
                    row_str += "\u2588" if preview_grid[r][c] else " "
                try:
                    if preview_grid[r]:
                        cp = curses.color_pair(1)
                    else:
                        cp = curses.color_pair(2)
                    stdscr.addstr(3 + r, prev_x, row_str, curses.color_pair(1))
                except curses.error:
                    pass

        # Footer
        footer = "UP/DOWN: select | ENTER: launch in simulator | SPACE: play/pause preview | q/Esc: quit"
        try:
            stdscr.addstr(max_y - 1, 2, footer[:max_x - 4], curses.color_pair(5))
        except curses.error:
            pass

        stdscr.refresh()

    def init_preview():
        nonlocal preview_grid, preview_gen, preview_running
        _random.seed(42)  # deterministic seed for previews
        preview_grid = ga._make_seed_grid()
        preview_gen = 0
        preview_running = True

    def step_preview():
        nonlocal preview_grid, preview_gen
        top = ga.get_top_rules(20)
        if not top or selected_idx >= len(top):
            return
        rule = top[selected_idx][0]
        full_rule = {"b": rule["b"], "s": rule["s"], "name": "preview"}
        pop = _count_population(preview_grid)
        if pop > 0:
            preview_grid = step(preview_grid, full_rule)
            preview_gen += 1

    # --- Evolution phase ---
    stdscr.nodelay(True)
    stdscr.timeout(0)

    for ga_gen in range(ga_generations):
        # Evaluate with progress updates
        seed_state = _random.getstate()
        ga.fitness_scores = []
        best_score = ga.best_ever[0][1] if ga.best_ever else 0.0
        best_rule = ga.best_ever[0][0] if ga.best_ever else None

        for i, rule in enumerate(ga.population):
            _random.setstate(seed_state)
            score = ga.evaluate_fitness(rule)
            ga.fitness_scores.append(score)

            # Update display every 5 candidates
            if i % 5 == 0:
                draw_evolving(ga_gen, best_score, best_rule, i + 1)
                key = stdscr.getch()
                if key == ord('q'):
                    # Skip to results
                    ga.evaluate_all()
                    ga.evolve_one_generation()
                    phase = "results"
                    break
                elif key == 27:  # Esc
                    return None

        if phase == "results":
            break

        # Rank and evolve
        ranked = list(zip(ga.population, ga.fitness_scores))
        ranked.sort(key=lambda x: x[1], reverse=True)

        # Track best-ever
        for rule, score in ranked[:3]:
            rule_str = _rule_to_str(rule)
            existing = {_rule_to_str(r): s for r, s in ga.best_ever}
            if rule_str not in existing or existing[rule_str] < score:
                ga.best_ever = [(r, s) for r, s in ga.best_ever
                                if _rule_to_str(r) != rule_str]
                ga.best_ever.append((dict(rule), score))
        ga.best_ever.sort(key=lambda x: x[1], reverse=True)
        ga.best_ever = ga.best_ever[:20]

        # Selection, crossover, mutation
        new_population = [dict(r) for r, _ in ranked[:ga.elite_count]]
        while len(new_population) < ga.pop_size:
            parent_a = ga.select_parent(ranked)
            parent_b = ga.select_parent(ranked)
            child = ga.crossover(parent_a, parent_b)
            child = ga.mutate(child)
            new_population.append(child)
        ga.population = new_population
        ga.generation += 1

        draw_evolving(ga_gen + 1, best_score, best_rule, pop_size)

    # --- Results phase ---
    phase = "results"
    init_preview()
    stdscr.timeout(80)  # ~12 fps for preview animation

    while True:
        draw_results()
        top = ga.get_top_rules(20)
        if not top:
            stdscr.timeout(-1)
            stdscr.getch()
            return None

        if preview_running:
            step_preview()

        key = stdscr.getch()
        if key == -1:
            continue
        elif key == curses.KEY_UP:
            selected_idx = max(0, selected_idx - 1)
            init_preview()
        elif key == curses.KEY_DOWN:
            selected_idx = min(len(top) - 1, selected_idx + 1)
            init_preview()
        elif key == ord(' '):
            preview_running = not preview_running
            if preview_running and preview_gen == 0:
                init_preview()
        elif key == ord('r'):
            init_preview()
        elif key in (curses.KEY_ENTER, 10, 13):
            # Return the selected rule for interactive exploration
            sel_rule = top[selected_idx][0]
            return {
                "b": sel_rule["b"],
                "s": sel_rule["s"],
                "name": f"Discovered ({_rule_to_str(sel_rule)})",
            }
        elif key in (ord('q'), 27):
            return None


def main():
    parser = argparse.ArgumentParser(description="Cellular automaton simulator in the terminal")
    parser.add_argument("--rows", type=int, default=40, help="Grid height (default: 40)")
    parser.add_argument("--cols", type=int, default=80, help="Grid width (default: 80)")
    parser.add_argument("--speed", type=float, default=0.1, help="Delay between generations in seconds (default: 0.1)")
    parser.add_argument(
        "--pattern",
        choices=list(PATTERNS.keys()),
        default="glider",
        help="Starter pattern (default: glider)",
    )
    parser.add_argument(
        "--load",
        type=str,
        default=None,
        help="Load a .cells or .rle file (path or name from ~/.life-patterns/)",
    )
    parser.add_argument(
        "--rule",
        type=str,
        default="life",
        help="Rule preset (" + ", ".join(RULE_NAMES) + ") or B/S notation (e.g. B36/S23). Default: life",
    )
    parser.add_argument(
        "--host",
        type=int,
        default=None,
        metavar="PORT",
        help="Host a multiplayer session on PORT (e.g. --host 4444)",
    )
    parser.add_argument(
        "--connect",
        type=str,
        default=None,
        metavar="HOST:PORT",
        help="Connect to a multiplayer host (e.g. --connect 192.168.1.5:4444)",
    )
    parser.add_argument(
        "--script",
        type=str,
        default=None,
        metavar="PATH",
        help="Run a Lua-like Python script on startup (path or name from ~/.life-scripts/)",
    )
    parser.add_argument(
        "--gs-preset",
        choices=list(GS_PRESETS.keys()),
        default="mitosis",
        help="Gray-Scott preset when --rule grayscott (default: mitosis). "
             "Options: " + ", ".join(GS_PRESETS.keys()),
    )
    parser.add_argument(
        "--eca-rule",
        type=int,
        default=30,
        metavar="N",
        help="Wolfram rule number (0-255) when --rule elementary (default: 30). "
             "Notable: 30 (PRNG), 110 (Turing-complete), 90 (Sierpinski)",
    )
    parser.add_argument(
        "--lenia-preset",
        choices=list(LENIA_PRESETS.keys()),
        default="orbium",
        help="Lenia species preset when --rule lenia (default: orbium). "
             "Options: " + ", ".join(LENIA_PRESETS.keys()),
    )
    parser.add_argument(
        "--turmite-preset",
        choices=list(TURMITE_PRESETS.keys()),
        default="langton",
        help="Turmite preset when --rule turmite (default: langton). "
             "Options: " + ", ".join(TURMITE_PRESETS.keys()),
    )
    parser.add_argument(
        "--wator-preset",
        choices=list(WATOR_PRESETS.keys()),
        default="classic",
        help="Wa-Tor ecosystem preset when --rule wator (default: classic). "
             "Options: " + ", ".join(WATOR_PRESETS.keys()),
    )
    parser.add_argument(
        "--fallingsand-preset",
        choices=list(FALLINGSAND_PRESETS.keys()),
        default="hourglass",
        help="Falling Sand preset when --rule fallingsand (default: hourglass). "
             "Options: " + ", ".join(FALLINGSAND_PRESETS.keys()),
    )
    parser.add_argument(
        "--physarum-preset",
        choices=list(PHYSARUM_PRESETS.keys()),
        default="dendritic",
        help="Physarum preset when --rule physarum (default: dendritic). "
             "Options: " + ", ".join(PHYSARUM_PRESETS.keys()),
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        default=False,
        help="Launch genetic algorithm rule discovery mode to evolve interesting rulesets",
    )
    parser.add_argument(
        "--ga-generations",
        type=int,
        default=50,
        metavar="N",
        help="Number of GA generations to run in discovery mode (default: 50)",
    )
    parser.add_argument(
        "--ga-pop-size",
        type=int,
        default=60,
        metavar="N",
        help="GA population size in discovery mode (default: 60)",
    )
    parser.add_argument(
        "--ga-sim-depth",
        type=int,
        default=200,
        metavar="N",
        help="Simulation steps per candidate in discovery mode (default: 200)",
    )
    parser.add_argument(
        "--render",
        type=int,
        default=None,
        metavar="N",
        help="Headless batch-render mode: run N generations and output PNG frames",
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=8,
        metavar="PX",
        help="Pixel size of each cell for PNG rendering (default: 8)",
    )
    parser.add_argument(
        "--palette",
        choices=list(_PNG_PALETTES.keys()),
        default="classic",
        help="Color palette for PNG rendering (default: classic). "
             "Options: " + ", ".join(_PNG_PALETTES.keys()),
    )
    parser.add_argument(
        "--grid-lines",
        action="store_true",
        default=False,
        help="Draw grid lines between cells in PNG output",
    )
    parser.add_argument(
        "--no-aa",
        action="store_true",
        default=False,
        help="Disable anti-aliasing on cell edges in PNG output",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="frames",
        metavar="DIR",
        help="Output directory for rendered PNG frames (default: frames)",
    )
    args = parser.parse_args()

    global _gs_preset_idx, _gs_feed, _gs_kill, _eca_rule_num, _eca_notable_idx, _lenia_preset_idx, _turmite_preset_idx, _wator_preset_idx, _fs_preset_idx

    # Headless batch-render mode: output PNG frames without terminal UI
    if args.render is not None:
        if args.render < 1:
            parser.error("--render requires a positive integer (number of generations)")
        # Resolve rule
        if args.rule.lower() in RULES:
            rule = RULES[args.rule.lower()]
        else:
            try:
                rule = parse_rule_string(args.rule)
            except ValueError as e:
                parser.error(str(e))
        run_headless_render(
            rows=args.rows,
            cols=args.cols,
            speed=args.speed,
            rule=rule,
            pattern=args.pattern,
            load_path=args.load,
            generations=args.render,
            cell_size=args.cell_size,
            palette_name=args.palette,
            grid_lines=args.grid_lines,
            grid_line_color=None,
            output_dir=args.output_dir,
            aa=not args.no_aa,
        )
        return

    # Discovery mode: run genetic algorithm to find interesting rules
    if args.discover:
        def _run_discovery(stdscr):
            return run_discovery(
                stdscr, args.rows, args.cols,
                ga_generations=args.ga_generations,
                pop_size=args.ga_pop_size,
                sim_generations=args.ga_sim_depth,
            )

        discovered_rule = curses.wrapper(_run_discovery)
        if discovered_rule is None:
            return
        # User selected a rule — launch the normal simulator with it
        rule = discovered_rule
        grid = make_grid(args.rows, args.cols)
        place_pattern(grid, "random")
        script_engine = ScriptEngine()
        try:
            curses.wrapper(lambda stdscr: run(stdscr, grid, args.speed, rule, None, script_engine))
        finally:
            pass
        return

    # Resolve rule
    if args.rule.lower() in RULES:
        rule = RULES[args.rule.lower()]
    else:
        try:
            rule = parse_rule_string(args.rule)
        except ValueError as e:
            parser.error(str(e))

    # Set up multiplayer networking
    network = None
    if args.host is not None and args.connect is not None:
        parser.error("Cannot use --host and --connect at the same time")
    if args.host is not None:
        network = NetworkPeer()
        network.host(args.host)
    elif args.connect is not None:
        network = NetworkPeer()
        try:
            if ":" in args.connect:
                host, port_str = args.connect.rsplit(":", 1)
                port = int(port_str)
            else:
                parser.error("--connect requires HOST:PORT format (e.g. 127.0.0.1:4444)")
            network.connect(host, port)
        except (ValueError, OSError) as e:
            parser.error(f"Failed to connect: {e}")

    grid = make_grid(args.rows, args.cols)
    if args.load:
        path = args.load
        # If it's just a name, look in the patterns directory
        if not os.path.isfile(path):
            # Try both .rle and .cells extensions
            for ext in ("", ".rle", ".cells"):
                candidate = os.path.join(CELLS_DIR, path + ext)
                if os.path.isfile(candidate):
                    path = candidate
                    break
        grid, loaded_ww = _load_pattern_file(path, args.rows, args.cols)
        if loaded_ww:
            rule = RULES["wireworld"]
    elif args.rule.lower() == "wireworld":
        # Wireworld mode with default pattern: place a clock
        place_wireworld_pattern(grid, "ww_clock")
    elif args.rule.lower() == "grayscott":
        # Gray-Scott reaction-diffusion: initialize U/V concentrations
        gs_preset_name = args.gs_preset
        if gs_preset_name in GS_PRESETS:
            _gs_preset_idx = GS_PRESET_NAMES.index(gs_preset_name)
            preset = GS_PRESETS[gs_preset_name]
            _gs_feed = preset["F"]
            _gs_kill = preset["k"]
            rule["name"] = f"Gray-Scott ({preset['name']})"
        _gs_init(args.rows, args.cols)
        grid = _gs_to_grid(args.rows, args.cols)
    elif args.rule.lower() == "elementary":
        # 1D Elementary CA: initialize with Wolfram rule number
        eca_num = args.eca_rule
        if not (0 <= eca_num <= 255):
            parser.error("--eca-rule must be between 0 and 255")
        _eca_rule_num = eca_num
        if _eca_rule_num in ECA_NOTABLE_RULES:
            _eca_notable_idx = ECA_NOTABLE_RULES.index(_eca_rule_num)
        rule["name"] = f"Elementary CA (Rule {_eca_rule_num})"
        _eca_init(args.cols)
        grid = _eca_to_grid(args.rows, args.cols)
    elif args.rule.lower() == "lenia":
        # Lenia continuous smooth-kernel CA
        lenia_preset_name = args.lenia_preset
        if lenia_preset_name in LENIA_PRESETS:
            _lenia_preset_idx = LENIA_PRESET_NAMES.index(lenia_preset_name)
            _lenia_apply_preset(lenia_preset_name)
            preset = LENIA_PRESETS[lenia_preset_name]
            rule["name"] = f"Lenia ({preset['name']})"
        _lenia_init(args.rows, args.cols, preset.get("seed", "orbium"))
        grid = _lenia_to_grid(args.rows, args.cols)
    elif args.rule.lower() == "turmite":
        # Langton's Ant / generalized turmites
        turmite_preset_name = args.turmite_preset
        if turmite_preset_name in TURMITE_PRESETS:
            _turmite_preset_idx = TURMITE_PRESET_NAMES.index(turmite_preset_name)
            preset = TURMITE_PRESETS[turmite_preset_name]
            rule["name"] = preset["name"]
        _turmite_init(args.rows, args.cols, turmite_preset_name)
        grid = _turmite_to_grid(args.rows, args.cols)
    elif args.rule.lower() == "wator":
        # Wa-Tor predator-prey ecosystem
        wator_preset_name = args.wator_preset
        if wator_preset_name in WATOR_PRESETS:
            _wator_preset_idx = WATOR_PRESET_NAMES.index(wator_preset_name)
            preset = WATOR_PRESETS[wator_preset_name]
            rule["name"] = f"Wa-Tor ({preset['name']})"
        _wator_init(args.rows, args.cols, wator_preset_name)
        grid = _wator_to_grid(args.rows, args.cols)
    elif args.rule.lower() == "fallingsand":
        # Falling Sand particle simulation
        fs_preset_name = args.fallingsand_preset
        if fs_preset_name in FALLINGSAND_PRESETS:
            _fs_preset_idx = FALLINGSAND_PRESET_NAMES.index(fs_preset_name)
            preset = FALLINGSAND_PRESETS[fs_preset_name]
            rule["name"] = f"Falling Sand ({preset['name']})"
        _fs_init(args.rows, args.cols, fs_preset_name)
        grid = _fs_to_grid(args.rows, args.cols)
    elif args.rule.lower() == "physarum":
        # Physarum slime mold transport network
        phys_preset_name = args.physarum_preset
        if phys_preset_name in PHYSARUM_PRESETS:
            _phys_preset_idx = PHYSARUM_PRESET_NAMES.index(phys_preset_name)
            preset = PHYSARUM_PRESETS[phys_preset_name]
            rule["name"] = f"Physarum ({preset['name']})"
        _phys_init(args.rows, args.cols, phys_preset_name)
        grid = _phys_to_grid(args.rows, args.cols)
    else:
        place_pattern(grid, args.pattern)

    # Set up scripting engine
    script_engine = ScriptEngine()
    if args.script:
        spath = args.script
        if not os.path.isfile(spath):
            # Try scripts directory
            for ext in ("", ".py"):
                candidate = os.path.join(SCRIPTS_DIR, spath + ext)
                if os.path.isfile(candidate):
                    spath = candidate
                    break
        if os.path.isfile(spath):
            actions = script_engine.load_and_run(spath, grid)
            if actions:
                for action_type, action_data in actions:
                    if action_type == "rule":
                        rule = action_data
        else:
            parser.error(f"Script file not found: {args.script}")

    try:
        curses.wrapper(lambda stdscr: run(stdscr, grid, args.speed, rule, network, script_engine))
    finally:
        if network:
            network.close()


if __name__ == "__main__":
    main()
