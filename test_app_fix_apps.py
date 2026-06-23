import unittest
from pathlib import Path

import app_fix_apps


class PathParsingTests(unittest.TestCase):
    def test_escaped_dragged_path(self):
        path = app_fix_apps._parse_dragged_path(
            "/Applications/My\\ App.app"
        )

        self.assertEqual(path, Path("/Applications/My App.app"))

    def test_quoted_dragged_path(self):
        path = app_fix_apps._parse_dragged_path(
            "'/Applications/My App.app'"
        )

        self.assertEqual(path, Path("/Applications/My App.app"))

    def test_empty_path(self):
        self.assertIsNone(app_fix_apps._parse_dragged_path("  "))


class CommandTests(unittest.TestCase):
    def test_remove_quarantine_command(self):
        command = app_fix_apps._build_command(
            app_fix_apps.ACTION_REMOVE_QUARANTINE,
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
        command = app_fix_apps._build_command(
            app_fix_apps.ACTION_CODE_SIGN,
            Path("/Applications/My App.app"),
        )

        self.assertEqual(
            command,
            [
                "codesign", "--force", "--deep", "--sign", "-",
                "/Applications/My App.app",
            ],
        )


if __name__ == "__main__":
    unittest.main()
