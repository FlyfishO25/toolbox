import os
import subprocess
from pathlib import Path

import ui
import utils


ACTION_REMOVE_QUARANTINE = 0
ACTION_CODE_SIGN = 1

ACTIONS = [
    ("Remove quarantine", ACTION_REMOVE_QUARANTINE),
    ("Code sign", ACTION_CODE_SIGN),
]


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
        command = ["sudo", "-n", *command]
    return subprocess.run(command, capture_output=True).returncode


def main():
    while True:
        items = [
            {"label": label, "type": ui.ITEM_BUTTON}
            for label, _ in ACTIONS
        ]
        result = ui.select(items, title="Fix Apps")
        if result is None:
            return

        action_label, action = ACTIONS[result["index"]]

        while True:
            paths = ui.file_drop(
                parser=utils.parse_paths,
                title=action_label,
                hint="Drag one or more apps, files, or folders here",
            )
            if paths is None:
                break

            missing = [path for path in paths if not path.exists()]
            if missing:
                ui.alert(
                    "These paths do not exist:\n" + "\n".join(map(str, missing)),
                    title="Invalid Paths",
                )
                continue

            sudo_states = [_needs_sudo(path) for path in paths]
            if any(sudo_states):
                should_continue = ui.alert(
                    "Administrator permission is required for one or more items.",
                    title=action_label,
                )
                if not should_continue:
                    continue
                result = ui.suspend(lambda: subprocess.run(["sudo", "-v"]))
                if result.returncode != 0:
                    ui.alert("Administrator permission was not granted.", title="Failed")
                    continue

            succeeded = 0

            def process_one(path, needs_sudo):
                nonlocal succeeded
                command = _build_command(action, path)
                if _run_command(command, needs_sudo) == 0:
                    succeeded += 1

            remaining_sudo_states = iter(sudo_states)

            def process_path(path):
                process_one(path, next(remaining_sudo_states))

            ui.show_progress(paths, title=action_label, callback=process_path)
            ui.alert(
                f"{succeeded}/{len(paths)} items completed successfully.",
                title=action_label,
            )
            return
