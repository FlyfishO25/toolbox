import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import utilities


class UtilitiesTests(unittest.TestCase):
    def test_flush_dns_runs_both_macos_commands(self):
        with patch.object(
            utilities.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0),
        ) as run:
            self.assertTrue(utilities._flush_dns())

        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [
                ["sudo", "-n", "dscacheutil", "-flushcache"],
                ["sudo", "-n", "killall", "-HUP", "mDNSResponder"],
            ],
        )

    def test_main_confirms_and_shows_one_step_progress(self):
        def run_progress(items, title, callback):
            self.assertEqual(items, ["Flush DNS cache"])
            callback(items[0])

        with (
            patch.object(utilities.ui, "select", return_value={"index": 0}),
            patch.object(utilities.ui, "confirm", return_value=True),
            patch.object(
                utilities.ui,
                "suspend",
                return_value=SimpleNamespace(returncode=0),
            ),
            patch.object(
                utilities.ui,
                "show_progress",
                side_effect=run_progress,
            ),
            patch.object(utilities.ui, "alert"),
            patch.object(utilities, "_flush_dns", return_value=True) as flush,
        ):
            utilities.main()

        flush.assert_called_once()


if __name__ == "__main__":
    unittest.main()
