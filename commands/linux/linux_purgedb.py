


import getpass
from os.path import expanduser


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)

special_commands = [
]

action_cmds = [
    ["sudo", "-S", "-i", "-u", "postgres", "psql", "-c", "DROP DATABASE so_data;"],
    ["sudo", "-S", "-i", "-u", "postgres", "psql", "-c", "CREATE DATABASE so_data;"],
    ["sudo", "-S", f"/home/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "migrate"],
    ["echo", 'Complete'],
]

    