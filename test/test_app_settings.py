import unittest
from unittest.mock import patch

from app import settings


FEATURES = [
    {"key": "one", "label": "One"},
    {"key": "two", "label": "Two"},
]


class SettingsTests(unittest.TestCase):
    def test_missing_feature_state_defaults_to_enabled(self):
        with patch.object(settings.config, "get", return_value={}):
            self.assertTrue(settings.is_enabled("new_feature"))

    def test_existing_false_state_disables_feature(self):
        with patch.object(
            settings.config,
            "get",
            return_value={"new_feature": False},
        ):
            self.assertFalse(settings.is_enabled("new_feature"))

    def test_legacy_feature_state_is_used_when_new_key_is_missing(self):
        with patch.object(
            settings.config,
            "get",
            return_value={"old_feature": False},
        ):
            self.assertFalse(
                settings.is_enabled(
                    "new_feature",
                    legacy_keys=["old_feature"],
                )
            )

    def test_new_feature_state_overrides_legacy_state(self):
        with patch.object(
            settings.config,
            "get",
            return_value={"new_feature": True, "old_feature": False},
        ):
            self.assertTrue(
                settings.is_enabled(
                    "new_feature",
                    legacy_keys=["old_feature"],
                )
            )

    def test_build_items_uses_saved_states(self):
        with patch.object(
            settings.config,
            "get",
            return_value={"two": False},
        ):
            items = settings._build_items(FEATURES)

        self.assertEqual(
            [(item["label"], item["type"], item["state"]) for item in items],
            [
                ("One", settings.ui.ITEM_TOGGLE, True),
                ("Two", settings.ui.ITEM_TOGGLE, False),
            ],
        )

    def test_save_states_preserves_unknown_feature_flags(self):
        with (
            patch.object(
                settings.config,
                "get",
                return_value={"legacy": False},
            ),
            patch.object(settings.config, "set") as set_config,
        ):
            settings._save_states(FEATURES, [False, True])

        set_config.assert_called_once_with(
            settings.FEATURES_CONFIG_KEY,
            {
                "legacy": False,
                "one": False,
                "two": True,
            },
        )

    def test_main_saves_selected_toggle_states(self):
        with (
            patch.object(
                settings.ui,
                "select",
                return_value={"states": [False, True]},
            ) as select,
            patch.object(settings, "_save_states") as save_states,
            patch.object(settings.ui, "alert") as alert,
        ):
            settings.main(FEATURES)

        self.assertEqual(select.call_args.kwargs["action_label"], "confirm")
        save_states.assert_called_once_with(FEATURES, [False, True])
        alert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
