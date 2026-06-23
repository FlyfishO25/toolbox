import search
import app_steam_launcher
# import app_os_tweak
import app_fix_apps
import locksmith
import ejector

apps = [
    ("Steam Launcher", app_steam_launcher.launch_game),
    # ("Menu Icons (Tahoe)", app_os_tweak.main),
    ("Fix Apps", app_fix_apps.main),
    ("File Locksmith", locksmith.main),
    ("Clean & Eject Drive", ejector.main),
]

items = [{"label": name, "type": search.ITEM_BUTTON} for name, _ in apps]

result = search.select(items, title="Toolbox")
print("Selected:", result["index"] if result else None)

if result is None:
    exit(0)

apps[result["index"]][1]()
