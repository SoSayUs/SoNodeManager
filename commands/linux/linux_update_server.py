

import os
import subprocess
import getpass
from os.path import expanduser

from ..utils import get_operatorData, get_package_manager


username = getpass.getuser()
# print(username)
homepath = expanduser("~")
# print(homepath)

package_manager = get_package_manager()


def hardware_check(output=None):
    from commands.utils import run_hardware_test
    if not run_hardware_test(output=output):
        raise Exception('Failed hardware check')

def run_update_repo(output=None, remote_cmd=False):
    from commands.utils import pull_git_server, update_output
    if not pull_git_server(output=output):
        update_output('\n\n', output)
        raise Exception('Device is up to date')

def install_cloudflared_old(output=None, remote_cmd=False):
    import distro

    os_id = distro.id()
    print(f"Detected OS: {os_id}")
    os_id = distro.id()
    if os_id in ['debian', 'ubuntu']:
        commands = [
            "sudo mkdir -p --mode=0755 /usr/share/keyrings",
            "curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null",
            "echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list",
            "sudo apt-get update",
            "sudo apt-get install -y cloudflared"
        ]
    elif os_id == 'fedora':
        
        import subprocess
        import urllib.request
        import os

        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm"
        rpm_path = "/tmp/cloudflared.rpm"

        print(f"Downloading cloudflared from {url}...")
        urllib.request.urlretrieve(url, rpm_path)
        print("Download complete.")

        commands = [
            [f"sudo dnf install -y {rpm_path}"],
            ["cloudflared", "--version"]
            ]
    for cmd in commands:
        print(cmd)
        try:
            r = subprocess.run(
                cmd,
                check=True,
                shell=True,
                capture_output=True
            )
            print('r',r)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else "No stderr output"
            print('error_msg',error_msg)

def restart_cloudflare_service(output=None, remote_cmd=False):
    print('-run_activate_cloudflare')
    import yaml
    from pathlib import Path

    config_path = Path.home() / "Sonet" / ".data" / "cloudflare_registration" / "config.yml"
    if config_path.exists():

        USER = os.getenv("USER")
        CONFIG_PATH = f"/home/{USER}/Sonet/.data/cloudflare_registration/config.yml"

        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)

        tunnel_name = config.get("tunnel")
        if not tunnel_name:
            raise ValueError("Missing 'tunnel:' entry in config.yml")

        SERVICE_NAME = f"cloudflared-{tunnel_name}.service"

        from commands.utils import fetch_secure_item
        systemPass = fetch_secure_item('sysPass')
        subprocess.run(["sudo", "-S", "systemctl", "restart", SERVICE_NAME], input=systemPass + "\n", text=True)
        print(f"Restarted: {SERVICE_NAME}")

def run_adjust_settings_update(option=None, remote_cmd=False):
    print('-run_adjust_settings update node', option)
    from commands.utils import adjust_settings
    operatorData = get_operatorData()
    if 'local_nodeId' in operatorData:
        node_data = operatorData['myNodes'][operatorData['local_nodeId']]
        adjust_settings(nodeData=node_data)

def pause(remote_cmd=False):
    print('pausing')
    import time
    time.sleep(6)

def special_job(output=None, remote_cmd=False):
    # print('-special_job')
    from .linux_install_cmds import edit_supervisor
    edit_supervisor(install=False, output=output, remote_cmd=remote_cmd)
    pass

special_commands = [
    {'cmd':'hardware_check', 'reqs':'output_display'},
    {'cmd':'run_adjust_settings_update', 'reqs':'None'},
    {'cmd':'restart_cloudflare_service', 'reqs':'output_display'},
    {'cmd':'special_job', 'reqs':'output_display'},
    {'cmd':'run_update_repo', 'reqs':'output_display'},
    {'cmd':'pause'},
]

action_cmds = [
    ['echo','this is an update check'],
    ['run_command', 'run_update_repo'],
    ['run_command', 'special_job'],
    ['run_command', 'run_adjust_settings_update'],
    ["sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "migrate"],
    ['run_command', 'run_adjust_settings_update'], # seemed to need a second instance after adding tor to supervisor - was causing nginx restart issue
    ["raise_if_error", "sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "check"],
    ["raise_if_error", "sudo", "-S", f"{homepath}/Sonet/.data/env/bin/python3", f"{homepath}/Sonet/SoNodeServer/manage.py", "collectstatic", "--noinput"],
    ['run_command', 'restart_cloudflare_service'],
    ["sudo", "-S", "supervisorctl", "reread"],
    ["sudo", "-S", "supervisorctl", "update"],
    ["sudo", "-S", "supervisorctl", "reload"],
    # ["sudo", "-S", 'semanage', 'fcontext', '-a', '-t', 'httpd_config_t', f"/etc/nginx/sites-available/sonode"],
    # ["sudo", "-S", 'restorecon', '-v', f"/etc/nginx/sites-available/sonode"],
    ["sudo", "-S", "systemctl", "daemon-reexec"],
    ["sudo", "-S", "systemctl", "daemon-reload"],
    ['echo', 'Rebooting...'],
    ["sudo", "-S", "systemctl", "restart", "gunicorn"],
    ["sudo", "-S", "systemctl", "restart", "nginx"],

    # sudo apt install unattended-upgrades
    # sudo apt update
    # sudo apt upgrade
    # sudo apt autoremove
    # [ -f /var/run/reboot-required ] && echo "Reboot needed" || echo "No reboot needed"

]

    

