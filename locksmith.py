import subprocess
import search


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
    filepath = input("File path: ").strip()
    if not filepath:
        print("No path provided.")
        return

    procs = get_locking_processes(filepath)

    if not procs:
        print(f"No process is locking: {filepath}")
        return

    items = [{"label": f"{cmd} (PID {pid}, user {user})", "type": search.ITEM_BUTTON}
             for cmd, pid, user in procs]
    result = search.select(items, title=f"Locking: {filepath}")

    if result is not None:
        cmd, pid, user = procs[result["index"]]
        print(f"\nProcess: {cmd}  PID: {pid}  User: {user}")
        print(f"To kill: kill {pid}")
