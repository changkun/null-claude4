#!/usr/bin/env python3
"""Terminal-based Conway's Game of Life simulator."""

import argparse
import copy
import curses
import time

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


def step(grid):
    rows, cols = len(grid), len(grid[0])
    new = make_grid(rows, cols)
    for r in range(rows):
        for c in range(cols):
            n = _neighbours(grid, r, c, rows, cols)
            if grid[r][c]:
                new[r][c] = 1 if n in (2, 3) else 0
            else:
                new[r][c] = 1 if n == 3 else 0
    return new


def _neighbours(grid, r, c, rows, cols):
    count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = (r + dr) % rows, (c + dc) % cols
            count += grid[nr][nc]
    return count


def run(stdscr, grid, speed):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_WHITE, -1)

    rows, cols = len(grid), len(grid[0])
    generation = 0
    paused = False
    delay = speed

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # Draw grid
        for r in range(min(rows, max_y - 1)):
            line = ""
            for c in range(min(cols, (max_x - 1) // 2)):
                line += "\u2588\u2588" if grid[r][c] else "  "
            try:
                stdscr.addstr(r, 0, line, curses.color_pair(1) if grid[r][0] or True else 0)
            except curses.error:
                pass

        # Status bar
        status = f" Gen {generation} | Delay {delay:.2f}s | {'PAUSED' if paused else 'Running'} | [space]pause [+/-]speed [r]andom [q]uit"
        try:
            stdscr.addstr(min(rows, max_y - 1), 0, status[:max_x - 1], curses.color_pair(2) | curses.A_REVERSE)
        except curses.error:
            pass

        stdscr.refresh()

        # Handle input
        key = stdscr.getch()
        if key == ord("q"):
            break
        elif key == ord(" "):
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
        elif key == ord("n") and paused:
            grid = step(grid)
            generation += 1

        if not paused:
            grid = step(grid)
            generation += 1

        time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description="Conway's Game of Life in the terminal")
    parser.add_argument("--rows", type=int, default=40, help="Grid height (default: 40)")
    parser.add_argument("--cols", type=int, default=80, help="Grid width (default: 80)")
    parser.add_argument("--speed", type=float, default=0.1, help="Delay between generations in seconds (default: 0.1)")
    parser.add_argument(
        "--pattern",
        choices=list(PATTERNS.keys()),
        default="glider",
        help="Starter pattern (default: glider)",
    )
    args = parser.parse_args()

    grid = make_grid(args.rows, args.cols)
    place_pattern(grid, args.pattern)
    curses.wrapper(lambda stdscr: run(stdscr, grid, args.speed))


if __name__ == "__main__":
    main()
