import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import fix_apps
import utils


class PathParsingTests(unittest.TestCase):
    def test_escaped_dragged_path(self):
        paths = utils.parse_paths(
            "/Applications/My\\ App.app"
        )

        self.assertEqual(paths, [Path("/Applications/My App.app")])

    def test_quoted_dragged_path(self):
        paths = utils.parse_paths(
            "'/Applications/My App.app'"
        )

        self.assertEqual(paths, [Path("/Applications/My App.app")])

    def test_multiple_dragged_paths(self):
        paths = utils.parse_paths(
            "/Applications/One.app /Applications/Two\\ App.app"
        )

        self.assertEqual(
            paths,
            [
                Path("/Applications/One.app"),
                Path("/Applications/Two App.app"),
            ],
        )

    def test_empty_path(self):
        self.assertEqual(utils.parse_paths("  "), [])


class CommandTests(unittest.TestCase):
    def test_remove_quarantine_command(self):
        command = fix_apps._build_command(
            fix_apps.ACTION_REMOVE_QUARANTINE,
            Path("/Applications/My App.app"),
        )

        self.assertEqual(
            command,
            [
                "xattr", "-d", "-r", "com.apple.quarantine",
                "/Applications/My App.app",
            ],
        )

    def test_code_sign_command(self):
        command = fix_apps._build_command(
            fix_apps.ACTION_CODE_SIGN,
            Path("/Applications/My App.app"),
        )

        self.assertEqual(
            command,
            [
                "codesign", "--force", "--deep", "--sign", "-",
                "/Applications/My App.app",
            ],
        )


class MultipleItemWorkflowTests(unittest.TestCase):
    def test_main_processes_every_selected_path(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory, "First App.app")
            second = Path(directory, "Second App.app")
            first.mkdir()
            second.mkdir()
            paths = [first, second]

            def run_progress(items, title, callback):
                for item in items:
                    callback(item)

            with (
                patch.object(fix_apps.ui, "select", return_value={"index": 0}),
                patch.object(fix_apps.ui, "file_drop", return_value=paths),
                patch.object(fix_apps.ui, "show_progress", side_effect=run_progress),
                patch.object(fix_apps.ui, "alert"),
                patch.object(fix_apps, "_needs_sudo", return_value=False),
                patch.object(fix_apps, "_run_command", return_value=0) as run_command,
            ):
                fix_apps.main()

        self.assertEqual(run_command.call_count, 2)

if __name__ == "__main__":
    unittest.main()
