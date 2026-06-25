import unittest
from unittest.mock import patch

import toolbox


class HomeMenuTests(unittest.TestCase):
    def test_disabled_features_are_hidden_from_home(self):
        with patch.object(
            toolbox.settings,
            "is_enabled",
            side_effect=lambda key: key != "bootstrapper",
        ):
            labels = [label for label, _ in toolbox._visible_apps()]

        self.assertNotIn("Bootstrapper", labels)
        self.assertIn("Steam Launcher", labels)

    def test_settings_is_always_visible(self):
        with patch.object(toolbox.settings, "is_enabled", return_value=False):
            labels = [label for label, _ in toolbox._visible_apps()]

        self.assertEqual(labels, ["Settings"])


if __name__ == "__main__":
    unittest.main()
