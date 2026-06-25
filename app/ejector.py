import os
import subprocess
from pathlib import Path

import ui

JUNK_FILENAMES = {".DS_Store"}
JUNK_PREFIXES = ("._",)


def _list_external_volumes():
    vol_root = Path("/Volumes")
    if not vol_root.exists():
        return []

    return sorted(
        str(path)
        for path in vol_root.iterdir()
        if path.is_dir() and not path.is_symlink() and path.name != "Macintosh HD"
    )


def _find_junk(volume_path, on_file=None):
    junk = []
    for root, dirs, files in os.walk(volume_path):
        for f in files:
            if on_file:
                on_file()
            if f in JUNK_FILENAMES or f.startswith(JUNK_PREFIXES):
                junk.append(os.path.join(root, f))
    return junk


def _volume_is_read_only(volume_path):
    try:
        flags = os.statvfs(volume_path).f_flag
    except OSError:
        return False
    return bool(flags & os.ST_RDONLY)


def _eject_volume(volume, volume_name):
    result = subprocess.run(
        ["diskutil", "eject", volume],
        capture_output=True,
    )
    return (
        f"{volume_name} was ejected successfully."
        if result.returncode == 0
        else f"Could not eject {volume_name}."
    )


def main():
    volumes = _list_external_volumes()
    if not volumes:
        ui.alert(
            "No external drives were found. Connect a drive and try again.",
            title="Clean & Eject Drive",
        )
        return

    choice = ui.choose(volumes, title="Select Drive to Clean")
    if choice is None:
        return

    volume = volumes[choice]
    volume_name = Path(volume).name

    if _volume_is_read_only(volume):
        message = (
            f"{volume_name} is read-only. No cleanup was attempted.\n\n"
            f"{_eject_volume(volume, volume_name)}"
        )
        ui.alert(message, title="Clean & Eject Drive")
        return

    scan_state = {"files": 0}

    def count_file():
        scan_state["files"] += 1

    junk = ui.show_activity(
        lambda: _find_junk(volume, on_file=count_file),
        title=f"Scanning {volume_name}",
        message="Looking for metadata files",
        detail=lambda: f"{scan_state['files']} files scanned",
    )

    if not junk:
        ui.alert(
            f"Scanned {scan_state['files']} files. No metadata files were found.",
            title=f"{volume_name} Is Clean",
        )
        return

    deleted = 0

    def delete_one(path):
        nonlocal deleted
        try:
            os.remove(path)
            deleted += 1
        except OSError:
            pass

    ui.show_progress(junk, title=f"Cleaning {volume_name}", callback=delete_one)

    if deleted > 0:
        answer = ui.choose(
            ["No - Keep drive mounted", "Yes - Eject drive"],
            title=f"Removed {deleted}/{len(junk)} Files",
            search=False,
        )
        if answer == 1:
            ui.alert(
                _eject_volume(volume, volume_name),
                title="Clean & Eject Drive",
            )
    else:
        ui.alert(
            f"Could not remove any of the {len(junk)} metadata files.",
            title="Clean & Eject Drive",
        )
