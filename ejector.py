import os
from pathlib import Path
import search


def _list_external_volumes():
    volumes = []
    vol_root = Path("/Volumes")
    if not vol_root.exists():
        return volumes

    for p in vol_root.iterdir():
        if p.is_dir() and not p.is_symlink() and p.name != "Macintosh HD":
            volumes.append(str(p))
    return sorted(volumes)


def _find_junk(volume_path):
    junk = []
    for root, dirs, files in os.walk(volume_path):
        for f in files:
            if f.startswith("._") or f == ".DS_Store":
                junk.append(os.path.join(root, f))
    return junk


def main():
    volumes = _list_external_volumes()
    if not volumes:
        print("No external volumes found in /Volumes")
        return

    items = [{"label": v, "type": search.ITEM_BUTTON} for v in volumes]
    result = search.select(items, title="Select Drive to Clean")

    if result is None:
        return

    volume = volumes[result["index"]]
    print(f"\nScanning {volume} for junk files...")

    junk = _find_junk(volume)

    if not junk:
        print("No ._* or .DS_Store files found.")
        return

    print(f"Found {len(junk)} junk files.\n")

    deleted = 0

    def delete_one(path):
        nonlocal deleted
        try:
            os.remove(path)
            deleted += 1
        except OSError:
            pass

    search.show_progress(junk, title=f"Cleaning {Path(volume).name}", callback=delete_one)

    print(f"\nRemoved {deleted}/{len(junk)} files from {Path(volume).name}")

    if deleted > 0:
        answer = input("\nEject volume? [y/N] ").strip().lower()
        if answer in ("y", "yes"):
            os.system(f"diskutil eject '{volume}'")
