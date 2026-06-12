# Toolbox

A terminal-based toolbox for macOS. Launches a curses TUI where you fuzzy-search and select utilities to run.

## Apps

### Steam Launcher
Fuzzy-search your Steam library and launch games natively (macOS) or via CrossOver/Wine. Reads game metadata from `appmanifest_*.acf` files in configured Steam library paths.

### Menu Icons (Tahoe)
Toggle menu action images globally (`defaults write -g`) or per app. Scans /Applications, /System/Applications, and ~/Applications for installed apps. Changes are saved to `config.json` and applied in parallel with a spinner.

### File Locksmith
Check which process is locking a file (preventing deletion). Runs `lsof` on the given path and displays the command, PID, and user of each locking process.

### Clean & Eject Drive
Scan an external volume for `._*` and `.DS_Store` files, remove them with a progress bar, then optionally eject the drive via `diskutil`.

## TUI Widgets

The `search.py` module provides a unified `select()` widget and utilities:

- **`select(items, title, search)`** — Unified widget. Items have a `type` (ITEM_TOGGLE, ITEM_BUTTON, ITEM_NEXT) determining their indicator and behavior. Always searchable. Returns `{"index": int, "states": [bool]}` or `None`.
  - Toggle: `[x]`/`[ ]` indicator, Space toggles, Enter confirms
  - Button: ` * ` indicator, Enter executes
  - Next: ` > ` indicator, Enter selects (caller handles navigation)
- **`spinner(tasks, title)`** — Runs callables in parallel via ThreadPoolExecutor with a curses spinner overlay.
- **`show_progress(items, title, callback)`** — Animated progress bar.
- **`fuzzy_select(options)`**, **`toggle_select(...)`**, **`button_select(...)`** — Backward-compat wrappers.

## Configuration

`config.json` stores user settings. The `config.py` module provides generic `get(key, default)` and `set(key, value)` functions. Tahoe icon toggle states are persisted under the `tahoe_states` key.

```json
{
  "steamapps_paths_macos": ["~/Library/Application Support/Steam/steamapps"],
  "steamapps_paths_crossover": ["~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps"],
  "tahoe_states": {
    "__global__": true,
    "com.apple.Safari": false
  }
}
```

## Running

```bash
python3 toolbox.py
```

Requires Python 3 with curses (built-in). macOS only.
