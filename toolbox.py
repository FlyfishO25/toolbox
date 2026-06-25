import ui
from app import (
    bootstrapper,
    ejector,
    fix_apps,
    locksmith,
    settings,
    steam_launcher,
    utilities,
)
# from app import os_tweak

FEATURES = [
    {
        "key": "steam_launcher",
        "label": "Steam Launcher",
        "action": steam_launcher.launch_game,
    },
    # {
    #     "key": "menu_icons_tahoe",
    #     "label": "Menu Icons (Tahoe)",
    #     "action": os_tweak.main,
    # },
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
        if settings.is_enabled(feature["key"])
    ]
    apps.append(("Settings", _open_settings))
    return apps


def main():
    def menu_loop():
        while True:
            apps = _visible_apps()
            items = [{"label": name, "type": ui.ITEM_BUTTON} for name, _ in apps]
            result = ui.select(items, title="home", back_label="quit")
            if result is None:
                return
            apps[result["index"]][1]()

    try:
        ui.run(menu_loop)
    except ui.QuitRequested:
        return


if __name__ == "__main__":
    main()
