#! /usr/bin/env python

import shlex
from pathlib import Path


def parse_paths(raw):
    """Parse one or more shell-escaped paths, as produced by Finder dragging."""
    raw = raw.strip()
    if not raw:
        return []

    try:
        parts = shlex.split(raw)
    except ValueError:
        parts = [raw]

    paths = [Path(part).expanduser() for part in parts]

    # Preserve convenient manual entry of one existing, unquoted path that
    # contains spaces. Finder-dragged paths are escaped and do not need this.
    if len(paths) > 1:
        joined = Path(" ".join(parts)).expanduser()
        if joined.exists() and not all(path.exists() for path in paths):
            return [joined]

    return paths

def list_steam_games(steam_paths_macos, steam_paths_crossover):
    res = []

    # print("Getting appids")
    for path in steam_paths_macos:
        path = Path(path)
        # Process each application manifest file to extract game info
        # Steam stores game metadata in appmanifest_[AppID].acf files
        for game in path.glob("./appmanifest_*.acf"):
            appid = ""
            gamename = ""
            # Reads each appmanifest file line by line to extract the AppID and game name
            # These files use a custom Valve format (VDF) that we parse with simple string operations
            if Path.is_file(game):
                with open(game, 'r') as f:
                    for line in f.readlines():
                        # Extract the AppID from the manifest (unique identifier for each game)
                        # This is used to locate the game's prefix directory
                        if '"appid"' in line:
                            parts = line.split('"')
                            appid = parts[3]
                        # Extract the game name from the manifest
                        # This will be used as the symlink name for easy identification
                        if '"name"' in line:
                            parts = line.split('"')
                            gamename = parts[3]
            # print(f"--------------\nFound: {gamename} -- {appid}")
            res.append(tuple((gamename, appid, "macOS")))

    for path in steam_paths_crossover:
        path = Path(path)
        # Process each application manifest file to extract game info
        # Steam stores game metadata in appmanifest_[AppID].acf files
        for game in path.glob("./appmanifest_*.acf"):
            appid = ""
            gamename = ""
            # Reads each appmanifest file line by line to extract the AppID and game name
            # These files use a custom Valve format (VDF) that we parse with simple string operations
            if Path.is_file(game):
                with open(game, 'r') as f:
                    for line in f.readlines():
                        # Extract the AppID from the manifest (unique identifier for each game)
                        # This is used to locate the game's prefix directory
                        if '"appid"' in line:
                            parts = line.split('"')
                            appid = parts[3]
                            # Extract the game name from the manifest
                            # This will be used as the symlink name for easy identification
                        if '"name"' in line:
                            parts = line.split('"')
                            gamename = parts[3]
                            # print(f"--------------\nFound: {gamename} -- {appid}")
            res.append(tuple((gamename, appid, "crossover")))
            
    return res
