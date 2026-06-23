import plistlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import config
import search


PREFERENCE_KEY = "NSMenuEnableActionImages"
GLOBAL_DOMAIN = "-g"
GLOBAL_CONFIG_KEY = "tahoe_global"

APP_DIRS = [
    Path.home() / "Applications",
    Path("/Applications"),
    Path("/System/Applications"),
]


@dataclass(frozen=True)
class _AppState:
    name: str
    bundle_id: str
    record: Optional[bool]


@dataclass(frozen=True)
class _Task:
    name: str
    domain: str
    hidden: Optional[bool]

    def __str__(self):
        return f"{self.name}  ({self.domain})"


def _get_apps():
    apps = []
    seen = set()

    for directory in APP_DIRS:
        if not directory.exists():
            continue

        for entry in sorted(directory.iterdir()):
            if entry.suffix != ".app" or entry.name in seen:
                continue
            seen.add(entry.name)

            plist_path = entry / "Contents" / "Info.plist"
            if not plist_path.exists():
                continue

            try:
                with open(plist_path, "rb") as plist_file:
                    info = plistlib.load(plist_file)
            except Exception:
                continue

            bundle_id = info.get("CFBundleIdentifier", "")
            if bundle_id:
                apps.append((entry.stem, bundle_id))

    return apps


def _read_record(domain):
    """Return the explicit hidden state, or None when the key is absent."""
    result = subprocess.run(
        ["defaults", "read", domain, PREFERENCE_KEY],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    value = result.stdout.strip().lower()
    if value in {"0", "false", "no"}:
        return True
    if value in {"1", "true", "yes"}:
        return False
    return None


def _effective_state(record, global_hidden):
    return global_hidden if record is None else record


def _get_global_state():
    recorded_state = config.get(GLOBAL_CONFIG_KEY)
    if recorded_state is not None:
        return bool(recorded_state)
    return _read_record(GLOBAL_DOMAIN) is True


def _load_app_states(apps):
    return [
        _AppState(name, bundle_id, _read_record(bundle_id))
        for name, bundle_id in apps
    ]


def _build_items(app_states, global_hidden):
    items = [{
        "label": "[Global] (apps without their own setting)",
        "type": search.ITEM_TOGGLE,
        "state": global_hidden,
        "global": True,
    }]

    for app in app_states:
        items.append({
            "label": f"{app.name}  ({app.bundle_id})",
            "type": search.ITEM_TOGGLE,
            "state": _effective_state(app.record, global_hidden),
            "global_override": app.record,
        })

    return items


def _plan_changes(app_states, current_global, desired_global, desired_states):
    tasks = []

    if desired_global != current_global:
        global_value = True if desired_global else None
        tasks.append(_Task("Global", GLOBAL_DOMAIN, global_value))

    for app, desired_state in zip(app_states, desired_states):
        resolved_state = _effective_state(app.record, desired_global)
        if desired_state == resolved_state:
            continue

        # Matching global means the app should inherit it. Otherwise the app
        # needs an explicit value, including an explicit "shown" override.
        app_value = None if desired_state == desired_global else desired_state
        tasks.append(_Task(app.name, app.bundle_id, app_value))

    return tasks


def _apply(task):
    if task.hidden is None:
        args = ["defaults", "delete", task.domain, PREFERENCE_KEY]
    else:
        enabled = "false" if task.hidden else "true"
        args = [
            "defaults", "write", task.domain, PREFERENCE_KEY,
            "-bool", enabled,
        ]

    result = subprocess.run(args, capture_output=True)
    return result.returncode == 0


def main():
    print("Scanning applications...")
    apps = _get_apps()
    if not apps:
        print("No apps found.")
        return

    print(f"Found {len(apps)} apps. Reading states...")
    global_hidden = _get_global_state()
    app_states = _load_app_states(apps)

    result = search.select(
        _build_items(app_states, global_hidden),
        title="Menu Icons (Tahoe)",
    )
    if result is None:
        return

    desired_global = result["states"][0]
    tasks = _plan_changes(
        app_states,
        current_global=global_hidden,
        desired_global=desired_global,
        desired_states=result["states"][1:],
    )
    if not tasks:
        print("No changes.")
        return

    success_count = 0
    global_succeeded = desired_global == global_hidden

    def apply_one(task):
        nonlocal success_count, global_succeeded

        if task.domain != GLOBAL_DOMAIN and not global_succeeded:
            return

        succeeded = _apply(task)
        if task.domain == GLOBAL_DOMAIN:
            global_succeeded = succeeded
            if succeeded:
                config.set(GLOBAL_CONFIG_KEY, desired_global)
        if succeeded:
            success_count += 1

    search.show_progress(tasks, title="Applying Changes", callback=apply_one)

    print(f"\nApplied: {success_count}/{len(tasks)} succeeded.")
    if success_count > 0:
        print("Restart affected apps for changes to take effect.")
