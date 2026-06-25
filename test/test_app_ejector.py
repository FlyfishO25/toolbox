import unittest
from types import SimpleNamespace
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

    def test_read_only_drive_ejects_without_scanning_or_deleting(self):
        with (
            patch.object(
                ejector,
                "_list_external_volumes",
                return_value=["/Volumes/ReadOnly"],
            ),
            patch.object(ejector.ui, "select", return_value={"index": 0}),
            patch.object(ejector, "_volume_is_read_only", return_value=True),
            patch.object(
                ejector.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0),
            ) as run,
            patch.object(ejector.ui, "alert") as alert,
            patch.object(ejector.ui, "show_activity") as show_activity,
            patch.object(ejector.ui, "show_progress") as show_progress,
            patch.object(ejector.os, "remove") as remove,
        ):
            ejector.main()

        show_activity.assert_not_called()
        show_progress.assert_not_called()
        remove.assert_not_called()
        run.assert_called_once_with(
            ["diskutil", "eject", "/Volumes/ReadOnly"],
            capture_output=True,
        )
        self.assertIn("read-only", alert.call_args.args[0])

    def test_volume_read_only_uses_statvfs_flag(self):
        with patch.object(
            ejector.os,
            "statvfs",
            return_value=SimpleNamespace(f_flag=ejector.os.ST_RDONLY),
        ):
            self.assertTrue(ejector._volume_is_read_only("/Volumes/Locked"))


if __name__ == "__main__":
    unittest.main()
