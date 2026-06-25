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


def missing_paths(paths):
    return [path for path in paths if not path.exists()]


def missing_paths_message(paths):
    return "These paths do not exist:\n" + "\n".join(map(str, paths))


def _read_steam_manifest(path):
    values = {"appid": "", "name": ""}
    with open(path, "r") as manifest:
        for line in manifest:
            for key in values:
                if f'"{key}"' in line:
                    parts = line.split('"')
                    if len(parts) > 3:
                        values[key] = parts[3]
    return values["name"], values["appid"]


def _iter_steam_games(paths, platform):
    for path in map(Path, paths):
        for manifest in path.glob("appmanifest_*.acf"):
            if manifest.is_file():
                name, appid = _read_steam_manifest(manifest)
                yield (name, appid, platform)


def list_steam_games(steam_paths_macos, steam_paths_crossover):
    return [
        *_iter_steam_games(steam_paths_macos, "macOS"),
        *_iter_steam_games(steam_paths_crossover, "crossover"),
    ]
