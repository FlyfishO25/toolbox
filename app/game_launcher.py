import os
import subprocess
import stat
import tempfile
from pathlib import Path

import config
import ui
import utils

TITLE = "Game Launcher"
CUSTOM_EXECUTABLES_CONFIG_KEY = "game_executables"
ACTION_ADD_CUSTOM = "add_custom"
ACTION_DELETE_CUSTOM = "delete_custom"
ACTION_CUSTOM_EXECUTABLE = "custom_executable"
ACTION_STEAM_TAB = "steam_tab"
ACTION_STEAM_GAME = "steam_game"

STEAM_TABS = [
    ("Steam: Main (CrossOver)", "steam://open/main"),
    ("Steam: Store (CrossOver)", "steam://open/store"),
    ("Steam: Library (CrossOver)", "steam://open/games"),
    ("Steam: Friends (CrossOver)", "steam://open/friends"),
    ("Steam: Downloads (CrossOver)", "steam://open/downloads"),
    ("Steam: Settings (CrossOver)", "steam://open/settings"),
]

# ── CrossOver config ───────────────────────────────────────────────────────────
CROSSOVER_SCRIPT_TEMPLATE = """\
#!/bin/bash
export PYTHONPATH="/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/lib/python"
export COMMAND_MODE="unix2003"
export XPC_SERVICE_NAME="application.com.codeweavers.CrossOver.94969528.94981241"
export CX_APP_BUNDLE_PATH="/Applications/CrossOver.app"
export CX_BOTTLE_PATH="$HOME/Library/Application Support/CrossOver/Bottles"
export CX_MANAGED_BOTTLE_PATH="/Library/Application Support/CrossOver/Bottles"
export __CFBundleIdentifier="com.codeweavers.CrossOver"
export CX_ROOT="/Applications/CrossOver.app/Contents/SharedSupport/CrossOver"
export XPC_FLAGS="0x0"
export http_proxy="http://127.0.0.1:7897/"
export CX_BOTTLE="Steam"
export PATH="/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin:$PATH"
cd "$HOME/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam"
wine --cx-app steam.exe "{steam_url}"
"""


