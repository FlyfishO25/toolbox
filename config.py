import json
from pathlib import Path

CONFIG_FILE = Path("config.json")

DEFAULTS = {
    "steamapps_paths_macos": [
        "~/Library/Application Support/Steam/steamapps"
    ],
    "steamapps_paths_crossover": [
        "~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps"
    ],
}


def _read():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def _write(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)
    f.close()


def get(key, default=None):
    data = _read()
    return data.get(key, DEFAULTS.get(key, default))


def set(key, value):
    data = _read()
    data[key] = value
    _write(data)


def _get_paths(key):
    paths = []
    for p in get(key, []):
        try:
            path = Path(p).expanduser()
            if path.exists():
                paths.append(str(path))
        except Exception:
            continue
    return paths


def get_steam_paths_macos():
    return _get_paths("steamapps_paths_macos")


def get_steam_paths_crossover():
    return _get_paths("steamapps_paths_crossover")
