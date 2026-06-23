import unittest
from unittest.mock import patch

import ui


class _Screen:
    def __init__(self, keys):
        self.keys = iter(keys)
        self.drawn = []

    def getmaxyx(self):
        return 24, 80

    def erase(self):
        pass

    def addstr(self, y, x, text, attr=0):
        self.drawn.append(str(text))

    def move(self, y, x):
        pass

    def refresh(self):
        pass

    def getch(self):
        return next(self.keys)

    def get_wch(self):
        return next(self.keys)


def _run_widget(screen, callback):
    with (
        patch.object(ui, "_init_colors"),
        patch.object(ui.curses, "curs_set"),
        patch.object(ui.curses, "color_pair", return_value=0),
        patch.object(ui.curses, "wrapper", side_effect=lambda run: run(screen)),
    ):
        return callback()


class NavigationTests(unittest.TestCase):
    def test_menu_transitions_share_one_curses_session(self):
        screen = _Screen([ui.curses.KEY_RIGHT, ui.curses.KEY_LEFT])

        with (
            patch.object(ui, "_init_colors"),
            patch.object(ui.curses, "curs_set"),
            patch.object(ui.curses, "color_pair", return_value=0),
            patch.object(
                ui.curses,
                "wrapper",
                side_effect=lambda run: run(screen),
            ) as wrapper,
        ):
            def flow():
                selected = ui.select([{"label": "One"}], title="First")
                self.assertEqual(selected["index"], 0)
                self.assertIsNone(ui.select([{"label": "Two"}], title="Second"))

            ui.run(flow)

        wrapper.assert_called_once()

    def test_right_selects_current_menu_item(self):
        screen = _Screen([ui.curses.KEY_RIGHT])

        result = _run_widget(
            screen,
            lambda: ui.select([{"label": "One"}], title="Test"),
        )

        self.assertEqual(result["index"], 0)

    def test_left_goes_back_and_home_labels_it_quit(self):
        screen = _Screen([ui.curses.KEY_LEFT])

        result = _run_widget(
            screen,
            lambda: ui.select(
                [{"label": "One"}],
                title="home",
                back_label="quit",
            ),
        )

        self.assertIsNone(result)
        self.assertTrue(any("left/esc: quit" in text for text in screen.drawn))

    def test_ctrl_q_raises_immediate_quit(self):
        screen = _Screen([ui.CTRL_Q])

        with self.assertRaises(ui.QuitRequested):
            _run_widget(
                screen,
                lambda: ui.select([{"label": "One"}], title="Test"),
            )


class FileDropTests(unittest.TestCase):
    def test_drop_is_added_then_right_confirms(self):
        keys = [*"dropped", "\n", ui.curses.KEY_RIGHT]
        screen = _Screen(keys)

        result = _run_widget(
            screen,
            lambda: ui.file_drop(
                parser=lambda raw: ["/tmp/one", "/tmp/two"],
                title="Drop",
            ),
        )

        self.assertEqual(result, ["/tmp/one", "/tmp/two"])

    def test_delete_removes_selected_item(self):
        keys = [*"dropped", "\n", ui.curses.KEY_DC, ui.curses.KEY_RIGHT]
        screen = _Screen(keys)

        result = _run_widget(
            screen,
            lambda: ui.file_drop(
                parser=lambda raw: ["/tmp/one", "/tmp/two"],
                title="Drop",
            ),
        )

        self.assertEqual(result, ["/tmp/one"])


if __name__ == "__main__":
    unittest.main()
