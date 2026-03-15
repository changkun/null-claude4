#!/usr/bin/env python3
"""Terminal-based cellular automaton simulator with multiple rulesets."""

import argparse
import copy
import curses
import os
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
    """Return list of .cells files in the patterns directory."""
    if not os.path.isdir(CELLS_DIR):
        return []
    return sorted(f for f in os.listdir(CELLS_DIR) if f.endswith(".cells"))


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


def run(stdscr, grid, speed, rule=None):
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

    rows, cols = len(grid), len(grid[0])
    generation = 0
    paused = False
    editing = False
    cursor_r, cursor_c = rows // 2, cols // 2
    delay = speed
    # Find current rule index for cycling
    rule_idx = -1
    for i, name in enumerate(RULE_NAMES):
        if RULES[name] is rule:
            rule_idx = i
            break

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        vis_rows = min(rows, max_y - 1)
        vis_cols = min(cols, (max_x - 1) // 2)

        # Draw grid
        for r in range(vis_rows):
            for c in range(vis_cols):
                age = grid[r][c]
                cell_str = "\u2588\u2588" if age else "  "
                if editing and r == cursor_r and c == cursor_c:
                    attr = curses.color_pair(4) if age else curses.color_pair(3)
                else:
                    attr = curses.color_pair(_age_color(age)) if age else curses.color_pair(1)
                try:
                    stdscr.addstr(r, c * 2, cell_str, attr)
                except curses.error:
                    pass

        # Status bar
        rule_label = rule.get("name", "Custom")
        if editing:
            status = f" EDITOR ({cursor_r},{cursor_c}) | Gen {generation} | {rule_label} | [arrows]move [enter/space]toggle [s]ave [l]oad [c]lear [R]ule [e]exit editor [q]uit"
        else:
            status = f" Gen {generation} | Delay {delay:.2f}s | {rule_label} | {'PAUSED' if paused else 'Running'} | [space]pause [e]dit [+/-]speed [r]andom [R]ule [n]ext [q]uit"
        try:
            stdscr.addstr(min(rows, max_y - 1), 0, status[:max_x - 1], curses.color_pair(2) | curses.A_REVERSE)
        except curses.error:
            pass

        stdscr.refresh()

        # Handle input
        key = stdscr.getch()
        if key == ord("q"):
            break

        if editing:
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
            elif key == ord("c"):
                for r2 in range(rows):
                    for c2 in range(cols):
                        grid[r2][c2] = 0
                generation = 0
            elif key == ord("s"):
                max_y, max_x = stdscr.getmaxyx()
                name = curses_input(stdscr, "Save as (name, no ext): ", max_y, max_x)
                if name:
                    os.makedirs(CELLS_DIR, exist_ok=True)
                    filepath = os.path.join(CELLS_DIR, name + ".cells")
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
                            grid = load_cells(filepath, rows, cols)
                            generation = 0
                            picking = False
                        elif pk == 27:
                            picking = False
                    stdscr.nodelay(True)
                else:
                    # No saved patterns; prompt for a file path
                    path = curses_input(stdscr, "Load file path: ", max_y, max_x)
                    if path and os.path.isfile(path):
                        grid = load_cells(path, rows, cols)
                        generation = 0
            elif key == ord("R"):
                if rule_idx >= 0:
                    rule_idx = (rule_idx + 1) % len(RULE_NAMES)
                    rule = RULES[RULE_NAMES[rule_idx]]
                else:
                    rule_idx = 0
                    rule = RULES[RULE_NAMES[0]]
            elif key == ord("e"):
                editing = False
        else:
            # Normal-mode controls
            if key == ord(" "):
                paused = not paused
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
            elif key == ord("R"):
                if rule_idx >= 0:
                    rule_idx = (rule_idx + 1) % len(RULE_NAMES)
                    rule = RULES[RULE_NAMES[rule_idx]]
                else:
                    rule_idx = 0
                    rule = RULES[RULE_NAMES[0]]
            elif key == ord("n") and paused:
                grid = step(grid, rule)
                generation += 1
            elif key == ord("e"):
                paused = True
                editing = True

        if not paused and not editing:
            grid = step(grid, rule)
            generation += 1

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
        help="Load a .cells file (path or name from ~/.life-patterns/)",
    )
    parser.add_argument(
        "--rule",
        type=str,
        default="life",
        help="Rule preset (" + ", ".join(RULE_NAMES) + ") or B/S notation (e.g. B36/S23). Default: life",
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

    grid = make_grid(args.rows, args.cols)
    if args.load:
        path = args.load
        # If it's just a name, look in the patterns directory
        if not os.path.isfile(path):
            candidate = os.path.join(CELLS_DIR, path)
            if not candidate.endswith(".cells"):
                candidate += ".cells"
            if os.path.isfile(candidate):
                path = candidate
        grid = load_cells(path, args.rows, args.cols)
    else:
        place_pattern(grid, args.pattern)
    curses.wrapper(lambda stdscr: run(stdscr, grid, args.speed, rule))


if __name__ == "__main__":
    main()