def launch_mac_url(url: str):
    subprocess.Popen(
        ["open", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_mac_game(game_id):
    launch_mac_url(f"steam://rungameid/{game_id}")


def launch_crossover_url(steam_url: str):
    script = CROSSOVER_SCRIPT_TEMPLATE.format(steam_url=steam_url)
    tmp = tempfile.NamedTemporaryFile(
        suffix=".sh", delete=False, mode="w", prefix="toolbox-steam-"
    )
    tmp.write(script)
    tmp.close()
    os.chmod(tmp.name, os.stat(tmp.name).st_mode | stat.S_IEXEC)
    subprocess.Popen(
        ["/bin/bash", tmp.name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_crossover_game(game_id):
    launch_crossover_url(f"steam://rungameid/{game_id}")


def _dedupe_paths(paths):
    seen = set()
    deduped = []
    for path in paths:
        normalized = str(Path(path).expanduser())
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def _load_custom_executables():
    values = config.get(CUSTOM_EXECUTABLES_CONFIG_KEY, [])
    if not isinstance(values, list):
        return []

    paths = []
    for value in values:
        if not isinstance(value, str):
            continue
        path = Path(value).expanduser()
        if path.exists():
            paths.append(str(path))
    return _dedupe_paths(paths)


def _save_custom_executables(paths):
    config.set(CUSTOM_EXECUTABLES_CONFIG_KEY, _dedupe_paths(paths))


def _custom_executable_label(path):
    path = Path(path)
    name = path.stem if path.suffix.lower() == ".app" else path.name
    return f"Custom: {name}"


def _custom_executable_command(path):
    path = Path(path).expanduser()
    if path.is_file() and os.access(path, os.X_OK):
        return [str(path)], str(path.parent)
    return ["open", str(path)], None


def launch_custom_executable(path):
    path = Path(path).expanduser()
    if not path.exists():
        ui.alert(f"This executable no longer exists:\n{path}", title="Missing Game")
        return False

    command, cwd = _custom_executable_command(path)
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if cwd:
        kwargs["cwd"] = cwd

    try:
        subprocess.Popen(command, **kwargs)
    except OSError as error:
        ui.alert(f"Could not launch:\n{path}\n\n{error}", title="Launch Failed")
        return False
    return True


def _add_custom_executables():
    paths = ui.file_drop(
        parser=utils.parse_paths,
        title="Add Game Executable",
        hint="Drag one or more game apps or executables here",
    )
    if paths is None:
        return

    missing = utils.missing_paths(paths)
    if missing:
        ui.alert(utils.missing_paths_message(missing), title="Invalid Paths")
        return

    current = _load_custom_executables()
    saved = _dedupe_paths([*current, *paths])
    added = len(saved) - len(current)
    _save_custom_executables(saved)

    if added:
        message = f"Saved {added} custom executable{'s' if added != 1 else ''}."
    else:
        message = "No new custom executables were saved."
    ui.alert(message, title=TITLE)


def _delete_custom_executable(path):
    current = _load_custom_executables()
    normalized = str(Path(path).expanduser())
    saved = [candidate for candidate in current if candidate != normalized]

    if len(saved) == len(current):
        ui.alert("That custom game is no longer saved.", title=TITLE)
        return

    _save_custom_executables(saved)
    name = _custom_executable_label(path).replace("Custom: ", "", 1)
    ui.alert(
        f"Removed {name} from Game Launcher.\n\nThe file was not deleted.",
        title=TITLE,
    )


def _load_games():
    return utils.list_steam_games(
        config.get_steam_paths_macos(),
        config.get_steam_paths_crossover(),
    )


def _build_launcher_actions(games, custom_executables):
    actions = [
        (
            _custom_executable_label(path),
            ACTION_CUSTOM_EXECUTABLE,
            path,
        )
        for path in custom_executables
    ]
    actions.extend((label, ACTION_STEAM_TAB, url) for label, url in STEAM_TABS)
    actions.extend(
        (
            f"{name} ({platform})",
            ACTION_STEAM_GAME,
            (appid, platform),
        )
        for name, appid, platform in games
    )
    return actions


def launch_game():
    while True:
        games = _load_games()
        custom_executables = _load_custom_executables()
        actions = _build_launcher_actions(games, custom_executables)
        result = ui.select(
            ui.button_items([label for label, _, _ in actions]),
            title=TITLE,
            shortcuts=[
                {
                    "key": ui.CTRL_A,
                    "keys": "ctrl-a",
                    "label": "add",
                    "name": ACTION_ADD_CUSTOM,
                },
                {
                    "key": ui.CTRL_D,
                    "keys": "ctrl-d",
                    "label": "delete",
                    "name": ACTION_DELETE_CUSTOM,
                },
            ],
        )
        if result is None:
            return

        if result.get("shortcut") == ACTION_ADD_CUSTOM:
            _add_custom_executables()
            continue

        if result.get("shortcut") == ACTION_DELETE_CUSTOM:
            index = result.get("index")
            if index is None or index >= len(actions):
                ui.alert("Select a custom game to delete.", title=TITLE)
                continue

            _, action, payload = actions[index]
            if action != ACTION_CUSTOM_EXECUTABLE:
                ui.alert(
                    "Only custom games can be removed from Game Launcher.\n\n"
                    "Steam games stay in your Steam library.",
                    title=TITLE,
                )
                continue

            _delete_custom_executable(payload)
            continue

        _, action, payload = actions[result["index"]]
        if action == ACTION_CUSTOM_EXECUTABLE:
            launch_custom_executable(payload)
            return

        if action == ACTION_STEAM_TAB:
            launch_crossover_url(payload)
            return

        appid, platform = payload
        launcher = launch_mac_game if platform == "macOS" else launch_crossover_game
        launcher(appid)
        return
