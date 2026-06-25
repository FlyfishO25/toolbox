import subprocess

import ui
import utils


def get_locking_processes(filepath):
    """Run lsof and return list of (command, pid, user) tuples locking the file."""
    try:
        result = subprocess.run(
            ["lsof", filepath], capture_output=True, text=True, timeout=5
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    lines = result.stdout.strip().split("\n")
    if len(lines) < 2:
        return []

    processes = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 3:
            processes.append((parts[0], parts[1], parts[2]))

    return processes


def main():
    while True:
        paths = ui.file_drop(
            parser=utils.parse_paths,
            title="File Locksmith",
            hint="Drag one or more files or folders here",
        )
        if paths is None:
            return

        missing = utils.missing_paths(paths)
        if missing:
            ui.alert(
                utils.missing_paths_message(missing),
                title="Invalid Paths",
            )
            continue

        locks = []

        def inspect_one(path):
            locks.extend(
                (path, command, pid, user)
                for command, pid, user in get_locking_processes(str(path))
            )

        ui.show_progress(paths, title="Checking Locks", callback=inspect_one)

        if not locks:
            ui.alert(
                f"No locking processes found for {len(paths)} item(s).",
                title="File Locksmith",
            )
            continue

        while True:
            choice = ui.choose(
                [
                    f"{path.name}: {command} (PID {pid}, {user})"
                    for path, command, pid, user in locks
                ],
                title=f"Locks Found: {len(locks)}",
            )
            if choice is None:
                break

            path, command, pid, user = locks[choice]
            ui.alert(
                f"Path: {path}\nProcess: {command}\nPID: {pid}\nUser: {user}"
                f"\n\nTo terminate it: kill {pid}",
                title="Lock Details",
            )
