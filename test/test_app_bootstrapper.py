import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import bootstrapper


class BootstrapperTests(unittest.TestCase):
    def test_touch_id_uses_requested_command(self):
        with patch.object(
            bootstrapper,
            "_run",
            return_value=SimpleNamespace(returncode=0),
        ) as run:
            self.assertEqual(bootstrapper._enable_touch_id(), "succeeded")

        run.assert_called_once_with(
            ["/bin/sh", "-c", "curl -sL git.io/sudo-touch-id | sh"]
        )

    def test_xcode_installer_is_reported_pending(self):
        with (
            patch.object(
                bootstrapper,
                "_command_line_tools_installed",
                return_value=False,
            ),
            patch.object(
                bootstrapper,
                "_run",
                return_value=SimpleNamespace(returncode=0),
            ) as run,
        ):
            result = bootstrapper._install_command_line_tools()

        self.assertEqual(result, "pending")
        run.assert_called_once_with(["xcode-select", "--install"])

    def test_main_asks_each_step_and_skips_declined_steps(self):
        def run_progress(items, title, callback):
            self.assertEqual(len(items), 1)
            self.assertIn("/", title)
            for item in items:
                callback(item)

        with (
            patch.object(
                bootstrapper.ui,
                "confirm",
                side_effect=[True, False, True],
            ) as confirm,
            patch.object(
                bootstrapper.ui,
                "suspend",
                return_value=SimpleNamespace(returncode=0),
            ) as suspend,
            patch.object(
                bootstrapper.ui,
                "show_progress",
                side_effect=run_progress,
            ) as show_progress,
            patch.object(bootstrapper.ui, "alert") as alert,
            patch.object(
                bootstrapper,
                "_enable_touch_id",
                return_value="succeeded",
            ) as touch_id,
            patch.object(
                bootstrapper,
                "_install_command_line_tools",
                return_value="succeeded",
            ) as command_line_tools,
            patch.object(
                bootstrapper,
                "_install_homebrew",
                return_value="succeeded",
            ) as homebrew,
        ):
            bootstrapper.main()

        self.assertEqual(confirm.call_count, 3)
        self.assertEqual(show_progress.call_count, 2)
        self.assertEqual(suspend.call_count, 2)
        touch_id.assert_called_once()
        command_line_tools.assert_not_called()
        homebrew.assert_called_once()

        summary = alert.call_args.args[0]
        self.assertIn("[OK] Enable Touch ID for sudo", summary)
        self.assertIn(
            "[SKIPPED] Install Xcode Command Line Tools and accept license",
            summary,
        )
        self.assertIn("[OK] Install Homebrew", summary)


if __name__ == "__main__":
    unittest.main()
