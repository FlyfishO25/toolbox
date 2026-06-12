import curses

MAX_DISPLAY = 10

ITEM_TOGGLE = 0
ITEM_BUTTON = 1
ITEM_NEXT = 2

# visual indicators per type
_TOGGLE_ON = "[x]"
_TOGGLE_OFF = "[ ]"
_BTN_MARK = " * "
_NEXT_MARK = " > "


def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)   # border
    curses.init_pair(2, curses.COLOR_GREEN, -1)   # accent


def _draw_frame(stdscr, title=""):
    h, w = stdscr.getmaxyx()
    stdscr.attron(curses.color_pair(1))
    stdscr.border(0)
    if title:
        stdscr.addstr(0, 2, f" {title} ")
    stdscr.attroff(curses.color_pair(1))


def _draw_status(stdscr, text):
    h, w = stdscr.getmaxyx()
    stdscr.attron(curses.color_pair(1))
    stdscr.addstr(h - 1, 2, f" {text} "[:w-3])
    stdscr.attroff(curses.color_pair(1))


def _safe_addstr(stdscr, y, x, text, attr=0):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return
    text = str(text)[:w - x - 1]
    if text:
        stdscr.addstr(y, x, text, attr)


def _spinner_gen():
    frames = ["|", "/", "\\", "-"]
    i = 0
    while True:
        yield frames[i % 4]
        i += 1


# ── fuzzy match ────────────────────────────────────────────────────────────────

def _match_positions(query, text):
    q = query.lower()
    t = text.lower()
    pos = []
    j = 0
    for i, ch in enumerate(t):
        if j < len(q) and ch == q[j]:
            pos.append(i)
            j += 1
    return pos if j == len(q) else None


def _filter(query, items):
    results = []
    for idx, item in enumerate(items):
        label = item["label"]
        if not query:
            results.append((idx, label, []))
            continue
        mp = _match_positions(query, label)
        if mp is not None:
            results.append((idx, label, mp))
    results.sort(key=lambda x: x[1].lower())
    return results


# ── unified select widget ──────────────────────────────────────────────────────

