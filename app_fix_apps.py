import os
import shlex
import subprocess
from pathlib import Path

import search


ACTION_REMOVE_QUARANTINE = 0
ACTION_CODE_SIGN = 1

ACTIONS = [
    ("Remove quarantine", ACTION_REMOVE_QUARANTINE),
    ("Code sign", ACTION_CODE_SIGN),
]


def _parse_dragged_path(raw):
    raw = raw.strip()
    if not raw:
        return None

    try:
        parts = shlex.split(raw)
    except ValueError:
        return Path(raw).expanduser()

    if not parts:
        return None
    return Path(" ".join(parts)).expanduser()


def _is_writable_tree(path):
    if not os.access(path, os.W_OK):
        return False

    if not path.is_dir():
        return True

    for root, dirs, files in os.walk(path):
        root_path = Path(root)
        if not os.access(root_path, os.W_OK):
            return False

        for name in dirs + files:
            child = root_path / name
            if not child.is_symlink() and not os.access(child, os.W_OK):
                return False

    return True


def _needs_sudo(path):
    return os.geteuid() != 0 and not _is_writable_tree(path)


def _build_command(action, path):
    if action == ACTION_REMOVE_QUARANTINE:
        return ["xattr", "-d", "-r", "com.apple.quarantine", str(path)]
    if action == ACTION_CODE_SIGN:
        return ["codesign", "--force", "--deep", "--sign", "-", str(path)]
    raise ValueError(f"Unknown action: {action}")


def _run_command(command, needs_sudo):
    if needs_sudo:
        command = ["sudo", *command]
        print("Admin permission is needed. sudo may ask for your password.")

    print("\nRunning:")
    print(" ".join(shlex.quote(part) for part in command))
    return subprocess.run(command).returncode


def main():
    items = [{"label": label, "type": search.ITEM_BUTTON} for label, _ in ACTIONS]
    result = search.select(items, title="Fix Apps")
    if result is None:
        return

    action_label, action = ACTIONS[result["index"]]

    print(f"\n{action_label}")
    print("Drag an app/file/folder here, then press Return.")
    raw_path = input("Path: ")
    path = _parse_dragged_path(raw_path)

    if path is None:
        print("No path provided.")
        return

    if not path.exists():
        print(f"Path does not exist: {path}")
        return

    needs_sudo = _needs_sudo(path)
    command = _build_command(action, path)
    returncode = _run_command(command, needs_sudo)

    if returncode == 0:
        print(f"\nDone: {action_label}")
    else:
        print(f"\nFailed with exit status {returncode}.")
        raise SystemExit(returncode)
