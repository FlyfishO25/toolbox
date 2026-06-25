"""
Steam Game Launcher
Launches Steam games natively on macOS or via CrossOver.
"""

import os
import stat
import tempfile
import subprocess
import config
import ui
import utils

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


def _load_games():
    return utils.list_steam_games(
        config.get_steam_paths_macos(),
        config.get_steam_paths_crossover(),
    )


def launch_game():
    games = _load_games()
    choice = ui.choose(
        [label for label, _ in STEAM_TABS]
        + [f"{name} ({platform})" for name, _, platform in games],
        title="Steam Launcher",
    )
    if choice is None:
        return

    if choice < len(STEAM_TABS):
        launch_crossover_url(STEAM_TABS[choice][1])
        return

    _, appid, platform = games[choice - len(STEAM_TABS)]
    launcher = launch_mac_game if platform == "macOS" else launch_crossover_game
    launcher(appid)
