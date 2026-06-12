import utils
import config
import search
import app_steam_launcher
import app_os_tweak

apps = [("Steam Launcher", app_steam_launcher.launch_game)]

options=[]

for item in apps:
    options.append("{0}".format(item[0]))

choice = search.fuzzy_select(options)
print("Selected:", choice)

if choice == None:
    exit(0)

apps[choice][1]()
