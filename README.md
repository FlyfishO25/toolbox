# Toolbox

A terminal-based toolbox for macOS. Launches a curses TUI where you fuzzy-search and select utilities to run.

## Apps

### Steam Launcher
Open common Steam tabs such as Store, Library, Friends, Downloads, Settings,
and Console, or fuzzy-search your Steam library and launch games natively
(macOS) or via CrossOver/Wine. Reads game metadata from `appmanifest_*.acf`
files in configured Steam library paths.

### Menu Icons (Tahoe) [Deprecated]
Toggle menu action images globally (`defaults write -g`) or per app. Scans
/Applications, /System/Applications, and ~/Applications for installed apps.
Changes are saved to `config.json` and shown with a progress bar while applying.

### Fix Apps
Repair downloaded or modified apps by removing the quarantine extended
attribute (`xattr -d -r com.apple.quarantine`) or ad-hoc code signing
(`codesign --force --deep --sign -`). The drag-only picker accepts one or more
files or apps from Finder, shows them in a removable queue, and uses sudo only
when a target is not writable.

### File Locksmith
Check which processes are locking one or more files. Runs `lsof` on every path
and displays the command, PID, user, and affected item for each lock.

### Clean & Eject Drive
Scan an external volume for `._*` and `.DS_Store` files with live scan progress,
remove them with a determinate progress bar, then optionally eject the drive via
`diskutil`. Read-only volumes skip cleanup entirely and are ejected directly.

### Utilities
Provides small maintenance actions. The initial action flushes the macOS DNS
cache after Y/N confirmation and administrator authorization.

### Bootstrapper
Runs a three-step setup with a separate Y/N prompt and `1/3` style progress for
each step: enable Touch ID for sudo, install Xcode Command Line Tools and accept
the Xcode license, then install Homebrew. Declined steps are skipped. If Apple
opens the Command Line Tools installer, dependent work is reported as pending or
skipped until Bootstrapper is run again.

## TUI Widgets

The `ui.py` module provides a unified `select()` widget and utilities:

All widgets share a sparse SourceHut-inspired header, active bands, cyan accents,
and consistent arrow-key navigation. Mouse users can click to select,
double-click to enter, right-click to go back, and use the scroll wheel to move
through lists. Ctrl-Q quits immediately from any screen.

- **`select(items, title, search)`** — Unified widget. Items have a `type` (ITEM_TOGGLE, ITEM_BUTTON, ITEM_NEXT) determining their indicator and behavior. Right/Enter selects and Left/Escape goes back. Returns `{"index": int, "states": [bool]}` or `None`.
  - Toggle: `[x]`/`[ ]` indicator, Space toggles, Right/Enter confirms
  - Button: ` · ` indicator, Right/Enter executes
  - Next: ` › ` indicator, Right/Enter selects (caller handles navigation)
- **`show_progress(items, title, callback)`** — Animated progress bar.
- **`show_activity(task, title, message, detail)`** — Indeterminate progress bar for tasks whose total work is not known in advance.
- **`alert(message, title)`** — Framed notice using the same navigation style.
- **`confirm(message, title)`** — Styled Y/N confirmation with keyboard and mouse support.
- **`file_drop(parser, title, hint)`** — Drag-only multi-item selection that automatically adds dropped paths to a removable queue.
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

## macOS App Bundle

Build a Finder-launchable app bundle:

```bash
python3 build_macos_app.py
```

The generated app is written to `dist/Toolbox.app`. Because Toolbox uses a
terminal UI, launching the app opens Terminal, runs the bundled Python sources
there, and closes that Terminal window when Toolbox exits successfully. If
Toolbox exits with an error, the window stays open so the traceback is visible.
The app stores its writable config at
`~/Library/Application Support/Toolbox/config.json`.
