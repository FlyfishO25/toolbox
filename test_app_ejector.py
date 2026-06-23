import unittest
from unittest.mock import patch

from app import ejector


class JunkScanningTests(unittest.TestCase):
    @patch.object(ejector.os, "walk")
    def test_find_junk_reports_progress_for_every_file(self, walk):
        walk.return_value = [
            ("/Volumes/Test", [], [".DS_Store", "photo.jpg", "._photo.jpg"]),
        ]
        scanned = []

        junk = ejector._find_junk("/Volumes/Test", on_file=lambda: scanned.append(1))

        self.assertEqual(
            junk,
            ["/Volumes/Test/.DS_Store", "/Volumes/Test/._photo.jpg"],
        )
        self.assertEqual(len(scanned), 3)

    @patch.object(ejector.ui, "alert")
    @patch.object(ejector, "_list_external_volumes", return_value=[])
    def test_no_drives_uses_styled_alert(self, list_volumes, alert):
        ejector.main()

        alert.assert_called_once()
        self.assertEqual(alert.call_args.kwargs["title"], "Clean & Eject Drive")

    @patch.object(ejector.ui, "alert")
    @patch.object(ejector.ui, "show_activity", return_value=[])
    @patch.object(ejector.ui, "select", return_value={"index": 0})
    @patch.object(
        ejector,
        "_list_external_volumes",
        return_value=["/Volumes/Test"],
    )
    def test_drive_scan_uses_activity_progress(
        self, list_volumes, select, show_activity, alert
    ):
        ejector.main()

        show_activity.assert_called_once()
        self.assertEqual(show_activity.call_args.kwargs["title"], "Scanning Test")


if __name__ == "__main__":
    unittest.main()
