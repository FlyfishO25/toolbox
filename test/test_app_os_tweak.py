import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import os_tweak
import ui


def _app(name, record):
    return os_tweak._AppState(name, f"com.example.{name.lower()}", record)


class GlobalToggleTests(unittest.TestCase):
    def test_global_toggle_only_updates_apps_without_records(self):
        apps = [
            _app("Inherited", None),
            _app("Hidden", True),
            _app("Shown", False),
        ]
        items = os_tweak._build_items(apps, global_hidden=True)
        types = [item["type"] for item in items]
        states = [item["state"] for item in items]

        ui._toggle(items, types, states, 0)

        self.assertEqual(states, [False, False, True, False])

    def test_global_toggle_can_be_reenabled(self):
        apps = [_app("Inherited", None), _app("Shown", False)]
        items = os_tweak._build_items(apps, global_hidden=False)
        types = [item["type"] for item in items]
        states = [item["state"] for item in items]

        ui._toggle(items, types, states, 0)

        self.assertEqual(states, [True, True, False])


class GlobalStateTests(unittest.TestCase):
    def test_recorded_global_state_is_used_when_available(self):
        with (
            patch.object(os_tweak.config, "get", return_value=False),
            patch.object(os_tweak, "_read_record") as read_record,
        ):
            self.assertFalse(os_tweak._get_global_state())

        read_record.assert_not_called()

    def test_defaults_global_state_is_fallback_for_existing_configs(self):
        with (
            patch.object(os_tweak.config, "get", return_value=None),
            patch.object(os_tweak, "_read_record", return_value=True),
        ):
            self.assertTrue(os_tweak._get_global_state())


class ChangePlanningTests(unittest.TestCase):
    def test_disabling_global_preserves_existing_app_records(self):
        apps = [
            _app("Inherited", None),
            _app("Hidden", True),
            _app("Shown", False),
        ]

        tasks = os_tweak._plan_changes(
            apps,
            current_global=True,
            desired_global=False,
            desired_states=[False, True, False],
        )

        self.assertEqual(
            tasks,
            [os_tweak._Task("Global", os_tweak.GLOBAL_DOMAIN, None)],
        )

    def test_enabling_global_uses_one_global_write(self):
        apps = [_app("One", None), _app("Two", None)]

        tasks = os_tweak._plan_changes(
            apps,
            current_global=False,
            desired_global=True,
            desired_states=[True, True],
        )

        self.assertEqual(
            tasks,
            [os_tweak._Task("Global", os_tweak.GLOBAL_DOMAIN, True)],
        )

    def test_shown_override_under_hidden_global_is_explicit(self):
        apps = [_app("One", None)]

        tasks = os_tweak._plan_changes(
            apps,
            current_global=True,
            desired_global=True,
            desired_states=[False],
        )

        self.assertEqual(
            tasks,
            [os_tweak._Task("One", "com.example.one", False)],
        )

    def test_matching_global_deletes_conflicting_app_record(self):
        apps = [_app("One", False)]

        tasks = os_tweak._plan_changes(
            apps,
            current_global=True,
            desired_global=True,
            desired_states=[True],
        )

        self.assertEqual(
            tasks,
            [os_tweak._Task("One", "com.example.one", None)],
        )

    def test_hidden_override_without_global_is_explicit(self):
        apps = [_app("One", None)]

        tasks = os_tweak._plan_changes(
            apps,
            current_global=False,
            desired_global=False,
            desired_states=[True],
        )

        self.assertEqual(
            tasks,
            [os_tweak._Task("One", "com.example.one", True)],
        )


class ApplyTests(unittest.TestCase):
    def test_shown_override_writes_true_instead_of_deleting(self):
        task = os_tweak._Task("One", "com.example.one", False)

        with patch.object(
            os_tweak.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0),
        ) as run:
            self.assertTrue(os_tweak._apply(task))

        run.assert_called_once_with(
            [
                "defaults", "write", "com.example.one",
                os_tweak.PREFERENCE_KEY, "-bool", "true",
            ],
            capture_output=True,
        )


if __name__ == "__main__":
    unittest.main()
