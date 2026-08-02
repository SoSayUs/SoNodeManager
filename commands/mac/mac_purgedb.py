


import getpass
from os.path import expanduser


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)
psql_path = '/opt/homebrew/bin/psql'

special_commands = [
]

action_cmds = [
    f"sudo -S -u {username} {psql_path} -c \"DROP DATABASE so_data;\"",
    f"sudo -S -u {username} {psql_path} -c \"CREATE DATABASE so_data;\"",
    [f'/Users/{username}/Sonet/.data/env/bin/python3', f'{homepath}/Sonet/SoNodeServer/manage.py', 'migrate'],
    ["echo", 'Complete'],
]

    