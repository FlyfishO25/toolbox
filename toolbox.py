import ui
from app import (
    bootstrapper,
    ejector,
    fix_apps,
    game_launcher,
    locksmith,
    settings,
    utilities,
)

FEATURES = [
    {
        "key": "game_launcher",
        "legacy_keys": ["steam_launcher"],
        "label": "Game Launcher",
        "action": game_launcher.launch_game,
    },
    {
        "key": "fix_apps",
        "label": "Fix Apps",
        "action": fix_apps.main,
    },
    {
        "key": "file_locksmith",
        "label": "File Locksmith",
        "action": locksmith.main,
    },
    {
        "key": "clean_eject_drive",
        "label": "Clean & Eject Drive",
        "action": ejector.main,
    },
    {
        "key": "utilities",
        "label": "Utilities",
        "action": utilities.main,
    },
    {
        "key": "bootstrapper",
        "label": "Bootstrapper",
        "action": bootstrapper.main,
    },
]


def _open_settings():
    settings.main(FEATURES)


def _visible_apps():
    apps = [
        (feature["label"], feature["action"])
        for feature in FEATURES
        if settings.is_enabled(feature["key"], feature.get("legacy_keys"))
    ]
    apps.append(("Settings", _open_settings))
    return apps


def main():
    def menu_loop():
        while True:
            apps = _visible_apps()
            choice = ui.choose(
                [name for name, _ in apps],
                title="home",
                back_label="quit",
            )
            if choice is None:
                return
            apps[choice][1]()

    try:
        ui.run(menu_loop)
    except ui.QuitRequested:
        return


if __name__ == "__main__":
    main()
