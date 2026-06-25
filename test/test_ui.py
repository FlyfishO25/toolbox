import unittest
from unittest.mock import patch

import ui


class _Screen:
    def __init__(self, keys):
        self.keys = iter(keys)
        self.drawn = []
        self.timeouts = []

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

    def timeout(self, milliseconds):
        self.timeouts.append(milliseconds)

    def nodelay(self, enabled):
        self.timeouts.append(0 if enabled else -1)

    def _next_key(self):
        key = next(self.keys)
        if isinstance(key, BaseException):
            raise key
        return key

    def getch(self):
        return self._next_key()

    def get_wch(self):
        return self._next_key()


def _run_widget(screen, callback):
    with (
        patch.object(ui, "_init_colors"),
        patch.object(ui.curses, "curs_set"),
        patch.object(ui.curses, "color_pair", return_value=0),
        patch.object(ui.curses, "wrapper", side_effect=lambda run: run(screen)),
    ):
        return callback()


class NavigationTests(unittest.TestCase):
    def test_widget_restores_blocking_input_mode(self):
        screen = _Screen([])

        _run_widget(
            screen,
            lambda: ui._run_widget(lambda stdscr: stdscr.nodelay(True)),
        )

        self.assertEqual(screen.timeouts[-1], -1)

    def test_confirmation_accepts_y_and_rejects_n(self):
        yes_screen = _Screen([ord("y")])
        no_screen = _Screen([ord("n")])

        self.assertTrue(
            _run_widget(yes_screen, lambda: ui.confirm("Continue?"))
        )
        self.assertFalse(
            _run_widget(no_screen, lambda: ui.confirm("Continue?"))
        )

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

    def test_mouse_double_click_selects_menu_item(self):
        screen = _Screen([ui.curses.KEY_MOUSE])
        double_click = getattr(ui.curses, "BUTTON1_DOUBLE_CLICKED", 0)

        with patch.object(ui, "_mouse_event", return_value=(2, 6, double_click)):
            result = _run_widget(
                screen,
                lambda: ui.select([{"label": "One"}], title="Test"),
            )

        self.assertEqual(result["index"], 0)


class FileDropTests(unittest.TestCase):
    def test_drop_is_added_automatically_then_right_confirms(self):
        keys = [*"dropped", ui.curses.error("no input"), ui.curses.KEY_RIGHT]
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
        keys = [
            *"dropped",
            ui.curses.error("no input"),
            ui.curses.KEY_DC,
            ui.curses.KEY_RIGHT,
        ]
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