def select(items, title="", search=True):
    """Unified select widget with search.

    items: list of dicts with keys:
        "label" (str)
        "type"  (ITEM_TOGGLE | ITEM_BUTTON | ITEM_NEXT)
        "state" (bool, for toggles only)

    Returns dict{"index": int, "states": list[bool]} or None on ESC.
    """
    if not items:
        return None

    states = [it.get("state", False) for it in items]
    types = [it.get("type", ITEM_BUTTON) for it in items]

    def _run(stdscr):
        nonlocal states
        _init_colors()
        curses.curs_set(1 if search else 0)

        query = ""
        sel = 0
        offset = 0

        while True:
            stdscr.clear()
            _draw_frame(stdscr, title)
            h, w = stdscr.getmaxyx()

            matches = _filter(query, items)
            total = len(matches)

            # ── search bar ──
            if search:
                _safe_addstr(stdscr, 1, 2, f"Search: {query}", curses.A_BOLD)

            y_body = 2 if search else 1

            # ── empty state ──
            if total == 0:
                _safe_addstr(stdscr, y_body + 1, 2, "No matches")
                _draw_status(stdscr, "ESC: cancel")
                key = stdscr.getch()
                if key == 27:
                    return None
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    query = query[:-1]
                elif 32 <= key <= 126:
                    query += chr(key)
                continue

            # ── clamp selection ──
            sel = max(0, min(sel, total - 1))
            if sel < offset:
                offset = sel
            elif sel >= offset + MAX_DISPLAY:
                offset = sel - MAX_DISPLAY + 1

            _safe_addstr(stdscr, y_body, 2, f"{sel + 1}/{total}", curses.color_pair(2))

            visible = matches[offset : offset + MAX_DISPLAY]

            has_toggle = any(types[orig] == ITEM_TOGGLE for orig, _, _ in matches)

            for i, (orig, label, hl_pos) in enumerate(visible):
                real = offset + i
                is_sel = real == sel
                y = y_body + 1 + i
                if y >= h - 1:
                    break

                itype = types[orig]

                # indicator
                if itype == ITEM_TOGGLE:
                    ind = _TOGGLE_ON if states[orig] else _TOGGLE_OFF
                elif itype == ITEM_NEXT:
                    ind = _NEXT_MARK
                else:
                    ind = _BTN_MARK

                cursor = ">" if is_sel else " "

                if is_sel:
                    line = f"{cursor}{ind} {label}"
                    _safe_addstr(stdscr, y, 2, line, curses.A_REVERSE)
                else:
                    # draw with match highlights
                    x = 2
                    _safe_addstr(stdscr, y, x, f"{cursor}{ind} ")
                    x += len(cursor) + len(ind) + 1
                    for ci, ch in enumerate(label):
                        a = curses.A_BOLD if ci in hl_pos else curses.A_NORMAL
                        _safe_addstr(stdscr, y, x, ch, a)
                        x += 1

            # ── status bar ──
            parts = []
            if has_toggle:
                parts.append("SPACE: toggle")
            parts.append("ENTER: select")
            parts.append("ESC: cancel")
            _draw_status(stdscr, "  ".join(parts))

            # ── input ──
            key = stdscr.getch()

            if key in (10, 13):  # Enter
                orig, _, _ = matches[sel]
                itype = types[orig]
                if itype == ITEM_TOGGLE:
                    # confirm all toggle changes
                    return {"index": orig, "states": list(states)}
                else:
                    return {"index": orig, "states": list(states)}

            elif key == 27:  # ESC
                return None

            elif key == ord(" "):  # Space
                orig, _, _ = matches[sel]
                if types[orig] == ITEM_TOGGLE:
                    states[orig] = not states[orig]

            elif key in (curses.KEY_BACKSPACE, 127, 8):
                query = query[:-1]
                sel = 0
                offset = 0

            elif key == curses.KEY_DOWN:
                if sel < total - 1:
                    sel += 1

            elif key == curses.KEY_UP:
                if sel > 0:
                    sel -= 1

            elif 32 <= key <= 126:
                query += chr(key)
                sel = 0
                offset = 0

    return curses.wrapper(_run)


# ── backward-compat wrappers ───────────────────────────────────────────────────

def fuzzy_select(options):
    """Backward compat: select from string list, returns index or None."""
    items = [{"label": opt, "type": ITEM_BUTTON} for opt in options]
    r = select(items, title="Search")
    return r["index"] if r else None


def toggle_select(options, states=None, title=""):
    """Backward compat: multi-toggle, returns list[bool] or None."""
    if states is None:
        states = [False] * len(options)
    items = [{"label": opt, "type": ITEM_TOGGLE, "state": s}
             for opt, s in zip(options, states)]
    r = select(items, title=title, search=True)
    return r["states"] if r else None


def button_select(options, title=""):
    """Backward compat: single-select button list, returns index or None."""
    items = [{"label": opt, "type": ITEM_BUTTON} for opt in options]
    r = select(items, title=title, search=True)
    return r["index"] if r else None


# ── progress bar ───────────────────────────────────────────────────────────────

def show_progress(items, title="Progress", callback=None):
    """Show a progress bar while processing items. Calls callback(item) for each."""
    total = len(items)

    def _run(stdscr):
        _init_colors()
        curses.curs_set(0)
        spin = _spinner_gen()

        for i, item in enumerate(items):
            stdscr.clear()
            _draw_frame(stdscr, title)
            h, w = stdscr.getmaxyx()

            bar_w = min(w - 8, 50)
            filled = int(((i + 1) / total) * bar_w) if total > 0 else bar_w
            bar = "[" + "=" * filled + " " * (bar_w - filled) + "]"
            pct = int(((i + 1) / total) * 100) if total > 0 else 100

            _safe_addstr(stdscr, h // 2 - 1, 4, f"{next(spin)} {item}")
            _safe_addstr(stdscr, h // 2, 4, bar, curses.A_BOLD)
            _safe_addstr(stdscr, h // 2 + 1, 4, f"{i + 1}/{total}  {pct}%")
            stdscr.refresh()

            if callback:
                callback(item)

        curses.napms(500)

    curses.wrapper(_run)


