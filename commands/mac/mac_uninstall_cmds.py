
import os
import subprocess
import getpass
from os.path import expanduser
import shutil
from kivy.clock import Clock

from ..utils import get_operatorData, fetch_secure_item, now_utc, sign


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)
brew_path = shutil.which("brew")
uid = os.getuid()

operatorData = get_operatorData()

from commands.mac.mac_install_cmds import update_output

def edit_sites_available():
    text = [
        '',
    ]
    text_str = ''.join(text)
    with open(f"/tmp/sonode_sites_avail", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", f"/tmp/sonode_sites_avail", f"/usr/local/etc/nginx/sites-available/sonode"],
        ["sudo", "-S", "chmod", "644", f"/usr/local/etc/nginx/sites-available/sonode"],
    ]

def edit_supervisor():
    # text = [
    # '',
    # ]
    # text_str = ''.join(text)
    # with open("/tmp/django_rq.conf", "w") as temp_file:
    #     temp_file.write(text_str)
    # subprocess.run(["sudo", "-S", "mv", "/tmp/django_rq.conf", "/etc/supervisor/conf.d/django_rq.conf"])
    # subprocess.run(["sudo", "-S", "chmod", "644", "/etc/supervisor/conf.d/django_rq.conf"])
    # # subprocess.run(["sudo", "-S", "systemctl", "daemon-reload"])
    print('-edit_supervisor')
    x = '''sudo rm /etc/supervisor/conf.d/django_rq.conf'''
    # subprocess.run()
    # file_path = '/etc/supervisor/conf.d/django_rq.conf'

    # os.remove(file_path)


def config_supervisor(install=True, output=None):
    print('-config_supervisor')
    text = [
        ''
    ]
    text_str = ''.join(text)
    with open("/tmp/supervisord.conf", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/supervisord.conf", f"/Users/{username}/Sonet/.data/supervisor/supervisord.conf"],
    ]
    if install:
        systemPass = fetch_secure_item('sysPass')
        for cmd in commands:
            Clock.schedule_once(lambda dt, line=cmd: update_output(line, output))
            result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
            if result.returncode == 0:
                content = f"supervisor configured successfully:\n{result.stdout}"
                Clock.schedule_once(lambda dt, line=content: update_output(line, output))
            else:
                content = f"Error configuring supervisor:\n{result.stderr}"
                Clock.schedule_once(lambda dt, line=content: update_output(line, output))
                raise content
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()


def config_gunicorn(install=True, output=None):
    print('-config_supervisor')
    text = [
        ''
    ]
    text_str = ''.join(text)
    with open("/tmp/gunicorn_start.sh", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/gunicorn_start.sh", f"/Users/{username}/Sonet/.data/supervisor/gunicorn_start.sh"],
    ]
    if install:
        systemPass = fetch_secure_item('sysPass')
        for cmd in commands:
            Clock.schedule_once(lambda dt, line=cmd: update_output(line, output))
            result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
            if result.returncode == 0:
                content = f"gunicorn configured successfully:\n{result.stdout}"
                Clock.schedule_once(lambda dt, line=content: update_output(line, output))
            else:
                content = f"Error configuring gunicorn:\n{result.stderr}"
                Clock.schedule_once(lambda dt, line=content: update_output(line, output))
                raise content
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()

def config_nginx(install=True, output=None):
    text = [
        ''
    ]
    text_str = ''.join(text)
    with open("/tmp/SoNodeServer.conf", "w") as temp_file:
        temp_file.write(text_str)
    commands = [
        ["sudo", "-S", "mv", "/tmp/SoNodeServer.conf", "/opt/homebrew/etc/nginx/servers/SoNodeServer.conf"],
    ]
    if install:
        systemPass = fetch_secure_item('sysPass')
        for cmd in commands:
            Clock.schedule_once(lambda dt, line=cmd: update_output(line, output))
            result = subprocess.run(cmd, input=systemPass, text=True, capture_output=True)
            if result.returncode == 0:
                content = f"Nginx configured successfully\n{result.stdout}"
                Clock.schedule_once(lambda dt, line=content: update_output(line, output))
            else:
                content = f"Error configuring Nginx:\n{result.stderr}"
                Clock.schedule_once(lambda dt, line=content: update_output(line, output))
                raise content
    else:
        from ops import CommandRunner
        import threading
        command_runner = CommandRunner(None, commands, None, None, special_commands)
        threading.Thread(target=command_runner.run_commands).start()

remove_for_quick_uninstall = [
    ["sudo", "-S", "rm", "-r", homepath + "/Sonet"]
]

remove_to_save_database = [
    ["sudo", "-S", "-i", "-u", username, "psql", "-c", "DROP DATABASE so_data;"],
    [brew_path, 'uninstall', '--force', 'postgresql'],
]


special_commands = [
    {'cmd':'config_gunicorn'},
    {'cmd':'config_nginx'},
    {'cmd':'config_supervisor'},
]

action_cmds = [
    ["sudo", "-S", f"/Users/{username}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "crontab", "remove"],
    ['/opt/homebrew/bin/supervisorctl', '-c', f'/Users/{username}/Sonet/.data/supervisor/supervisord.conf', 'stop', 'all'],
    ['launchctl', 'bootout', f'gui/{uid}', f'/Users/{username}/Library/LaunchAgents/com.sonet.supervisor.plist'],
    ['sudo', '-S', 'pkill', '-f', 'supervisord'],
    ['sudo', '-S', 'pkill', '-f', 'gunicorn'],
    ['sudo', '-S', 'pkill', '-f', 'nginx'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisor.sock'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/supervisord.pid'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/nginx.pid'],
    ['/bin/rm', '-f', f'/Users/{username}/Sonet/.data/supervisor/gunicorn.sock'],
    [brew_path, 'services', 'stop', 'postgresql'],
    ['run_command', 'config_gunicorn'],
    ['run_command', 'config_nginx'],
    ['run_command', 'config_supervisor'],
    ["sudo", "-S", "-i", "-u", username, "psql", "-c", "DROP DATABASE so_data;"],
    [brew_path, 'autoremove'],
    [brew_path, 'cleanup'],
    # # consider not removing this folder, might want to save operatorData.json
    # # ["sudo", "-S", "rm", "-r", homepath + "/Sonet"],
    ['echo', 'Finished!'],



]