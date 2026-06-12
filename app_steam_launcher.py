"""
Steam Game Launcher
Launches Steam games natively on macOS or via CrossOver.
"""

import os
import stat
import tempfile
import subprocess
import config
import search
import utils

# init
steam_paths_macos = config.get_steam_paths_macos()
steam_paths_crossover = config.get_steam_paths_crossover()
steam_games = utils.list_steam_games(steam_paths_macos, steam_paths_crossover)

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
wine --cx-app steam.exe "steam://rungameid/{game_id}"
"""


def launch_mac_game(game_id: int):
    subprocess.Popen(
        ["open", f"steam://rungameid/{game_id}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def launch_crossover_game(game_id: int):
    script = CROSSOVER_SCRIPT_TEMPLATE.format(game_id=game_id)
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

def launch_game():
    # build options
    options=[]

    for item in steam_games:
        options.append("{0}({1})".format(item[0], item[2]))

    print(options)

    choice = search.fuzzy_select(options)
    print("Selected:", choice)
    if choice == None:
        return

    if steam_games[choice][2] == 'macOS':
        launch_mac_game(steam_games[choice][1])
    else:
        launch_crossover_game(steam_games[choice][1])

