import os
import shutil
import subprocess

import ui


TOUCH_ID_COMMAND = "curl -sL git.io/sudo-touch-id | sh"
HOMEBREW_COMMAND = (
    '/bin/bash -c "$(curl -fsSL '
    'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
)

STEPS = [
    "Enable Touch ID for sudo",
    "Install Xcode Command Line Tools and accept license",
    "Install Homebrew",
]


def _run(command, env=None):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env,
        )
    except OSError as error:
        return subprocess.CompletedProcess(
            command,
            127,
            stdout="",
            stderr=str(error),
        )


def _enable_touch_id():
    result = _run(["/bin/sh", "-c", TOUCH_ID_COMMAND])
    return "succeeded" if result.returncode == 0 else "failed"


def _command_line_tools_installed():
    return _run(["xcode-select", "-p"]).returncode == 0


def _install_command_line_tools():
    if not _command_line_tools_installed():
        result = _run(["xcode-select", "--install"])
        return "pending" if result.returncode == 0 else "failed"

    license_result = _run(
        ["sudo", "-n", "xcodebuild", "-license", "accept"]
    )
    return "succeeded" if license_result.returncode == 0 else "failed"


def _homebrew_installed():
    return bool(
        shutil.which("brew")
        or os.path.exists("/opt/homebrew/bin/brew")
        or os.path.exists("/usr/local/bin/brew")
    )


def _install_homebrew():
    if _homebrew_installed():
        return "succeeded"
    if not _command_line_tools_installed():
        return "skipped"

    environment = os.environ.copy()
    environment["NONINTERACTIVE"] = "1"
    result = _run(["/bin/bash", "-c", HOMEBREW_COMMAND], env=environment)
    return "succeeded" if result.returncode == 0 else "failed"


def _authorize():
    return ui.suspend(lambda: subprocess.run(["sudo", "-v"])).returncode == 0


def _ask_step(index, total, step):
    message = (
        f"Run this bootstrap step?\n\n"
        f"{index}/{total}: {step}\n\n"
        "This may download or run installation commands and may require "
        "administrator permission."
    )
    return ui.confirm(message, title=f"Bootstrapper {index}/{total}")


def _run_step(index, total, step, runner):
    outcome = "failed"

    def execute(_):
        nonlocal outcome
        if not _authorize():
            outcome = "failed"
            return
        try:
            outcome = runner()
        except Exception:
            outcome = "failed"

    ui.show_progress(
        [step],
        title=f"Bootstrapper {index}/{total}",
        callback=execute,
    )
    return outcome


def main():
    runners = [
        _enable_touch_id,
        _install_command_line_tools,
        _install_homebrew,
    ]
    outcomes = []
    total = len(STEPS)

    for index, (step, runner) in enumerate(zip(STEPS, runners), start=1):
        if not _ask_step(index, total, step):
            outcome = "skipped"
        else:
            outcome = _run_step(index, total, step, runner)
        outcomes.append((step, outcome))

    labels = {
        "succeeded": "OK",
        "failed": "FAILED",
        "pending": "PENDING",
        "skipped": "SKIPPED",
    }
    summary = "\n".join(
        f"[{labels[outcome]}] {step}" for step, outcome in outcomes
    )
    if any(outcome == "pending" for _, outcome in outcomes):
        summary += (
            "\n\nFinish the Command Line Tools installer, then run "
            "Bootstrapper again to accept the license and install Homebrew."
        )
    ui.alert(summary, title="Bootstrapper Results")
