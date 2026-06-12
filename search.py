import curses

MAX_DISPLAY = 10

def match_positions(query, text):
    q = query.lower()
    t = text.lower()

    positions = []
    j = 0

    for i, c in enumerate(t):
        if j < len(q) and c == q[j]:
            positions.append(i)
            j += 1

    return positions if j == len(q) else None

def fuzzy_filter(query, options):
    results = []

    for idx, opt in enumerate(options):
        if not query:
            results.append((idx, opt, []))
            continue

        pos = match_positions(query, opt)
        if pos is not None:
            results.append((idx, opt, pos))

    results.sort(key=lambda x: (len(x[2]), len(x[1])))
    return results

def draw_highlight(stdscr, y, text, positions, selected):
    x = 0
    for i, ch in enumerate(text):
        attr = curses.A_BOLD if i in positions else curses.A_NORMAL
        if selected:
            attr |= curses.A_REVERSE
        stdscr.addstr(y, x, ch, attr)
        x += 1

def fzf(stdscr, options):
    curses.curs_set(1)

    query = ""
    selected = 0
    offset = 0

    while True:
        stdscr.clear()

        matches = fuzzy_filter(query, options)
        total = len(matches)

        stdscr.addstr(0, 0, f"Search: {query}")

        # ✅ EMPTY STATE HANDLING (KEY FIX)
        if total == 0:
            stdscr.addstr(2, 0, "No matches")
            stdscr.addstr(3, 0, "ESC to exit")

            key = stdscr.getch()

            if key == 27:  # ESC
                return None

            elif key in (curses.KEY_BACKSPACE, 127, 8):
                query = query[:-1]

            elif 32 <= key <= 126:
                query += chr(key)

            continue  # IMPORTANT: skip rest of loop safely

        # clamp selection
        selected = max(0, min(selected, total - 1))

        # scrolling
        if selected < offset:
            offset = selected
        elif selected >= offset + MAX_DISPLAY:
            offset = selected - MAX_DISPLAY + 1

        visible = matches[offset:offset + MAX_DISPLAY]

        stdscr.addstr(1, 0, f"{selected+1}/{total}")

        for i, (idx, text, pos) in enumerate(visible):
            real = offset + i
            is_sel = (real == selected)
            draw_highlight(stdscr, i + 2, text, pos, is_sel)

        key = stdscr.getch()

        if key in (10, 13):  # Enter
            return matches[selected][0]

        elif key == 27:  # ESC
            return None

        elif key in (curses.KEY_BACKSPACE, 127, 8):
            query = query[:-1]
            selected = 0
            offset = 0

        elif key == curses.KEY_DOWN:
            if selected < total - 1:
                selected += 1

        elif key == curses.KEY_UP:
            if selected > 0:
                selected -= 1

        elif 32 <= key <= 126:
            query += chr(key)
            selected = 0
            offset = 0

def fuzzy_select(options):
    return curses.wrapper(fzf, options)
