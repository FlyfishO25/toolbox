import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import locksmith


class MultipleItemWorkflowTests(unittest.TestCase):
    def test_main_checks_every_selected_path(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory, "one.txt")
            second = Path(directory, "two.txt")
            first.touch()
            second.touch()
            paths = [first, second]

            def run_progress(items, title, callback):
                for item in items:
                    callback(item)

            with (
                patch.object(
                    locksmith.ui,
                    "file_drop",
                    side_effect=[paths, None],
                ),
                patch.object(locksmith.ui, "show_progress", side_effect=run_progress),
                patch.object(locksmith.ui, "select", return_value=None),
                patch.object(
                    locksmith,
                    "get_locking_processes",
                    return_value=[("Finder", "123", "user")],
                ) as get_locks,
            ):
                locksmith.main()

        self.assertEqual(get_locks.call_count, 2)


if __name__ == "__main__":
    unittest.main()
