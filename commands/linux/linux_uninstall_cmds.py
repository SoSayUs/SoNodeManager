
import subprocess
import getpass
from os.path import expanduser

from ..utils import get_operatorData, get_package_manager


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)


package_manager = get_package_manager()
if package_manager:
    print(f"Detected package manager: {package_manager}")
else:
    print("Could not detect package manager.")


operatorData = get_operatorData()
port = ''
try:
    if 'local_nodeId' in operatorData:
        node_id = operatorData['local_nodeId']
        node_data = operatorData['myNodes'][operatorData['local_nodeId']]
        port = node_data['settings']['port']
except:
    pass

def write_gunicorn_socket():
    print('-write_gunicorn_socket')
    text = [
        '',
    ]
    text_str = ''.join(text)
    with open("/tmp/gunicorn.socket", "w") as temp_file:
        temp_file.write(text_str)
    subprocess.run(["sudo", "-S", "mv", "/tmp/gunicorn.socket", "/etc/systemd/system/gunicorn.socket"])
    subprocess.run(["sudo", "-S", "chmod", "644", "/etc/systemd/system/gunicorn.socket"])

def write_gunicorn_service():
    print('-write_gunicorn_service')
    text = [ 
        '',
    ]
    text_str = ''.join(text)
    with open("/tmp/gunicorn.service", "w") as temp_file:
        temp_file.write(text_str)
    subprocess.run(["sudo", "-S", "mv", "/tmp/gunicorn.service", "/etc/systemd/system/gunicorn.service"])
    subprocess.run(["sudo", "-S", "chmod", "644", "/etc/systemd/system/gunicorn.service"])

def edit_sites_available():
    print('-edit_sites_available')
    text = [
        '',
    ]
    text_str = ''.join(text)
    with open("/tmp/sonode_sites_avail", "w") as temp_file:
        temp_file.write(text_str)
    subprocess.run(["sudo", "-S", "mv", "/tmp/sonode_sites_avail", "/etc/nginx/sites-available/sonode"])
    subprocess.run(["sudo", "-S", "chmod", "644", "/etc/nginx/sites-available/sonode"])

def edit_supervisor():
    print('-edit_supervisor')
    x = '''sudo rm /etc/supervisor/conf.d/django_rq.conf'''

remove_for_quick_uninstall = [
    ["sudo", "-S", "rm", "-r", homepath + "/Sonet/SoNodeServer"]
]

remove_to_save_database = [
    ["sudo", "-S", "-i", "-u", "postgres", "psql", "-c", "DROP DATABASE so_data;"],
    ["echo 'y' | sudo -S apt purge postgresql postgresql-contrib"],
]

special_commands = [
    {'cmd':'write_gunicorn_socket'},
    {'cmd':'write_gunicorn_service'},
    {'cmd':'edit_sites_available'},
    {'cmd':'edit_supervisor'},
]

action_cmds = [
    ["sudo", "-S", "echo", "uninstalling"],
    ["sudo", "-S", "ufw", "delete", "allow", port],
    ["sudo", "-S", "systemctl", "stop", "gunicorn.socket"],
    ["sudo", "-S", "systemctl", "stop", "gunicorn"],
    ["sudo", "-S", "systemctl", "stop", "nginx"],
    ['sudo', "-S", 'systemctl', 'disable', 'nginx'],
    ["sudo", "-S", "supervisorctl", "reload"],
    ['run_command', 'write_gunicorn_socket'],
    ['run_command', 'write_gunicorn_service'],
    ['run_command', 'edit_sites_available'],
    # ['run_command', 'edit_supervisor'],
    ['sudo', 'rm', '/etc/supervisor/conf.d/django_rq.conf'],
    ["sudo", "-S", "-i", "-u", "postgres", "psql", "-c", "DROP DATABASE so_data;"],
    ['sudo', '-S', 'systemctl', 'stop', 'postgresql'],
]

if package_manager == 'dnf':
    action_cmds += [
        ['sudo', '-S', 'dnf', 'remove', '-y', 'postgresql'],
        ['sudo', '-S', 'systemctl', 'stop', 'redis-server'],
        ['sudo', '-S', 'dnf', 'remove', '-y', 'redis-server'],
        ['sudo', '-S', 'dnf', 'remove', '-y', 'nginx'],
        ['sudo', '-S', 'dnf', 'remove', '-y', 'supervisor'],

        # sudo rm -rf /etc/postgresql /var/lib/pgsql /var/log/postgresql /etc/redis /etc/nginx /etc/supervisord.conf /var/log/redis /var/log/nginx /var/log/supervisor

        # consider not removing this folder, might want to save operatorData.json
        # ["sudo", "-S", "rm", "-r", homepath + "/Sonet"],
        ["sudo", "-S", "systemctl", "daemon-reload"],
        ['sudo', '-S', 'rm', f'/home/{username}/Sonet/.data/special/settings.py'],
        ['sudo', '-S', 'dnf', 'autoremove', '-y'],
        ['echo', 'Finished!'],
    ]
elif package_manager == 'apt':
    action_cmds += [
        ["echo 'y' | sudo -S apt purge postgresql postgresql-contrib"],
        ['sudo', '-S', 'systemctl', 'stop', 'redis-server'],
        ["echo 'y' | sudo -S apt purge redis-server"],
        ["echo 'y' | sudo -S apt purge libpq-dev nginx"],
        ["echo 'y' | sudo -S apt purge supervisor"],
        # consider not removing this folder, might want to save operatorData.json
        # ["sudo", "-S", "rm", "-r", homepath + "/Sonet"],
        ["sudo", "-S", "systemctl", "daemon-reload"],
        ['sudo', '-S', 'rm', f'/home/{username}/Sonet/.data/special/settings.py'],
        ['sudo', '-S', 'apt', 'autoremove', '-y'],
        ['echo', 'Finished!'],
    ]


