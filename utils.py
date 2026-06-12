#! /usr/bin/env python

import os
from pathlib import Path

def list_steam_games(steam_paths_macos, steam_paths_crossover):
    home_dir = Path.home()  # Path to user's home directory
    steam_prefixes_dir = home_dir / "SteamPrefixes"
    multiple_paths = False  # If there are multiple steam paths, and user wants to use them all
    res = []

    # print("Getting appids")
    for path in steam_paths_macos:
        path = Path(path)
        print(path)
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
        print(path)
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
