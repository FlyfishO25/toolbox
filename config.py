import json
from pathlib import Path

config_path = "config.json"
cfg = Path(config_path)

def error(msg):
    print(f"[ERROR] {msg}")
    exit(1)

def load_config():
    if not cfg.exists():
        error("Config file not found.")

    try:
        with open(cfg, "r") as f:
            return json.load(f)

    except json.JSONDecodeError as e:
        error(f"Invalid JSON syntax: {e}")

    except Exception as e:
        error(f"Failed to read config: {e}")

def _get_paths(key):
    data = load_config()

    if key not in data:
        return []

    paths = []
    for p in data.get(key, []):
        try:
            path = Path(p).expanduser()
            if path.exists():
                paths.append(str(path))
        except Exception:
            # skip invalid paths silently
            continue

    return paths

def get_steam_paths_macos():
    return _get_paths("steamapps_paths_macos")

def get_steam_paths_crossover():
    return _get_paths("steamapps_paths_crossover")
