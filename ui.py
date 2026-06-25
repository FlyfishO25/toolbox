import curses
import threading
import textwrap

MAX_DISPLAY = 10
HEADER_HEIGHT = 3

ITEM_TOGGLE = 0
ITEM_BUTTON = 1
ITEM_NEXT = 2
CTRL_Q = 17


class QuitRequested(Exception):
    """Raised when Ctrl-Q requests an immediate application exit."""


_active_screen = None


def _check_quit(key):
    if key in (CTRL_Q, "\x11"):
        raise QuitRequested


def _run_widget(callback):
    def _invoke(stdscr):
        try:
            return callback(stdscr)
        finally:
            # Animated progress widgets use nonblocking reads. Never allow that
            # mode to leak into the next interactive screen.
            stdscr.timeout(-1)

    if _active_screen is not None:
        return _invoke(_active_screen)
    return curses.wrapper(_invoke)


def run(callback):
    """Run a complete UI flow in one curses session."""
    global _active_screen

    if _active_screen is not None:
        return callback()

    def _run(stdscr):
        global _active_screen
        _active_screen = stdscr
        try:
            return callback()
        finally:
            _active_screen = None

    return curses.wrapper(_run)


def suspend(callback):
    """Temporarily restore the normal terminal for an interactive command."""
    if _active_screen is None:
        return callback()

    curses.def_prog_mode()
    curses.endwin()
    try:
        return callback()
    finally:
        curses.reset_prog_mode()
        _init_colors()
        _active_screen.touchwin()

# visual indicators per type
_TOGGLE_ON = "[x]"
_TOGGLE_OFF = "[ ]"
_BTN_MARK = " · "
_NEXT_MARK = " › "


def _init_colors():
    # cbreak mode leaves Ctrl-Q reserved for terminal flow control. Raw mode
    # lets the UI receive it; curses.wrapper restores the shell mode on exit.
    curses.raw()
    # Curses otherwise waits roughly a second before treating a standalone ESC
    # as Escape rather than the beginning of an arrow-key sequence.
    curses.set_escdelay(25)
    curses.start_color()
    curses.use_default_colors()
    try:
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        curses.mouseinterval(150)
    except curses.error:
        pass
    curses.init_pair(1, curses.COLOR_CYAN, -1)  # links and rules
    curses.init_pair(2, curses.COLOR_CYAN, -1)  # accent
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)  # active bands


def _mouse_event():
    try:
        _, x, y, _, state = curses.getmouse()
        return x, y, state
    except curses.error:
        return None


def _mouse_has(state, *names):
    return any(state & getattr(curses, name, 0) for name in names)


def _draw_frame(stdscr, title=""):
    h, w = stdscr.getmaxyx()
    _safe_addstr(stdscr, 0, 2, "toolbox", curses.color_pair(1) | curses.A_BOLD)
    if w > 34:
        _safe_addstr(stdscr, 0, w - 20, "terminal utilities", curses.A_DIM)

    _safe_addstr(stdscr, 1, 0, " " * max(0, w - 1), curses.color_pair(3))
    heading = f" ~toolbox / {title or 'home'} "
    _safe_addstr(stdscr, 1, 1, heading, curses.color_pair(3) | curses.A_BOLD)
    _safe_addstr(stdscr, 2, 0, "─" * max(0, w - 1), curses.color_pair(1))


def _format_status(parts):
    if isinstance(parts, str):
        return parts

    labels = []
    for part in parts:
        if isinstance(part, str):
            if part:
                labels.append(part)
            continue
        keys, label = part
        if not label:
            continue
        labels.append(f"{keys}: {label}" if keys else str(label))
    return "  ".join(labels)


def _draw_status(stdscr, parts):
    text = _format_status(parts)
    h, w = stdscr.getmaxyx()
    _safe_addstr(stdscr, h - 1, 0, " " * max(0, w - 1), curses.color_pair(3))
    _safe_addstr(stdscr, h - 1, 2, text, curses.color_pair(3))


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


