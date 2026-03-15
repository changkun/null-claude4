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
import threading
import time

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
}

RULE_NAMES = list(RULES.keys())


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
                """Count live neighbours of cell (r, c) with toroidal wrapping."""
                rows, cols = engine._grid_rows, engine._grid_cols
                count = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = (r + dr) % rows, (c + dc) % cols
                        if engine._grid[nr][nc]:
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


def save_cells(grid, filepath):
    """Save grid to a .cells plaintext file."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    rows, cols = len(grid), len(grid[0])
    # Find bounding box of live cells to trim empty borders
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
        if min_r == float("inf"):
            # Empty grid
            f.write(".\n")
            return
        for r in range(min_r, max_r + 1):
            line = ""
            for c in range(min_c, max_c + 1):
                line += "O" if grid[r][c] else "."
            f.write(line.rstrip(".") + "\n")


def load_cells(filepath, rows, cols):
    """Load a .cells plaintext file into a new grid, centred."""
    pattern_rows = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line.startswith("!"):
                continue
            row = []
            for ch in line:
                if ch == "O":
                    row.append(1)
                else:
                    row.append(0)
            pattern_rows.append(row)
    if not pattern_rows:
        return make_grid(rows, cols)
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
    return grid


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
        if ch == "b":
            current_row.extend([0] * run_count)
        elif ch == "o":
            current_row.extend([1] * run_count)
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
    """Encode a 2D list of 0/1 into RLE format text."""
    if not stamp or not stamp[0]:
        return ""
    height = len(stamp)
    width = max(len(r) for r in stamp)

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
            ch = "o" if val else "b"
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
    pattern_rows, _name, _rule = parse_rle(text)
    if not pattern_rows:
        return make_grid(rows, cols)
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
    return grid


def save_rle(grid, filepath, rule=None):
    """Save grid to an RLE file."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    rows, cols = len(grid), len(grid[0])
    # Find bounding box of live cells
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
            row.append(1 if grid[r][c] else 0)
        stamp.append(row)
    rule_str = "B3/S23"
    if rule:
        b = "".join(str(d) for d in sorted(rule["b"]))
        s = "".join(str(d) for d in sorted(rule["s"]))
        rule_str = f"B{b}/S{s}"
    with open(filepath, "w") as f:
        f.write(encode_rle(stamp, name=name, rule_str=rule_str))


def _load_pattern_file(filepath, rows, cols):
    """Load a pattern file (.cells or .rle) based on extension."""
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
            nr, nc = (r + dr) % rows, (c + dc) % cols
            count += 1 if grid[nr][nc] else 0
    return count


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
        # Convert grid to 0/1 (strip age info for sync)
        flat = [[1 if c else 0 for c in row] for row in grid]
        b = "".join(str(d) for d in sorted(rule["b"]))
        s = "".join(str(d) for d in sorted(rule["s"]))
        self.send({
            "t": "sync",
            "g": flat,
            "gen": generation,
            "rule": f"B{b}/S{s}",
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
        flat = [[1 if c else 0 for c in row] for row in grid]
        self.send({"t": "step", "g": flat, "gen": generation})

    def send_clear(self):
        self.send({"t": "clear"})

    def send_pause(self, paused):
        self.send({"t": "pause", "p": paused})

    def send_rule_change(self, rule, rule_idx):
        b = "".join(str(d) for d in sorted(rule["b"]))
        s = "".join(str(d) for d in sorted(rule["s"]))
        self.send({
            "t": "rule",
            "rule": f"B{b}/S{s}",
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
        for r in range(vis_rows):
            for c in range(vis_cols):
                age = grid[r][c]
                cell_str = "\u2588\u2588" if age else "  "
                if editing and r == cursor_r and c == cursor_c and not pasting:
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
                else:
                    attr = curses.color_pair(_age_color(age)) if age else curses.color_pair(1)
                try:
                    stdscr.addstr(r, c * 2, cell_str, attr)
                except curses.error:
                    pass

        # Draw pattern labels on grid
        if detect_enabled and detected:
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
            status = f" EDITOR ({cursor_r},{cursor_c}) | Gen {generation} | {rule_label} | [arrows]move [enter/space]toggle [v]select [p]aste [P]attern [s]ave(rle/cells) [l]oad [c]lear [R]ule [e]xit [q]uit"
        else:
            pop_str = f" | Pop {pop}" if not show_stats else ""
            state_str = 'REWOUND' if browsing_history else ('PAUSED' if paused else 'Running')
            detect_str = " | DETECT" if detect_enabled else ""
            status = f" Gen {generation} | Delay {delay:.2f}s | {rule_label} | {state_str}{hist_str}{pop_str}{detect_str}{challenge_str}{script_str} | [space]pause [e]dit [g]raph [d]etect [+/-]speed [r]andom [R]ule [L]ua [n]ext [[][]]scrub [b]eginning [q]uit"
        try:
            stdscr.addstr(min(rows, max_y - 1), 0, status[:max_x - 1], curses.color_pair(2) | curses.A_REVERSE)
        except curses.error:
            pass

        # Multiplayer: show remote cursor
        if mp and remote_cursor[0] >= 0:
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
                        if RULES[rname]["b"] == rule["b"] and RULES[rname]["s"] == rule["s"]:
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
                                grid[gr][gc] = 1
                                if mp:
                                    network.send_cell_toggle(gr, gc, 1)
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
                        save_cells(grid, filepath)
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
                            grid = _load_pattern_file(filepath, rows, cols)
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
                        grid = _load_pattern_file(path, rows, cols)
                        generation = 0
                        history = [copy.deepcopy(grid)]
                        hist_idx = 0
                        browsing_history = False
                        pop_history = []
            elif key == ord("R"):
                if rule_idx >= 0:
                    rule_idx = (rule_idx + 1) % len(RULE_NAMES)
                    rule = RULES[RULE_NAMES[rule_idx]]
                else:
                    rule_idx = 0
                    rule = RULES[RULE_NAMES[0]]
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
                import random
                for r2 in range(rows):
                    for c2 in range(cols):
                        grid[r2][c2] = random.randint(0, 1)
                generation = 0
                history = [copy.deepcopy(grid)]
                hist_idx = 0
                browsing_history = False
                pop_history = []
                if mp:
                    network.send_grid_sync(grid, generation, rule)
            elif key == ord("R"):
                if rule_idx >= 0:
                    rule_idx = (rule_idx + 1) % len(RULE_NAMES)
                    rule = RULES[RULE_NAMES[rule_idx]]
                else:
                    rule_idx = 0
                    rule = RULES[RULE_NAMES[0]]
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

        # Multiplayer: send cursor position (throttled)
        if mp and network.connected and editing:
            now = time.monotonic()
            if now - last_cursor_send > 0.05:
                network.send_cursor(cursor_r, cursor_c)
                last_cursor_send = now

        if not paused and not editing and not browsing_history:
            # In multiplayer, only the host drives simulation
            if not mp or network.is_host:
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

        time.sleep(delay)


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
    args = parser.parse_args()

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
        grid = _load_pattern_file(path, args.rows, args.cols)
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
