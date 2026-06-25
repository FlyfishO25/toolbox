import subprocess

import ui


UTILITIES = ["Flush DNS Cache"]


def _flush_dns():
    commands = [
        ["sudo", "-n", "dscacheutil", "-flushcache"],
        ["sudo", "-n", "killall", "-HUP", "mDNSResponder"],
    ]
    results = [
        subprocess.run(command, capture_output=True).returncode
        for command in commands
    ]
    return all(returncode == 0 for returncode in results)


def main():
    while True:
        items = [
            {"label": label, "type": ui.ITEM_BUTTON}
            for label in UTILITIES
        ]
        result = ui.select(items, title="Utilities")
        if result is None:
            return

        if not ui.confirm(
            "Flush the macOS DNS cache now? Administrator permission is required.",
            title="Flush DNS Cache",
        ):
            continue

        authorization = ui.suspend(lambda: subprocess.run(["sudo", "-v"]))
        if authorization.returncode != 0:
            ui.alert("Administrator permission was not granted.", title="Failed")
            continue

        succeeded = False

        def run_step(_):
            nonlocal succeeded
            succeeded = _flush_dns()

        ui.show_progress(
            ["Flush DNS cache"],
            title="Utilities",
            callback=run_step,
        )
        ui.alert(
            "DNS cache flushed successfully."
            if succeeded
            else "The DNS cache could not be flushed.",
            title="Utilities",
        )
        return
