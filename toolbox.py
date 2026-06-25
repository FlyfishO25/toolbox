import ui
from app import (
    bootstrapper,
    ejector,
    fix_apps,
    locksmith,
    steam_launcher,
    utilities,
)
# from app import os_tweak

apps = [
    ("Steam Launcher", steam_launcher.launch_game),
    # ("Menu Icons (Tahoe)", os_tweak.main),
    ("Fix Apps", fix_apps.main),
    ("File Locksmith", locksmith.main),
    ("Clean & Eject Drive", ejector.main),
    ("Utilities", utilities.main),
    ("Bootstrapper", bootstrapper.main),
]

def main():
    items = [{"label": name, "type": ui.ITEM_BUTTON} for name, _ in apps]

    def menu_loop():
        while True:
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
