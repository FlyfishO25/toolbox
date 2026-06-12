import plistlib
import subprocess
import config
import search
from pathlib import Path

APP_DIRS = [
    Path.home() / "Applications",
    Path("/Applications"),
    Path("/System/Applications"),
]


def _get_apps():
    apps = []
    seen = set()
    for d in APP_DIRS:
        if not d.exists():
            continue
        for entry in sorted(d.iterdir()):
            if entry.suffix != ".app" or entry.name in seen:
                continue
            seen.add(entry.name)
            plist_path = entry / "Contents" / "Info.plist"
            if not plist_path.exists():
                continue
            try:
                with open(plist_path, "rb") as f:
                    info = plistlib.load(f)
                bid = info.get("CFBundleIdentifier", "")
                if bid:
                    apps.append((entry.name.replace(".app", ""), bid))
            except Exception:
                continue
    return apps


def _read_state(bundle_id):
    """True if NSMenuEnableActionImages is set to false (icons hidden)."""
    r = subprocess.run(
        ["defaults", "read", bundle_id, "NSMenuEnableActionImages"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return False
    return r.stdout.strip() == "0"


def _apply(bundle_id, hide):
    """hide=True -> defaults write -bool false. hide=False -> defaults delete."""
    if hide:
        args = ["defaults", "write", bundle_id, "NSMenuEnableActionImages",
                "-bool", "false"]
    else:
        args = ["defaults", "delete", bundle_id, "NSMenuEnableActionImages"]
    r = subprocess.run(args, capture_output=True)
    return r.returncode == 0


def main():
    print("Scanning applications...")
    apps = _get_apps()
    if not apps:
        print("No apps found.")
        return

    saved = config.get("tahoe_states", {})
    print(f"Found {len(apps)} apps. Reading states...")

    # load states: True = icons hidden ([x])
    global_hidden = saved.get("__global__", _read_state("-g"))

    items = [{
        "label": "[Global] (all apps) (Check this first and then restart to toggle other)",
        "type": search.ITEM_TOGGLE,
        "state": global_hidden,
    }]

    for name, bid in apps:
        s = saved.get(bid, _read_state(bid))
        items.append({
            "label": f"{name}  ({bid})",
            "type": search.ITEM_TOGGLE,
            "state": s,
        })

    result = search.select(items, title="Menu Icons (Tahoe)")
    if result is None:
        return

    states = result["states"]
    new_global = states[0]

    # cascade: global off hides all, global on shows all
    if new_global != global_hidden:
        for i in range(1, len(states)):
            states[i] = new_global

    # persist
    new_saved = {"__global__": new_global}
    for i, (name, bid) in enumerate(apps):
        new_saved[bid] = states[i + 1]
    config.set("tahoe_states", new_saved)

    # build apply list
    class _Task:
        def __init__(self, name, bid, hide):
            self.name = name
            self.bid = bid
            self.hide = hide
        def __str__(self):
            return f"{self.name}  ({self.bid})"

    changed = []

    if new_global != global_hidden:
        changed.append(_Task("Global", "-g", new_global))
    else:
        # only apply per-app changes when global didn't change
        for i, (name, bid) in enumerate(apps):
            new_state = states[i + 1]
            old_state = saved.get(bid, _read_state(bid))
            if new_state != old_state:
                changed.append(_Task(name, bid, new_state))

    if not changed:
        print("No changes.")
        return

    ok_count = 0

    def apply_one(task):
        nonlocal ok_count
        if _apply(task.bid, task.hide):
            ok_count += 1

    search.show_progress(changed, title="Applying Changes", callback=apply_one)

    print(f"\nApplied: {ok_count}/{len(changed)} succeeded.")
    if ok_count > 0:
        print("Restart affected apps for changes to take effect.")