def _toggle(items, types, states, index):
    """Toggle one item and recalculate states controlled by a global toggle."""
    new_state = not states[index]
    states[index] = new_state

    if not items[index].get("global"):
        return

    for child_index, child in enumerate(items):
        if child_index == index or types[child_index] != ITEM_TOGGLE:
            continue
        override = child.get("global_override")
        states[child_index] = new_state if override is None else bool(override)


# ── unified select widget ──────────────────────────────────────────────────────

def select(
    items,
    title="",
    search=True,
    back_label="back",
    action_label="select",
    toggle_label="toggle",
    quit_label="quit",
):
    """Unified select widget with optional fuzzy search.

    items: list of dicts with keys:
        "label" (str)
        "type"  (ITEM_TOGGLE | ITEM_BUTTON | ITEM_NEXT)
        "state" (bool, for toggles only)
        "global" (bool, marks a toggle as the global controller)
        "global_override" (bool | None, fixed child state during global changes)

    action_label/back_label/toggle_label/quit_label customize status text.

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
        stdscr.timeout(-1)

        query = ""
        sel = 0
        offset = 0

        while True:
            stdscr.erase()
            _draw_frame(stdscr, title)
            h, w = stdscr.getmaxyx()

            matches = _filter(query, items)
            total = len(matches)

            # ── search bar ──
            if search:
                _safe_addstr(
                    stdscr, 3, 2, "search", curses.color_pair(1) | curses.A_BOLD
                )
                _safe_addstr(
                    stdscr,
                    3,
                    10,
                    query or "type to filter",
                    0 if query else curses.A_DIM,
                )

            y_body = 5 if search else HEADER_HEIGHT

            # ── empty state ──
            if total == 0:
                _safe_addstr(stdscr, y_body + 1, 2, "No matches")
                _draw_status(
                    stdscr,
                    [
                        ("← left/esc", back_label),
                        ("ctrl-q", quit_label),
                    ],
                )
                if search:
                    stdscr.move(3, min(w - 2, 10 + len(query)))
                key = stdscr.getch()
                _check_quit(key)
                if key == curses.KEY_MOUSE:
                    event = _mouse_event()
                    if event and _mouse_has(
                        event[2], "BUTTON3_CLICKED", "BUTTON3_PRESSED"
                    ):
                        return None
                    continue
                if key in (curses.KEY_LEFT, 27):
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
                    _safe_addstr(
                        stdscr,
                        y,
                        1,
                        " " * max(0, w - 2),
                        curses.color_pair(3),
                    )
                    _safe_addstr(
                        stdscr, y, 2, line, curses.color_pair(3) | curses.A_BOLD
                    )
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
                parts.append(("space", toggle_label))
            parts.append(("→ right/enter", action_label))
            parts.append(("← left/esc", back_label))
            parts.append(("ctrl-q", quit_label))
            _draw_status(stdscr, parts)
            if search:
                stdscr.move(3, min(w - 2, 10 + len(query)))
            stdscr.refresh()

            # ── input ──
            key = stdscr.getch()
            _check_quit(key)

            if key == curses.KEY_MOUSE:
                event = _mouse_event()
                if not event:
                    continue
                _, mouse_y, mouse_state = event
                if _mouse_has(
                    mouse_state, "BUTTON3_CLICKED", "BUTTON3_PRESSED"
                ):
                    return None
                if _mouse_has(mouse_state, "BUTTON4_PRESSED"):
                    sel = max(0, sel - 1)
                    continue
                if _mouse_has(mouse_state, "BUTTON5_PRESSED"):
                    sel = min(total - 1, sel + 1)
                    continue

                clicked_row = mouse_y - (y_body + 1)
                if 0 <= clicked_row < len(visible):
                    sel = offset + clicked_row
                    if _mouse_has(mouse_state, "BUTTON1_DOUBLE_CLICKED"):
                        orig, _, _ = matches[sel]
                        return {"index": orig, "states": list(states)}
                continue

            if key in (curses.KEY_RIGHT, 10, 13):  # Enter
                orig, _, _ = matches[sel]
                itype = types[orig]
                if itype == ITEM_TOGGLE:
                    # confirm all toggle changes
                    return {"index": orig, "states": list(states)}
                else:
                    return {"index": orig, "states": list(states)}

            elif key in (curses.KEY_LEFT, 27):  # Back
                return None

            elif key == ord(" "):  # Space
                orig, _, _ = matches[sel]
                if types[orig] == ITEM_TOGGLE:
                    _toggle(items, types, states, orig)

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

    return _run_widget(_run)


# ── message widgets ───────────────────────────────────────────────────────────

def alert(message, title="Notice"):
    """Display a framed message; return True to continue or False to go back."""

    def _run(stdscr):
        _init_colors()
        curses.curs_set(0)
        stdscr.timeout(-1)

        while True:
            stdscr.erase()
            _draw_frame(stdscr, title)
            h, w = stdscr.getmaxyx()

            lines = []
            for paragraph in str(message).splitlines() or [""]:
                lines.extend(textwrap.wrap(paragraph, max(1, w - 8)) or [""])

            start_y = max(HEADER_HEIGHT + 1, (h - len(lines)) // 2)
            for index, line in enumerate(lines):
                _safe_addstr(stdscr, start_y + index, 4, line)

            _draw_status(
                stdscr,
                [
                    ("← left/esc", "back"),
                    ("→ right/enter", "continue"),
                    ("ctrl-q", "quit"),
                ],
            )
            stdscr.refresh()

            key = stdscr.getch()
            _check_quit(key)
            if key == curses.KEY_MOUSE:
                event = _mouse_event()
                if not event:
                    continue
                if _mouse_has(
                    event[2], "BUTTON3_CLICKED", "BUTTON3_PRESSED"
                ):
                    return False
                if _mouse_has(
                    event[2],
                    "BUTTON1_CLICKED",
                    "BUTTON1_DOUBLE_CLICKED",
                    "BUTTON1_PRESSED",
                ):
                    return True
                continue
            if key in (curses.KEY_RIGHT, 10, 13):
                return True
            if key in (curses.KEY_LEFT, 27):
                return False

    return _run_widget(_run)


# ── confirmation widget ──────────────────────────────────────────────────────

def confirm(message, title="Confirm"):
    """Ask a styled yes/no question. Y/Right/Enter confirms."""

    def _run(stdscr):
        _init_colors()
        curses.curs_set(0)
        stdscr.timeout(-1)

        while True:
            stdscr.erase()
            _draw_frame(stdscr, title)
            h, w = stdscr.getmaxyx()

            lines = []
            for paragraph in str(message).splitlines() or [""]:
                lines.extend(textwrap.wrap(paragraph, max(1, w - 8)) or [""])
            start_y = max(HEADER_HEIGHT + 1, (h - len(lines)) // 2)
            for index, line in enumerate(lines):
                _safe_addstr(stdscr, start_y + index, 4, line)

            _draw_status(
                stdscr,
                [
                    ("y / right / enter", "yes"),
                    ("n / left / esc", "no"),
                    ("ctrl-q", "quit"),
                ],
            )
            stdscr.refresh()

            key = stdscr.getch()
            _check_quit(key)
            if key == curses.KEY_MOUSE:
                event = _mouse_event()
                if not event:
                    continue
                if _mouse_has(
                    event[2], "BUTTON3_CLICKED", "BUTTON3_PRESSED"
                ):
                    return False
                if _mouse_has(
                    event[2],
                    "BUTTON1_CLICKED",
                    "BUTTON1_DOUBLE_CLICKED",
                    "BUTTON1_PRESSED",
                ):
                    return True
                continue
            if key in (ord("y"), ord("Y"), curses.KEY_RIGHT, 10, 13):
                return True
            if key in (ord("n"), ord("N"), curses.KEY_LEFT, 27):
                return False

    return _run_widget(_run)


# ── drag-only file selection ──────────────────────────────────────────────────

def file_drop(parser, title="Select Files", hint="Drag files or folders here"):
    """Collect Finder-dropped paths into a removable list.

    Dropped paths are added automatically. Right/Enter confirms the list,
    Left/Escape goes back, and Delete/Backspace removes the selected item.
    """

    def _run(stdscr):
        _init_colors()
        curses.curs_set(0)
        stdscr.timeout(-1)

        items = []
        pending = ""
        selected = 0
        offset = 0
        notice = ""

        def commit_pending():
            nonlocal pending, selected, notice
            if not pending:
                return
            try:
                dropped = parser(pending)
            except (TypeError, ValueError):
                dropped = []
            pending = ""
            added = 0
            for item in dropped:
                if item not in items:
                    items.append(item)
                    added += 1
            selected = max(0, len(items) - 1)
            notice = f"Added {added} item{'s' if added != 1 else ''}."

        while True:
            stdscr.erase()
            _draw_frame(stdscr, title)
            h, w = stdscr.getmaxyx()

            _safe_addstr(stdscr, 4, 2, hint, curses.A_BOLD)
            instruction = (
                "receiving dropped items…"
                if pending
                else "drop one or more items into this window"
            )
            _safe_addstr(stdscr, 5, 2, instruction, curses.A_DIM)

            if not items:
                _safe_addstr(stdscr, 8, 2, "No items selected", curses.A_DIM)
            else:
                selected = max(0, min(selected, len(items) - 1))
                if selected < offset:
                    offset = selected
                elif selected >= offset + MAX_DISPLAY:
                    offset = selected - MAX_DISPLAY + 1

                _safe_addstr(
                    stdscr,
                    7,
                    2,
                    f"{len(items)} item{'s' if len(items) != 1 else ''}",
                    curses.color_pair(1),
                )
                for visible_index, item in enumerate(
                    items[offset:offset + MAX_DISPLAY]
                ):
                    item_index = offset + visible_index
                    y = 8 + visible_index
                    if y >= h - 1:
                        break
                    label = str(item)
                    if item_index == selected:
                        _safe_addstr(
                            stdscr,
                            y,
                            1,
                            " " * max(0, w - 2),
                            curses.color_pair(3),
                        )
                        _safe_addstr(
                            stdscr,
                            y,
                            2,
                            f"> ·  {label}",
                            curses.color_pair(3) | curses.A_BOLD,
                        )
                    else:
                        _safe_addstr(stdscr, y, 2, f"  ·  {label}")

            if notice:
                _safe_addstr(stdscr, h - 3, 2, notice, curses.A_DIM)

            _draw_status(
                stdscr,
                [
                    ("→ right/enter", "confirm"),
                    ("← left/esc", "back"),
                    ("delete", "remove"),
                    ("ctrl-q", "quit"),
                ],
            )
            stdscr.refresh()

            # A Finder drop arrives as a burst of characters. Once the burst
            # has been quiet briefly, parse and add it without another prompt.
            stdscr.timeout(75 if pending else -1)
            try:
                key = stdscr.get_wch()
            except curses.error:
                commit_pending()
                continue
            _check_quit(key)

            if key == curses.KEY_MOUSE:
                event = _mouse_event()
                if not event:
                    continue
                _, mouse_y, mouse_state = event
                if _mouse_has(
                    mouse_state, "BUTTON3_CLICKED", "BUTTON3_PRESSED"
                ):
                    return None
                if _mouse_has(mouse_state, "BUTTON4_PRESSED") and items:
                    selected = max(0, selected - 1)
                    continue
                if _mouse_has(mouse_state, "BUTTON5_PRESSED") and items:
                    selected = min(len(items) - 1, selected + 1)
                    continue

                clicked_row = mouse_y - 8
                visible_count = min(MAX_DISPLAY, max(0, len(items) - offset))
                if 0 <= clicked_row < visible_count:
                    selected = offset + clicked_row
                    if _mouse_has(mouse_state, "BUTTON1_DOUBLE_CLICKED"):
                        commit_pending()
                        return list(items)
                continue

            if key in (curses.KEY_LEFT, "\x1b", 27):
                return None
            if key == curses.KEY_RIGHT:
                commit_pending()
                if items:
                    return list(items)
                notice = "Drag at least one item here first."
                continue
            if key in ("\n", "\r", curses.KEY_ENTER):
                commit_pending()
                if items:
                    return list(items)
                notice = "Drag at least one item here first."
                continue
            if key == curses.KEY_DOWN and items:
                selected = min(len(items) - 1, selected + 1)
                continue
            if key == curses.KEY_UP and items:
                selected = max(0, selected - 1)
                continue
            if key in (curses.KEY_DC, curses.KEY_BACKSPACE, "\x7f", "\b"):
                if pending:
                    pending = ""
                    notice = "Pending drop discarded."
                elif items:
                    removed = items.pop(selected)
                    selected = min(selected, max(0, len(items) - 1))
                    notice = f"Removed {removed}."
                continue
            if isinstance(key, str) and key.isprintable():
                pending += key
                notice = ""

    return _run_widget(_run)


# ── indeterminate progress ────────────────────────────────────────────────────

def show_activity(task, title="Working", message="Please wait", detail=None):
    """Run task in a worker while showing an animated, indeterminate progress bar."""
    result = []
    errors = []
    done = threading.Event()

    def _work():
        try:
            result.append(task())
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    def _run(stdscr):
        _init_colors()
        curses.curs_set(0)
        stdscr.nodelay(True)
        worker = threading.Thread(target=_work, daemon=True)
        worker.start()
        frame = 0

        first_frame = True
        while first_frame or not done.is_set():
            first_frame = False
            stdscr.erase()
            _draw_frame(stdscr, title)
            h, w = stdscr.getmaxyx()

            bar_width = max(3, min(w - 10, 50))
            pulse_width = max(2, bar_width // 5)
            travel = max(1, bar_width - pulse_width)
            position = frame % (travel * 2)
            if position > travel:
                position = travel * 2 - position
            bar = (
                "[" + "░" * position + "█" * pulse_width
                + "░" * (bar_width - position - pulse_width) + "]"
            )

            _safe_addstr(stdscr, h // 2 - 1, 4, message, curses.A_BOLD)
            _safe_addstr(stdscr, h // 2, 4, bar, curses.color_pair(2))
            if detail:
                detail_text = detail() if callable(detail) else detail
                _safe_addstr(stdscr, h // 2 + 1, 4, detail_text)
            _draw_status(stdscr, [(None, "working…"), ("ctrl-q", "quit")])
            stdscr.refresh()

            key = stdscr.getch()
            if key != -1:
                _check_quit(key)

            if done.is_set():
                break
            done.wait(0.06)
            frame += 1

        worker.join()

    _run_widget(_run)

    if errors:
        raise errors[0]
    return result[0] if result else None


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
        stdscr.nodelay(True)
        spin = _spinner_gen()

        for i, item in enumerate(items):
            stdscr.erase()
            _draw_frame(stdscr, title)
            h, w = stdscr.getmaxyx()

            bar_w = max(3, min(w - 10, 50))
            filled = int(((i + 1) / total) * bar_w) if total > 0 else bar_w
            bar = "[" + "█" * filled + "░" * (bar_w - filled) + "]"
            pct = int(((i + 1) / total) * 100) if total > 0 else 100

            _safe_addstr(stdscr, h // 2 - 1, 4, f"{next(spin)} {item}")
            _safe_addstr(stdscr, h // 2, 4, bar, curses.color_pair(2))
            _safe_addstr(stdscr, h // 2 + 1, 4, f"{i + 1}/{total}  {pct}%")
            _draw_status(stdscr, [(None, "working…"), ("ctrl-q", "quit")])
            stdscr.refresh()

            key = stdscr.getch()
            if key != -1:
                _check_quit(key)

            if callback:
                callback(item)

            key = stdscr.getch()
            if key != -1:
                _check_quit(key)

    _run_widget(_run)
