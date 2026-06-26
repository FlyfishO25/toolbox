import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import game_launcher


class GameLauncherTests(unittest.TestCase):
    def test_build_launcher_actions_includes_custom_executables(self):
        actions = game_launcher._build_launcher_actions(
            [("Portal", "400", "macOS")],
            ["/Applications/Hades.app"],
        )

        self.assertEqual(
            actions[0],
            ("Custom: Hades", "custom_executable", "/Applications/Hades.app"),
        )
        self.assertIn(
            ("Portal (macOS)", "steam_game", ("400", "macOS")),
            actions,
        )

    def test_add_custom_executables_persists_dragged_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            app_path = Path(directory) / "Game.app"
            app_path.mkdir()

            with (
                patch.object(
                    game_launcher.ui,
                    "file_drop",
                    return_value=[app_path],
                ),
                patch.object(
                    game_launcher.config,
                    "get",
                    return_value=[],
                ),
                patch.object(game_launcher.config, "set") as set_config,
                patch.object(game_launcher.ui, "alert") as alert,
            ):
                game_launcher._add_custom_executables()

        set_config.assert_called_once_with("game_executables", [str(app_path)])
        alert.assert_called_once()

    def test_custom_app_launches_with_open(self):
        with tempfile.TemporaryDirectory() as directory:
            app_path = Path(directory) / "Game.app"
            app_path.mkdir()

            with patch.object(game_launcher.subprocess, "Popen") as popen:
                self.assertTrue(game_launcher.launch_custom_executable(app_path))

        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ["open", str(app_path)])
        self.assertNotIn("cwd", popen.call_args.kwargs)

    def test_custom_executable_launches_directly_from_its_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "game"
            executable.write_text("#!/bin/sh\n")
            executable.chmod(os.stat(executable).st_mode | 0o111)

            with patch.object(game_launcher.subprocess, "Popen") as popen:
                self.assertTrue(game_launcher.launch_custom_executable(executable))

        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], [str(executable)])
        self.assertEqual(popen.call_args.kwargs["cwd"], str(executable.parent))

    def test_launch_game_uses_game_launcher_title_and_launches_custom_choice(self):
        with (
            patch.object(game_launcher, "_load_games", return_value=[]),
            patch.object(
                game_launcher,
                "_load_custom_executables",
                return_value=["/Applications/Hades.app"],
            ),
            patch.object(
                game_launcher.ui,
                "select",
                return_value={"index": 0},
            ) as select,
            patch.object(game_launcher, "launch_custom_executable") as launch,
        ):
            game_launcher.launch_game()

        self.assertEqual(select.call_args.kwargs["title"], "Game Launcher")
        labels = [item["label"] for item in select.call_args.args[0]]
        self.assertEqual(labels[0], "Custom: Hades")
        self.assertNotIn("Add Custom Executable", labels)
        self.assertEqual(
            select.call_args.kwargs["shortcuts"],
            [
                {
                    "key": game_launcher.ui.CTRL_A,
                    "keys": "ctrl-a",
                    "label": "add",
                    "name": "add_custom",
                },
                {
                    "key": game_launcher.ui.CTRL_D,
                    "keys": "ctrl-d",
                    "label": "delete",
                    "name": "delete_custom",
                },
            ],
        )
        launch.assert_called_once_with("/Applications/Hades.app")

    def test_ctrl_a_adds_custom_executable_without_menu_item(self):
        with (
            patch.object(game_launcher, "_load_games", return_value=[]),
            patch.object(game_launcher, "_load_custom_executables", return_value=[]),
            patch.object(
                game_launcher.ui,
                "select",
                side_effect=[{"shortcut": "add_custom"}, None],
            ),
            patch.object(game_launcher, "_add_custom_executables") as add,
        ):
            game_launcher.launch_game()

        add.assert_called_once()

    def test_ctrl_d_deletes_custom_executable_from_config(self):
        with (
            patch.object(game_launcher, "_load_games", return_value=[]),
            patch.object(
                game_launcher,
                "_load_custom_executables",
                side_effect=[
                    ["/Applications/Hades.app"],
                    ["/Applications/Hades.app"],
                    [],
                ],
            ),
            patch.object(
                game_launcher.ui,
                "select",
                side_effect=[{"shortcut": "delete_custom", "index": 0}, None],
            ),
            patch.object(game_launcher.config, "set") as set_config,
            patch.object(game_launcher.ui, "alert") as alert,
        ):
            game_launcher.launch_game()

        set_config.assert_called_once_with("game_executables", [])
        alert.assert_called_once()

    def test_ctrl_d_does_not_delete_steam_game(self):
        with (
            patch.object(
                game_launcher,
                "_load_games",
                return_value=[("Portal", "400", "macOS")],
            ),
            patch.object(game_launcher, "_load_custom_executables", return_value=[]),
            patch.object(
                game_launcher.ui,
                "select",
                side_effect=[
                    {
                        "shortcut": "delete_custom",
                        "index": len(game_launcher.STEAM_TABS),
                    },
                    None,
                ],
            ),
            patch.object(game_launcher.config, "set") as set_config,
            patch.object(game_launcher.ui, "alert") as alert,
        ):
            game_launcher.launch_game()

        set_config.assert_not_called()
        alert.assert_called_once()
        self.assertIn("Steam games stay", alert.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
